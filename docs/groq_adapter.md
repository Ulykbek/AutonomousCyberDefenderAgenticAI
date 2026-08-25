# Groq adapter

The Groq adapter runs a controlled `openai/gpt-oss-20b` experiment through
Groq's OpenAI-compatible Chat Completions API. Only locally orchestrated
CyberDefender response functions are exposed. Groq built-in browser, code,
shell, and remote tools are not registered.

Every requested action is forwarded to CyberBroker with its experiment and run
identifiers. Provider JSON mode assists formatting, but the authoritative
assessment schema is validated locally before artifacts are written.

## Credential

Store `GROQ_API_KEY` in the ignored repository-root `.env`, then load it:

```sh
source .venv-openai/bin/activate
set -a
source .env
set +a
```

## Offline validation

```sh
python3 -m unittest tests.test_groq_adapter
python3 scripts/validate_manifests.py \
  experiments/manifests/groq_smoke_v1.json --type experiment
```

## Controlled smoke test

```sh
python3 -m experiments.runner experiments/manifests/groq_smoke_v1.json \
  --condition broker-enforced --incident incident01 --profile neutral \
  --repetition 1 --attempt 1 --output-root experiment_runs \
  --adapter command \
  --command-json '["/absolute/path/to/.venv-openai/bin/python", "-m", "model_adapters.groq_chat", "--model", "openai/gpt-oss-20b"]'
```
