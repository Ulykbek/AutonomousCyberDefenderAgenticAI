# Paper 171 release boundaries

The paper's frozen data and offline verification live in the companion evaluator repository. Use the evaluator's `tools/export_publication.py` to create current-file source exports of both repositories, with no Git history, no local `.env`, no proposal document and no later research files.

From the evaluator repository:

```sh
python3 tools/export_publication.py --agent-repo ../AutonomousCyberDefenderAgenticAI --output release-dist/paper171
```

The agent export excludes exploratory preflight directories and root-level working logs/reports. The evaluator's archived cohort retains the original first-experiment attempt ledger, including retries; exploratory pilot files are not silently counted as paper observations.

## Existing history

The proposal document was removed from the current tracked tree, but old commits still contain it. Removing a file in a new commit does not remove it from history. **Making this entire existing repository public would also expose its history.** Use the clean source export to initialize a dedicated public artifact repository when ready. No force-push or historical rewrite has been performed.

The automated credential-pattern scan is a limited check, not a comprehensive disclosure review. Licensing is recorded separately in `LICENSING.md`. Before public release, finalize that choice and the recorded-output sharing terms, then cite the actual stable release in the paper. The repository can remain private during this preparation.
