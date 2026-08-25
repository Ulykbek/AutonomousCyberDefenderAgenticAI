import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from audit_context import context_suffix

LOG_FILE = Path(os.environ.get("CYBERDEFENDER_ACTION_LOG", Path(__file__).resolve().parent.parent / "logs" / "cyberdefender_actions.txt"))


def block_port(port, protocol="TCP", *, audit_context=None):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(
            f"[{timestamp}] "
            f"ACTION=BLOCK_PORT | "
            f"TARGET={port}/{protocol} | "
            f"STATUS=SIMULATED"
            f"{context_suffix(audit_context)}\n"
        )

    print(f"SIMULATED: Port {port}/{protocol} blocked")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python block_port.py <PORT> [PROTOCOL]")
        sys.exit(1)

    protocol = sys.argv[2] if len(sys.argv) >= 3 else "TCP"

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agent.tool_cli import submit

    raise SystemExit(
        submit("block_port", {"target": sys.argv[1], "protocol": protocol})
    )
