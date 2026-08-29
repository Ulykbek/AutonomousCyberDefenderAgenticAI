"""DeepSeek Chat Completions adapter with CyberBroker-only response tools."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from copy import deepcopy
from typing import Any

from agent.broker_client import request_action
from model_adapters.base import ModelRunContext
from model_adapters.openai_responses import (
    TOOLS,
    atomic_text,
    evidence_prompt,
    final_output_schema,
    object_dump,
    run_start_indicator,
)
from scripts.validate_assessment import validate_assessment


DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def chat_tools() -> list[dict[str, Any]]:
    """Translate the provider-neutral response tools to Chat Completions format."""
    converted = []
    for tool in TOOLS:
        converted.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "strict": tool["strict"],
                "parameters": tool["parameters"],
            },
        })
    return converted


def value(value: Any, field: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(field, default)
    return getattr(value, field, default)


def assistant_message(message: Any) -> dict[str, Any]:
    """Preserve the assistant turn, including reasoning needed after tool calls."""
    if hasattr(message, "model_dump"):
        dumped = message.model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    result: dict[str, Any] = {
        "role": value(message, "role", "assistant"),
        "content": value(message, "content"),
    }
    reasoning = value(message, "reasoning_content")
    if reasoning is not None:
        result["reasoning_content"] = reasoning
    calls = value(message, "tool_calls")
    if calls:
        result["tool_calls"] = [tool_call_message(call) for call in calls]
    return result


def tool_call_message(call: Any) -> dict[str, Any]:
    if isinstance(call, dict):
        return call
    if hasattr(call, "model_dump"):
        dumped = call.model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    function = value(call, "function")
    return {
        "id": value(call, "id"),
        "type": value(call, "type", "function"),
        "function": {
            "name": value(function, "name"),
            "arguments": value(function, "arguments"),
        },
    }


class DeepSeekChatAdapter:
    provider_name = "deepseek"
    provider_label = "DeepSeek"
    max_format_repairs = 0
    final_via_tool = False
    unsupported_tool_schema_keywords: tuple[str, ...] = ()

    def __init__(
        self,
        client: Any,
        model: str,
        max_output_tokens: int = 8000,
        max_action_calls: int = 12,
        evidence_byte_limit: int = 1_000_000,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        sdk_version: str | None = None,
        request_extra_body: dict[str, Any] | None = None,
        final_tool_strict: bool = True,
    ):
        if not model:
            raise ValueError("model is required")
        if max_output_tokens < 1 or max_action_calls < 0 or evidence_byte_limit < 1:
            raise ValueError("adapter limits must be positive")
        self.client = client
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.max_action_calls = max_action_calls
        self.evidence_byte_limit = evidence_byte_limit
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.sdk_version = sdk_version
        self.request_extra_body = request_extra_body
        self.final_tool_strict = final_tool_strict

    def run(self, context: ModelRunContext) -> dict[str, Any]:
        if context.model_provider.casefold() != self.provider_name:
            raise ValueError(
                f"run provider is not {self.provider_label}: {context.model_provider}"
            )
        if context.model_id != self.model:
            raise ValueError(
                f"configured model {self.model!r} does not match manifest {context.model_id!r}"
            )
        schema = final_output_schema(context.assessment_schema_path)
        tools = chat_tools()
        if self.final_via_tool:
            assessment_schema = schema["properties"]["assessment"]
            final_tool_properties = {
                "report_markdown": {"type": "string"},
                **deepcopy(assessment_schema["properties"]),
            }
            # Several OpenAI-compatible providers do not implement JSON Schema
            # unions in tool arguments consistently. Use an unambiguous transport
            # enum and decode it before applying the unchanged local assessment
            # validator.
            final_tool_properties["incident_occurred"] = {
                "type": "string",
                "enum": ["true", "false", "null"],
            }
            if self.unsupported_tool_schema_keywords:
                def strip_unsupported(value: Any) -> None:
                    if isinstance(value, dict):
                        # Some strict tool-schema implementations require an
                        # explicit JSON type next to const even though const is
                        # independently valid JSON Schema. This transport-only
                        # annotation does not change the accepted value or the
                        # unchanged local assessment validator.
                        if "const" in value and "type" not in value:
                            constant = value["const"]
                            inferred = (
                                "boolean" if isinstance(constant, bool)
                                else "integer" if isinstance(constant, int)
                                else "number" if isinstance(constant, float)
                                else "string" if isinstance(constant, str)
                                else "null" if constant is None
                                else None
                            )
                            if inferred is not None:
                                value["type"] = inferred
                        for keyword in self.unsupported_tool_schema_keywords:
                            value.pop(keyword, None)
                        for nested in value.values():
                            strip_unsupported(nested)
                    elif isinstance(value, list):
                        for nested in value:
                            strip_unsupported(nested)

                strip_unsupported(final_tool_properties)
            tools.append({
                "type": "function",
                "function": {
                    "name": "submit_final_report",
                    "description": (
                        "Submit the final incident report and structured assessment. "
                        "This records output only and is not a response action."
                    ),
                    "strict": self.final_tool_strict,
                    "parameters": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": final_tool_properties,
                        "required": ["report_markdown", *assessment_schema["required"]],
                    },
                },
            })
        instructions = context.instructions_path.read_text(encoding="utf-8")
        if self.final_via_tool:
            instructions += (
                "\n\nWhen the investigation is complete, invoke submit_final_report "
                "exactly once. Pass the report in report_markdown and pass every assessment "
                "field as a separate top-level function argument. The reconstructed "
                "assessment must conform to this JSON Schema. Do not return the final "
                "report as ordinary assistant content:\n"
                + json.dumps(schema, sort_keys=True)
            )
        else:
            instructions += (
                "\n\nYour final answer must be one JSON object and no surrounding prose. "
                "It must conform exactly to this JSON Schema:\n"
                + json.dumps(schema, sort_keys=True)
            )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": evidence_prompt(context, self.evidence_byte_limit)},
        ]
        response_records: list[dict[str, Any]] = []
        tool_records: list[dict[str, Any]] = []
        action_calls = 0
        format_repairs = 0

        def request_format_repair(message: Any, reason: str) -> bool:
            nonlocal format_repairs
            if format_repairs >= self.max_format_repairs:
                return False
            format_repairs += 1
            messages.append(assistant_message(message))
            messages.append({
                "role": "user",
                "content": (
                    "Protocol correction: your previous response was not accepted "
                    f"because {reason}. Do not describe or encode an action request "
                    "inside ordinary JSON content. If an action is justified, invoke "
                    "exactly one of the provided functions using the API tool-call "
                    "mechanism. If no further action is needed, return exactly the "
                    "required final JSON object with only report_markdown and assessment."
                ),
            })
            return True

        while True:
            parameters: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "max_tokens": self.max_output_tokens,
                "stream": False,
            }
            if not self.final_via_tool:
                parameters["response_format"] = {"type": "json_object"}
            if self.temperature is not None:
                parameters["temperature"] = self.temperature
            if self.reasoning_effort is not None:
                parameters["reasoning_effort"] = self.reasoning_effort
            if self.request_extra_body is not None:
                parameters["extra_body"] = self.request_extra_body

            response = self.client.chat.completions.create(**parameters)
            choices = value(response, "choices", [])
            if not choices:
                raise ValueError(f"{self.provider_label} returned no completion choice")
            choice = choices[0]
            message = value(choice, "message")
            if message is None:
                raise ValueError(f"{self.provider_label} returned no assistant message")
            finish_reason = value(choice, "finish_reason")
            response_records.append({
                "response_id": value(response, "id", ""),
                "model": value(response, "model"),
                "status": finish_reason,
                "usage": object_dump(value(response, "usage")),
            })
            calls = value(message, "tool_calls", []) or []
            if calls:
                final_calls = [
                    call for call in calls
                    if value(value(call, "function"), "name") == "submit_final_report"
                ]
                if final_calls:
                    if not self.final_via_tool or len(calls) != 1:
                        raise ValueError("final report call must be the only function call")
                    raw_arguments = value(value(final_calls[0], "function"), "arguments", "{}")
                    if not isinstance(raw_arguments, str):
                        raise ValueError("final report arguments must be JSON text")
                    submitted = json.loads(raw_arguments)
                    if not isinstance(submitted, dict):
                        raise ValueError("final report arguments must be an object")
                    final = {
                        "report_markdown": submitted.get("report_markdown"),
                        "assessment": {
                            key: submitted.get(key)
                            for key in assessment_schema["required"]
                        },
                    }
                    incident_state = final["assessment"].get("incident_occurred")
                    final["assessment"]["incident_occurred"] = {
                        "true": True,
                        "false": False,
                        "null": None,
                    }.get(incident_state, incident_state)
                elif action_calls + len(calls) > self.max_action_calls:
                    raise RuntimeError("model exceeded maximum response-action calls")
                else:
                    messages.append(assistant_message(message))
                    for call in calls:
                        call_id = value(call, "id")
                        function = value(call, "function")
                        name = value(function, "name")
                        raw_arguments = value(function, "arguments", "{}")
                        if not isinstance(call_id, str) or not call_id or not isinstance(name, str):
                            raise ValueError("malformed model function call")
                        if not isinstance(raw_arguments, str):
                            raise ValueError("model function arguments must be JSON text")
                        arguments = json.loads(raw_arguments)
                        if not isinstance(arguments, dict):
                            raise ValueError("model function arguments must be an object")
                        broker_result = request_action(
                            name,
                            arguments,
                            context.broker_socket,
                            experiment_id=context.experiment_id,
                            run_id=context.run_id,
                        )
                        action_calls += 1
                        tool_records.append({
                            "call_id": call_id,
                            "action": name,
                            "arguments": arguments,
                            "broker_result": broker_result,
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(broker_result, sort_keys=True),
                        })
                    continue
            elif self.final_via_tool:
                raise ValueError("model returned content instead of submit_final_report")
            elif finish_reason not in {None, "stop"}:
                raise RuntimeError(
                    f"{self.provider_label} completion did not finish normally: {finish_reason}"
                )
            else:
                raw_output = value(message, "content")
                if not isinstance(raw_output, str) or not raw_output.strip():
                    raise ValueError("model returned no final structured output")
                try:
                    final = json.loads(raw_output)
                except json.JSONDecodeError:
                    if request_format_repair(message, "the content was not valid JSON"):
                        continue
                    raise
            if not isinstance(final, dict) or set(final) != {"report_markdown", "assessment"}:
                if not self.final_via_tool:
                    atomic_text(
                        context.metadata_path.with_name(
                            f"invalid_final_output_{format_repairs + 1:02d}.txt"
                        ),
                        raw_output.rstrip() + "\n",
                    )
                keys = sorted(final) if isinstance(final, dict) else []
                if request_format_repair(
                    message, f"the top-level fields were {keys!r}"
                ):
                    continue
                raise ValueError(f"invalid final output envelope; keys={keys!r}")
            if not isinstance(final["report_markdown"], str) or not final["report_markdown"].strip():
                if request_format_repair(message, "report_markdown was empty or invalid"):
                    continue
                raise ValueError("incident report is empty")
            try:
                validate_assessment(final["assessment"], context.incident_id)
            except (TypeError, ValueError) as error:
                if request_format_repair(
                    message, f"the assessment failed validation: {error}"
                ):
                    continue
                raise

            atomic_text(context.report_path, final["report_markdown"].rstrip() + "\n")
            atomic_text(
                context.assessment_path,
                json.dumps(final["assessment"], indent=2, sort_keys=True) + "\n",
            )
            metadata = {
                "schema_version": "1.0",
                "provider": self.provider_name,
                "requested_model": self.model,
                "returned_models": [item["model"] for item in response_records],
                "sdk_version": self.sdk_version,
                "configuration": {
                    "max_output_tokens": self.max_output_tokens,
                    "max_action_calls": self.max_action_calls,
                    "evidence_byte_limit": self.evidence_byte_limit,
                    "temperature": self.temperature,
                    "reasoning_effort": self.reasoning_effort,
                    "store": False,
                    "parallel_tool_calls": False,
                    "max_format_repairs": self.max_format_repairs,
                    "format_repairs_used": format_repairs,
                    "final_via_tool": self.final_via_tool,
                    "request_extra_body": self.request_extra_body,
                    "unsupported_tool_schema_keywords": list(
                        self.unsupported_tool_schema_keywords
                    ),
                    "final_tool_strict": self.final_tool_strict,
                },
                "responses": response_records,
                "tool_calls": tool_records,
            }
            atomic_text(
                context.metadata_path,
                json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            )
            return metadata


def environment_int(name: str, default: int) -> int:
    configured = os.environ.get(name)
    return default if configured is None else int(configured)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model")
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--max-action-calls", type=int)
    parser.add_argument("--evidence-byte-limit", type=int)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--reasoning-effort")
    args = parser.parse_args()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        parser.error("DEEPSEEK_API_KEY is required")
    context = ModelRunContext.from_environment()
    model = args.model or os.environ.get("DEEPSEEK_MODEL") or context.model_id
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("install the pinned OpenAI SDK dependency") from error
    adapter = DeepSeekChatAdapter(
        OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL),
        model,
        args.max_output_tokens or environment_int("DEEPSEEK_MAX_OUTPUT_TOKENS", 8000),
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
