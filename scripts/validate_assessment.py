"""Dependency-free validation for agent-produced structured assessments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED = {
    "schema_version", "incident_id", "classification", "incident_occurred",
    "severity", "accounts", "hosts", "network_indicators", "attack_techniques",
}
CLASSIFICATIONS = {"malicious", "benign", "ambiguous"}
SEVERITIES = {"none", "low", "medium", "high", "critical", "undetermined"}
ACCOUNT_STATES = {"compromised", "misused", "attempted", "benign", "uncertain"}
HOST_STATES = {"compromised", "affected", "benign", "uncertain"}
INDICATOR_STATES = {"malicious", "suspicious", "benign", "uncertain"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_assessment(data: Any, incident_id: str) -> None:
    require(isinstance(data, dict), "assessment must be an object")
    require(set(data) == REQUIRED, "assessment has missing or unexpected fields")
    require(data["schema_version"] == "1.0", "unsupported assessment schema")
    require(data["incident_id"] == incident_id, "assessment incident mismatch")
    require(data["classification"] in CLASSIFICATIONS, "invalid classification")
    require(data["incident_occurred"] in {True, False, None}, "invalid incident state")
    require(data["severity"] in SEVERITIES, "invalid severity")
    for field, states in (
        ("accounts", ACCOUNT_STATES), ("hosts", HOST_STATES),
        ("network_indicators", INDICATOR_STATES),
    ):
        require(isinstance(data[field], dict), f"{field} must be an object")
        require(all(
            isinstance(key, str) and key and value in states
            for key, value in data[field].items()
        ), f"invalid {field}")
    techniques = data["attack_techniques"]
    require(isinstance(techniques, list), "attack_techniques must be an array")
    require(all(isinstance(value, str) and value for value in techniques),
            "invalid attack technique")
    require(len(techniques) == len(set(techniques)), "duplicate attack technique")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("assessment", type=Path)
    parser.add_argument("--incident", required=True)
    args = parser.parse_args()
    validate_assessment(
        json.loads(args.assessment.read_text(encoding="utf-8")), args.incident
    )
    print(f"VALID assessment: {args.assessment}")
