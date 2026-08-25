import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "cyberdefender_actions.txt"


def block_process(process, host):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(
            f"[{timestamp}] "
            f"ACTION=BLOCK_PROCESS | "
            f"TARGET={process} | "
            f"HOST={host} | "
            f"STATUS=SIMULATED\n"
        )

    print(f"SIMULATED: Process {process} on {host} blocked")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python block_process.py <PROCESS> <HOST>")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "policy"))
    from action_executor import execute_action

    print(
        execute_action(
            "block_process", {"target": sys.argv[1], "host": sys.argv[2]}
        )
    )
