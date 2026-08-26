"""Responses resource."""

from __future__ import annotations

from collections.abc import Iterator
from functools import cached_property, wraps
from typing import TYPE_CHECKING, Any, Optional

from .._api_response import LegacyAPIResponse
from .._models import (
    CompactedResponse,
    ParsedResponse,
    Response,
    ResponseStreamEvent,
    ServiceTier,
)
from .._streaming import stream_response_events
from .._utils import (
    _UNSET,
    CodexBackendUnsupportedParameterError,
    _default,
    _is_given,
    _reject_backend_unsupported,
)
from ._responses_payloads import (
    ResponsesCreateRequest,
    _usage_from_backend,
    collect_response,
    merge_text_format,
    normalize_input_item,
    normalize_reasoning,
    normalize_text,
    normalize_tools,
    pydantic_to_format,
)

if TYPE_CHECKING:
    from .._client import CodexClient


class Responses:
    def __init__(self, client: CodexClient) -> None:
        self._client = client

    @cached_property
    def with_raw_response(self) -> "ResponsesWithRawResponse":
        """Return the official-compatible raw wrapper for Responses creation."""
        return ResponsesWithRawResponse(self)

    def create(
        self,
        *,
        background: Any = _UNSET,
        context_management: Any = _UNSET,
        conversation: Any = _UNSET,
        include: Any = _UNSET,
        input: Any = _UNSET,
        instructions: Any = _UNSET,
        max_output_tokens: Any = _UNSET,
        max_tool_calls: Any = _UNSET,
        metadata: Any = _UNSET,
        model: Any = _UNSET,
        parallel_tool_calls: Any = _UNSET,
        previous_response_id: Any = _UNSET,
        prompt: Any = _UNSET,
        prompt_cache_key: Any = _UNSET,
        prompt_cache_retention: Any = _UNSET,
        reasoning: Any = _UNSET,
        safety_identifier: Any = _UNSET,
        service_tier: Optional[ServiceTier] = _UNSET,
        store: Any = _UNSET,
        stream: Any = _UNSET,
        stream_options: Any = _UNSET,
        temperature: Any = _UNSET,
        text: Any = _UNSET,
        tool_choice: Any = _UNSET,
        tools: Any = _UNSET,
        top_logprobs: Any = _UNSET,
        top_p: Any = _UNSET,
        truncation: Any = _UNSET,
        user: Any = _UNSET,
        timeout: Any = _UNSET,
    ) -> Response | Iterator[ResponseStreamEvent]:
        params = dict(locals())
        params.pop("self")
        return self._create_raw_response(params).parse()

    def _create_raw_response(
        self,
        params: dict[str, Any],
    ) -> LegacyAPIResponse[Response | Iterator[ResponseStreamEvent]]:
        def value(name: str) -> Any:
            return params.get(name, _UNSET)

        _reject_backend_unsupported(
            background=value("background"),
            context_management=value("context_management"),
            conversation=value("conversation"),
            max_output_tokens=value("max_output_tokens"),
            max_tool_calls=value("max_tool_calls"),
            metadata=value("metadata"),
            previous_response_id=value("previous_response_id"),
            prompt=value("prompt"),
            prompt_cache_retention=value("prompt_cache_retention"),
            safety_identifier=value("safety_identifier"),
            stream_options=value("stream_options"),
            temperature=value("temperature"),
            top_logprobs=value("top_logprobs"),
            top_p=value("top_p"),
            truncation=value("truncation"),
            user=value("user"),
        )

        store = value("store")
        if _is_given(store) and store is not False:
            raise CodexBackendUnsupportedParameterError(
                "The Codex backend only accepts store=False."
            )

        request = ResponsesCreateRequest.from_openai_params(
            client_defaults=self._client._defaults,
            input=value("input"),
            include=value("include"),
            instructions=value("instructions"),
            model=value("model"),
            parallel_tool_calls=value("parallel_tool_calls"),
            prompt_cache_key=value("prompt_cache_key"),
            reasoning=value("reasoning"),
            service_tier=value("service_tier"),
            text=value("text"),
            tool_choice=value("tool_choice"),
            tools=value("tools"),
        )
        response = self._client._request_response(
            body=request.payload,
            stream=True,
            timeout=value("timeout"),
        )
        stream = value("stream")
        stream_enabled = bool(stream) if _is_given(stream) else False
        if not stream_enabled:
            # Eagerly buffer the body like openai-python's non-streaming raw
            # wrapper. The getattr keeps lightweight test transports usable.
            _ = getattr(response, "content", None)

        def parse() -> Response | Iterator[ResponseStreamEvent]:
            events = stream_response_events(response)
            if stream_enabled:
                return events
            return collect_response(events, http_response=response)

        return LegacyAPIResponse(
            raw=response,
            parser=parse,
            retries_taken=getattr(response, "_codex_retries_taken", 0),
        )

    def parse(
        self,
        *,
        text_format: type[Any],
        background: Any = _UNSET,
        context_management: Any = _UNSET,
        conversation: Any = _UNSET,
        include: Any = _UNSET,
        input: Any = _UNSET,
        instructions: Any = _UNSET,
        max_output_tokens: Any = _UNSET,
        max_tool_calls: Any = _UNSET,
        metadata: Any = _UNSET,
        model: Any = _UNSET,
        parallel_tool_calls: Any = _UNSET,
        previous_response_id: Any = _UNSET,
        prompt: Any = _UNSET,
        prompt_cache_key: Any = _UNSET,
        prompt_cache_retention: Any = _UNSET,
        reasoning: Any = _UNSET,
        safety_identifier: Any = _UNSET,
        service_tier: Optional[ServiceTier] = _UNSET,
        store: Any = _UNSET,
        stream_options: Any = _UNSET,
        temperature: Any = _UNSET,
        text: Any = _UNSET,
        tool_choice: Any = _UNSET,
        tools: Any = _UNSET,
        top_logprobs: Any = _UNSET,
        top_p: Any = _UNSET,
        truncation: Any = _UNSET,
        user: Any = _UNSET,
        timeout: Any = _UNSET,
    ) -> ParsedResponse[Any]:
        fmt = pydantic_to_format(text_format)
        response = self.create(
            background=background,
            context_management=context_management,
            conversation=conversation,
            include=include,
            input=input,
            instructions=instructions,
            max_output_tokens=max_output_tokens,
            max_tool_calls=max_tool_calls,
            metadata=metadata,
            model=model,
            parallel_tool_calls=parallel_tool_calls,
            previous_response_id=previous_response_id,
            prompt=prompt,
            prompt_cache_key=prompt_cache_key,
            prompt_cache_retention=prompt_cache_retention,
            reasoning=reasoning,
            safety_identifier=safety_identifier,
            service_tier=service_tier,
            store=store,
            stream=False,
            stream_options=stream_options,
            temperature=temperature,
            text=merge_text_format(text, fmt),
            tool_choice=tool_choice,
            tools=tools,
            top_logprobs=top_logprobs,
            top_p=top_p,
            truncation=truncation,
            user=user,
            timeout=timeout,
        )
        if not isinstance(response, Response):
            raise TypeError("responses.parse() expected a non-streaming Response")
        return ParsedResponse(
            response=response,
            output_parsed=text_format.model_validate_json(response.output_text),
        )

    def compact(
        self,
        *,
        input: list[dict[str, Any]],
        model: Any = _UNSET,
        instructions: Any = _UNSET,
        tools: Any = _UNSET,
        parallel_tool_calls: Any = _UNSET,
        reasoning: Any = _UNSET,
        service_tier: Any = _UNSET,
        prompt_cache_key: Any = _UNSET,
        text: Any = _UNSET,
    ) -> CompactedResponse:
        normalized_tools = normalize_tools(tools)
        payload = {
            "model": _default(model, self._client._defaults["model"]),
            "instructions": _default(instructions, self._client._defaults["instructions"]) or "",
            "input": [normalize_input_item(item) for item in input],
            "tools": normalized_tools,
            "parallel_tool_calls": (
                bool(_default(parallel_tool_calls, False)) if normalized_tools else False
            ),
        }
        if _is_given(reasoning) and reasoning is not None:
            payload["reasoning"] = normalize_reasoning(reasoning)
        if _is_given(service_tier) and service_tier is not None:
            payload["service_tier"] = service_tier
        if _is_given(prompt_cache_key) and prompt_cache_key is not None:
            payload["prompt_cache_key"] = prompt_cache_key
        if _is_given(text) and text is not None:
            payload["text"] = normalize_text(text)
        response = self._client._request_compaction(body=payload)
        try:
            data = response.json()
        finally:
            response.close()
        parsed = dict(data)
        parsed.setdefault("id", "")
        parsed.setdefault("object", "response.compacted")
        parsed.setdefault("output", [])
        parsed["usage"] = _usage_from_backend(data.get("usage"))
        return CompactedResponse.model_validate(parsed)


class ResponsesWithRawResponse:
    """Official-compatible raw wrapper for the supported create operation."""

    def __init__(self, responses: Responses) -> None:
        self._responses = responses

        @wraps(responses.create)
        def create(*args: Any, **kwargs: Any) -> LegacyAPIResponse[Any]:
            if args:
                raise TypeError("responses.create() accepts keyword arguments only")
            return responses._create_raw_response(kwargs)

        self.create = create
