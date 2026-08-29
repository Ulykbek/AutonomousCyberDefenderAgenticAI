"""OpenRouter Chat Completions adapter with CyberBroker-only response tools."""

from __future__ import annotations

import argparse
import importlib.metadata
import os

from model_adapters.base import ModelRunContext
from model_adapters.deepseek_chat import DeepSeekChatAdapter, environment_int
from model_adapters.openai_responses import run_start_indicator


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterChatAdapter(DeepSeekChatAdapter):
    provider_name = "openrouter"
    provider_label = "OpenRouter"
    final_via_tool = True
    unsupported_tool_schema_keywords = ("uniqueItems",)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model")
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--max-action-calls", type=int)
    parser.add_argument("--evidence-byte-limit", type=int)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--provider", action="append", dest="providers")
    parser.add_argument("--disable-provider-fallbacks", action="store_true")
    parser.add_argument("--non-strict-final-tool", action="store_true")
    args = parser.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        parser.error("OPENROUTER_API_KEY is required")
    context = ModelRunContext.from_environment()
    model = args.model or os.environ.get("OPENROUTER_MODEL") or context.model_id
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("install the pinned OpenAI SDK dependency") from error
    adapter = OpenRouterChatAdapter(
        OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://localhost",
                "X-Title": "CyberDefender-PoC",
            },
        ),
        model,
        args.max_output_tokens
        or environment_int("OPENROUTER_MAX_OUTPUT_TOKENS", 16000),
        args.max_action_calls if args.max_action_calls is not None else environment_int(
            "CYBERDEFENDER_MAX_ACTION_CALLS", 12
        ),
        args.evidence_byte_limit or environment_int(
            "CYBERDEFENDER_EVIDENCE_BYTE_LIMIT", 1_000_000
        ),
        args.temperature,
        args.reasoning_effort,
        importlib.metadata.version("openai"),
        {
            "provider": {
                "order": args.providers,
                "allow_fallbacks": not args.disable_provider_fallbacks,
            }
        } if args.providers else None,
        not args.non_strict_final_tool,
    )
    run_start_indicator(context)
    adapter.run(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
