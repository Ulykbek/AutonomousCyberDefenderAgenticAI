import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from audit_context import context_suffix

LOG_FILE = Path(os.environ.get("CYBERDEFENDER_ACTION_LOG", Path(__file__).resolve().parent.parent / "logs" / "cyberdefender_actions.txt"))


def isolate_host(host, *, audit_context=None):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(
            f"[{timestamp}] "
            f"ACTION=ISOLATE_HOST | "
            f"TARGET={host} | "
            f"STATUS=SIMULATED"
            f"{context_suffix(audit_context)}\n"
        )

    print(f"SIMULATED: Host {host} isolated")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python isolate_host.py <HOST>")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agent.tool_cli import submit

    raise SystemExit(submit("isolate_host", {"target": sys.argv[1]}))
