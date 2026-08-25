"""Generic no-shell command adapter."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from experiments.adapters.base import AgentResult
from experiments.context import RunContext


class CommandAdapter:
    def __init__(self, command: list[str], project_root: Path):
        if not command or not all(isinstance(item, str) and item for item in command):
            raise ValueError("command adapter requires a non-empty argument list")
        self.command = command
        self.project_root = project_root

    def run(self, context: RunContext) -> AgentResult:
        environment = os.environ.copy()
        environment.update(context.agent_environment())
        existing_pythonpath = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            str(self.project_root)
            if not existing_pythonpath
            else f"{self.project_root}{os.pathsep}{existing_pythonpath}"
        )
        stdout_path = context.output_dir / "agent_stdout.txt"
        stderr_path = context.output_dir / "agent_stderr.txt"
        try:
            with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
                "w", encoding="utf-8"
            ) as stderr:
                completed = subprocess.run(
                    self.command,
                    cwd=context.run_dir,
                    env=environment,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=context.timeout_seconds,
                    check=False,
                    shell=False,
                )
            return AgentResult(completed.returncode)
        except subprocess.TimeoutExpired:
            return AgentResult(124, timed_out=True, detail="agent command timeout")
