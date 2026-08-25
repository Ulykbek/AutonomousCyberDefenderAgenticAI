"""Gemini OpenAI-compatible adapter with CyberBroker-only response tools."""

from __future__ import annotations

import argparse
import importlib.metadata
import os

from model_adapters.base import ModelRunContext
from model_adapters.deepseek_chat import DeepSeekChatAdapter, environment_int
from model_adapters.openai_responses import run_start_indicator


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiChatAdapter(DeepSeekChatAdapter):
    """Use Gemini while retaining the common broker-enforced chat boundary."""

    provider_name = "gemini"
    provider_label = "Gemini"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model")
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--max-action-calls", type=int)
    parser.add_argument("--evidence-byte-limit", type=int)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--reasoning-effort")
    args = parser.parse_args()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        parser.error("GEMINI_API_KEY is required")
    context = ModelRunContext.from_environment()
    model = args.model or os.environ.get("GEMINI_MODEL") or context.model_id
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("install the pinned OpenAI SDK dependency") from error
    adapter = GeminiChatAdapter(
        OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL),
        model,
        args.max_output_tokens or environment_int("GEMINI_MAX_OUTPUT_TOKENS", 8000),
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
