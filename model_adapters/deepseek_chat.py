"""DeepSeek Chat Completions adapter with CyberBroker-only response tools."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
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
        instructions = context.instructions_path.read_text(encoding="utf-8")
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

        while True:
            parameters: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "tools": chat_tools(),
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "response_format": {"type": "json_object"},
                "max_tokens": self.max_output_tokens,
                "stream": False,
            }
            if self.temperature is not None:
                parameters["temperature"] = self.temperature
            if self.reasoning_effort is not None:
                parameters["reasoning_effort"] = self.reasoning_effort

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
                if action_calls + len(calls) > self.max_action_calls:
                    raise RuntimeError("model exceeded maximum response-action calls")
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

            if finish_reason not in {None, "stop"}:
                raise RuntimeError(
                    f"{self.provider_label} completion did not finish normally: {finish_reason}"
                )
            raw_output = value(message, "content")
            if not isinstance(raw_output, str) or not raw_output.strip():
                raise ValueError("model returned no final structured output")
            final = json.loads(raw_output)
            if not isinstance(final, dict) or set(final) != {"report_markdown", "assessment"}:
                raise ValueError("invalid final output envelope")
            if not isinstance(final["report_markdown"], str) or not final["report_markdown"].strip():
                raise ValueError("incident report is empty")
            validate_assessment(final["assessment"], context.incident_id)

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
