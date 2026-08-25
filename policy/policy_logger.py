"""Append CyberDefender policy decisions as JSON Lines records."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_FILE = Path(
    os.environ.get(
        "CYBERDEFENDER_POLICY_LOG",
        Path(__file__).resolve().parent.parent / "logs" / "policy_decisions.jsonl",
    )
)


def log_decision(
    action: str,
    arguments: dict[str, Any],
    decision: Any,
    request_id: str | None = None,
    experiment_id: str | None = None,
    run_id: str | None = None,
    component: str = "local_executor",
) -> None:
    """Record one policy decision without modifying incident evidence."""
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "component": component,
        "experiment_id": experiment_id,
        "run_id": run_id,
        "request_id": request_id,
        "arguments": arguments,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "risk": decision.risk,
        "policy_version": decision.policy_version,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record, sort_keys=True) + "\n")
