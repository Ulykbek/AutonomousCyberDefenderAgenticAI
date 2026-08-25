# WP1 Threat-Model Validation — Phase 2

Validation date: 2026-08-25  
Threat-model baseline: `wp1-poc-v0.1`  
Validation type: implementation traceability and integration testing

## Summary

- Baseline verification: **PASS — 31/31 files matched**
- Policy JSON validation: **PASS**
- Existing CyberBroker integration tests: **PASS — 6/6**
- Fully supported invariants: **4**
- Partially supported invariants: **5**
- Documented but not yet tested: **3**

`PASS` below means that current automated evidence directly exercises the stated
property within its tested input. It is not a formal proof or a claim covering all
possible values and adversaries.

## Invariant traceability

| Invariant | Status | Implementation evidence | Test evidence / gap |
|---|---|---|---|
| INV-01 Complete broker mediation | Partial | Agent client uses the Unix socket; compatibility CLIs call `agent.tool_cli`; local `policy/action_executor.py` is a broker-client facade | `test_tool_cli_routes_through_broker` proves the supplied isolation CLI is mediated. Other CLIs are not individually tested, and arbitrary same-user imports remain an A4 bypass. |
| INV-02 Default deny | Pass | `policy_engine.authorize` checks capability presence and `allowed` before arguments or dispatch | Tests cover `UNKNOWN_CAPABILITY` and `CAPABILITY_NOT_GRANTED`, with no denied execution. |
| INV-03 Argument confinement | Partial | `ARGUMENT_SCHEMAS`, required/optional-field checks, IP/port validation, and protocol validation are implemented | Test covers missing `host`. Unexpected fields, wrong types, invalid IPs, invalid ports, and invalid protocols need systematic tests. |
| INV-04 Resource confinement | Partial | Policy code checks loopback/private IPs, protected users/processes/ports, and quarantine paths | No existing integration test exercises each protected-resource class. |
| INV-05 Denial non-execution | Pass | Broker returns before `execute_tool` on denial | Tests prove denied `isolate_host` leaves the action log unchanged, including via compatibility CLI. Broader generated coverage is still desirable. |
| INV-06 Allow-before-execute | Pass | Broker logs the decision before calling the registry and passes correlation context to the tool | The allowed-action test verifies the same experiment, run, and request IDs in the response, decision, and execution record. Pre-Phase-3 historical entries remain legacy records. |
| INV-07 Request/decision correlation | Pass | Client creates UUID; broker response and policy logger preserve it | `test_every_request_has_correlated_audit_record` validates matching request IDs for one allowed request. |
| INV-08 One decision per accepted request | Partial | `handle_request` calls `log_decision` once per protocol-valid request | Existing tests do not assert decision-log increments for every status under concurrency or failure. |
| INV-09 No fallback on broker failure | Untested | Client raises on socket connection failure; CLIs contain no local execution fallback | Add an integration test with no broker socket and assert unchanged action log. |
| INV-10 Evidence immutability | Untested | Investigation instructions require evidence preservation; baseline records evidence hashes | Add before/after evidence-tree hashing around complete incident runs. |
| INV-11 Policy immutability during a request | Untested | Policy is loaded during `authorize`; broker executes immediately after the decision | No file locking, immutable snapshot identifier, or concurrent policy-replacement test exists. |
| INV-12 Fixed dispatch | Partial | `tool_registry.py` maps fixed action strings to Python callables; production path contains no shell or subprocess invocation | Static inspection supports the property. Add generated action-name and metacharacter tests. |

## Trusted-computing-base validation

The code trace confirms the documented flow:

```text
broker.server
  -> protocol.parse_request
  -> executor.handle_request
  -> policy_engine.authorize
  -> policy_logger.log_decision
  -> tool_registry.execute_tool only after ALLOW
```

Observed alignment:

- The protocol requires exactly `request_id`, `action`, and `arguments`.
- Requests larger than 64 KiB are rejected before parsing.
- The policy defaults to denial for unknown and ungranted capabilities.
- Per-action argument schemas reject missing and unexpected fields.
- Tool selection uses a fixed dictionary of Python callables.
- No agent-provided string is passed to a shell in the production path.
- Broker policy records include component and request ID.
- Supplied agent-facing CLIs use the broker client.

Observed TCB limitations match the threat model:

- Broker, policy, and simulated tools run under the same OS identity.
- Tool implementation functions remain importable by arbitrary same-user Python
  code.
- Policy and local audit files are writable by that same user.
- The action log does not contain broker request IDs.
- Malformed protocol denials are not written to the policy decision log.

## Adversary-level assessment

| Level | Current evidence |
|---|---|
| A0 Benign or mistaken agent | Partially validated through malformed arguments and allowed/denied requests |
| A1 Evidence-content attacker | Demonstrated in Incident 01, but not yet automated as a controlled experiment |
| A2 Reasoning-layer attacker | Boundary supports arbitrary structured requests; representative unknown and denied requests pass tests |
| A3 Agent-runtime attacker | Raw protocol validation exists, but replay, concurrency, oversize, and fuzz testing remain incomplete |
| A4 Broker or host attacker | Explicitly unsupported by the current same-user PoC |

## Claim supported at this stage

The implementation and current tests support a limited claim:

> For representative known, unknown, malformed, and ungranted requests submitted
> through the documented interfaces, CyberBroker applies policy before dispatch
> and prevents tested denied requests from reaching simulated tools.

They do not yet justify claiming complete coverage of A0–A3 inputs, formal
verification, tamper resistance, replay protection, or OS-level non-bypassability.

## Validation gaps to carry into later phases

1. Test every protected-resource class and reason code.
2. Test broker absence and prove fail-closed CLI behavior.
3. Test malformed, oversized, duplicate, replayed, and concurrent requests.
4. Hash evidence before and after complete runs.
5. Define policy-snapshot semantics for one request.
6. Add generated/property-based tests for argument and action strings.
7. Separate application-boundary claims from future container-enforced claims.

These gaps are retained as research tasks rather than being silently interpreted as
successful validation.
