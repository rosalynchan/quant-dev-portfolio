# Fixing Corrections: Recognize the Revision Delta, Not the Surprise Twice

## Abstract

The first official fixing replaces a projected rate with an observed one. A later correction replaces that observation, not the original forecast again. Confusing these two transitions can double count PnL even when each coupon calculation is individually correct. This article develops a revision-delta bridge for an unpaid linear term-rate coupon, demonstrates its reconciliation to the original forecast, and translates the economics into an idempotent processing contract. The focus is recognition and reproducibility, not a universal accounting or benchmark-publication policy.

## The Desk Problem

A receive-floating coupon was projected at 4.20%. The first official observation was 4.24%, producing a positive fixing explain. Later, the observation was corrected to 4.23%.

The trader asks whether the corrected 4.23% represents another positive fixing surprise. Relative to the forecast it does, but relative to the value already recognized it is a negative correction. Adding both forecast-to-observation gains would overstate the cumulative result.

The essential distinction is between a level and a change. A corrected valuation is a new level. Incremental PnL is the difference from the previously recognized level.

## A Controlled Revision Bridge

Restrict the example to an unpaid, uncapped, uncompounded term-rate coupon. Freeze valuation time, trades, accrual fraction, discount factor, and every other pricing input. Let N be notional, a accrual fraction, D the payment discount factor, F the saved forecast, L1 the original observation, and L2 the corrected observation. Receipt has sign s equal to positive one; payment has negative one.

The first fixing component is

$$
P_1=sNaD(L_1-F)
$$

The correction component is

$$
P_c=sNaD(L_2-L_1)
$$

Their sum is the corrected cumulative fixing effect:

$$
P_1+P_c=sNaD(L_2-F)
$$

The identity is deliberately narrow. For a compounded coupon, optional coupon, or settlement-in-advance instrument, use controlled full revaluation of the affected cashflow under the two revisions. Do not force a linear shortcut onto a different payoff.

The common discount state also matters. If the correction arrives on a later day and discounting has changed, distinguish the historical restatement from the current valuation impact. They may not have the same amount.

## Worked Numerical Example

Consider these generic illustrative inputs:

| Input | Value |
|---|---:|
| Receive-floating notional | GBP 100,000,000 |
| Accrual fraction | 0.25 |
| Frozen payment discount factor | 0.99 |
| Saved forecast | 4.20% |
| Original fixing | 4.24% |
| Corrected fixing | 4.23% |

The first observation exceeds forecast by four basis points. Its discounted PnL is GBP +9,900.

The correction lowers the rate by one basis point. The incremental correction is

$$
100{,}000{,}000\times0.25\times0.99\times(-0.0001)
=-2{,}475
$$

Cumulative fixing PnL becomes GBP +7,425, which equals the three-basis-point difference between corrected fixing and forecast.

| Component | GBP |
|---|---:|
| Original fixing recognition | +9,900 |
| Incremental correction | -2,475 |
| Corrected cumulative fixing PnL | +7,425 |

The incorrect implementation adds GBP +7,425 to the already recognized GBP +9,900, producing GBP +17,325. Every individual rate comparison can look sensible while the recognition logic is wrong.

A full replacement report may show only the corrected cumulative GBP +7,425, provided it clearly supersedes the earlier report. A delta stream instead publishes GBP -2,475. Mixing replacement semantics and additive consumer behavior creates the same double-counting failure.

## Effective Time and Known-At Time

The correction belongs to the same index observation date as the original fixing. Its arrival time tells us when the system learned the corrected value. These answer different questions.

An as-observed replay should reproduce the original report before the correction was known. A corrected-history view can use the revised observation. Neither should silently overwrite the other.

For a correction crossing an official reporting cutoff, the desk must choose an approved restatement or adjustment workflow. The economic reconciliation does not decide which business date owns the reporting entry.

A second boundary is payment. This article assumes the coupon remains unpaid. If settlement has already occurred, a revised contractual amount may create a settlement adjustment receivable or payable. Reopening the original payment blindly can duplicate cash. That case needs a separately defined settlement workflow.

## Engineering Connection

Use an immutable observation key and a monotonic internal accepted revision. Vendor revision formats can be mapped into this internal sequence. Duplicates must not create new economics.

```python
def apply_fixing_revision(state, event, pv_for_rate):
    if event.observation_key != state.observation_key:
        raise ValueError("observation mismatch")
    if event.revision < state.revision:
        return {"status": "IGNORED_OLD_REVISION"}
    if event.revision == state.revision:
        if event.rate != state.rate:
            raise ValueError("conflicting same revision")
        return {"status": "DUPLICATE", "pnl_delta": 0}
    if event.supersedes_revision != state.revision:
        return {"status": "REVISION_GAP"}

    delta = pv_for_rate(event.rate) - pv_for_rate(state.rate)
    return {
        "status": "APPLY",
        "expected_revision": state.revision,
        "new_revision": event.revision,
        "new_rate": event.rate,
        "pnl_delta": delta,
    }
```

This is a decision function, not the complete transaction. The storage layer must atomically compare the expected revision, persist the new state, and record the outgoing delta, typically with an outbox. Otherwise a crash can persist the revision without delivering PnL, or deliver PnL twice.

The valuation callback must use a fixed comparison context. Fetching a new live discount curve between its two calls contaminates correction PnL with market movement.

## Selective Production Controls

Four controls are particularly valuable:

1. Preserve revision lineage. Store the observation key, old and new values, superseded revision, publication time, and ingestion time.
2. Separate delta and replacement contracts. Reports that supersede earlier totals must never be consumed as additive PnL events.
3. Commit state and output consistently. Use compare-and-set revision handling with transactional output recording.
4. Define cutoff and payment boundaries. Escalate cross-cutoff corrections and already-settled coupons into approved workflows.

Tests should cover duplicate delivery, an older revision arriving late, a conflicting value under the same revision, a missing predecessor, and a simulated crash around output publication. Replaying the accepted sequence should produce the same cumulative economic result.

## Desk Questions and Takeaways

Ask whether consumers expect incremental adjustments or replacement totals, which valuation context defines the correction, whether the affected coupon is unpaid, and who approves a cross-day restatement. Also clarify how vendor corrections map to internal revision identities.

A useful interview answer is: “I recognize the corrected observation against the previously accepted observation, preserve the forecast anchor for cumulative reconciliation, and make revision state plus PnL output atomic. A correction is not a second forecast surprise.”

The main lesson is simple: value levels can be replaced; PnL deltas must telescope. The original fixing effect plus every accepted correction should equal the latest accepted valuation minus the original forecast valuation under the same comparison context.

All figures are generic educational examples without confidential employer or client information. Nothing here constitutes investment advice.
