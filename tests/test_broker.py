from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from agent.broker_client import request_action


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT_ID = "EXP-TEST-001"
RUN_ID = "RUN-TEST-001"


class CyberBrokerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        root = Path(cls.temp_dir.name)
        cls.socket_path = root / "broker.sock"
        cls.action_log = root / "actions.log"
        cls.policy_log = root / "decisions.jsonl"
        env = os.environ.copy()
        env["CYBERDEFENDER_ACTION_LOG"] = str(cls.action_log)
        env["CYBERDEFENDER_POLICY_LOG"] = str(cls.policy_log)
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "broker.server", "--socket", str(cls.socket_path)],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 5
        while not cls.socket_path.exists() and time.monotonic() < deadline:
            if cls.server.poll() is not None:
                stdout, stderr = cls.server.communicate()
                raise RuntimeError(f"broker failed: {stdout}{stderr}")
            time.sleep(0.02)
        if not cls.socket_path.exists():
            raise RuntimeError("broker socket was not created")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.terminate()
        cls.server.wait(timeout=5)
        cls.temp_dir.cleanup()

    def request(self, action: str, arguments: dict) -> dict:
        return request_action(
            action,
            arguments,
            self.socket_path,
            experiment_id=EXPERIMENT_ID,
            run_id=RUN_ID,
        )

    def test_denied_capability_never_executes(self) -> None:
        before = self.action_log.read_text() if self.action_log.exists() else ""
        response = self.request("isolate_host", {"target": "127.0.0.1"})
        after = self.action_log.read_text() if self.action_log.exists() else ""
        self.assertEqual("DENIED", response["status"])
        self.assertEqual("CAPABILITY_NOT_GRANTED", response["reason"])
        self.assertEqual(before, after)

    def test_unknown_capability_is_denied(self) -> None:
        response = self.request("run_shell", {"target": "id"})
        self.assertEqual("UNKNOWN_CAPABILITY", response["reason"])

    def test_invalid_arguments_are_denied(self) -> None:
        response = self.request("block_process", {"target": "malware"})
        self.assertEqual("INVALID_ARGUMENTS", response["reason"])

    def test_allowed_action_executes_once(self) -> None:
        before = self.action_log.read_text().splitlines() if self.action_log.exists() else []
        response = self.request("block_ip", {"target": "192.0.2.55", "reason": "test"})
        after = self.action_log.read_text().splitlines()
        self.assertEqual("EXECUTED", response["status"])
        self.assertEqual(len(before) + 1, len(after))
        self.assertIn("TARGET=192.0.2.55", after[-1])
        self.assertIn(f"EXPERIMENT_ID={EXPERIMENT_ID}", after[-1])
        self.assertIn(f"RUN_ID={RUN_ID}", after[-1])
        self.assertIn(f"REQUEST_ID={response['request_id']}", after[-1])

    def test_every_request_has_correlated_audit_record(self) -> None:
        response = self.request("block_user", {"target": "deploy"})
        records = [json.loads(line) for line in self.policy_log.read_text().splitlines()]
        self.assertEqual(response["request_id"], records[-1]["request_id"])
        self.assertEqual(EXPERIMENT_ID, response["experiment_id"])
        self.assertEqual(RUN_ID, response["run_id"])
        self.assertEqual(EXPERIMENT_ID, records[-1]["experiment_id"])
        self.assertEqual(RUN_ID, records[-1]["run_id"])
        self.assertEqual("cyberbroker", records[-1]["component"])

    def test_tool_cli_routes_through_broker(self) -> None:
        env = os.environ.copy()
        env["CYBERBROKER_SOCKET"] = str(self.socket_path)
        env["CYBERDEFENDER_EXPERIMENT_ID"] = EXPERIMENT_ID
        env["CYBERDEFENDER_RUN_ID"] = RUN_ID
        before = self.action_log.read_text() if self.action_log.exists() else ""
        result = subprocess.run(
            [sys.executable, "tools/isolate_host.py", "127.0.0.1"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        after = self.action_log.read_text() if self.action_log.exists() else ""
        response = json.loads(result.stdout)
        self.assertEqual(2, result.returncode)
        self.assertEqual("CAPABILITY_NOT_GRANTED", response["reason"])
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
