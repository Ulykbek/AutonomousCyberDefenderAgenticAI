"""Prepare, execute, and finalize one controlled WP1 experiment run."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiments.adapters.base import AgentAdapter, AgentResult
from experiments.context import RunContext
from experiments.correlation import validate_correlation
from scripts.validate_manifests import validate_experiment


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def make_run_id(
    experiment_id: str,
    condition_id: str,
    incident_id: str,
    profile_id: str,
    repetition: int,
    attempt: int | None = None,
) -> str:
    value = f"{experiment_id}-{condition_id}-{incident_id}-{profile_id}-R{repetition:03d}"
    if attempt is not None:
        if attempt < 1:
            raise ValueError("attempt must be positive")
        value += f"-A{attempt:03d}"
    if len(value) > 128:
        raise ValueError("generated run_id exceeds 128 characters")
    return value


class RunLifecycle:
    def __init__(
        self,
        experiment_manifest: Path,
        output_root: Path,
        condition_id: str,
        incident_id: str,
        profile_id: str,
        repetition: int,
        timeout_seconds: float,
        attempt: int | None = None,
    ):
        self.experiment_path = experiment_manifest.resolve()
        self.output_root = output_root.resolve()
        self.condition_id = condition_id
        self.incident_id = incident_id
        self.profile_id = profile_id
        self.repetition = repetition
        self.timeout_seconds = timeout_seconds
        self.attempt = attempt
        self.manifest: dict[str, Any] = {}
        self.context: RunContext | None = None
        self.broker: subprocess.Popen[str] | None = None
        self._broker_stdout = None
        self._broker_stderr = None
        self._socket_dir: Path | None = None

    def prepare(self) -> RunContext:
        experiment = json.loads(self.experiment_path.read_text(encoding="utf-8"))
        validate_experiment(experiment)
        condition_ids = {item["condition_id"] for item in experiment["conditions"]}
        if self.condition_id not in condition_ids:
            raise ValueError(f"unknown condition_id: {self.condition_id}")
        if self.incident_id not in experiment["incident_ids"]:
            raise ValueError(f"incident not selected by experiment: {self.incident_id}")
        if self.profile_id not in experiment["instruction_profiles"]:
            raise ValueError(f"profile not selected by experiment: {self.profile_id}")
        if not 1 <= self.repetition <= experiment["repetitions"]:
            raise ValueError("repetition outside experiment range")

        profile_registry = json.loads(
            (PROJECT_ROOT / "instructions" / "profiles.json").read_text(encoding="utf-8")
        )
        if self.profile_id not in profile_registry["profiles"]:
            raise ValueError(f"unknown profile: {self.profile_id}")
        common_path = PROJECT_ROOT / profile_registry["common"]["path"]
        profile_path = PROJECT_ROOT / profile_registry["profiles"][self.profile_id]["path"]
        if sha256(common_path) != profile_registry["common"]["sha256"]:
            raise ValueError("common instruction hash mismatch")
        if sha256(profile_path) != profile_registry["profiles"][self.profile_id]["sha256"]:
            raise ValueError("instruction profile hash mismatch")

        run_id = make_run_id(
            experiment["experiment_id"], self.condition_id, self.incident_id,
            self.profile_id, self.repetition, self.attempt,
        )
        run_dir = self.output_root / experiment["experiment_id"] / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        evidence_dir = run_dir / "evidence"
        output_dir = run_dir / "output"
        runtime_dir = run_dir / "runtime"
        tools_dir = run_dir / "tools"
        logs_dir = run_dir / "logs"
        evidence_dir.mkdir()
        output_dir.mkdir()
        runtime_dir.mkdir()
        tools_dir.mkdir()
        logs_dir.mkdir()

        source_evidence = PROJECT_ROOT / "cases" / self.incident_id / "evidence"
        if not source_evidence.is_dir():
            raise ValueError(f"missing evidence directory: {source_evidence}")
        for source in sorted(source_evidence.iterdir()):
            if source.is_file():
                destination = evidence_dir / source.name
                shutil.copy2(source, destination)
                destination.chmod(0o444)
        shutil.copy2(PROJECT_ROOT / "tools" / "start.py", tools_dir / "start.py")
        (tools_dir / "start.py").chmod(0o555)
        assessment_schema_path = run_dir / "assessment.schema.json"
        shutil.copy2(
            PROJECT_ROOT / "experiments" / "schemas" / "assessment.schema.json",
            assessment_schema_path,
        )
        assessment_schema_path.chmod(0o444)

        # Unix-domain socket paths are short on macOS (typically 104 bytes), so
        # a socket nested under the descriptive run ID is not portable.
        self._socket_dir = Path(tempfile.mkdtemp(prefix="cyberbroker-"))
        socket_path = self._socket_dir / "broker.sock"
        instruction_path = run_dir / "instructions.md"
        report_path = output_dir / "incident_report.md"
        assessment_path = output_dir / "assessment.json"
        instruction_text = (
            common_path.read_text(encoding="utf-8")
            + "\n\n"
            + profile_path.read_text(encoding="utf-8")
            + "\n\n# Run context\n\n"
            + f"- Experiment ID: `{experiment['experiment_id']}`\n"
            + f"- Run ID: `{run_id}`\n"
            + f"- Incident evidence: `{evidence_dir}`\n"
            + f"- Report target: `{report_path}`\n"
            + f"- Structured assessment target: `{assessment_path}`\n"
            + f"- Structured assessment schema: `{assessment_schema_path}`\n"
            + f"- CyberBroker socket: `{socket_path}`\n"
        )
        instruction_path.write_text(instruction_text, encoding="utf-8")
        instruction_path.chmod(0o444)

        context = RunContext(
            experiment["experiment_id"], run_id, self.condition_id,
            self.incident_id, self.profile_id,
            experiment["model"]["provider"], experiment["model"]["model_id"],
            run_dir, evidence_dir, output_dir,
            report_path, assessment_path, instruction_path, socket_path,
            self.timeout_seconds,
        )
        before = file_hashes(evidence_dir)
        self.manifest = {
            "schema_version": "1.0",
            "experiment_id": experiment["experiment_id"],
            "run_id": run_id,
            "condition_id": self.condition_id,
            "baseline_id": experiment["baseline_id"],
            "incident_id": self.incident_id,
            "instruction_profile": self.profile_id,
            "attempt": self.attempt,
            "model": experiment["model"],
            "seed": experiment.get("seed"),
            "started_at": now(),
            "completed_at": None,
            "evidence_hashes": before,
            "evidence_hashes_after": None,
            "output_hashes": None,
            "instruction_hashes": {
                "common": sha256(common_path),
                "profile": sha256(profile_path),
                "composed": sha256(instruction_path),
            },
            "policy_hash": sha256(PROJECT_ROOT / "policies" / "cyberdefender_policy.json"),
            "status": "running",
            "failure_reason": None,
            "artifacts": {
                "instructions": "instructions.md",
                "report": "output/incident_report.md",
                "assessment": "output/assessment.json",
                "assessment_schema": "assessment.schema.json",
                "model_metadata": "output/model_run.json",
                "policy_log": "output/policy_decisions.jsonl",
                "action_log": "output/cyberdefender_actions.txt",
                "agent_stdout": "output/agent_stdout.txt",
                "agent_stderr": "output/agent_stderr.txt",
                "broker_stdout": "output/broker_stdout.txt",
                "broker_stderr": "output/broker_stderr.txt",
                "start_indicator_log": "logs/cyberdefender_actions.txt"
            },
            "notes": "Prepared by Phase 7 experiment runner."
        }
        write_json(run_dir / "manifest.json", self.manifest)
        self.context = context
        return context

    def start_broker(self) -> None:
        if self.context is None:
            raise RuntimeError("prepare must run before start_broker")
        environment = os.environ.copy()
        environment["CYBERDEFENDER_POLICY_LOG"] = str(
            self.context.output_dir / "policy_decisions.jsonl"
        )
        environment["CYBERDEFENDER_ACTION_LOG"] = str(
            self.context.output_dir / "cyberdefender_actions.txt"
        )
        environment["CYBERBROKER_SOCKET"] = str(self.context.socket_path)
        self._broker_stdout = (self.context.output_dir / "broker_stdout.txt").open(
            "w", encoding="utf-8"
        )
        self._broker_stderr = (self.context.output_dir / "broker_stderr.txt").open(
            "w", encoding="utf-8"
        )
        self.broker = subprocess.Popen(
            [sys.executable, "-m", "broker.server", "--socket", str(self.context.socket_path)],
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=self._broker_stdout,
            stderr=self._broker_stderr,
            text=True,
        )
        deadline = time.monotonic() + 5
        while not self.context.socket_path.exists() and time.monotonic() < deadline:
            if self.broker.poll() is not None:
                raise RuntimeError("CyberBroker exited before socket creation")
            time.sleep(0.02)
        if not self.context.socket_path.exists():
            raise RuntimeError("CyberBroker socket was not created")

    def stop_broker(self) -> None:
        if self.broker is not None and self.broker.poll() is None:
            self.broker.terminate()
            try:
                self.broker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.broker.kill()
                self.broker.wait(timeout=5)
        if self._broker_stdout:
            self._broker_stdout.close()
        if self._broker_stderr:
            self._broker_stderr.close()
        if self._socket_dir is not None and self._socket_dir.exists():
            shutil.rmtree(self._socket_dir)

    def finalize(self, agent_result: AgentResult) -> dict[str, Any]:
        if self.context is None:
            raise RuntimeError("prepare must run before finalize")
        after = file_hashes(self.context.evidence_dir)
        self.manifest["evidence_hashes_after"] = after
        output_hashes = {}
        for name in ("incident_report.md", "assessment.json", "model_run.json"):
            path = self.context.output_dir / name
            if path.is_file():
                output_hashes[name] = sha256(path)
        self.manifest["output_hashes"] = output_hashes
        status = "completed"
        failure = None
        if after != self.manifest["evidence_hashes"]:
            status, failure = "invalid", "EVIDENCE_MODIFIED"
        elif agent_result.timed_out:
            status, failure = "timed_out", "AGENT_TIMEOUT"
        elif agent_result.returncode != 0:
            status, failure = "failed", f"AGENT_EXIT_{agent_result.returncode}"
        elif not self.context.report_path.is_file() or not self.context.report_path.stat().st_size:
            status, failure = "failed", "REPORT_MISSING"
        try:
            counts = validate_correlation(
                self.context.output_dir / "policy_decisions.jsonl",
                self.context.output_dir / "cyberdefender_actions.txt",
                self.context.experiment_id,
                self.context.run_id,
            )
            self.manifest["audit_counts"] = counts
        except (ValueError, json.JSONDecodeError) as error:
            status, failure = "invalid", f"AUDIT_CORRELATION: {error}"
        self.manifest["status"] = status
        self.manifest["failure_reason"] = failure
        self.manifest["completed_at"] = now()
        write_json(self.context.run_dir / "manifest.json", self.manifest)
        return self.manifest

    def run(self, adapter: AgentAdapter) -> dict[str, Any]:
        self.prepare()
        result = AgentResult(1, detail="agent did not start")
        try:
            self.start_broker()
            result = adapter.run(self.context)  # type: ignore[arg-type]
        except Exception as error:
            result = AgentResult(1, detail=f"runner error: {error}")
            self.manifest["notes"] = result.detail
        finally:
            self.stop_broker()
        return self.finalize(result)
