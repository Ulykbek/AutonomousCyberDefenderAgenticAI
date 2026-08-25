"""CLI entry point for one controlled WP1 run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.adapters.command import CommandAdapter
from experiments.adapters.manual import ManualAdapter
from experiments.lifecycle import PROJECT_ROOT, RunLifecycle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--incident", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--repetition", type=int, default=1)
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--output-root", type=Path, default=Path("/tmp/cyberdefender-runs"))
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--adapter", choices=("manual", "command"), default="manual")
    parser.add_argument(
        "--command-json",
        help="JSON array of command arguments; required by the command adapter",
    )
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.attempt is not None and args.attempt <= 0:
        parser.error("--attempt must be positive")
    if args.adapter == "command":
        if not args.command_json:
            parser.error("--command-json is required for command adapter")
        command = json.loads(args.command_json)
        if not isinstance(command, list):
            parser.error("--command-json must contain a JSON array")
        adapter = CommandAdapter(command, PROJECT_ROOT)
    else:
        if args.command_json:
            parser.error("--command-json is valid only for command adapter")
        adapter = ManualAdapter()

    lifecycle = RunLifecycle(
        args.manifest,
        args.output_root,
        args.condition,
        args.incident,
        args.profile,
        args.repetition,
        args.timeout,
        args.attempt,
    )
    result = lifecycle.run(adapter)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
