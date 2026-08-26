from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.campaign import CampaignManager, expand_matrix
from scripts.validate_manifests import validate_campaign


class CampaignManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "experiment.json"
        self.data = {
            "schema_version": "1.0", "experiment_id": "EXP-CAMPAIGN-TEST",
            "baseline_id": "wp1-poc-v0.1", "title": "Campaign test",
            "research_question": "Does orchestration preserve every cell?",
            "conditions": [{"condition_id": "broker", "description": "Brokered"}],
            "incident_ids": ["incident01", "incident02"],
            "instruction_profiles": ["neutral", "security-aware"],
            "model": {"provider": "test", "model_id": "fake"},
            "repetitions": 2,
        }
        self.write_manifest()
        self.command = ["python3", "fake_agent.py"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_manifest(self) -> None:
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")

    def manager(self, retry_failed: bool = False) -> CampaignManager:
        return CampaignManager(
            self.manifest, self.root / "runs", self.command, 10, 2, retry_failed
        )

    def test_matrix_is_cartesian_and_stable(self) -> None:
        cells = expand_matrix(self.data)
        self.assertEqual(8, len(cells))
        self.assertEqual(8, len({cell["cell_id"] for cell in cells}))
        self.assertNotIn("evidence_variant", cells[0])
        self.assertEqual(
            "broker--incident01--neutral--R001", cells[0]["cell_id"]
        )

    def test_evidence_variants_are_an_orthogonal_matrix_axis(self) -> None:
        self.data["evidence_variants"] = ["c91f7a2e", "4d8b2c61", "a73e5f90"]
        cells = expand_matrix(self.data)
        self.assertEqual(24, len(cells))
        self.assertEqual(24, len({cell["cell_id"] for cell in cells}))
        self.assertEqual(
            {"c91f7a2e", "4d8b2c61", "a73e5f90"},
            {cell["evidence_variant"] for cell in cells},
        )

    @patch("experiments.campaign.RunLifecycle.run")
    def test_completed_campaign_resumes_without_duplicate_runs(self, run) -> None:
        run.return_value = {"status": "completed", "failure_reason": None}
        first = self.manager().run()
        self.assertEqual("completed", first["status"])
        validate_campaign(first)
        self.assertEqual(8, run.call_count)
        second = self.manager().run()
        self.assertEqual("completed", second["status"])
        self.assertEqual(8, run.call_count)
        self.assertTrue(all(len(cell["attempts"]) == 1 for cell in second["cells"]))

    @patch("experiments.campaign.RunLifecycle.run")
    def test_failed_attempt_is_preserved_before_explicit_retry(self, run) -> None:
        self.data["incident_ids"] = ["incident01"]
        self.data["instruction_profiles"] = ["neutral"]
        self.data["repetitions"] = 1
        self.write_manifest()
        run.side_effect = [
            {"status": "failed", "failure_reason": "REPORT_MISSING"},
            {"status": "completed", "failure_reason": None},
        ]
        first = self.manager().run()
        self.assertEqual("completed_with_failures", first["status"])
        self.assertEqual(1, len(first["cells"][0]["attempts"]))
        second = self.manager(retry_failed=True).run()
        attempts = second["cells"][0]["attempts"]
        self.assertEqual(["failed", "completed"], [item["status"] for item in attempts])
        self.assertTrue(attempts[0]["run_id"].endswith("A001"))
        self.assertTrue(attempts[1]["run_id"].endswith("A002"))

    @patch("experiments.campaign.RunLifecycle.run")
    def test_interrupted_attempt_is_preserved_and_automatically_retried(self, run) -> None:
        self.data["incident_ids"] = ["incident01"]
        self.data["instruction_profiles"] = ["neutral"]
        self.data["repetitions"] = 1
        self.write_manifest()
        manager = self.manager()
        cell = manager.state["cells"][0]
        cell["attempts"].append({
            "attempt": 1, "run_id": "old", "run_directory": "/tmp/old",
            "started_at": "2026-01-01T00:00:00Z", "completed_at": None,
            "status": "running", "failure_reason": None,
        })
        manager._write_state()
        run.return_value = {"status": "completed", "failure_reason": None}
        resumed = self.manager().run()
        self.assertEqual(
            ["interrupted", "completed"],
            [item["status"] for item in resumed["cells"][0]["attempts"]],
        )

    def test_changed_manifest_is_rejected_on_resume(self) -> None:
        self.manager()
        self.data["title"] = "Changed after campaign creation"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            self.manager()


if __name__ == "__main__":
    unittest.main()
