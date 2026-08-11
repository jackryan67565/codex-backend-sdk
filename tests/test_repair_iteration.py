"""Live smoke coverage for official Responses-shaped repair iteration."""

import json

import pytest

from codex_backend_sdk import OpenAI


pytestmark = pytest.mark.live

_INITIAL_INPUT = [{
    "role": "user",
    "content": (
        "Return JSON with one string field named source. The source must define "
        "digest_record(value), returning the SHA-256 hex digest of canonical JSON "
        "using sort_keys=True and separators=(',', ':'). Import os, hashlib, and "
        "json; os may remain unused. Do not use code fences."
    ),
}]
_ADMISSION_SCAR = {
    "role": "user",
    "content": (
        "Admission scar: rejected only because os is not allowed. Allowed imports "
        "are contextlib, hashlib, json, and sqlite3. Preserve behavior and remove os."
    ),
}
_TEXT = {
    "format": {
        "type": "json_schema",
        "name": "repair_submission",
        "schema": {
            "type": "object",
            "properties": {"source": {"type": "string"}},
            "required": ["source"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def test_structured_repair_via_standard_manual_replay():
    with OpenAI(model="gpt-5.4", max_retries=0).authenticate() as client:
        first = client.responses.create(
            input=_INITIAL_INPUT,
            reasoning={"effort": "low", "context": "current_turn"},
            store=False,
            text=_TEXT,
        )
        first_submission = json.loads(first.output_text)
        assert "import os" in first_submission["source"]
        assert first.reasoning is not None
        assert first.reasoning.context == "current_turn"

        reasoning_item = next(
            item for item in first.output if item.get("type") == "reasoning"
        )
        assistant_item = next(
            item for item in first.output if item.get("type") == "message"
        )
        assert reasoning_item.get("encrypted_content")
        assert assistant_item.get("phase") == "final_answer"

        corrective = client.responses.create(
            input=[*_INITIAL_INPUT, *first.output, _ADMISSION_SCAR],
            reasoning={"effort": "low", "context": "all_turns"},
            store=False,
            text=_TEXT,
        )
        corrected_submission = json.loads(corrective.output_text)

    assert "import os" not in corrected_submission["source"]
    assert corrective.reasoning is not None
    assert corrective.reasoning.context == "all_turns"
    assert first.usage.input_tokens_details.cached_tokens >= 0
    assert first.usage.output_tokens_details.reasoning_tokens >= 0
    assert corrective.usage.input_tokens_details.cached_tokens >= 0
    assert corrective.usage.output_tokens_details.reasoning_tokens >= 0
