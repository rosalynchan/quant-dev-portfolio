# Building a Governed Data Agent for Quantitative Risk Workflows

## Abstract

Agent platforms are moving beyond chat into long-running workflows that can query enterprise data, execute code, and coordinate tools. In quantitative finance, that power is useful only when the system preserves metric definitions, data entitlements, temporal consistency, and deterministic numerical computation. This article proposes a minimal governed architecture for a Rates risk data agent and a two-hour experiment for testing whether a machine-readable semantic contract reduces hard failures.

## Why this matters

A request such as “show the desk’s largest DV01 concentration and explain the PnL move” appears simple, but it hides several contracts. DV01 has a currency and unit convention. Risk and PnL snapshots have timestamps. Trades belong to books and desks under entitlements. Missing values may mean unavailable data rather than zero. Curve sources can disagree.

An LLM can interpret intent, select tools, and explain results. It should not silently decide these contracts or become the calculator of record.

## Design principles

1. **Make the semantic contract executable.** Units, grain, valid aggregations, time zones, missing-data policy, and source precedence belong in versioned schema.
2. **Let deterministic code own numbers.** Python calculates DV01, PnL aggregates, coverage, and quality checks.
3. **Authorize before retrieval.** Disallowed fields and rows must never enter model context.
4. **Make time part of every answer.** Every result carries an as-of timestamp and rejects incompatible snapshots.
5. **Use typed failures.** Missing data, stale data, policy denial, schema mismatch, and tool failure are distinct outcomes.
6. **Make writes idempotent.** A retry with the same request identifier cannot duplicate an action.
7. **Make every result replayable.** Retain contract version, data hash, model version, prompt version, tool trace, and approvals.

## Quant scenario

The prototype uses a synthetic IRS risk snapshot containing trade, desk, currency, tenor, DV01, PnL, curve source, and quality status. Users ask for desk-level DV01, dominant tenor concentrations, explanations of PnL changes, and stale or incomplete records.

The dataset deliberately contains unit conflicts, stale timestamps, duplicate trades, missing sources, and a restricted field. All examples are synthetic and public-safe.

## Architecture

The workflow is:

1. Accept the user request.
2. Interpret intent and select a tool.
3. Apply the policy gate before retrieving data.
4. Resolve the relevant semantic contract.
5. Run deterministic Python validation and calculation.
6. Produce a restricted evidence package.
7. Let the LLM explain the approved evidence.
8. Store an audit event and the final result.

The deterministic layer performs schema validation, temporal validation, DV01 and PnL aggregation, and data-quality checks. The model never receives raw restricted columns.

## Example semantic contract

A minimal contract for DV01 should specify:

- unit: GBP per one-basis-point move;
- grain: trade and as-of timestamp;
- aggregation: sum;
- null policy: error;
- required fields: currency, as-of time, and curve source;
- maximum permitted snapshot age;
- allowed and denied fields for the current role.

The contract is intentionally small. It makes the most dangerous assumptions explicit and testable rather than attempting to reproduce an enterprise data catalog.

## Reliability controls

### Schema validation

Pydantic rejects invalid types, unknown units, missing keys, and unsupported quality states before analysis.

### Temporal validation

The tool rejects mixed snapshots unless a comparison operation explicitly permits them. Every result includes the exact as-of time.

### Entitlement enforcement

Policy removes forbidden columns and rows before retrieval. A denial can identify the policy rule but must never expose the protected value.

### Deterministic calculation

Aggregation and ranking use tested Python functions. The LLM receives structured output and does not recompute financial values.

### Source lineage

Every result records its source, contract version, transformation name, and data hash.

### Idempotency

Audit and write operations use the request identifier as an idempotency key.

### Fail-closed behavior

Unknown units, stale data, missing sources, or an unavailable policy service produce typed errors rather than approximate answers.

## Experiment method

Create 40–60 synthetic IRS risk rows and seed five failure classes:

- conflicting DV01 units;
- stale snapshots;
- duplicate trade identifiers;
- missing curve sources;
- unauthorized field requests.

Run ten questions in two conditions:

- **Bare schema:** the agent receives only column names and data.
- **Governed schema:** the agent also uses the versioned semantic contract.

All numerical answers are compared with an independent Python oracle. Each run emits JSONL telemetry containing the request ID, contract version, data hash, tool trace, result, and error class.

## Success criteria

The experiment passes when:

- all five seeded failure classes are detected;
- every returned number matches the Python oracle;
- governed results never omit unit or as-of time;
- every unauthorized request is denied without leaking a value;
- retries do not duplicate audit or write events;
- hard failures fall by at least 50% relative to the bare-schema condition;
- every run is replayable from its recorded metadata.

A model failure does not automatically fail the project. If the harness detects, blocks, and records it, the reliability design is working.

## What this demonstrates to a Quant employer

This is not another financial chatbot. It demonstrates the ability to translate Rates conventions into machine-readable contracts, separate probabilistic reasoning from deterministic calculation, enforce least privilege, build schema and data-quality controls, design idempotent observable workflows, and evaluate an agent using domain-specific invariants.

Those are the same engineering concerns that appear in risk dashboards, pricing pipelines, front-office analytics, and research platforms.

## Limitations

The prototype uses synthetic data and a deliberately small permission model. It does not reproduce production entitlements, legal retention requirements, market-data licensing, cross-region residency, or multi-vendor operations. Ten questions are enough for a smoke test, not a statistical claim about a model.

The semantic contract can also be wrong. Production governance requires ownership, review, change control, and contract-drift monitoring.

## Next steps

1. Add property-based tests for units, signs, and temporal ordering.
2. Introduce competing curve sources and a reconciliation policy.
3. Test prompt injection inside a data-quality note.
4. Add checkpoint and resume testing for interrupted runs.
5. Compare a fixed model with an automatically routed model while logging every routing decision.
6. Connect a read-only MCP server only after the local invariants pass.

## Publication status

This is a draft. Add measured experiment results, update the limitations from observed failures, and verify that no proprietary employer data or implementation detail is present before merging.