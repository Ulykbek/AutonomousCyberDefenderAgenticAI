"""Policy gate and dispatcher for simulated response tools."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from block_ip import block_ip
from block_port import block_port
from block_process import block_process
from block_user import block_user
from isolate_host import isolate_host
from quarantine_file import quarantine_file
from policy_engine import authorize
from policy_logger import log_decision


def _execute_tool(action: str, arguments: dict[str, Any]) -> str:
    target = arguments["target"]
    tools: dict[str, Callable[[], None]] = {
        "block_ip": lambda: block_ip(target, arguments.get("reason", "No reason provided")),
        "block_port": lambda: block_port(
            target.split("/", 1)[0],
            arguments.get(
                "protocol", target.split("/", 1)[1] if "/" in target else "TCP"
            ),
        ),
        "block_process": lambda: block_process(target, arguments["host"]),
        "block_user": lambda: block_user(target),
        "isolate_host": lambda: isolate_host(target),
        "quarantine_file": lambda: quarantine_file(target),
    }
    tools[action]()
    return "SIMULATED"


def execute_action(action: str, arguments: dict[str, Any]) -> str:
    """Authorize, audit, and conditionally execute one response action."""
    decision = authorize(action, arguments)
    log_decision(action, arguments, decision)
    if not decision.allowed:
        return f"DENIED: {decision.reason}"
    return _execute_tool(action, arguments)
