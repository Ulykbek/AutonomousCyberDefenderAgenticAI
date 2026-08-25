"""Verify a frozen WP1 baseline manifest without modifying project files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "baselines" / "wp1-poc-v0.1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(manifest_path: Path) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for relative_path, expected_hash in manifest["files"].items():
        path = PROJECT_ROOT / relative_path
        if not path.is_file():
            failures.append(f"MISSING {relative_path}")
            continue
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            failures.append(
                f"CHANGED {relative_path}: expected {expected_hash}, got {actual_hash}"
            )
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    failures = verify(args.manifest)
    if failures:
        print("\n".join(failures))
        raise SystemExit(1)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    print(
        f"VERIFIED {manifest['baseline_id']}: "
        f"{len(manifest['files'])} files match"
    )
