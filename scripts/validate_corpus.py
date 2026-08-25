"""Validate the structure of the agent-visible synthetic incident corpus."""

from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_ROOT = PROJECT_ROOT / "cases"
REGISTRY_PATH = CORPUS_ROOT / "corpus.json"
INCIDENT_ID = re.compile(r"^incident[0-9]{2}$")
FORBIDDEN_AGENT_PATH_TERMS = ("ground_truth", "answer_key", "expected_actions")


def validate() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("schema_version") != "1.0":
        raise ValueError("unsupported corpus-registry schema version")
    incident_ids = registry.get("incident_ids")
    channels = registry.get("evidence_channels")
    if not isinstance(incident_ids, list) or not incident_ids:
        raise ValueError("incident_ids must be a non-empty list")
    if len(incident_ids) != len(set(incident_ids)):
        raise ValueError("incident_ids must be unique")
    if not all(isinstance(value, str) and INCIDENT_ID.fullmatch(value) for value in incident_ids):
        raise ValueError("invalid incident identifier")
    if not isinstance(channels, list) or not channels:
        raise ValueError("evidence_channels must be a non-empty list")

    registered = set(incident_ids)
    discovered = {
        path.name
        for path in CORPUS_ROOT.iterdir()
        if path.is_dir() and INCIDENT_ID.fullmatch(path.name)
    }
    if registered != discovered:
        raise ValueError(
            f"registry/directory mismatch: missing={registered-discovered}, "
            f"unregistered={discovered-registered}"
        )

    file_count = 0
    for incident_id in incident_ids:
        evidence_dir = CORPUS_ROOT / incident_id / "evidence"
        actual = {path.name for path in evidence_dir.iterdir() if path.is_file()}
        expected = set(channels)
        if actual != expected:
            raise ValueError(
                f"{incident_id}: evidence mismatch; missing={expected-actual}, "
                f"unexpected={actual-expected}"
            )
        for path in evidence_dir.iterdir():
            if path.stat().st_size == 0:
                raise ValueError(f"{incident_id}: empty evidence file {path.name}")
            lowered = str(path.relative_to(CORPUS_ROOT)).casefold()
            if any(term in lowered for term in FORBIDDEN_AGENT_PATH_TERMS):
                raise ValueError(f"evaluator-only term exposed in agent path: {path}")
            file_count += 1

    if registry.get("classification_disclosed_to_agent") is not False:
        raise ValueError("classification disclosure flag must be false")
    if registry.get("ground_truth_in_agent_visible_tree") is not False:
        raise ValueError("ground-truth visibility flag must be false")

    print(
        f"VALID corpus {registry['corpus_id']}: {len(incident_ids)} incidents, "
        f"{file_count} non-empty evidence files"
    )


if __name__ == "__main__":
    validate()
