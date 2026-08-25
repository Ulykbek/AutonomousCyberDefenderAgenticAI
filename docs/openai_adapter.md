# OpenAI Responses API adapter

The OpenAI adapter is the first implementation of the provider-neutral model
boundary. It is intended for reproducible API experiments, not interactive
ChatGPT sessions.

## Security boundary

The model receives the composed experimental instructions and the contents of
the staged evidence files. It receives no shell, filesystem, web-search, code
execution, or evaluator tool. The only model-callable functions are the six
response actions registered by this project. Every function call is forwarded
unchanged to CyberBroker with the experiment and run identifiers; the broker
result is returned to the model.

Evidence is wrapped and labelled as untrusted data. This label is a treatment
control, not a security boundary: the CyberBroker remains the authoritative
enforcement point. The adapter refuses symlink/non-file evidence entries,
invalid UTF-8, oversized evidence bundles, malformed tool calls, excessive
action calls, mismatched provider/model identity, and invalid final output.

No OpenAI built-in tools are enabled. API response storage is disabled with
`store=false`, and parallel function calls are disabled to keep action order
and audit correlation unambiguous. Consult the applicable provider data terms
before sending non-synthetic evidence.

## Final output

The API is asked for one strict structured object containing:

- `report_markdown` — the narrative incident report;
- `assessment` — the exact Phase 8 structured assessment.

The adapter validates the assessment again locally before atomically writing
either output. It also writes `output/model_run.json`, recording the requested
and returned model identifiers, SDK version, response IDs, usage, model
configuration, tool requests, and broker results. Phase 7 hashes all three
model outputs into the run manifest. Its agent-visible contract is defined in
`experiments/schemas/model_run.schema.json`.

## Installation

Use a dedicated virtual environment. Install the official OpenAI Python SDK,
then freeze the exact installed dependency set before collecting research data:

```sh
python3 -m venv .venv-openai
source .venv-openai/bin/activate
python3 -m pip install openai
python3 -m pip freeze > requirements-openai.lock
```

Do not commit an API key. Supply it only through the process environment:

```sh
export OPENAI_API_KEY="your-key"
```

## Experiment configuration

Set the experiment manifest model explicitly:

```json
{
  "model": {
    "provider": "openai",
    "model_id": "PINNED_MODEL_OR_SNAPSHOT_ID"
  }
}
```

Prefer a dated or otherwise immutable model snapshot when the provider offers
one. Do not change model ID, SDK lock file, instructions, policy, corpus, or
adapter limits inside a confirmatory campaign.

## One-run smoke test

After replacing the model ID in both locations with the same value:

```sh
python3 -m experiments.runner path/to/openai-experiment.json \
  --condition broker-enforced \
  --incident incident01 \
  --profile neutral \
  --repetition 1 \
  --output-root experiment_runs \
  --adapter command \
  --command-json '["python3", "-m", "model_adapters.openai_responses", "--model", "PINNED_MODEL_OR_SNAPSHOT_ID"]'
```

Optional adapter limits are `--max-output-tokens`, `--max-action-calls`,
`--evidence-byte-limit`, `--temperature`, and `--reasoning-effort`. Record them
before the pilot. Unsupported parameters vary by model; omit optional sampling
or reasoning parameters unless they are part of the frozen design.

## Isolation limitation

This adapter prevents model-level filesystem access because file and shell tools
are not exposed. The local adapter process still runs as the current OS user.
For a strong evaluator-secrecy claim, execute the agent-side project in a
container or restricted account that cannot read the evaluator directory. Mount
only the staged run, broker socket, required adapter code, and API credentials.
