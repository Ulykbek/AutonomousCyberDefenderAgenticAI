import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "cyberdefender_actions.txt"


def run_start():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(
            f"[{timestamp}] "
            f"ACTION=SYSTEM_START | "
            f"TARGET=CYBERDEFENDER_TOOLS | "
            f"STATUS=SUCCESS\n"
        )

    print("CyberDefender START: SUCCESS")
    return True


if __name__ == "__main__":
    success = run_start()

    if not success:
        sys.exit(1)