"""Ground-truth-blind campaign orchestration for Phase 9."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiments.adapters.command import CommandAdapter
from experiments.lifecycle import PROJECT_ROOT, RunLifecycle, make_run_id
from scripts.validate_manifests import validate_experiment


RETRYABLE = {"failed", "timed_out", "invalid", "runner_error", "interrupted"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cell_id(condition: str, incident: str, profile: str, repetition: int) -> str:
    return f"{condition}--{incident}--{profile}--R{repetition:03d}"


def expand_matrix(experiment: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "cell_id": cell_id(condition["condition_id"], incident, profile, repetition),
            "condition_id": condition["condition_id"],
            "incident_id": incident,
            "instruction_profile": profile,
            "repetition": repetition,
            "attempts": [],
        }
        for condition in experiment["conditions"]
        for incident in experiment["incident_ids"]
        for profile in experiment["instruction_profiles"]
        for repetition in range(1, experiment["repetitions"] + 1)
    ]


class CampaignManager:
    def __init__(
        self,
        experiment_manifest: Path,
        output_root: Path,
        command: list[str],
        timeout_seconds: float,
        max_workers: int,
        retry_failed: bool = False,
    ):
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.experiment_path = experiment_manifest.resolve()
        self.output_root = output_root.resolve()
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.max_workers = max_workers
        self.retry_failed = retry_failed
        self.experiment = json.loads(self.experiment_path.read_text(encoding="utf-8"))
        validate_experiment(self.experiment)
        self.campaign_dir = self.output_root / self.experiment["experiment_id"]
        self.index_path = self.campaign_dir / "campaign.json"
        self.lock = threading.Lock()
        self.state = self._load_or_create()

    def _load_or_create(self) -> dict[str, Any]:
        expected_cells = expand_matrix(self.experiment)
        if self.index_path.exists():
            state = json.loads(self.index_path.read_text(encoding="utf-8"))
            if state.get("experiment_manifest_hash") != sha256(self.experiment_path):
                raise ValueError("experiment manifest changed since campaign creation")
            if [item["cell_id"] for item in state.get("cells", [])] != [
                item["cell_id"] for item in expected_cells
            ]:
                raise ValueError("campaign matrix does not match experiment manifest")
            if state.get("agent_command") != self.command:
                raise ValueError("agent command changed since campaign creation")
            changed = False
            for cell in state["cells"]:
                if cell["attempts"] and cell["attempts"][-1]["status"] == "running":
                    cell["attempts"][-1]["status"] = "interrupted"
                    cell["attempts"][-1]["completed_at"] = now()
                    cell["attempts"][-1]["failure_reason"] = "CAMPAIGN_INTERRUPTED"
                    changed = True
            if changed:
                state["updated_at"] = now()
                self._write_state(state)
            return state
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "schema_version": "1.0",
            "campaign_id": self.experiment["experiment_id"],
            "experiment_manifest": str(self.experiment_path),
            "experiment_manifest_hash": sha256(self.experiment_path),
            "agent_command": self.command,
            "created_at": now(),
            "updated_at": now(),
            "status": "planned",
            "max_workers_last_run": self.max_workers,
            "cells": expected_cells,
        }
        self._write_state(state)
        return state

    def _write_state(self, state: dict[str, Any] | None = None) -> None:
        value = self.state if state is None else state
        temporary = self.index_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.index_path)

    def _should_run(self, cell: dict[str, Any]) -> bool:
        if not cell["attempts"]:
            return True
        last = cell["attempts"][-1]["status"]
        if last == "completed":
            return False
        if last == "interrupted":
            return True
        return self.retry_failed and last in RETRYABLE

    def _execute_cell(self, cell: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            attempt_number = len(cell["attempts"]) + 1
            run_id = make_run_id(
                self.experiment["experiment_id"], cell["condition_id"],
                cell["incident_id"], cell["instruction_profile"],
                cell["repetition"], attempt_number,
            )
            attempt = {
                "attempt": attempt_number,
                "run_id": run_id,
                "run_directory": str(self.campaign_dir / run_id),
                "started_at": now(),
                "completed_at": None,
                "status": "running",
                "failure_reason": None,
            }
            cell["attempts"].append(attempt)
            self.state["updated_at"] = now()
            self._write_state()
        try:
            lifecycle = RunLifecycle(
                self.experiment_path, self.output_root, cell["condition_id"],
                cell["incident_id"], cell["instruction_profile"],
                cell["repetition"], self.timeout_seconds, attempt_number,
            )
            result = lifecycle.run(CommandAdapter(self.command, PROJECT_ROOT))
            status = result["status"]
            failure_reason = result.get("failure_reason")
        except Exception as error:
            status = "runner_error"
            failure_reason = f"{type(error).__name__}: {error}"
        with self.lock:
            attempt["status"] = status
            attempt["failure_reason"] = failure_reason
            attempt["completed_at"] = now()
            self.state["updated_at"] = now()
            self._write_state()
        return attempt

    def run(self) -> dict[str, Any]:
        runnable = [cell for cell in self.state["cells"] if self._should_run(cell)]
        self.state["status"] = "running"
        self.state["max_workers_last_run"] = self.max_workers
        self.state["updated_at"] = now()
        self._write_state()
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._execute_cell, cell) for cell in runnable]
            for future in as_completed(futures):
                future.result()
        completed = sum(
            bool(cell["attempts"] and cell["attempts"][-1]["status"] == "completed")
            for cell in self.state["cells"]
        )
        total = len(self.state["cells"])
        self.state["status"] = "completed" if completed == total else "completed_with_failures"
        self.state["summary"] = {
            "total_cells": total,
            "completed_cells": completed,
            "incomplete_cells": total - completed,
            "attempts": sum(len(cell["attempts"]) for cell in self.state["cells"]),
        }
        self.state["updated_at"] = now()
        self._write_state()
        return self.state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("/tmp/cyberdefender-campaigns"))
    parser.add_argument("--command-json", required=True)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    command = json.loads(args.command_json)
    if not isinstance(command, list) or not command or not all(
        isinstance(item, str) and item for item in command
    ):
        parser.error("--command-json must be a non-empty JSON string array")
    manager = CampaignManager(
        args.manifest, args.output_root, command, args.timeout,
        args.max_workers, args.retry_failed,
    )
    state = manager.run()
    print(json.dumps(state["summary"], indent=2, sort_keys=True))
    print(f"Campaign index: {manager.index_path}")
    return 0 if state["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
