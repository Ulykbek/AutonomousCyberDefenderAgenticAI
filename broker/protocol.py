"""CyberBroker wire-protocol validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Request:
    experiment_id: str
    run_id: str
    request_id: str
    action: str
    arguments: dict[str, Any]


class ProtocolError(ValueError):
    pass


def parse_request(payload: Any) -> Request:
    if not isinstance(payload, dict):
        raise ProtocolError("REQUEST_MUST_BE_OBJECT")
    if set(payload) != {
        "experiment_id",
        "run_id",
        "request_id",
        "action",
        "arguments",
    }:
        raise ProtocolError("INVALID_REQUEST_FIELDS")
    experiment_id = payload["experiment_id"]
    run_id = payload["run_id"]
    request_id = payload["request_id"]
    action = payload["action"]
    arguments = payload["arguments"]
    if not isinstance(experiment_id, str) or not experiment_id or len(experiment_id) > 128:
        raise ProtocolError("INVALID_EXPERIMENT_ID")
    if not isinstance(run_id, str) or not run_id or len(run_id) > 128:
        raise ProtocolError("INVALID_RUN_ID")
    if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
        raise ProtocolError("INVALID_REQUEST_ID")
    if not isinstance(action, str) or not action or len(action) > 64:
        raise ProtocolError("INVALID_ACTION")
    if not isinstance(arguments, dict):
        raise ProtocolError("INVALID_ARGUMENTS")
    return Request(experiment_id, run_id, request_id, action, arguments)
