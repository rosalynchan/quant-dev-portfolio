# Observable Quant Agents: Tracing Decisions Without Leaking Financial Data

> **Draft status:** The experiment described below has not been run. All examples use synthetic data. Do not merge this article until measured results, failure cases, and limitations have been added.

## Design principles

A production Quant agent should be observable before it is autonomous. Observability does not mean recording every prompt or copying market data into a monitoring platform. It means preserving enough structured evidence to reconstruct what the agent did without exposing the underlying sensitive content.

The design follows five principles:

1. Trace decisions, not raw secrets.
2. Keep numerical computation in deterministic Python tools.
3. Record permission checks as first-class events.
4. Separate model behavior from tool and data failures.
5. Make every run reproducible through versioned configuration and hashed inputs.

## Quant scenario

Consider a small agent that answers questions about synthetic rates positions. It loads a position snapshot, calculates DV01, identifies missing inputs, and explains the result. The agent may choose tools, but it may not calculate risk figures itself or access files and network destinations outside an allowlist.

The key operational question is not only whether the final DV01 is correct. We also need to know:

- which model and prompt version initiated the run;
- which data snapshot and as-of date were used;
- which tools were called and with which validated parameters;
- whether any permission request was denied;
- whether the deterministic oracle accepted the result;
- where latency and retries occurred.

## Architecture

The minimal architecture has four layers:

1. **Agent layer:** interprets the request and selects tools.
2. **Policy layer:** checks file, network, and credential permissions.
3. **Deterministic tool layer:** loads synthetic positions, calculates DV01, and validates outputs.
4. **Telemetry layer:** emits OpenTelemetry-compatible spans to a local collector or test exporter.

A root `agent.run` span links child spans such as `model.request`, `policy.check`, `tool.calculate_dv01`, and `validation.oracle`. Each span records metadata such as `run_id`, `model_id`, `tool_name`, `policy_decision`, `input_hash`, `as_of`, `validation_status`, and `latency_ms`.

Raw prompts, position values, credentials, and customer identifiers are excluded.

## Reliability controls

The experiment will enforce the following controls:

- deny-by-default file and network policies;
- schema validation for every tool argument;
- deterministic Python calculations for all numerical claims;
- source and as-of metadata on every answer;
- idempotency keys for retried tool calls;
- input hashing instead of raw input capture;
- explicit error spans rather than silent fallback;
- a telemetry redaction test using a canary secret.

A trace is useful only if it is complete and safe. Missing spans create blind spots, while excessive capture creates a new data-leakage channel.

## Experiment method

The test set contains 12 synthetic scenarios:

- six valid DV01 questions;
- two cases with missing market or position data;
- two attempts to read a forbidden file;
- one request to call an unauthorized network destination;
- one injected tool failure.

The same agent configuration will run every scenario. A Python oracle will independently calculate expected values. Two failures will be injected deliberately so that diagnosis time can be measured.

The planned success criteria are:

- complete root and child traces for 12 of 12 runs;
- 100% agreement with the Python oracle on valid scenarios;
- all three unauthorized access attempts blocked;
- zero raw prompts, positions, credentials, or canary secrets in telemetry;
- both injected failures localized from traces within three minutes;
- no more than 15% p95 latency overhead from tracing.

These are targets, not completed results.

## Limitations

This is a local contract test, not evidence that an agent is safe for live trading, production risk, or regulated client data. Synthetic scenarios cannot reproduce every failure mode. A local exporter does not test the access controls, retention policies, or cross-border data implications of a production observability backend.

Trace completeness also does not guarantee semantic correctness. An agent can produce a perfectly observable but wrong decision. Numerical oracles, temporal data controls, repeatability tests, and human approval remain necessary.

## Next steps

After the experiment, the article should be updated with measured trace coverage, latency overhead, diagnosis time, redaction failures, and representative failure traces. If the contract passes, the next iteration should add retry and idempotency tests, then compare two models using the same policy and telemetry layer.

The goal is not to maximize agent autonomy. It is to make every increase in autonomy measurable, reviewable, and reversible.

## Sources

- [OpenTelemetry in the GitHub Copilot app, September 22, 2026](https://github.blog/changelog/2026-09-22-opentelemetry-in-the-github-copilot-app/)
- [Default Enablement of Copilot Features, September 24, 2026](https://github.blog/changelog/2026-09-24-default-enablement-of-copilot-features-for-copilot-business-and-enterprise/)
- [GitHub Copilot Weekly Releases, September 25, 2026](https://github.blog/changelog/2026-09-25-github-copilot-weekly-releases-september-21/)
