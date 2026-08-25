# DeepSeek adapter

The DeepSeek adapter runs controlled API experiments through the provider's
OpenAI-compatible Chat Completions interface. It uses `deepseek-v4-flash` in
the supplied exploratory smoke manifest.

## Security boundary

DeepSeek receives only the composed agent instructions and staged, explicitly
untrusted incident evidence. Its only callable functions are CyberDefender
response requests. The adapter never executes those requests: it forwards each
one to CyberBroker with the experiment and run identifiers, then returns the
broker's decision to the model.

The adapter limits action requests, disables parallel tool calls, rejects
malformed calls, validates the final JSON locally, and writes outputs only
after validation. Provider JSON mode is a formatting aid and is not treated as
an enforcement boundary. CyberBroker remains authoritative.

## Credentials and dependencies

The existing pinned OpenAI Python SDK is used as the protocol client. Keep the
credential in the ignored repository-root `.env`, then explicitly load it into
the process environment:

```sh
source .venv-openai/bin/activate
set -a
source .env
set +a
```

The required variable is `DEEPSEEK_API_KEY`. Never place its value in a
manifest, report, log, command argument, or evaluator repository.

## Offline validation

```sh
python3 -m unittest tests.test_deepseek_adapter
python3 scripts/validate_manifests.py \
  experiments/manifests/deepseek_smoke_v1.json --type experiment
```

These tests use a fake API client and incur no provider charge.

## Controlled smoke test

Run this only after offline validation and explicit approval for one paid API
request sequence:

```sh
python3 -m experiments.runner experiments/manifests/deepseek_smoke_v1.json \
  --condition broker-enforced \
  --incident incident01 \
  --profile neutral \
  --repetition 1 \
  --output-root experiment_runs \
  --adapter command \
  --command-json '["python3", "-m", "model_adapters.deepseek_chat", "--model", "deepseek-v4-flash"]'
```

The command may make more than one API completion when the model requests a
brokered action. Results are stored under `experiment_runs/`, which is ignored
by Git. Review provider privacy and data terms before replacing the synthetic
corpus with sensitive evidence.
