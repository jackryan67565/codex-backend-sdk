"""Pydantic response models exposed by the SDK."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

ReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh"]
ReasoningSummary = Literal["concise", "detailed", "auto"]
ReasoningContext = Literal["current_turn", "all_turns"]
Verbosity = Literal["low", "medium", "high"]
ServiceTier = Literal["default", "priority"]
ParsedT = TypeVar("ParsedT")


class CodexBaseModel(BaseModel):
    """Pydantic base with convenience helpers matching openai-python objects."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def to_dict(
        self,
        *,
        mode: Literal["json", "python"] = "python",
        use_api_names: bool = True,
        exclude_unset: bool = True,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        warnings: bool = True,
    ) -> dict[str, Any]:
        return self.model_dump(
            mode=mode,
            by_alias=use_api_names,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            warnings=warnings,
        )

    def to_json(
        self,
        *,
        use_api_names: bool = True,
        exclude_unset: bool = True,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        warnings: bool = True,
    ) -> str:
        return self.model_dump_json(
            by_alias=use_api_names,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            warnings=warnings,
        )

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class Reasoning(CodexBaseModel):
    context: Optional[ReasoningContext] = None
    effort: Optional[ReasoningEffort] = None
    summary: Optional[ReasoningSummary] = None


class TokenDetails(CodexBaseModel):
    cached_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None


class ResponseUsage(CodexBaseModel):
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    input_tokens_details: Optional[TokenDetails] = None
    output_tokens_details: Optional[TokenDetails] = None


class ResponseFormatJsonSchema(CodexBaseModel):
    type: Literal["json_schema"] = "json_schema"
    name: str
    schema_: dict[str, Any] = Field(alias="schema")
    strict: Optional[bool] = None
    description: Optional[str] = None


class Response(CodexBaseModel):
    id: Optional[str] = None
    created_at: Optional[float] = None
    error: Optional[dict[str, Any]] = None
    incomplete_details: Optional[dict[str, Any]] = None
    instructions: Any = None
    metadata: Optional[dict[str, Any]] = None
    model: Optional[str] = None
    object: Optional[Literal["response"]] = None
    output: Optional[list[dict[str, Any]]] = None
    parallel_tool_calls: Optional[bool] = None
    temperature: Optional[float] = None
    tool_choice: Any = None
    tools: Optional[list[dict[str, Any]]] = None
    top_p: Optional[float] = None
    background: Optional[bool] = None
    completed_at: Optional[float] = None
    conversation: Any = None
    max_output_tokens: Optional[int] = None
    max_tool_calls: Optional[int] = None
    previous_response_id: Optional[str] = None
    prompt: Any = None
    prompt_cache_key: Optional[str] = None
    prompt_cache_retention: Optional[str] = None
    reasoning: Optional[Reasoning] = None
    safety_identifier: Optional[str] = None
    service_tier: Optional[str] = None
    status: Optional[str] = None
    text: Any = None
    top_logprobs: Optional[int] = None
    truncation: Optional[str] = None
    usage: Optional[ResponseUsage] = None
    user: Optional[str] = None
    _request_id: Optional[str] = PrivateAttr(default=None)

    @property
    def output_text(self) -> str:
        texts: list[str] = []
        for output in self.output or []:
            if output.get("type") == "message":
                for content in output.get("content", []):
                    if content.get("type") == "output_text":
                        texts.append(content.get("text", ""))
        return "".join(texts)

    @property
    def reasoning_summary(self) -> str | None:
        texts: list[str] = []
        for output in self.output or []:
            if output.get("type") == "reasoning":
                for summary in output.get("summary", []):
                    if isinstance(summary, dict):
                        texts.append(summary.get("text", ""))
        return "\n".join(text for text in texts if text) or None

    @property
    def tool_calls(self) -> list[dict[str, Any]]:
        return [
            output
            for output in self.output or []
            if output.get("type") == "function_call"
        ]


class ParsedResponse(CodexBaseModel, Generic[ParsedT]):
    response: Response
    output_parsed: ParsedT

    @property
    def id(self) -> Optional[str]:
        return self.response.id

    @property
    def model(self) -> Optional[str]:
        return self.response.model

    @property
    def output(self) -> Optional[list[dict[str, Any]]]:
        return self.response.output

    @property
    def output_text(self) -> str:
        return self.response.output_text

    @property
    def status(self) -> Optional[str]:
        return self.response.status

    @property
    def usage(self) -> Optional[ResponseUsage]:
        return self.response.usage

    @property
    def reasoning(self) -> Optional[Reasoning]:
        return self.response.reasoning


class ResponseStreamEvent(CodexBaseModel):
    type: str


class Model(CodexBaseModel):
    id: str
    created: int = 0
    object: Literal["model"] = "model"
    owned_by: str = "openai"


class SyncPage(CodexBaseModel):
    object: Literal["list"] = "list"
    data: list[Any] = Field(default_factory=list)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self.data[key]
        return getattr(self, key)

    def has_next_page(self) -> bool:
        return False

    def next_page_info(self) -> None:
        return None


class CompactedResponse(CodexBaseModel):
    id: str
    object: str = "response.compacted"
    output: list[dict[str, Any]] = Field(default_factory=list)
    usage: Optional[ResponseUsage] = Field(default_factory=ResponseUsage)
