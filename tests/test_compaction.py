"""Safe structural smoke test for the live compaction endpoint."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any

import pytest

from codex_backend_sdk import CompactedResponse, OpenAI


_MARKER = "LANTERN-4821"


def _matching_key_paths(value: Any, name: str, path: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key == name:
                matches.append(child_path)
            matches.extend(_matching_key_paths(item, name, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            matches.extend(_matching_key_paths(item, name, f"{path}[{index}]"))
    return matches


def _contains_text(value: Any, expected: str) -> bool:
    if isinstance(value, str):
        return expected in value
    if isinstance(value, dict):
        return any(_contains_text(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, expected) for item in value)
    return False


def _safe_compaction_report(compacted: CompactedResponse) -> dict[str, Any]:
    """Describe response structure without returning authenticated plaintext."""
    output = compacted.output
    compaction_items = [item for item in output if item.get("type") == "compaction"]
    message_items = [item for item in output if item.get("type") == "message"]
    encrypted_values = [
        item.get("encrypted_content")
        for item in compaction_items
        if isinstance(item.get("encrypted_content"), str)
    ]
    content_types = Counter(
        part.get("type", "<missing>")
        for item in message_items
        for part in item.get("content", [])
        if isinstance(part, dict)
    )
    top_level_fields = set(compacted.model_fields_set)
    top_level_fields.update((compacted.model_extra or {}).keys())

    usage = compacted.usage
    return {
        "top_level_fields": sorted(top_level_fields),
        "object": compacted.object,
        "output_item_count": len(output),
        "output_item_types": dict(sorted(Counter(
            item.get("type", "<missing>") for item in output
        ).items())),
        "compaction_item_count": len(compaction_items),
        "compaction_item_fields": [sorted(item) for item in compaction_items],
        "encrypted_content_lengths": [len(value) for value in encrypted_values],
        "encrypted_content_sha256": [
            hashlib.sha256(value.encode("utf-8")).hexdigest()
            for value in encrypted_values
        ],
        "retained_message_count": len(message_items),
        "retained_message_roles": dict(sorted(Counter(
            item.get("role", "<missing>") for item in message_items
        ).items())),
        "retained_content_types": dict(sorted(content_types.items())),
        "summary_key_paths": _matching_key_paths(
            compacted.model_dump(mode="python"), "summary"
        ),
        "usage": None if usage is None else {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        },
    }


def test_safe_compaction_report_excludes_ciphertext_and_plaintext():
    ciphertext = "opaque-secret-ciphertext"
    retained_text = "authenticated retained content"
    compacted = CompactedResponse(
        id="resp_test",
        object="response.compaction",
        output=[
            {
                "id": "msg_test",
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": retained_text}],
            },
            {
                "id": "cmp_test",
                "type": "compaction",
                "encrypted_content": ciphertext,
            },
        ],
        usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        extra_shape={"summary": "not included in report"},
    )

    report = _safe_compaction_report(compacted)
    serialized = json.dumps(report, sort_keys=True)

    assert ciphertext not in serialized
    assert retained_text not in serialized
    assert report["encrypted_content_lengths"] == [len(ciphertext)]
    assert report["summary_key_paths"] == ["$.extra_shape.summary"]


@pytest.mark.live
def test_live_compaction_endpoint_shape_and_continuation():
    """Probe compact output and replay it without printing response content."""
    history: list[dict[str, str]] = [
        {
            "role": "user",
            "content": f"For this smoke test, remember the exact marker {_MARKER}.",
        },
        {"role": "assistant", "content": "Marker recorded."},
    ]
    for index in range(1, 17):
        history.extend([
            {
                "role": "user",
                "content": f"Checkpoint {index}: retain the marker and answer ACK-{index}.",
            },
            {"role": "assistant", "content": f"ACK-{index}"},
        ])

    with OpenAI(max_retries=0).authenticate() as client:
        compacted = client.responses.compact(input=history)
        report = _safe_compaction_report(compacted)

        assert report["compaction_item_count"] >= 1
        assert report["encrypted_content_lengths"]
        assert all(length > 0 for length in report["encrypted_content_lengths"])

        marker_retained_in_plaintext = _contains_text(
            [item for item in compacted.output if item.get("type") != "compaction"],
            _MARKER,
        )
        continued = client.responses.create(
            input=[
                *compacted.output,
                {
                    "role": "user",
                    "content": "Return only the exact marker from the earliest instruction.",
                },
            ],
            store=False,
        )

    report["continuation"] = {
        "max_retries": 0,
        "marker_retained_in_plaintext": marker_retained_in_plaintext,
        "marker_recovered": _MARKER in continued.output_text,
        "status": continued.status,
        "usage": None if continued.usage is None else {
            "input_tokens": continued.usage.input_tokens,
            "output_tokens": continued.usage.output_tokens,
            "total_tokens": continued.usage.total_tokens,
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    assert report["continuation"]["marker_recovered"] is True
