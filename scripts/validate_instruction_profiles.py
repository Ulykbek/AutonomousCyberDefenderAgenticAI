"""Validate WP1 instruction-profile integrity and experiment references."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "instructions" / "profiles.json"
EXPERIMENT_TEMPLATE = (
    PROJECT_ROOT / "experiments" / "templates" / "experiment_manifest.json"
)
RUN_TEMPLATE = PROJECT_ROOT / "experiments" / "templates" / "run_manifest.json"
NEUTRAL_CONTAMINATION_TERMS = (
    "prompt injection",
    "indirect injection",
    "untrusted evidence",
    "adversarial evidence",
    "malicious instruction",
    "ignore instructions in",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_entry(label: str, entry: dict) -> Path:
    path = PROJECT_ROOT / entry["path"]
    if not path.is_file():
        raise ValueError(f"{label}: missing file {entry['path']}")
    actual = sha256(path)
    if actual != entry["sha256"]:
        raise ValueError(
            f"{label}: SHA-256 mismatch; expected {entry['sha256']}, got {actual}"
        )
    return path


def validate() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("schema_version") != "1.0":
        raise ValueError("unsupported profile-registry schema version")

    common_path = validate_entry("common", registry["common"])
    profiles = registry.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("profile registry must contain profiles")

    paths: list[Path] = []
    for profile_id, entry in profiles.items():
        if not entry.get("version"):
            raise ValueError(f"{profile_id}: missing version")
        paths.append(validate_entry(profile_id, entry))
    if len(paths) != len(set(paths)):
        raise ValueError("profile paths must be unique")

    neutral_path = PROJECT_ROOT / profiles["neutral"]["path"]
    neutral_bundle = (
        common_path.read_text(encoding="utf-8")
        + "\n"
        + neutral_path.read_text(encoding="utf-8")
    ).casefold()
    present = [term for term in NEUTRAL_CONTAMINATION_TERMS if term in neutral_bundle]
    if present:
        raise ValueError(f"neutral profile contamination terms found: {present}")

    experiment = json.loads(EXPERIMENT_TEMPLATE.read_text(encoding="utf-8"))
    run = json.loads(RUN_TEMPLATE.read_text(encoding="utf-8"))
    unknown = set(experiment["instruction_profiles"]) - set(profiles)
    if unknown:
        raise ValueError(f"experiment template references unknown profiles: {unknown}")
    if run["instruction_profile"] not in experiment["instruction_profiles"]:
        raise ValueError("run-template profile is not selected by experiment template")

    print(
        f"VALID instruction profiles: {len(profiles)} profiles, hashes and "
        "template references match; neutral bundle has no banned warning terms"
    )


if __name__ == "__main__":
    validate()
