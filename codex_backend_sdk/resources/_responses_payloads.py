"""Internal builders and collectors for the Codex Responses resource."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Optional

import requests
from pydantic import BaseModel

from .._exceptions import APIConnectionError, APIError, APIResponseValidationError
from .._models import (
    CodexBaseModel,
    Response,
    ResponseFormatJsonSchema,
    ResponseStreamEvent,
    ResponseUsage,
    ServiceTier,
)
from .._utils import (
    _UNSET,
    CodexBackendUnsupportedParameterError,
    _default,
    _is_given,
    _jsonable,
)


_SUPPORTED_CREATE_SERVICE_TIERS = frozenset({"default", "priority"})
_SUPPORTED_CREATE_REASONING_CONTEXTS = frozenset({"current_turn", "all_turns"})


class ResponsesCreateRequest(CodexBaseModel):
    model: str
    instructions: Optional[str]
    input: list[dict[str, Any]]
    include: list[str]
    parallel_tool_calls: bool
    prompt_cache_key: Optional[str]
    reasoning: Any
    service_tier: Optional[ServiceTier]
    text: Any
    tool_choice: Any
    tools: list[dict[str, Any]]
    payload: dict[str, Any]

    @classmethod
    def from_openai_params(
        cls,
        *,
        client_defaults: dict[str, Any],
        **params: Any,
    ) -> "ResponsesCreateRequest":
        input_items = normalize_input(params["input"])
        tools = normalize_tools(params["tools"])
        include = (
            []
            if not _is_given(params["include"]) or params["include"] is None
            else list(params["include"])
        )
        reasoning = None if not _is_given(params["reasoning"]) else params["reasoning"]
        text = None if not _is_given(params["text"]) else params["text"]
        tool_choice_given = _is_given(params["tool_choice"])
        tool_choice = params["tool_choice"] if tool_choice_given else (
            "auto" if tools else "none"
        )
        if tool_choice_given or tools:
            _validate_tool_choice(tool_choice, tools)
        parallel_tool_calls = bool(_default(params["parallel_tool_calls"], False))
        instructions = (
            params["instructions"]
            if _is_given(params["instructions"])
            else client_defaults["instructions"] or ""
        )

        payload = {
            "model": _default(params["model"], client_defaults["model"]),
            "instructions": instructions,
            "input": input_items,
            "tools": tools,
            "tool_choice": tool_choice,
            "parallel_tool_calls": parallel_tool_calls,
            "store": False,
            "stream": True,
            "include": include,
        }

        prompt_cache_key = (
            None if not _is_given(params["prompt_cache_key"]) else params["prompt_cache_key"]
        )
        service_tier = _validate_create_service_tier(params["service_tier"])
        if prompt_cache_key is not None:
            payload["prompt_cache_key"] = prompt_cache_key
        if service_tier is not None:
            payload["service_tier"] = service_tier
        if reasoning is not None:
            payload["reasoning"] = _normalize_create_reasoning(reasoning)
        if text is not None:
            payload["text"] = normalize_text(text)

        return cls(
            model=payload["model"],
            instructions=payload["instructions"],
            input=input_items,
            include=include,
            parallel_tool_calls=payload["parallel_tool_calls"],
            prompt_cache_key=prompt_cache_key,
            reasoning=payload.get("reasoning"),
            service_tier=service_tier,
            text=payload.get("text"),
            tool_choice=payload["tool_choice"],
            tools=tools,
            payload=payload,
        )


def collect_response(
    events: Iterable[ResponseStreamEvent],
    *,
    http_response: requests.Response,
) -> Response:
    terminal: Optional[dict[str, Any]] = None

    for event in events:
        if event.type in {
            "response.completed",
            "response.failed",
            "response.incomplete",
        }:
            if terminal is not None:
                raise APIResponseValidationError(
                    http_response,
                    body=None,
                    message="Response stream contained more than one terminal event.",
                )
            terminal = _event_response_dict(event)
            if terminal is None:
                raise APIResponseValidationError(
                    http_response,
                    body=None,
                    message="Terminal response event did not contain a Response object.",
                )
        elif event.type == "error":
            body = getattr(event, "error", None)
            if not isinstance(body, dict):
                body = {
                    key: value
                    for key in ("code", "message", "param")
                    if (value := getattr(event, key, None)) is not None
                }
            raise APIError(
                str(body.get("message", "Response stream failed.")),
                _prepared_request(http_response),
                body=body,
            )

    if terminal is None:
        raise APIConnectionError(
            message="Response stream ended without a terminal response event.",
            request=_prepared_request(http_response),
        )
    return Response.model_validate(terminal)


def _validate_create_service_tier(value: Any) -> Optional[ServiceTier]:
    if not _is_given(value) or value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("service_tier must be 'default' or 'priority'")
    if value not in _SUPPORTED_CREATE_SERVICE_TIERS:
        raise CodexBackendUnsupportedParameterError(
            f"This SDK does not support service_tier={value!r} for ChatGPT Codex "
            "Responses; use 'default', 'priority', or omit it."
        )
    return value


def _normalize_create_reasoning(reasoning: Any) -> dict[str, Any]:
    normalized = normalize_reasoning(reasoning)
    context = normalized.get("context")
    if context is not None and not isinstance(context, str):
        raise TypeError("reasoning.context must be 'current_turn' or 'all_turns'")
    if context is not None and context not in _SUPPORTED_CREATE_REASONING_CONTEXTS:
        raise CodexBackendUnsupportedParameterError(
            f"This SDK does not support reasoning.context={context!r} for ChatGPT "
            "Codex Responses; use 'current_turn', 'all_turns', or omit it."
        )
    return normalized


def normalize_input(input_value: Any) -> list[dict[str, Any]]:
    if not _is_given(input_value) or input_value is None:
        return []
    if isinstance(input_value, str):
        return [_message("user", [{"type": "input_text", "text": input_value}])]
    if isinstance(input_value, list):
        return [normalize_input_item(item) for item in input_value]
    return [normalize_input_item(input_value)]


def normalize_input_item(item: Any) -> dict[str, Any]:
    raw = _as_dict(item)
    if raw.get("type") and raw.get("type") != "message":
        return raw
    if "role" not in raw:
        return raw

    role = raw["role"]
    content = raw.get("content", [])
    if isinstance(content, str):
        content_type = "output_text" if role == "assistant" else "input_text"
        content = [{"type": content_type, "text": content}]
    elif isinstance(content, list):
        content = [
            {"type": "input_text", "text": part} if isinstance(part, str) else part
            for part in content
        ]
    normalized = _message(role, content)
    for field in ("id", "status", "phase"):
        if field in raw:
            normalized[field] = raw[field]
    return normalized


def normalize_tools(tools: Any) -> list[dict[str, Any]]:
    if not _is_given(tools) or tools is None:
        return []
    normalized = [_as_dict(tool) for tool in tools]
    for tool in normalized:
        if tool.get("type") != "function":
            raise ValueError(
                "The agent-safe SDK permits only caller-executed function tools; "
                "hosted, web-search, computer-use, and MCP tools are not allowed."
            )
        if not isinstance(tool.get("name"), str) or not tool["name"]:
            raise ValueError("Every function tool must have a non-empty `name`.")
        parameters = tool.get("parameters")
        if parameters is not None and not isinstance(parameters, dict):
            raise TypeError("Function tool `parameters` must be a JSON-schema object.")
    return normalized


def _validate_tool_choice(tool_choice: Any, tools: list[dict[str, Any]]) -> None:
    if isinstance(tool_choice, str) and tool_choice in {"auto", "none", "required"}:
        return
    choice = _as_dict(tool_choice)
    if choice.get("type") != "function":
        raise ValueError("The agent-safe SDK permits only function tool choices.")
    name = choice.get("name")
    available_names = {tool["name"] for tool in tools}
    if not isinstance(name, str) or name not in available_names:
        raise ValueError("Function tool choice must name one of the supplied tools.")


def normalize_reasoning(reasoning: Any) -> dict[str, Any]:
    reasoning = _jsonable(reasoning)
    if isinstance(reasoning, dict):
        return {key: value for key, value in reasoning.items() if value is not None}
    return {
        key: value
        for key in ("effort", "summary", "context")
        if (value := getattr(reasoning, key, None)) is not None
    }


def normalize_text(text: Any) -> dict[str, Any]:
    return _as_dict(text)


def merge_text_format(text: Any, fmt: ResponseFormatJsonSchema) -> dict[str, Any]:
    if not _is_given(text) or text is None:
        text_dict: dict[str, Any] = {}
    else:
        text_dict = normalize_text(text)
    if text_dict.get("format") is not None:
        raise TypeError("Cannot pass both text_format and text.format.")
    text_dict["format"] = fmt.model_dump(mode="json", by_alias=True, exclude_none=True)
    return text_dict


def pydantic_to_format(model_class: type[Any]) -> ResponseFormatJsonSchema:
    try:
        schema = model_class.model_json_schema()
        model_class.model_validate_json
    except AttributeError:
        raise TypeError("responses.parse() requires a Pydantic BaseModel class.") from None

    schema = _ensure_strict_schema(schema)
    return ResponseFormatJsonSchema(
        name=getattr(model_class, "__name__", "output"),
        schema=schema,
        strict=True,
    )


def _event_response_dict(event: ResponseStreamEvent) -> Optional[dict[str, Any]]:
    response = getattr(event, "response", None)
    if isinstance(response, BaseModel):
        return response.model_dump()
    return response if isinstance(response, dict) else None


def _message(role: str, content: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "message", "role": role, "content": content}


def _as_dict(value: Any) -> dict[str, Any]:
    value = _jsonable(value)
    if isinstance(value, dict):
        return value
    return dict(value)


def _ensure_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    schema = dict(schema)
    if schema.get("type") == "object":
        schema.setdefault("additionalProperties", False)
        props = schema.get("properties")
        if isinstance(props, dict):
            schema["properties"] = {
                key: _ensure_strict_schema(value) if isinstance(value, dict) else value
                for key, value in props.items()
            }
    items = schema.get("items")
    if isinstance(items, dict):
        schema["items"] = _ensure_strict_schema(items)
    for key in ("anyOf", "oneOf", "allOf"):
        variants = schema.get(key)
        if isinstance(variants, list):
            schema[key] = [
                _ensure_strict_schema(value) if isinstance(value, dict) else value
                for value in variants
            ]
    defs = schema.get("$defs")
    if isinstance(defs, dict):
        schema["$defs"] = {
            key: _ensure_strict_schema(value) if isinstance(value, dict) else value
            for key, value in defs.items()
        }
    return schema


def _usage_from_backend(raw: Any) -> Optional[ResponseUsage]:
    if raw is None:
        return None
    return ResponseUsage.model_validate(raw)


def _prepared_request(response: requests.Response) -> requests.PreparedRequest:
    if response.request is None:
        return requests.Request(
            "POST",
            response.url
            or "https://chatgpt.com/backend-api/codex/responses",
        ).prepare()
    return response.request
