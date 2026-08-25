"""Unix-socket CyberBroker server."""

from __future__ import annotations

import argparse
import json
import os
import socketserver
from pathlib import Path

from broker.executor import handle_request
from broker.protocol import ProtocolError, parse_request

DEFAULT_SOCKET = Path(os.environ.get("CYBERBROKER_SOCKET", "/tmp/cyberdefender-broker.sock"))
MAX_REQUEST_BYTES = 64 * 1024


class BrokerHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            response = {"status": "DENIED", "reason": "REQUEST_TOO_LARGE"}
        else:
            try:
                payload = json.loads(raw.decode("utf-8"))
                response = handle_request(parse_request(payload))
            except (UnicodeDecodeError, json.JSONDecodeError, ProtocolError) as error:
                response = {"status": "DENIED", "reason": str(error)}
        self.wfile.write((json.dumps(response, sort_keys=True) + "\n").encode("utf-8"))


class BrokerServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


def serve(socket_path: Path) -> None:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()
    try:
        with BrokerServer(str(socket_path), BrokerHandler) as server:
            os.chmod(socket_path, 0o600)
            print(f"CyberBroker listening on {socket_path}", flush=True)
            server.serve_forever()
    finally:
        if socket_path.exists():
            socket_path.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET)
    args = parser.parse_args()
    serve(args.socket)
