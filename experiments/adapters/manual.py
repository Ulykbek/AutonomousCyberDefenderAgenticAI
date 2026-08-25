"""Manual adapter that waits for a report produced by an interactive agent."""

from __future__ import annotations

import time

from experiments.adapters.base import AgentResult
from experiments.context import RunContext


class ManualAdapter:
    def run(self, context: RunContext) -> AgentResult:
        print(f"Manual run ready: {context.run_id}")
        print(f"Instructions: {context.instruction_path}")
        print(f"Evidence: {context.evidence_dir}")
        print(f"Report target: {context.report_path}")
        print(f"Broker socket: {context.socket_path}")
        deadline = time.monotonic() + context.timeout_seconds
        while time.monotonic() < deadline:
            if context.report_path.is_file() and context.report_path.stat().st_size:
                return AgentResult(0, detail="report detected")
            time.sleep(0.25)
        return AgentResult(124, timed_out=True, detail="manual report timeout")
