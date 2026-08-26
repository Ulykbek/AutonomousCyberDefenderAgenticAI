# Blinded Evidence Variants

The evidence-variant axis tests whether incident artifacts influence CyberDefender's
reasoning or response requests. It is independent of the incident, instruction
profile, model, and broker-enforcement condition.

Agent-side variants use opaque identifiers. This repository intentionally does not
associate those identifiers with attack-family names, expected actions, semantic
equivalents, success labels, or scoring rules. The evaluator-only repository must
hold that mapping.

## Evidence isolation

The lifecycle copies the selected incident evidence into a fresh run directory,
applies exactly one deterministic variant to that copy, and makes all evidence files
read-only. The source corpus under `cases/` is never edited.

Every run manifest records the opaque variant identifier, frozen payload hash,
unmodified source-evidence hashes, and overlaid evidence hashes before and after the
agent runs. A run is invalid if the before/after hashes differ.

The variant identifier is not added to the CyberDefender process environment or to
the model prompt as an experimental label. It appears only as an opaque component
needed to keep run artifacts unique. The model receives the composed instructions
and the resulting incident evidence, not evaluator metadata.

For stronger isolation, execute CyberDefender in a container or restricted account
that can read only its prepared run directory. Do not mount this repository's
variant registry or the evaluator repository into that environment.

## Pilot matrix

The pilot manifest is
`experiments/manifests/anthropic_haiku_45_variant_pilot_v1.json`:

```text
1 incident × 4 instruction profiles × 3 opaque evidence variants × 1 repetition
= 12 cells
```

Run the pilot sequentially and retain every attempt. Do not expand to all incidents
until the evaluator can collect the artifacts and score the opaque variants without
making its mapping visible to CyberDefender.
