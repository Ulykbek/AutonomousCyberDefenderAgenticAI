"""Dependency-free validation for WP1 experiment and run manifests."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_STATUSES = {
    "planned", "running", "completed", "failed", "aborted", "timed_out", "invalid"
}
CAMPAIGN_STATUSES = {"planned", "running", "completed", "completed_with_failures"}
ATTEMPT_STATUSES = {
    "running", "completed", "failed", "timed_out", "invalid",
    "runner_error", "interrupted",
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
    evidence_variants = data.get("evidence_variants")
    if evidence_variants is not None and (
        not isinstance(evidence_variants, list)
        or not evidence_variants
        or not all(valid_id(value) for value in evidence_variants)
        or len(evidence_variants) != len(set(evidence_variants))
    ):
        raise ValueError("evidence_variants must be a non-empty unique identifier list")
    if evidence_variants is not None:
        registry = json.loads(
            (PROJECT_ROOT / "evidence_variants" / "registry.json").read_text(
                encoding="utf-8"
            )
        )
        unknown = set(evidence_variants) - set(registry.get("variants", {})) - {"BASE"}
        if unknown:
            raise ValueError(f"unknown evidence_variants: {sorted(unknown)}")
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
    attempt = data.get("attempt")
    if attempt is not None and (not isinstance(attempt, int) or attempt < 1):
        raise ValueError("attempt must be null or a positive integer")
    evidence_variant = data.get("evidence_variant")
    variant_hash = data.get("evidence_variant_hash")
    if evidence_variant is not None:
        if not valid_id(evidence_variant):
            raise ValueError("invalid run evidence_variant")
        if evidence_variant == "BASE" and variant_hash is not None:
            raise ValueError("BASE evidence variant cannot have a hash")
        if evidence_variant != "BASE" and (
            not isinstance(variant_hash, str) or not SHA256.fullmatch(variant_hash)
        ):
            raise ValueError("derived evidence variant requires a SHA-256")
    base_hashes = data.get("base_evidence_hashes")
    if base_hashes is not None and (
        not isinstance(base_hashes, dict)
        or not base_hashes
        or not all(
            isinstance(value, str) and SHA256.fullmatch(value)
            for value in base_hashes.values()
        )
    ):
        raise ValueError("invalid base evidence SHA-256")


def validate_campaign(data: dict[str, Any]) -> None:
    require_fields(data, {
        "schema_version", "campaign_id", "experiment_manifest",
        "experiment_manifest_hash", "agent_command", "created_at", "updated_at",
        "status", "max_workers_last_run", "cells",
    })
    if data["schema_version"] != "1.0" or not valid_id(data["campaign_id"]):
        raise ValueError("invalid campaign schema version or campaign_id")
    if not isinstance(data["experiment_manifest_hash"], str) or not SHA256.fullmatch(
        data["experiment_manifest_hash"]
    ):
        raise ValueError("invalid experiment manifest hash")
    if not isinstance(data["agent_command"], list) or not data["agent_command"] or not all(
        isinstance(item, str) and item for item in data["agent_command"]
    ):
        raise ValueError("invalid agent command")
    if data["status"] not in CAMPAIGN_STATUSES:
        raise ValueError("invalid campaign status")
    if not isinstance(data["max_workers_last_run"], int) or data["max_workers_last_run"] < 1:
        raise ValueError("invalid campaign worker count")
    if not isinstance(data["cells"], list) or not data["cells"]:
        raise ValueError("campaign cells must be a non-empty list")
    cell_ids: set[str] = set()
    run_ids: set[str] = set()
    for cell in data["cells"]:
        require_fields(cell, {
            "cell_id", "condition_id", "incident_id", "instruction_profile",
            "repetition", "attempts",
        })
        evidence_variant = cell.get("evidence_variant")
        if evidence_variant is not None and not valid_id(evidence_variant):
            raise ValueError("invalid campaign evidence_variant")
        if not isinstance(cell["cell_id"], str) or not cell["cell_id"] or cell["cell_id"] in cell_ids:
            raise ValueError("missing or duplicate campaign cell_id")
        cell_ids.add(cell["cell_id"])
        if not isinstance(cell["repetition"], int) or cell["repetition"] < 1:
            raise ValueError("invalid campaign repetition")
        if not isinstance(cell["attempts"], list):
            raise ValueError("campaign attempts must be a list")
        for number, attempt_record in enumerate(cell["attempts"], start=1):
            require_fields(attempt_record, {
                "attempt", "run_id", "run_directory", "started_at", "completed_at",
                "status", "failure_reason",
            })
            if attempt_record["attempt"] != number:
                raise ValueError("campaign attempts must be sequential")
            if not valid_id(attempt_record["run_id"]) or attempt_record["run_id"] in run_ids:
                raise ValueError("invalid or duplicate campaign run_id")
            run_ids.add(attempt_record["run_id"])
            if attempt_record["status"] not in ATTEMPT_STATUSES:
                raise ValueError("invalid campaign attempt status")


def validate(path: Path, manifest_type: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    validators = {
        "experiment": validate_experiment,
        "run": validate_run,
        "campaign": validate_campaign,
    }
    validators[manifest_type](data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--type", choices=("experiment", "run", "campaign"), required=True)
    args = parser.parse_args()
    validate(args.manifest, args.type)
    print(f"VALID {args.type} manifest: {args.manifest}")
