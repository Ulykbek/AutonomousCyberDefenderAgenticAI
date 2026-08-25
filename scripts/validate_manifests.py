"""Dependency-free validation for WP1 experiment and run manifests."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
RUN_STATUSES = {
    "planned", "running", "completed", "failed", "aborted", "timed_out", "invalid"
}


def require_fields(data: dict[str, Any], fields: set[str]) -> None:
    missing = fields - set(data)
    if missing:
        raise ValueError(f"missing required fields: {sorted(missing)}")


def valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(IDENTIFIER.fullmatch(value))


def validate_experiment(data: dict[str, Any]) -> None:
    require_fields(
        data,
        {
            "schema_version",
            "experiment_id",
            "baseline_id",
            "title",
            "research_question",
            "conditions",
            "incident_ids",
            "instruction_profiles",
            "model",
            "repetitions",
        },
    )
    if data["schema_version"] != "1.0" or not valid_id(data["experiment_id"]):
        raise ValueError("invalid experiment schema version or experiment_id")
    if not isinstance(data["conditions"], list) or not data["conditions"]:
        raise ValueError("conditions must be a non-empty list")
    condition_ids = [item.get("condition_id") for item in data["conditions"]]
    if not all(valid_id(value) for value in condition_ids):
        raise ValueError("invalid condition_id")
    if len(condition_ids) != len(set(condition_ids)):
        raise ValueError("condition_id values must be unique")
    if not isinstance(data["repetitions"], int) or data["repetitions"] < 1:
        raise ValueError("repetitions must be a positive integer")
    if not isinstance(data["model"], dict) or not all(
        isinstance(data["model"].get(field), str) and data["model"][field]
        for field in ("provider", "model_id")
    ):
        raise ValueError("model provider and model_id are required")


def validate_run(data: dict[str, Any]) -> None:
    require_fields(
        data,
        {
            "schema_version",
            "experiment_id",
            "run_id",
            "condition_id",
            "baseline_id",
            "incident_id",
            "instruction_profile",
            "model",
            "evidence_hashes",
            "instruction_hashes",
            "policy_hash",
            "status",
        },
    )
    if data["schema_version"] != "1.0":
        raise ValueError("invalid run schema version")
    if not valid_id(data["experiment_id"]) or not valid_id(data["run_id"]):
        raise ValueError("invalid experiment_id or run_id")
    hashes = data["evidence_hashes"]
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("evidence_hashes must be a non-empty object")
    if not all(isinstance(value, str) and SHA256.fullmatch(value) for value in hashes.values()):
        raise ValueError("invalid evidence SHA-256")
    if not isinstance(data["policy_hash"], str) or not SHA256.fullmatch(data["policy_hash"]):
        raise ValueError("invalid policy_hash")
    instruction_hashes = data["instruction_hashes"]
    if set(instruction_hashes) != {"common", "profile", "composed"} or not all(
        isinstance(value, str) and SHA256.fullmatch(value)
        for value in instruction_hashes.values()
    ):
        raise ValueError("invalid instruction_hashes")
    if data["status"] not in RUN_STATUSES:
        raise ValueError("invalid run status")


def validate(path: Path, manifest_type: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    (validate_experiment if manifest_type == "experiment" else validate_run)(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--type", choices=("experiment", "run"), required=True)
    args = parser.parse_args()
    validate(args.manifest, args.type)
    print(f"VALID {args.type} manifest: {args.manifest}")
