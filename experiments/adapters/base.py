"""Adapter interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from experiments.context import RunContext


@dataclass(frozen=True)
class AgentResult:
    returncode: int
    timed_out: bool = False
    detail: str | None = None


class AgentAdapter(Protocol):
    def run(self, context: RunContext) -> AgentResult: ...
