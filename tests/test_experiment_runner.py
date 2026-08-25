from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.adapters.command import CommandAdapter
from experiments.lifecycle import PROJECT_ROOT, RunLifecycle
from scripts.validate_manifests import validate_run


FAKE_AGENT = PROJECT_ROOT / "tests" / "fixtures" / "phase7_fake_agent.py"


class ExperimentRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.experiment = self.root / "experiment.json"
        self.experiment.write_text(json.dumps({
            "schema_version": "1.0",
            "experiment_id": "EXP-PHASE7-TEST",
            "baseline_id": "wp1-poc-v0.1",
            "title": "Phase 7 lifecycle test",
            "research_question": "Does the runner preserve controlled runs?",
            "conditions": [{
                "condition_id": "broker-enforced",
                "description": "CyberBroker mediates every requested action."
            }],
            "incident_ids": ["incident01"],
            "instruction_profiles": ["neutral"],
            "model": {"provider": "test", "model_id": "fake-agent"},
            "repetitions": 4
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def execute(self, mode: str, repetition: int) -> dict:
        lifecycle = RunLifecycle(
            self.experiment, self.root / "runs", "broker-enforced",
            "incident01", "neutral", repetition, 10,
        )
        adapter = CommandAdapter([sys.executable, str(FAKE_AGENT)], PROJECT_ROOT)
        with patch.dict(os.environ, {"PHASE7_FAKE_MODE": mode}):
            return lifecycle.run(adapter)

    def test_allowed_action_completes_with_correlated_execution(self) -> None:
        result = self.execute("allowed", 1)
        self.assertEqual("completed", result["status"])
        self.assertEqual({"requests": 1, "allowed": 1, "denied": 0, "executed": 1},
                         result["audit_counts"])
        self.assertEqual(result["evidence_hashes"], result["evidence_hashes_after"])
        validate_run(result)

    def test_denied_action_never_reaches_execution_log(self) -> None:
        result = self.execute("denied", 2)
        self.assertEqual("completed", result["status"])
        self.assertEqual(1, result["audit_counts"]["denied"])
        self.assertEqual(0, result["audit_counts"]["executed"])

    def test_missing_report_fails_run(self) -> None:
        result = self.execute("missing-report", 3)
        self.assertEqual("failed", result["status"])
        self.assertEqual("REPORT_MISSING", result["failure_reason"])

    def test_evidence_mutation_invalidates_run(self) -> None:
        result = self.execute("modify-evidence", 4)
        self.assertEqual("invalid", result["status"])
        self.assertEqual("EVIDENCE_MODIFIED", result["failure_reason"])

    def test_existing_run_is_not_overwritten(self) -> None:
        self.execute("allowed", 1)
        with self.assertRaises(FileExistsError):
            self.execute("allowed", 1)


if __name__ == "__main__":
    unittest.main()
