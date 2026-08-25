"""Format broker correlation identifiers for simulated action records."""

from __future__ import annotations


def context_suffix(audit_context: dict[str, str] | None) -> str:
    if not audit_context:
        return ""
    return (
        f" | EXPERIMENT_ID={audit_context['experiment_id']}"
        f" | RUN_ID={audit_context['run_id']}"
        f" | REQUEST_ID={audit_context['request_id']}"
    )
