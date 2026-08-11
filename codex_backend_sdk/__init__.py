"""Agent-safe, unofficial Python client for the ChatGPT Codex backend.

The public package intentionally exposes only stateless Responses and model
discovery. It does not export credential objects, raw transports, account data,
uploads, Realtime connection material, or state-changing ChatGPT resources.
"""

__version__ = "0.5.1"

from ._network import OpenAINetworkPolicyError
from .codex_client import (
    CodexBackendUnsupportedParameterError,
    CodexBaseModel,
    CodexClient,
    CompactedResponse,
    Model,
    OpenAI,
    ParsedResponse,
    Reasoning,
    ReasoningContext,
    ReasoningEffort,
    ReasoningSummary,
    Response,
    ResponseFormatJsonSchema,
    ResponseStreamEvent,
    ResponseUsage,
    ServiceTier,
    SyncPage,
    Verbosity,
    image_b64,
    image_url,
)

__all__ = [
    "CodexBackendUnsupportedParameterError",
    "CodexBaseModel",
    "CodexClient",
    "CompactedResponse",
    "Model",
    "OpenAI",
    "OpenAINetworkPolicyError",
    "ParsedResponse",
    "Reasoning",
    "ReasoningContext",
    "ReasoningEffort",
    "ReasoningSummary",
    "Response",
    "ResponseFormatJsonSchema",
    "ResponseStreamEvent",
    "ResponseUsage",
    "ServiceTier",
    "SyncPage",
    "Verbosity",
    "image_b64",
    "image_url",
]
