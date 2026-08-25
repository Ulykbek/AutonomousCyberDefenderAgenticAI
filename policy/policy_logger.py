"""Append CyberDefender policy decisions as JSON Lines records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "policy_decisions.jsonl"


def log_decision(action: str, arguments: dict[str, Any], decision: Any) -> None:
    """Record one policy decision without modifying incident evidence."""
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "arguments": arguments,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "risk": decision.risk,
        "policy_version": decision.policy_version,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record, sort_keys=True) + "\n")
