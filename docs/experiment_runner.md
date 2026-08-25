# Phase 7: Automated experiment runner

The Phase 7 runner executes one controlled CyberDefender trial and preserves the
result for later evaluator-only scoring. It does not read ground truth and does
not decide whether the agent's diagnosis was correct.

## Trust boundary

The runner supplies the agent with only:

- a read-only copy of one incident's evidence;
- the common instructions plus exactly one registered instruction profile;
- a unique experiment ID, run ID, report path, and CyberBroker socket.

Every response action must cross the per-run CyberBroker. The runner records
policy decisions and simulated executions in separate output files and rejects
records whose experiment, run, or request identifiers do not correlate. A
denied request appearing in the execution log makes the run invalid.

The evaluator workspace is not referenced, mounted, copied, or placed in the
agent environment. Phase 7 outputs are inputs to a later evaluator phase.

## Run lifecycle

1. Validate the experiment manifest and selected condition, incident, profile,
   and repetition.
2. Refuse to reuse an existing run ID.
3. Copy evidence into a new run directory, make it read-only, and hash it.
4. Verify and compose the registered common and profile instructions.
5. Start a dedicated CyberBroker socket with per-run policy and action logs.
6. Invoke either the manual adapter or a no-shell command adapter.
7. Stop the broker, hash evidence again, validate audit correlation, and write
   the terminal run status to `manifest.json`.

Terminal statuses are `completed`, `failed`, `timed_out`, or `invalid`.
Evidence mutation and audit-correlation violations produce `invalid`, because
the trial can no longer be treated as valid experimental data.

## Command adapter

The command adapter receives a JSON array, never a shell command string. The
agent process receives these environment variables:

- `CYBERDEFENDER_EXPERIMENT_ID`
- `CYBERDEFENDER_RUN_ID`
- `CYBERDEFENDER_INCIDENT_ID`
- `CYBERDEFENDER_MODEL_PROVIDER`
- `CYBERDEFENDER_MODEL_ID`
- `CYBERBROKER_SOCKET`
- `CYBERDEFENDER_REPORT_PATH`
- `CYBERDEFENDER_ASSESSMENT_PATH`
- `CYBERDEFENDER_EVIDENCE_DIR`
- `CYBERDEFENDER_INSTRUCTIONS`

Example (replace the command with the actual agent launcher):

```sh
python3 -m experiments.runner experiments/templates/experiment_manifest.json \
  --condition broker-enforced \
  --incident incident01 \
  --profile neutral \
  --repetition 1 \
  --output-root /tmp/cyberdefender-runs \
  --adapter command \
  --command-json '["python3", "path/to/agent_launcher.py"]'
```

The manual adapter prints the prepared paths and waits for a non-empty report.
It is useful for interactive trials, but the command adapter is preferable for
repeatability.

## Preserved artifacts

Each run contains the composed instructions, staged evidence, incident report,
structured assessment, agent and broker standard streams, policy decisions,
simulated action records, and a run manifest. The manifest includes evidence
hashes before and after the trial, instruction and policy hashes, timestamps,
status, failure reason, and audit counts. The structured assessment is an
agent-visible machine-readable output for evaluator-only deterministic scoring;
it contains no ground truth or scoring weights.

Phase 7 guarantees reproducible run packaging and mediation checks. It does not
claim operating-system isolation: a real-agent experiment should run the agent
in a container or restricted account when protection against deliberate local
filesystem access is part of the research question.
