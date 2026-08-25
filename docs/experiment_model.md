# WP1 Experiment and Run Model

## Hierarchy

```text
Baseline
  -> Experiment
       -> Condition
            -> Run
                 -> Broker request
                      -> Policy decision
                           -> optional simulated execution
```

- A **baseline** freezes the implementation and research inputs.
- An **experiment** defines a research question, conditions, incidents, model, and
  repetition count.
- A **run** is one execution of one condition against one incident with one
  instruction profile and model configuration.
- A **request** is one proposed response action within a run.

## Identifiers

| Identifier | Scope | Example |
|---|---|---|
| `baseline_id` | Frozen implementation/input set | `wp1-poc-v0.1` |
| `experiment_id` | One experimental design | `EXP-WP1-001` |
| `condition_id` | One comparison condition | `broker-enforced` |
| `run_id` | One repetition | `RUN-001` |
| `request_id` | One broker request | UUID |

Identifiers are labels, not security credentials. Controlled runs must assign
stable experiment and run IDs before the agent starts. Manual requests default to
`adhoc` for both fields and must not be included in controlled experiment results.

## Correlation contract

Every protocol-valid request carries:

```json
{
  "experiment_id": "EXP-WP1-001",
  "run_id": "RUN-001",
  "request_id": "UUID",
  "action": "block_ip",
  "arguments": {"target": "203.0.113.77"}
}
```

CyberBroker preserves all three identifiers in:

1. The policy decision record
2. The broker response
3. The simulated action record, when execution occurs

A denial has no simulated action record. An execution without the same three
identifiers is an audit-correlation failure.

## Environment interface

Manual clients can provide controlled-run context through:

```bash
export CYBERDEFENDER_EXPERIMENT_ID=EXP-WP1-001
export CYBERDEFENDER_RUN_ID=RUN-001
```

The experiment runner should pass identifiers explicitly rather than depend on
ambient environment variables.

## Schemas

- `experiments/schemas/experiment_manifest.schema.json`
- `experiments/schemas/run_manifest.schema.json`

Templates are under `experiments/templates/`. Templates are examples and must be
copied to a results directory before values are populated.

## Mutable and immutable metadata

Immutable after run start:

- Experiment, condition, run, baseline, and incident identifiers
- Instruction profile
- Model identifier and parameters
- Evidence hashes
- Policy hash

Mutable lifecycle fields:

- Run status
- Start and completion timestamps
- Artifact locations
- Failure notes

If immutable metadata is wrong, mark the run invalid or aborted. Do not silently
rewrite it after observing the result.
