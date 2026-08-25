# WP1 PoC Baseline Release Checklist

Baseline identifier: `wp1-poc-v0.1`

## Included

- Research-oriented CyberDefender instructions
- CyberBroker Unix-socket process boundary
- Default-deny capability policy
- Argument and target validation
- Fixed simulated-tool registry
- Correlated broker policy decisions
- Incident 01 evidence and threat-intelligence input
- CyberBroker integration tests

## Excluded mutable artifacts

- `logs/` because records are appended by experimental runs
- `reports/` because reports are regenerated during experiments
- Python bytecode and caches
- The PhD proposal document
- Local Unix sockets and temporary test output

## Baseline verification

Run from the repository root:

```bash
python3 scripts/verify_baseline.py
```

A successful result means every file listed in the baseline manifest matches its
recorded SHA-256 digest. It does not verify unlisted files, runtime dependencies,
external models, or operating-system configuration.

## Release procedure

1. Verify the baseline manifest.
2. Run `python3 -m unittest -v tests/test_broker.py`.
3. Record the Python and operating-system versions used for experiments.
4. Confirm mutable logs and reports are not included in the frozen input set.
5. Commit the baseline files.
6. Create Git tag `wp1-poc-v0.1` only after explicit researcher approval.
7. Do not move the tag after experiments begin; create a new baseline version.

## Change policy

Any modification to a manifested file creates experimental drift. Intentional
changes require a new baseline identifier and manifest rather than silently
updating `wp1-poc-v0.1`.
