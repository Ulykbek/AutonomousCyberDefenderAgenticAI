"""Shared context and result types for model-provider adapters."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelRunContext:
    experiment_id: str
    run_id: str
    incident_id: str
    model_provider: str
    model_id: str
    evidence_dir: Path
    instructions_path: Path
    assessment_schema_path: Path
    report_path: Path
    assessment_path: Path
    metadata_path: Path
    broker_socket: Path

    @classmethod
    def from_environment(cls) -> "ModelRunContext":
        required = {
            "experiment_id": "CYBERDEFENDER_EXPERIMENT_ID",
            "run_id": "CYBERDEFENDER_RUN_ID",
            "incident_id": "CYBERDEFENDER_INCIDENT_ID",
            "model_provider": "CYBERDEFENDER_MODEL_PROVIDER",
            "model_id": "CYBERDEFENDER_MODEL_ID",
            "evidence_dir": "CYBERDEFENDER_EVIDENCE_DIR",
            "instructions_path": "CYBERDEFENDER_INSTRUCTIONS",
            "report_path": "CYBERDEFENDER_REPORT_PATH",
            "assessment_path": "CYBERDEFENDER_ASSESSMENT_PATH",
            "broker_socket": "CYBERBROKER_SOCKET",
        }
        missing = [variable for variable in required.values() if not os.environ.get(variable)]
        if missing:
            raise ValueError(f"missing run environment: {', '.join(sorted(missing))}")
        report_path = Path(os.environ[required["report_path"]]).resolve()
        run_dir = report_path.parent.parent
        return cls(
            os.environ[required["experiment_id"]],
            os.environ[required["run_id"]],
            os.environ[required["incident_id"]],
            os.environ[required["model_provider"]],
            os.environ[required["model_id"]],
            Path(os.environ[required["evidence_dir"]]).resolve(),
            Path(os.environ[required["instructions_path"]]).resolve(),
            (run_dir / "assessment.schema.json").resolve(),
            report_path,
            Path(os.environ[required["assessment_path"]]).resolve(),
            (report_path.parent / "model_run.json").resolve(),
            Path(os.environ[required["broker_socket"]]).resolve(),
        )
