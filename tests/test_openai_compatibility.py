import inspect
from typing import Any, Union, get_args, get_type_hints

import pytest

from codex_backend_sdk import (
    CodexBackendUnsupportedParameterError,
    CodexClient,
    OpenAI,
    Reasoning,
    ReasoningContext,
    Response,
    ResponseStreamEvent,
    ServiceTier,
)
from codex_backend_sdk.resources.responses import Responses


def test_openai_remains_the_primary_compatible_client_alias():
    assert OpenAI is CodexClient


def test_primary_client_keeps_official_timeout_and_retry_keyword_names():
    parameters = inspect.signature(OpenAI).parameters

    assert "timeout" in parameters
    assert "max_retries" in parameters


def test_primary_client_defaults_to_explicit_gpt_5_6_sol_model_id():
    parameters = inspect.signature(OpenAI).parameters

    assert parameters["model"].default == "gpt-5.6-sol"
    assert OpenAI()._defaults["model"] == "gpt-5.6-sol"


def test_responses_create_keeps_supported_official_keyword_names():
    parameters = inspect.signature(Responses.create).parameters
    expected = {
        "include",
        "input",
        "instructions",
        "max_output_tokens",
        "model",
        "parallel_tool_calls",
        "previous_response_id",
        "reasoning",
        "service_tier",
        "store",
        "stream",
        "text",
        "tool_choice",
        "tools",
        "timeout",
    }

    assert expected <= set(parameters)


def test_responses_input_annotation_matches_the_validated_top_level_shapes():
    expected = Union[str, list[Any]]

    assert get_type_hints(Responses.create)["input"] == expected
    assert get_type_hints(Responses.parse)["input"] == expected


def test_service_tier_type_matches_the_verified_backend_subset():
    assert get_args(ServiceTier) == ("default", "priority")


def test_reasoning_context_uses_the_verified_official_field_shape():
    assert get_args(ReasoningContext) == ("current_turn", "all_turns")
    reasoning = Reasoning(context="all_turns", effort="low")

    assert reasoning.context == "all_turns"
    assert reasoning.effort == "low"


def test_nonstandard_custody_lifecycle_is_not_on_primary_surface():
    client = OpenAI()

    for name in ("continue_from", "prepare", "send", "validate"):
        assert not hasattr(client.responses, name)
    assert not hasattr(client, "capabilities")
    assert "receipt" not in Response.model_fields
    assert "receipt" not in ResponseStreamEvent.model_fields


def test_max_output_tokens_remains_an_explicit_local_error():
    client = OpenAI()

    with pytest.raises(CodexBackendUnsupportedParameterError, match="max_output_tokens"):
        client.responses.create(input="Hello", max_output_tokens=32)

    assert client.authenticated is False
