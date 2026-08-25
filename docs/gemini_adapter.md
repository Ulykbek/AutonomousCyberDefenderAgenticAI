# Gemini adapter

The Gemini adapter runs controlled API experiments through Google's
OpenAI-compatible Chat Completions endpoint. The supplied exploratory manifest
uses `gemini-3.7-flash`.

Gemini receives only composed instructions and staged evidence. Its registered
functions are response requests, not executable local tools. Every request is
submitted to CyberBroker, and only the broker may authorize a simulated tool.
Final JSON is validated locally before any report or assessment is written.

## Credential

Store `GEMINI_API_KEY` in the ignored repository-root `.env`, then load it:

```sh
source .venv-openai/bin/activate
set -a
source .env
set +a
```

Never copy the key into manifests, reports, logs, or the evaluator repository.

## Offline validation

```sh
python3 -m unittest tests.test_gemini_adapter
python3 scripts/validate_manifests.py \
  experiments/manifests/gemini_smoke_v1.json --type experiment
```

## Controlled smoke test

```sh
python3 -m experiments.runner experiments/manifests/gemini_smoke_v1.json \
  --condition broker-enforced \
  --incident incident01 \
  --profile neutral \
  --repetition 1 \
  --output-root experiment_runs \
  --adapter command \
  --command-json '["/absolute/path/to/.venv-openai/bin/python", "-m", "model_adapters.gemini_chat", "--model", "gemini-3.7-flash"]'
```
