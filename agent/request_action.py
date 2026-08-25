"""CLI for submitting one structured action to CyberBroker."""

from __future__ import annotations

import argparse
import json

from agent.broker_client import request_action


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("arguments", help="JSON object containing action arguments")
    args = parser.parse_args()
    arguments = json.loads(args.arguments)
    print(json.dumps(request_action(args.action, arguments), sort_keys=True))
