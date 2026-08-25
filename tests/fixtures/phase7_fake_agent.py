"""Deterministic test double for the Phase 7 command adapter."""

from __future__ import annotations

import os
from pathlib import Path

from agent.broker_client import request_action


mode = os.environ.get("PHASE7_FAKE_MODE", "allowed")
report_path = Path(os.environ["CYBERDEFENDER_REPORT_PATH"])
evidence_dir = Path(os.environ["CYBERDEFENDER_EVIDENCE_DIR"])

if mode == "modify-evidence":
    target = next(path for path in evidence_dir.iterdir() if path.is_file())
    target.chmod(0o644)
    target.write_text(target.read_text(encoding="utf-8") + "\nmodified\n", encoding="utf-8")
elif mode != "missing-report":
    action = "isolate_host" if mode == "denied" else "block_ip"
    arguments = (
        {"target": "127.0.0.1"}
        if mode == "denied"
        else {"target": "192.0.2.55", "reason": "phase7 test"}
    )
    response = request_action(
        action,
        arguments,
        Path(os.environ["CYBERBROKER_SOCKET"]),
        experiment_id=os.environ["CYBERDEFENDER_EXPERIMENT_ID"],
        run_id=os.environ["CYBERDEFENDER_RUN_ID"],
    )
    report_path.write_text(
        "# Test incident report\n\n" + f"Broker status: {response['status']}\n",
        encoding="utf-8",
    )
