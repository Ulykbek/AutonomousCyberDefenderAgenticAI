"""Target-aware authorization for CyberDefender response actions."""

from __future__ import annotations

import ipaddress
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

POLICY_FILE = Path(__file__).resolve().parent.parent / "policies" / "cyberdefender_policy.json"
PRIVATE_NETWORKS = tuple(ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    risk: str | None = None
    policy_version: str | None = None


def _deny(reason: str, capability: Mapping[str, Any] | None, version: str) -> Decision:
    return Decision(False, reason, capability.get("risk") if capability else None, version)


def _constraint_violation(action: str, target: str, constraints: Mapping) -> str | None:
    if action == "block_ip":
        try:
            address = ipaddress.ip_address(target)
        except ValueError:
            return "INVALID_IP_ADDRESS"
        if constraints.get("deny_loopback") and address.is_loopback:
            return "LOOPBACK_IP_PROTECTED"
        if constraints.get("deny_private_ips") and any(address in n for n in PRIVATE_NETWORKS):
            return "PRIVATE_IP_PROTECTED"
    if action == "block_user" and target.casefold() in {str(v).casefold() for v in constraints.get("protected_users", [])}:
        return "PROTECTED_USER"
    if action == "block_process" and Path(target).name.casefold() in {str(v).casefold() for v in constraints.get("protected_processes", [])}:
        return "PROTECTED_PROCESS"
    if action == "block_port":
        try:
            port = int(target.split("/", 1)[0])
        except ValueError:
            return "INVALID_PORT"
        if port in constraints.get("protected_ports", []):
            return "PROTECTED_PORT"
    if action == "quarantine_file":
        normalized = target.replace("\\", "/").lstrip("./")
        denied = constraints.get("denied_paths", [])
        allowed = constraints.get("allowed_paths", [])
        if any(normalized.startswith(v.lstrip("./")) for v in denied):
            return "PATH_EXPLICITLY_DENIED"
        if allowed and not any(normalized.startswith(v.lstrip("./")) for v in allowed):
            return "PATH_OUTSIDE_ALLOWED_SCOPE"
    return None


def authorize(action: str, args: Mapping[str, Any]) -> Decision:
    """Authorize an action and arguments without executing or logging it."""
    with POLICY_FILE.open(encoding="utf-8") as policy_file:
        policy = json.load(policy_file)
    version = str(policy.get("policy_version", "unknown"))
    capabilities = policy.get("capabilities", {})
    if action not in capabilities:
        return _deny("UNKNOWN_CAPABILITY", None, version)
    capability = capabilities[action]
    if not capability.get("allowed", False):
        return _deny("CAPABILITY_NOT_GRANTED", capability, version)
    target = args.get("target")
    if not isinstance(target, str) or not target:
        return _deny("INVALID_ARGUMENTS", capability, version)
    violation = _constraint_violation(action, target, capability.get("constraints", {}))
    if violation:
        return _deny(violation, capability, version)
    return Decision(True, "ALLOW", capability.get("risk"), version)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python policy_engine.py <ACTION> <TARGET>")
        raise SystemExit(1)
    result = authorize(sys.argv[1], {"target": sys.argv[2]})
    print("ALLOW" if result.allowed else f"DENY: {result.reason}")
    raise SystemExit(0 if result.allowed else 2)
