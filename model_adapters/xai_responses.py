"""xAI Responses API adapter with CyberBroker-only response functions."""

from __future__ import annotations

import argparse
import importlib.metadata
import os
from typing import Any

from model_adapters.base import ModelRunContext
from model_adapters.openai_responses import (
    OpenAIResponsesAdapter,
    environment_int,
    run_start_indicator,
)
from scripts.validate_assessment import validate_assessment


XAI_BASE_URL = "https://api.x.ai/v1"


class XAIResponsesAdapter(OpenAIResponsesAdapter):
    provider_name = "xai"
    provider_label = "xAI"
    # xAI returns reasoning items directly; OpenAI's encrypted-content include
    # selector is provider-specific and is not requested from xAI.
    include_encrypted_reasoning = False
    include_request_metadata = False

    def final_schema(self, context: ModelRunContext) -> dict[str, Any]:
        status_entry = lambda statuses: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "status": {"type": "string", "enum": statuses},
            },
            "required": ["name", "status"],
        }
        assessment = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "schema_version": {"type": "string", "const": "1.0"},
                "incident_id": {"type": "string", "pattern": "^incident[0-9]{2}$"},
                "classification": {
                    "type": "string", "enum": ["malicious", "benign", "ambiguous"]
                },
                "incident_occurred": {"type": ["boolean", "null"]},
                "severity": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high", "critical", "undetermined"],
                },
                "accounts": {
                    "type": "array",
                    "items": status_entry([
                        "compromised", "misused", "attempted", "benign", "uncertain"
                    ]),
                },
                "hosts": {
                    "type": "array",
                    "items": status_entry(["compromised", "affected", "benign", "uncertain"]),
                },
                "network_indicators": {
                    "type": "array",
                    "items": status_entry(["malicious", "suspicious", "benign", "uncertain"]),
                },
                "attack_techniques": {
                    "type": "array", "items": {"type": "string"}
                },
            },
            "required": [
                "schema_version", "incident_id", "classification", "incident_occurred",
                "severity", "accounts", "hosts", "network_indicators", "attack_techniques",
            ],
        }
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "report_markdown": {"type": "string", "minLength": 1},
                "assessment": assessment,
            },
            "required": ["report_markdown", "assessment"],
        }

    @staticmethod
    def entries_to_map(entries: Any, field: str) -> dict[str, str]:
        if not isinstance(entries, list):
            raise ValueError(f"{field} must be an array")
        converted: dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"name", "status"}:
                raise ValueError(f"invalid {field} entry")
            name, status = entry["name"], entry["status"]
            if not isinstance(name, str) or not name or not isinstance(status, str):
                raise ValueError(f"invalid {field} entry values")
            if name in converted:
                raise ValueError(f"duplicate {field} entry: {name}")
            converted[name] = status
        return converted

    def parse_final(
        self, final: Any, context: ModelRunContext
    ) -> tuple[str, dict[str, Any]]:
        if not isinstance(final, dict) or set(final) != {"report_markdown", "assessment"}:
            raise ValueError("invalid final output envelope")
        report = final["report_markdown"]
        transport = final["assessment"]
        if not isinstance(report, str) or not report.strip():
            raise ValueError("incident report is empty")
        if not isinstance(transport, dict):
            raise ValueError("assessment must be an object")
        assessment = dict(transport)
        for field in ("accounts", "hosts", "network_indicators"):
            assessment[field] = self.entries_to_map(transport.get(field), field)
        validate_assessment(assessment, context.incident_id)
        return report, assessment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model")
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--max-action-calls", type=int)
    parser.add_argument("--evidence-byte-limit", type=int)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--reasoning-effort")
    args = parser.parse_args()
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        parser.error("XAI_API_KEY is required")
    context = ModelRunContext.from_environment()
    model = args.model or os.environ.get("XAI_MODEL") or context.model_id
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("install the pinned OpenAI SDK dependency") from error
    adapter = XAIResponsesAdapter(
        OpenAI(api_key=api_key, base_url=XAI_BASE_URL),
        model,
        args.max_output_tokens or environment_int("XAI_MAX_OUTPUT_TOKENS", 8000),
        args.max_action_calls if args.max_action_calls is not None else environment_int(
            "CYBERDEFENDER_MAX_ACTION_CALLS", 12
        ),
        args.evidence_byte_limit or environment_int(
            "CYBERDEFENDER_EVIDENCE_BYTE_LIMIT", 1_000_000
        ),
        args.temperature,
        args.reasoning_effort,
        importlib.metadata.version("openai"),
    )
    run_start_indicator(context)
    adapter.run(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
