# Phase 9: Experimental campaign manager

Phase 9 expands a validated experiment manifest into a complete Cartesian run
matrix and executes each cell through the Phase 7 lifecycle. Campaign execution
is ground-truth blind: this repository contains no evaluator path, score rubric,
or expected answer.

## Matrix and identity

The matrix is:

```text
conditions × incidents × instruction profiles × repetitions
```

Each cell has a stable identifier. Every physical execution also has an attempt
number (`A001`, `A002`, and so on), so retries never overwrite or disguise a
failed, timed-out, invalid, or interrupted trial.

## Durable campaign index

`campaign.json` is written atomically after every state change. It records the
experiment-manifest hash, exact no-shell agent command, every cell and attempt,
run directories, terminal outcomes, and campaign totals. Resume refuses a
changed manifest or agent command. A prior `running` attempt is preserved as
`interrupted`, and resume creates a new attempt.

Completed cells are never rerun. Failed terminal cells are preserved and skipped
unless `--retry-failed` is explicitly supplied. Concurrency is bounded by
`--max-workers`; each run still receives a separate broker socket and logs.

Do not put API secrets in command arguments because the exact argument list is
recorded for reproducibility. Supply credentials through an appropriately
restricted process environment or secret manager.

## Execution

```sh
python3 -m experiments.campaign path/to/experiment.json \
  --output-root /path/to/campaign-runs \
  --command-json '["python3", "path/to/agent_launcher.py"]' \
  --max-workers 2
```

Run the same command again to resume. Use concurrency conservatively when a real
model provider imposes rate or cost limits.

## Evaluation boundary

The campaign manager does not score runs. After agent execution has ended, run
the separate evaluator-side campaign collector. This two-stage procedure avoids
making the evaluator directory or its ground truth part of the agent's campaign
workspace. Statistical aggregation and hypothesis testing remain Phase 10.
