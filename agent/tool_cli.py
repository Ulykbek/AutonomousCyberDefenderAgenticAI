"""Shared CLI adapter that prevents tools from authorizing locally."""

from __future__ import annotations

import json
from typing import Any

from agent.broker_client import request_action


def submit(action: str, arguments: dict[str, Any]) -> int:
    response = request_action(action, arguments)
    print(json.dumps(response, sort_keys=True))
    return 0 if response.get("status") == "EXECUTED" else 2
