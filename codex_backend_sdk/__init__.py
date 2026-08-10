"""Agent-safe, unofficial Python client for the ChatGPT Codex backend.

The public package intentionally exposes only stateless Responses and model
discovery. It does not export credential objects, raw transports, account data,
uploads, Realtime connection material, or state-changing ChatGPT resources.
"""

__version__ = "0.4.0"

from ._network import OpenAINetworkPolicyError
from .codex_client import (
    CodexBackendUnsupportedParameterError,
    CodexBaseModel,
    CodexClient,
    CompactedResponse,
    Model,
    OpenAI,
    ParsedResponse,
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
