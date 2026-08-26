"""Deterministic evidence variants with opaque agent-side identifiers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "evidence_variants" / "registry.json"


@dataclass(frozen=True)
class EvidenceVariant:
    variant_id: str
    version: str
    channel: str
    source_path: Path
    sha256: str


def load_evidence_variant(variant_id: str) -> EvidenceVariant | None:
    if variant_id == "BASE":
        return None
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("schema_version") != "1.0":
        raise ValueError("unsupported evidence-variant registry version")
    entry = registry.get("variants", {}).get(variant_id)
    if not isinstance(entry, dict):
        raise ValueError(f"unknown evidence variant: {variant_id}")
    source = (PROJECT_ROOT / entry["path"]).resolve()
    payload_root = (PROJECT_ROOT / "evidence_variants" / "payloads").resolve()
    if source.parent != payload_root or not source.is_file() or source.is_symlink():
        raise ValueError(f"invalid evidence variant source: {variant_id}")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != entry.get("sha256"):
        raise ValueError(f"evidence variant hash mismatch: {variant_id}")
    return EvidenceVariant(
        variant_id, entry["version"], entry["channel"], source, digest
    )


def apply_evidence_variant(evidence_dir: Path, variant: EvidenceVariant | None) -> None:
    if variant is None:
        return
    destination = evidence_dir / variant.channel
    if destination.resolve().parent != evidence_dir.resolve() or not destination.is_file():
        raise ValueError(f"evidence variant channel unavailable: {variant.channel}")
    original = destination.read_text(encoding="utf-8")
    payload = variant.source_path.read_text(encoding="utf-8").strip()
    destination.write_text(original.rstrip("\n") + "\n" + payload + "\n", encoding="utf-8")
