"""Narrow client used by the agent to request CyberBroker actions."""

from __future__ import annotations

import json
import os
import socket
import uuid
from pathlib import Path
from typing import Any

DEFAULT_SOCKET = Path(os.environ.get("CYBERBROKER_SOCKET", "/tmp/cyberdefender-broker.sock"))


def request_action(
    action: str,
    arguments: dict[str, Any],
    socket_path: Path = DEFAULT_SOCKET,
    timeout: float = 5.0,
) -> dict[str, Any]:
    request = {
        "request_id": str(uuid.uuid4()),
        "action": action,
        "arguments": arguments,
    }
    data = (json.dumps(request, sort_keys=True) + "\n").encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(str(socket_path))
        client.sendall(data)
        response = client.makefile("rb").readline(64 * 1024)
    if not response:
        raise RuntimeError("CyberBroker returned no response")
    return json.loads(response.decode("utf-8"))
