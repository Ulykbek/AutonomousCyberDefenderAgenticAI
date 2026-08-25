import sys
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(os.environ.get("CYBERDEFENDER_ACTION_LOG", Path(__file__).resolve().parent.parent / "logs" / "cyberdefender_actions.txt"))


def block_user(username):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(
            f"[{timestamp}] "
            f"ACTION=BLOCK_USER | "
            f"TARGET={username} | "
            f"STATUS=SIMULATED\n"
        )

    print(f"SIMULATED: User {username} blocked")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python block_user.py <USERNAME>")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agent.tool_cli import submit

    raise SystemExit(submit("block_user", {"target": sys.argv[1]}))
