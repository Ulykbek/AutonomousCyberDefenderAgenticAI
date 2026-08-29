from __future__ import annotations

import unittest
from types import SimpleNamespace

from model_adapters.openrouter_chat import OpenRouterChatAdapter


class OpenRouterAdapterTests(unittest.TestCase):
    def test_provider_identity_and_native_finalization(self) -> None:
        self.assertEqual("openrouter", OpenRouterChatAdapter.provider_name)
        self.assertEqual("OpenRouter", OpenRouterChatAdapter.provider_label)
        self.assertEqual(0, OpenRouterChatAdapter.max_format_repairs)
        self.assertTrue(OpenRouterChatAdapter.final_via_tool)
        self.assertEqual(
            ("uniqueItems",), OpenRouterChatAdapter.unsupported_tool_schema_keywords
        )

    def test_provider_routing_is_sent_as_extra_body(self) -> None:
        adapter = OpenRouterChatAdapter(
            SimpleNamespace(), "model", request_extra_body={
                "provider": {"order": ["Groq"], "allow_fallbacks": False}
            }
        )
        self.assertEqual(
            {"provider": {"order": ["Groq"], "allow_fallbacks": False}},
            adapter.request_extra_body,
        )


if __name__ == "__main__":
    unittest.main()
