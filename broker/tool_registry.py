"""Fixed registry of simulated tools available only to CyberBroker."""

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


def execute_tool(
    action: str,
    arguments: dict[str, Any],
    audit_context: dict[str, str],
) -> str:
    target = arguments["target"]
    registry: dict[str, Callable[[], None]] = {
        "block_ip": lambda: block_ip(target, arguments.get("reason", "No reason provided"), audit_context=audit_context),
        "block_port": lambda: block_port(target, arguments.get("protocol", "TCP"), audit_context=audit_context),
        "block_process": lambda: block_process(target, arguments["host"], audit_context=audit_context),
        "block_user": lambda: block_user(target, audit_context=audit_context),
        "isolate_host": lambda: isolate_host(target, audit_context=audit_context),
        "quarantine_file": lambda: quarantine_file(target, audit_context=audit_context),
    }
    registry[action]()
    return "SIMULATED"
