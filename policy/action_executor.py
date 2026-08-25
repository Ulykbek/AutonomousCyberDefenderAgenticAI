"""Compatibility facade that sends actions to the separate CyberBroker."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.broker_client import request_action


def execute_action(action: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Submit an action; authorization and execution occur inside CyberBroker."""
    return request_action(action, arguments)
