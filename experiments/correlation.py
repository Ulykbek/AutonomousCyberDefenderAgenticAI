"""Validate broker decisions and simulated executions for one run."""

from __future__ import annotations

import json
import re
from pathlib import Path


REQUEST_ID = re.compile(r"(?:^| \| )REQUEST_ID=([^|\n]+)")
EXPERIMENT_ID = re.compile(r"(?:^| \| )EXPERIMENT_ID=([^|\n]+)")
RUN_ID = re.compile(r"(?:^| \| )RUN_ID=([^|\n]+)")


def _field(pattern: re.Pattern[str], line: str, name: str) -> str:
    match = pattern.search(line)
    if not match:
        raise ValueError(f"execution record missing {name}: {line}")
    return match.group(1).strip()


def validate_correlation(
    policy_log: Path,
    action_log: Path,
    experiment_id: str,
    run_id: str,
) -> dict[str, int]:
    decisions = [
        json.loads(line)
        for line in policy_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if policy_log.exists() else []
    seen: set[str] = set()
    allowed: set[str] = set()
    denied: set[str] = set()
    for decision in decisions:
        if decision.get("experiment_id") != experiment_id or decision.get("run_id") != run_id:
            raise ValueError("cross-run policy record detected")
        request_id = decision.get("request_id")
        if not isinstance(request_id, str) or not request_id or request_id in seen:
            raise ValueError("missing or duplicate request_id in policy log")
        seen.add(request_id)
        (allowed if decision.get("allowed") else denied).add(request_id)

    actions = [
        line
        for line in action_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if action_log.exists() else []
    executed: set[str] = set()
    for line in actions:
        if _field(EXPERIMENT_ID, line, "EXPERIMENT_ID") != experiment_id:
            raise ValueError("cross-experiment execution record detected")
        if _field(RUN_ID, line, "RUN_ID") != run_id:
            raise ValueError("cross-run execution record detected")
        request_id = _field(REQUEST_ID, line, "REQUEST_ID")
        if request_id in executed:
            raise ValueError("duplicate execution for request_id")
        if request_id not in allowed:
            raise ValueError("execution without matching ALLOW decision")
        if request_id in denied:
            raise ValueError("denied request was executed")
        executed.add(request_id)

    return {
        "requests": len(decisions),
        "allowed": len(allowed),
        "denied": len(denied),
        "executed": len(executed),
    }
