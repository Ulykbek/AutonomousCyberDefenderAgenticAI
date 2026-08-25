# CyberDefender experiment reproduction runbook

> **Protocol:** `WP1-REPRODUCTION-1.0`  
> **Scope:** agent execution and artifact production  
> **Ground truth:** prohibited in this workspace  
> **First use:** synthetic smoke test, then pilot, then frozen campaign

This runbook explains how another researcher can reproduce a CyberDefender
experiment without accidentally changing the experimental treatment or exposing
the evaluator-only ground truth. It begins with a single API-backed smoke test
and ends with a complete, auditable campaign handoff.

## 1. Understand the boundary before running anything

```text
Agent-visible workspace                      Evaluator-only workspace
───────────────────────                      ────────────────────────
instructions                                hidden ground truth
staged synthetic evidence                   scoring rubric
assessment schema                           scoring code and scores
CyberBroker socket                          statistical analysis
policy and simulated tools
        │
        └── response request → CyberBroker → ALLOW or DENY
```

CyberDefender may reason freely, including proposing an action that policy will
deny. It must never receive evaluator files, expected answers, justified-action
lists, scoring weights, or previous scores. A policy denial is experimental data,
not a reason to search for another execution route.

For smoke tests with synthetic evidence, same-host execution is convenient. For
a defensible secrecy claim, run the agent in a container or restricted OS account
that cannot read the evaluator workspace. Instructional separation alone is not
technical isolation.

## 2. Freeze the identity of the software under test

Before a pilot or final campaign, record:

```sh
git rev-parse HEAD
python3 --version
uname -a
```

Also preserve:

- `VERSION` and the baseline identifier;
- the experiment manifest;
- the dependency lock file;
- exact model provider and model/snapshot ID;
- instruction-profile, policy, corpus, and schema hashes;
- adapter limits and campaign concurrency;
- execution date and timezone.

Do not mix runs produced from different commits in one confirmatory campaign
unless software version is an explicit experimental factor.

## 3. Prepare an isolated Python environment

From the CyberDefender repository root:

```sh
python3 -m venv .venv-openai
source .venv-openai/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install openai
python3 -m pip freeze > requirements-openai.lock
```

For exact reproduction on a second machine:

```sh
python3 -m venv .venv-openai
source .venv-openai/bin/activate
python3 -m pip install -r requirements-openai.lock
```

Keep one lock file per frozen provider environment. Do not silently upgrade the
SDK during a campaign.

## 4. Validate locally before spending API credits

Run the adapter tests, then the complete agent-side regression suite:

```sh
python3 -m unittest -v tests.test_openai_adapter
```

```sh
python3 -m unittest -v \
  tests.test_openai_adapter \
  tests.test_campaign \
  tests.test_policy_paths \
  tests.test_experiment_runner \
  tests.test_broker
```

Validate the fixed research inputs:

```sh
python3 scripts/validate_instruction_profiles.py
python3 scripts/validate_corpus.py
```

Stop if any check fails. Record the failure and correct the environment before
creating research runs.

## 5. Configure credentials without recording them

Enter the API key interactively so it is not placed directly in shell history:

```sh
read -s OPENAI_API_KEY
export OPENAI_API_KEY
test -n "$OPENAI_API_KEY" && echo "API key configured"
```

Never place credentials in source files, manifests, campaign commands, reports,
logs, shell scripts committed to Git, or archived research artifacts. The
campaign index records the exact command arguments.

## 6. Create a one-run smoke-test manifest

Copy `experiments/templates/experiment_manifest.json` into a new file under
`experiments/manifests/`. Give every new experiment a new identifier. A minimal
API smoke test looks like this:

```json
{
  "schema_version": "1.0",
  "experiment_id": "EXP-OPENAI-SMOKE-001",
  "baseline_id": "wp1-poc-v0.1",
  "title": "OpenAI CyberDefender smoke test",
  "research_question": "Can the model complete one broker-controlled run?",
  "hypothesis": null,
  "conditions": [
    {
      "condition_id": "broker-enforced",
      "description": "Every response action is mediated by CyberBroker."
    }
  ],
  "incident_ids": ["incident01"],
  "instruction_profiles": ["neutral"],
  "model": {
    "provider": "openai",
    "model_id": "PINNED_MODEL_OR_SNAPSHOT_ID"
  },
  "repetitions": 1,
  "created_at": "REPLACE_WITH_UTC_TIMESTAMP",
  "notes": "Engineering smoke test; excluded from confirmatory analysis."
}
```

Prefer an immutable model snapshot when one is available. If an alias is used
for exploratory work, preserve the model identifier returned by the provider in
`model_run.json`.

Validate the manifest:

```sh
python3 scripts/validate_manifests.py \
  experiments/manifests/openai_smoke_v1.json \
  --type experiment
```

## 7. Execute exactly one incident

Use the same model ID in the manifest and adapter command:

```sh
python3 -m experiments.runner \
  experiments/manifests/openai_smoke_v1.json \
  --condition broker-enforced \
  --incident incident01 \
  --profile neutral \
  --repetition 1 \
  --output-root experiment_runs \
  --timeout 600 \
  --adapter command \
  --command-json '["python3","-m","model_adapters.openai_responses","--model","PINNED_MODEL_OR_SNAPSHOT_ID","--max-output-tokens","8000","--max-action-calls","8"]'
```

The runner refuses to overwrite an existing run. If setup was wrong, preserve
the failed run and create a new experiment ID rather than deleting evidence of
the failure.

## 8. Verify the run before evaluation

Set `RUN_DIR` to the directory printed by the runner, then inspect:

```sh
python3 -m json.tool "$RUN_DIR/manifest.json"
python3 -m json.tool "$RUN_DIR/output/assessment.json"
python3 -m json.tool "$RUN_DIR/output/model_run.json"
cat "$RUN_DIR/output/incident_report.md"
cat "$RUN_DIR/output/policy_decisions.jsonl"
cat "$RUN_DIR/output/cyberdefender_actions.txt"
```

Validate the structured assessment:

```sh
python3 scripts/validate_assessment.py \
  "$RUN_DIR/output/assessment.json" \
  --incident incident01
```

A usable run has:

- terminal status `completed`;
- `failure_reason: null`;
- identical evidence hashes before and after execution;
- non-empty narrative and structured assessment;
- model/SDK/usage metadata;
- one policy decision for every requested action;
- no execution record for a denied request;
- output hashes in `manifest.json`.

## 9. Diagnose without rewriting history

| Symptom | First file to inspect | Correct response |
|---|---|---|
| Agent exits nonzero | `output/agent_stderr.txt` | Preserve run; fix environment; use a new experiment/attempt |
| Broker fails to start | `output/broker_stderr.txt` | Check socket permissions and local sandboxing |
| Report missing | `output/agent_stdout.txt` and stderr | Check model refusal, incomplete response, or schema failure |
| Run is `invalid` | `manifest.json` | Inspect evidence hashes and audit-correlation reason |
| Action denied | `policy_decisions.jsonl` | Treat as valid behavior; do not bypass policy |
| Model IDs differ | `output/model_run.json` | Exclude or classify according to the preregistered rule |
| API rate/timeout error | agent stderr | Preserve attempt; apply the frozen retry rule |

Never edit a terminal run to make it pass. Corrections create a new attempt.

## 10. Move from smoke test to pilot

A useful first engineering pilot uses a small, preselected subset without
running the full matrix:

```text
incident01
incident02
incident03
incident07
incident08
```

Start with one profile and one repetition. After confirming artifact quality,
compare `neutral` with `injection-resistant`. Pilot results are used to test the
method, not to make confirmatory claims. The reasons for case selection belong
in the evaluator-only protocol and must not be supplied to CyberDefender.

Run a manifest-defined matrix with:

```sh
python3 -m experiments.campaign \
  experiments/manifests/openai_pilot_v1.json \
  --output-root experiment_runs \
  --command-json '["python3","-m","model_adapters.openai_responses","--model","PINNED_MODEL_OR_SNAPSHOT_ID","--max-output-tokens","8000","--max-action-calls","8"]' \
  --max-workers 1 \
  --timeout 600
```

Use conservative concurrency until rate limits, costs, and failure behavior are
understood. Re-run the identical command to resume. Completed cells are skipped.
Use `--retry-failed` only when the retry rule was defined before inspecting
outcomes.

## 11. Freeze the confirmatory campaign

After the pilot, freeze and hash:

- research questions and hypotheses;
- inclusion, exclusion, and retry rules;
- incidents and instruction profiles;
- model ID and provider configuration;
- policy and broker implementation;
- scoring rubric and analysis plan versions;
- repetitions, timeouts, token limits, action limits, and concurrency;
- dependency lock files and repository commits.

Do not tune these elements after inspecting confirmatory scores. Any necessary
change creates a new protocol version and campaign.

## 12. Handoff to the evaluator

Only after all agent processes and brokers have terminated, hand off:

- `campaign.json`;
- every referenced run directory;
- run manifests, reports, assessments, metadata, and audit logs;
- repository commit and dependency lock identifiers.

Make the handoff read-only where practical. Do not copy evaluator ground truth or
scores back into the agent workspace. The evaluator operator continues with the
separate evaluator reproduction runbook.

## 13. Minimum archive package

```text
protocol-version.txt
repository-commit.txt
environment.txt
requirements-openai.lock
experiment-manifest.json
campaign.json
run-directories/
```

The archive should make failures and retries visible. Reproducibility means
preserving what happened—not only preserving successful outputs.
