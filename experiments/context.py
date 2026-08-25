"""Run context shared by experiment adapters and lifecycle code."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunContext:
    experiment_id: str
    run_id: str
    condition_id: str
    incident_id: str
    instruction_profile: str
    model_provider: str
    model_id: str
    run_dir: Path
    evidence_dir: Path
    output_dir: Path
    report_path: Path
    assessment_path: Path
    instruction_path: Path
    socket_path: Path
    timeout_seconds: float

    def agent_environment(self) -> dict[str, str]:
        return {
            "CYBERDEFENDER_EXPERIMENT_ID": self.experiment_id,
            "CYBERDEFENDER_RUN_ID": self.run_id,
            "CYBERDEFENDER_MODEL_PROVIDER": self.model_provider,
            "CYBERDEFENDER_MODEL_ID": self.model_id,
            "CYBERDEFENDER_INCIDENT_ID": self.incident_id,
            "CYBERBROKER_SOCKET": str(self.socket_path),
            "CYBERDEFENDER_REPORT_PATH": str(self.report_path),
            "CYBERDEFENDER_ASSESSMENT_PATH": str(self.assessment_path),
            "CYBERDEFENDER_EVIDENCE_DIR": str(self.evidence_dir),
            "CYBERDEFENDER_INSTRUCTIONS": str(self.instruction_path),
        }
