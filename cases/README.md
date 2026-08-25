# Synthetic Incident Corpus

Each `incidentNN` directory is an independent synthetic investigation case. Files
inside `evidence/` are agent-visible incident inputs and may be incomplete,
ambiguous, malformed, or contradictory.

Directory names and this catalog do not identify expected conclusions. Evaluator
ground truth is intentionally not stored with agent-visible evidence.

The common evidence channels are:

- `auth.log`
- `web.log`
- `firewall.log`
- `process.log`
- `dns.log`

An empty channel means that the collection source observed no events during the
provided window; it does not prove that no activity occurred.
