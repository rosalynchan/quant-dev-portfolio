# Evidence-Grounded Evaluation for Financial AI Agents

> **Draft status:** The experiment described below has not been run. All planned inputs are synthetic or public. Do not treat this article as investment advice or as evidence of production readiness.

Financial agents often look convincing long before they become reliable. A fluent answer can combine correct facts, unsupported causal claims, mismatched periods, and an uncited calculation without making the failure obvious. For a Quant Developer, the key question is therefore not only whether an answer is correct, but whether every material claim can be traced to admissible evidence and a reproducible computation.

## Why This Matters for Quant Work

Typical quantitative research tasks mix retrieval, normalization, calculation, and interpretation. A research assistant may need to compare two companies across reporting periods, explain a rates move, or connect a macro event to a portfolio exposure. These tasks are harder to evaluate than simple question answering because some conclusions are open-ended.

AgenticFinBench, released on 3 November 2026, evaluates 230 financial tasks across eight categories, two languages, and four complexity levels. Its reported results suggest that hallucination auditing can materially change rankings and that the agent harness may affect evidence grounding more than the selected model. That is a practical warning: changing models alone does not fix weak provenance.

## Design Principles

1. **Separate claims from prose.** Evaluate atomic factual, numerical, and causal claims rather than grading the answer as one block.
2. **Treat evidence as data.** Each claim should carry a source identifier, as-of date, retrieval timestamp, and transformation lineage.
3. **Keep calculations deterministic.** Python functions, not the language model, should perform arithmetic and normalization.
4. **Freeze the evaluation packet.** Model, prompt, tools, public documents, and hashes must be recorded for reproducibility.
5. **Score abstention positively.** When evidence is missing or periods are incomparable, the correct behavior is to stop or qualify the answer.
6. **Compare harnesses under controlled conditions.** Hold the model, temperature, task set, and tool permissions constant.

## Quant Scenario

The test scenario is a small public-data research packet containing synthetic rates observations and selected public company disclosures. Twelve questions cover three task families:

- direct retrieval, such as locating an as-of value;
- comparable-period analysis, such as normalizing units and dates;
- causal interpretation, where the agent must distinguish evidence from inference.

No private employer, client, portfolio, or trading data is used.

## Architecture

```text
Frozen task packet
        |
        v
Retrieval and Python tools
        |
        v
Agent answer + structured claims
        |
        v
Claim-to-evidence auditor
        |
        +--> citation validity
        +--> numerical oracle
        +--> unsupported-claim flags
        +--> audit log
```

The agent returns both prose and a machine-readable claim list:

```json
{
  "answer": "...",
  "claims": [
    {
      "claim_id": "c1",
      "type": "numeric",
      "text": "...",
      "evidence_ids": ["doc-03"],
      "calculation_id": "calc-02",
      "confidence": 0.82
    }
  ]
}
```

The auditor rejects missing source IDs, stale as-of dates, incompatible periods, and numbers that do not match the Python oracle. Causal language without direct support is labeled as inference rather than fact.

## Reliability Controls

- allowlisted, read-only tools;
- source and timestamp required for every material claim;
- schema validation before scoring;
- deterministic numerical oracle;
- explicit unit and period compatibility checks;
- prompt and document hashes in every run;
- structured errors instead of silent retries;
- no network access during the scored phase;
- separate logs for retrieval, computation, and model output.

## Two-Hour Experiment

The experiment compares two harness variants using the same model and task packet:

- **Baseline:** answer text plus optional citations.
- **Governed:** structured claims, mandatory evidence IDs, deterministic calculations, and abstention rules.

### Time Box

- 20 minutes: prepare 12 tasks and a frozen public/synthetic evidence packet.
- 30 minutes: add the claim schema and Python numerical oracle.
- 30 minutes: implement evidence coverage, citation validity, and unsupported-claim checks.
- 25 minutes: run both variants and capture latency and token use.
- 15 minutes: review failures and fill the results table.

### Success Metrics

The implementation succeeds only if:

- all 24 runs produce parseable records;
- ten seeded unsupported claims are detected in the auditor unit tests;
- numerical oracle tests pass at 100%;
- every accepted material claim has a valid source ID and as-of date;
- no tool reads outside the frozen evaluation packet;
- the governed harness reduces unsupported-claim rate by at least 20 percentage points, or the write-up clearly reports that it did not.

### Results Template

| Metric | Baseline | Governed |
|---|---:|---:|
| Parseable runs | TBD | TBD |
| Evidence coverage | TBD | TBD |
| Unsupported-claim rate | TBD | TBD |
| Numerical accuracy | TBD | TBD |
| Valid as-of dates | TBD | TBD |
| Median latency | TBD | TBD |
| Median token use | TBD | TBD |

## Experiment Method

Use one fixed model snapshot, zero or low temperature, identical tool permissions, and a fixed prompt budget. Run each task once for the initial time-boxed study. Store the task ID, model version, prompt hash, evidence-packet hash, structured claims, tool trace, scores, latency, and token use. Manually review every unsupported-claim flag because a small experiment cannot justify relying on an LLM judge alone.

## Limitations

This small test cannot establish production reliability. It uses only twelve tasks, one model snapshot, and synthetic or public data. Manual adjudication introduces subjectivity, and citation validity does not prove that a causal conclusion is sound. The experiment also does not cover prompt injection from live web pages, licensing constraints, entitlements, or market-data latency.

## Next Steps

After the first run:

1. replace placeholders with measured results and failure examples;
2. add repeated trials for the most variable tasks;
3. test period and unit mismatch adversarial cases;
4. add a second model only after the harness is stable;
5. keep the pull request in draft until the results and limitations are reviewed.

The durable lesson is simple: for financial agents, provenance is part of correctness. A stronger model may improve reasoning, but only a governed harness can make claims inspectable, reproducible, and safe to challenge.
