"""Atomic authorize, audit, and execute boundary owned by CyberBroker."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "policy"))

from policy_engine import authorize
from policy_logger import log_decision

from broker.protocol import Request
from broker.tool_registry import execute_tool


def handle_request(request: Request) -> dict[str, Any]:
    decision = authorize(request.action, request.arguments)
    log_decision(
        request.action,
        request.arguments,
        decision,
        request_id=request.request_id,
        experiment_id=request.experiment_id,
        run_id=request.run_id,
        component="cyberbroker",
    )
    if not decision.allowed:
        return {
            "request_id": request.request_id,
            "experiment_id": request.experiment_id,
            "run_id": request.run_id,
            "status": "DENIED",
            "reason": decision.reason,
        }
    try:
        result = execute_tool(
            request.action,
            request.arguments,
            {
                "experiment_id": request.experiment_id,
                "run_id": request.run_id,
                "request_id": request.request_id,
            },
        )
    except (KeyError, TypeError, ValueError):
        return {
            "request_id": request.request_id,
            "experiment_id": request.experiment_id,
            "run_id": request.run_id,
            "status": "FAILED",
            "reason": "TOOL_ARGUMENT_ERROR",
        }
    except Exception:
        return {
            "request_id": request.request_id,
            "experiment_id": request.experiment_id,
            "run_id": request.run_id,
            "status": "FAILED",
            "reason": "TOOL_EXECUTION_FAILED",
        }
    return {
        "request_id": request.request_id,
        "experiment_id": request.experiment_id,
        "run_id": request.run_id,
        "status": "EXECUTED",
        "reason": "ALLOW",
        "result": result,
    }
