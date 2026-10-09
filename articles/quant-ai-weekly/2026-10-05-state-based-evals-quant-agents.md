# State-Based Evals for Quant Agents: Verify the Database, Not the Claim

> **Draft status:** The experiment described below has not been run. All records and formulas are synthetic. Do not merge until measured results, failure cases, and limitations have been added.

## Design principles

An agent that changes business state should be evaluated on the state it leaves behind, not on whether its final message sounds confident. A correct-looking response can hide a missing write, an incorrect version increment, a duplicated record, or an unintended change elsewhere in the database.

The design follows five principles:

1. Define the expected terminal state before running the agent.
2. Grade deterministic state with executable assertions.
3. Check forbidden side effects as well as required changes.
4. Reset every trial to the same initial state.
5. Measure repeated reliability rather than preserving a single successful demo.

## Quant scenario

Consider a synthetic configuration service for quantitative formulas. Each record contains a formula identifier, metric name, expression, unit, effective date, active flag, and version. An agent receives requests to create, modify, or deactivate formulas.

The agent is allowed to select tools and explain outcomes. It is not allowed to bypass schema validation, silently change units, overwrite history, or modify unrelated rows.

This resembles many financial engineering workflows without using any proprietary implementation or data: risk-rule configuration, curve metadata maintenance, data-quality exception handling, and research-pipeline controls.

## Architecture

The test harness contains four components:

1. **SQLite state store** containing synthetic formula records.
2. **Tool layer** exposing validated create, update, deactivate, and read operations.
3. **Agent runner** executing one request against an isolated database copy.
4. **State grader** comparing the terminal database snapshot with a golden state and checking forbidden effects.

Each trial starts from the same fixture. The grader executes SQL and Python assertions after the agent stops. The natural-language response is retained for analysis but is not accepted as proof of completion.

## Reliability controls

The harness enforces:

- schema validation before any write;
- explicit units and effective dates;
- append-only version history;
- transactions and rollback for invalid requests;
- idempotency keys for retries;
- assertions covering both target and non-target rows;
- isolated database state for every trial;
- hashes of initial and final snapshots;
- structured tool traces for diagnosing failures.

For tasks with more than one valid trajectory, assertions focus on the required effects rather than prescribing an exact tool-call sequence.

## Experiment method

The experiment uses eight synthetic tasks:

- two valid create requests;
- two valid updates requiring a version increment;
- one deactivation of an old version;
- one request with a required field missing;
- one request containing a unit conflict;
- one repeated request testing idempotency.

Each task will run five times, producing 40 trials. The harness stores the final response, tool trace, terminal database snapshot, and executable assertion results.

Planned success criteria are:

- terminal-state assertions executed for 40 of 40 trials;
- 100% equality with the golden state for valid tasks;
- no database change in all ten invalid-task trials;
- five of five idempotency trials create no duplicate record;
- zero changes to non-target rows;
- `Pass^5` of at least seven of eight tasks;
- a false-completion rate of zero, where false completion means the agent claims success but the terminal state fails.

These are targets, not completed results.

## Why final-answer grading is insufficient

A language-based grader may approve an answer such as “The formula was updated successfully.” It cannot prove that the write occurred, that the version advanced correctly, or that unrelated rows remained unchanged.

Tool-call grading is also incomplete. A valid call can return an error, be rolled back, or create an unintended side effect. The persistent terminal state is the closest available evidence that the workflow actually completed.

## Limitations

A small SQLite harness cannot reproduce the concurrency, authorization, retention, and operational complexity of a production financial platform. Golden-state assertions can also be too rigid when several outcomes are legitimately valid.

Passing the harness does not establish suitability for live risk, trading, or client workflows. Human review, access controls, temporal validation, monitoring, and deployment-specific testing remain necessary.

## Next steps

After running the experiment, this draft should be updated with pass@1, `Pass^5`, false-completion rate, representative state diffs, diagnosis time, and at least one failed trajectory.

A later iteration can add concurrent writes, optimistic locking, retry injection, and source-aware provenance checks. Only measured results should be promoted from targets to claims.

## Sources

- [Microsoft and Hugging Face: The Agent Said It Was Done. The Database Disagreed, October 3, 2026](https://huggingface.co/blog/microsoft/thinkingbox)
- [ThinkingBox paper](https://arxiv.org/abs/2608.19741)
- [ThinkingBox framework](https://github.com/microsoft/thinkingbox)
- [ThinkingBox data and MCP tool servers](https://github.com/microsoft/thinkingbox-data)
- [Source-Aware Verification for MCP Agents, September 29, 2026](https://huggingface.co/blog/MultiverseComputingCAI/getting-the-source-right-not-just-the-fact-source)
