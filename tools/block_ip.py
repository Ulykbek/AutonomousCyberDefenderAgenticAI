import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "cyberdefender_actions.txt"


def block_ip(ip, reason="No reason provided"):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(
            f"[{timestamp}] "
            f"ACTION=BLOCK_IP | "
            f"TARGET={ip} | "
            f"REASON={reason} | "
            f"STATUS=SIMULATED\n"
        )

    print(f"SIMULATED: IP {ip} blocked")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python block_ip.py <IP>")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "policy"))
    from action_executor import execute_action

    print(execute_action("block_ip", {"target": sys.argv[1]}))
