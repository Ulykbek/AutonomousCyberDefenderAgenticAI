import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "cyberdefender_actions.txt"


def quarantine_file(file_path):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(
            f"[{timestamp}] "
            f"ACTION=QUARANTINE_FILE | "
            f"TARGET={file_path} | "
            f"STATUS=SIMULATED\n"
        )

    print(f"SIMULATED: File {file_path} quarantined")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quarantine_file.py <FILE_PATH>")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "policy"))
    from action_executor import execute_action

    print(execute_action("quarantine_file", {"target": sys.argv[1]}))
