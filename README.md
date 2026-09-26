# Policy-mediated autonomous cyber defence — Experiment 1

Agent-side code and synthetic incident corpus supporting **From Adversarial Evidence to Executed Action: A Five-Model Study of Policy-Mediated Autonomous Cyber Defence**, Ulykbek Shambulov, Nazarbayev University. Paper 171 is accepted to SIDe 2026 on the Springer Nature STEAM-H route; final volume metadata and DOI are pending.

The study separates model requests, independent policy decisions and simulated execution. It covers 12 incidents × four instruction profiles × four evidence variants × five model configurations × three rounds: 2,880 planned cells and 2,858 scored cells. All 92 matched injected calls were denied. Injection targets were prohibited by policy design; this result does not establish semantic safety or OS-level non-bypassability.

## Reproduce the paper

The companion [AutonomousCyberDefenderEvaluator](https://github.com/Ulykbek/AutonomousCyberDefenderEvaluator) contains the frozen observations and a self-contained offline reproduction command:

```sh
cd ../AutonomousCyberDefenderEvaluator
python3 publication/side2026/reproduce.py --output replication-output/side2026
```

Python 3.10+ and the standard library are sufficient for offline reproduction. No model account, API key, network access or agent execution is required. The evaluator package includes the campaign ledger, saved run artifacts, original scores and provenance; it reconstructs the published tables and primary inference. See its `publication/side2026/README.md` for the exact mapping.

## Running new experiments

Start with [the agent runbook](docs/reproduction_runbook.md), [the threat model](docs/threat_model.md) and [the original CyberDefender role instructions](docs/cyberdefender_role.md). The role document preserves the previous README; frozen runs retain their original composed instructions. The code, policy and historical observations are not changed by the new publication landing page.

Hosted model identifiers and routing describe the recorded experiment, not a promise that the same endpoints remain available. Fresh model calls may produce different outputs and are a new replication, not exact recomputation. Response tools in this experiment simulate actions; the study is not evidence for unrestricted production deployment.

The evaluator, labels, variant mapping and published results must remain outside an acting agent's controlled experimental context. Use fresh restricted run directories and the documented separation between actor and evaluator.

## Scope and release status

- Experiment code baseline: `d335159e419c5e7d076a2803462de79a910226c4`.
- Later 24-scenario CyberBroker experiments are outside this publication.
- See [publication/release guidance](PUBLICATION.md) and [licensing status](LICENSING.md).
- Citation metadata: [CITATION.cff](CITATION.cff).

This is private release preparation. No public release, artifact DOI or final publisher DOI is claimed.
