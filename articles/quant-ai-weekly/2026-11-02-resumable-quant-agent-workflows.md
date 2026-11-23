# Building Resumable Quant Agent Workflows with Checkpoint Contracts

## Abstract

Long-running coding and research agents are moving from single interactive sessions to resumable workflows that can continue across devices, clients, and execution environments. For quantitative engineering, this changes the reliability problem. An agent must not merely remember the conversation; it must resume from a verifiable execution state without duplicating writes, using stale market data, weakening permissions, or silently changing its assumptions.

This draft proposes a checkpoint contract for a synthetic rates-data workflow. The contract records immutable inputs, completed stages, tool permissions, output checksums, and audit identifiers. A two-hour experiment compares uninterrupted runs with interrupted-and-resumed runs. Results are intentionally left pending until the experiment is executed.

## Why Resumability Matters in Quant Engineering

A realistic quant workflow may fetch market data, validate timestamps and units, calculate risk, generate an explanation, and persist an audit record. These stages do not always finish in one session. Compute may stop, a network call may fail, a human may pause the task, or the agent may move between local and cloud environments.

Naive conversational memory is insufficient. If the agent resumes from prose alone, it may repeat a write, recompute against a different snapshot, or continue under permissions that differ from the original run. The safe unit of recovery is therefore not the chat transcript. It is a versioned checkpoint tied to deterministic data and policy state.

## Design Principles

1. **Checkpoint facts, not intentions.** Store completed operations and their verified outputs, not a natural-language claim that a stage is done.
2. **Bind every checkpoint to immutable inputs.** Record an as-of timestamp, dataset hash, configuration hash, and code version.
3. **Preserve least privilege across resume.** A resumed run must never inherit broader file, network, or credential access than the original run.
4. **Make writes idempotent.** Every externally visible mutation needs an idempotency key and a terminal-state assertion.
5. **Revalidate before continuation.** A checkpoint is a proposal to resume, not automatic authority to continue.
6. **Keep the model outside numerical truth.** Python functions calculate risk and quality metrics; the model selects tools and explains verified outputs.

## Quant Scenario

The example workflow calculates portfolio DV01 from synthetic positions and curve data:

1. load positions and curve snapshots;
2. validate schema, units, source, and as-of timestamps;
3. calculate instrument and portfolio DV01 using deterministic Python;
4. write one audit event;
5. generate a cited explanation from the verified result.

The interruption occurs after validation but before calculation. The resumed run must produce the same terminal state as an uninterrupted control run.

## Architecture

A small orchestrator owns the workflow state. Deterministic Python tools perform data loading, validation, calculation, and persistence. The language model may decide which approved tool to call next, but it cannot edit the checkpoint directly.

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Checkpoint:
    run_id: str
    stage: Literal["loaded", "validated", "calculated", "committed"]
    dataset_hash: str
    config_hash: str
    policy_hash: str
    as_of: str
    output_checksum: str | None
    audit_id: str | None

def can_resume(checkpoint: Checkpoint, current: dict) -> bool:
    return (
        checkpoint.dataset_hash == current["dataset_hash"]
        and checkpoint.config_hash == current["config_hash"]
        and checkpoint.policy_hash == current["policy_hash"]
        and checkpoint.as_of == current["as_of"]
    )
```

The persistence layer uses `run_id + stage` as an idempotency key. A second attempt to commit the same stage returns the existing result rather than creating another event.

## Reliability Controls

### Input and time controls

The checkpoint stores the dataset checksum and as-of timestamp. Any change forces a fresh run. This prevents a resumed task from mixing positions from one time with curves from another.

### Permission controls

The policy hash covers allowed paths, network destinations, and credential scopes. Resume is rejected when the current environment is broader or materially different. The workflow should request explicit approval instead of silently adopting new access.

### Exactly-once visible effects

Exactly-once execution is difficult, but exactly-once visible effects are practical. Each audit write uses a stable idempotency key, and the evaluator checks the terminal database state rather than trusting the agent's final message.

### Numerical oracle

A separate Python function calculates expected DV01. The agent output passes only when its structured numbers match the oracle and include source and as-of metadata.

### Auditability

Every transition records the previous stage, next stage, tool name, input hash, output checksum, decision, and timestamp. The audit log must be append-only for the experiment.

## Two-Hour Experiment

Use only synthetic positions and curves. Implement four deterministic tools: `load_inputs`, `validate_inputs`, `calculate_dv01`, and `commit_audit`.

Run twelve cases:

- three uninterrupted controls;
- three interruptions after loading;
- three interruptions after validation;
- one resume with changed input data;
- one resume with a changed permission policy;
- one duplicate commit attempt.

Compare the terminal state of every successful resumed run with its uninterrupted control.

### Success criteria

- successful resumed runs match the Python oracle exactly;
- three repeated control/resume pairs produce identical output checksums;
- the audit store contains exactly one commit event per run;
- changed input and changed policy checkpoints are both rejected;
- no restricted file, network, or credential access occurs;
- every rejection contains a machine-readable reason code;
- all outputs include source and as-of metadata.

No performance or reliability result should be claimed until these cases have been executed.

## Relationship to Current Agent Evaluations

Recent financial-agent benchmarks reinforce two lessons. First, strong research presentation does not guarantee predictive performance. Second, evaluation criteria must preserve time cutoffs, evidence, calculations, and assumptions. A checkpoint contract complements those benchmarks by testing operational continuity: whether the same evidence and controls survive interruption and resume.

## Limitations

This experiment uses a small synthetic workflow, not a production trading or risk system. It does not prove distributed exactly-once execution, resilience to infrastructure partitions, or suitability for autonomous investment decisions. A checksum proves that bytes match, not that a financial assumption is economically correct. Human review remains necessary for material decisions, permission changes, and ambiguous business rules.

## Next Steps

After the experiment, add measured pass/fail results, failure traces, and the exact checkpoint schema. The next useful extension is a time-aware retrieval checkpoint that records document versions and prevents a resumed research agent from seeing information published after the original decision time.

## References

- [GitHub: Work from anywhere with a connected Copilot cloud experience](https://github.blog/changelog/2026-10-28-work-from-anywhere-with-a-new-connected-copilot-cloud-experience/)
- [GitHub Copilot in VS Code: Universe releases](https://github.blog/changelog/2026-10-28-github-copilot-in-vscode-universe-releases/)
- [FinAutoRubric](https://arxiv.org/abs/2609.35744)
- [Investor's Last Exam](https://arxiv.org/abs/2610.38342)

This article is an engineering experiment using synthetic data. It contains no investment advice and no confidential employer information.
