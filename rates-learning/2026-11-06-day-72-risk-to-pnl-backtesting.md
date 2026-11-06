# Risk-to-PnL Backtesting: Does Yesterday’s DV01 Explain Today’s Curve PnL?

## Abstract

A DV01 report can be numerically stable and still fail to describe the economic behavior of a rates portfolio. Risk-to-PnL backtesting closes that gap: yesterday’s bucketed DV01 is combined with observed quote moves to produce a first-order PnL estimate, which is then compared with a full revaluation of the same trade population. The residual is not automatically a model defect, but it is a powerful control signal. This article shows the calculation, the data contracts needed to make it meaningful, and the production questions a front-office developer should resolve before calling PnL “explained.”

## Desk Context

Suppose a trader sees a stable 2Y/5Y/10Y DV01 report at yesterday’s close. The curve moves overnight. Multiplying the stored risk by the observed quote changes predicts a GBP 27,000 loss, while full revaluation produces a GBP 29,400 loss.

The desk question is not merely, “What is the residual?” It is, “Is the extra GBP 2,400 a plausible nonlinear effect, or did we compare incompatible market snapshots, quote definitions, or trade populations?”

This is the role of **risk-to-PnL backtesting**. It is a quality test for the risk representation, not a trading forecast and not investment advice.

## From Stable Risk to Economically Useful Risk

For a static portfolio observed at time $t_0$, store signed DV01 by curve bucket. At $t_1$, calculate changes in the same market quotes, expressed in basis points. The first-order estimate is

$$
\mathrm{PredictedPnL}=\sum_i \mathrm{DV01}_{i,t_0}\Delta q_i.
$$

The sign convention matters. Here, a bucket DV01 is the change in portfolio PV when that quote increases by one basis point. No additional minus sign should be introduced later. A system that stores positive duration magnitudes cannot be combined safely with a system that expects signed PV changes without an explicit conversion.

The comparison value should be a full revaluation of the same $t_0$ trade population under the $t_1$ market:

$$
\mathrm{ActualPnL}=PV(t_1\text{ market},t_0\text{ book})-PV(t_0\text{ market},t_0\text{ book}).
$$

Then

$$
\mathrm{Residual}=\mathrm{ActualPnL}-\mathrm{PredictedPnL}.
$$

DV01 is a local, first-order approximation. A residual can therefore contain convexity, cross-factor interactions, and other nonlinear effects. It can also expose a far less sophisticated failure: different snapshots, missing buckets, inconsistent units, or a changed book.

The most useful initial test is a **static-book backtest**. If the actual PnL comes from a live book, new trades, amendments, terminations, cash events, and fees can enter the result. Those effects should be separated as activity PnL rather than left for DV01 to “explain.” Carry, theta, fixing effects, and roll-down also need an explicit scope decision.

## Worked Numerical Example

Assume yesterday’s closing risk and today’s official quote changes are:

| Bucket | DV01 (GBP/bp) | Quote move (bp) | First-order PnL (GBP) |
|---|---:|---:|---:|
| 2Y | -5,000 | +2 | -10,000 |
| 5Y | +8,000 | -1 | -8,000 |
| 10Y | -3,000 | +3 | -9,000 |

The predicted PnL is

$$
-10{,}000-8{,}000-9{,}000=-27{,}000\text{ GBP}.
$$

Full revaluation of the same trade snapshot under today’s market gives GBP -29,400. The residual is therefore

$$
-29{,}400-(-27{,}000)=-2{,}400\text{ GBP}.
$$

A simple explained ratio is

$$
1-\frac{|\mathrm{Residual}|}{\max(|\mathrm{ActualPnL}|,\mathrm{floor})}=91.84\%.
$$

The ratio says that first-order curve risk captures most of the move, but it should not be the only acceptance test. A GBP 2,400 residual may be material for one book and immaterial for another. A robust control combines an absolute threshold with a relative threshold and uses a denominator floor when actual PnL is close to zero.

## Engineering Design

The input is not just two arrays. A risk snapshot should carry `risk_asof`, `market_snapshot_id`, `trade_snapshot_id`, `taxonomy_version`, and signed DV01 by bucket. A move set should identify its start and end market snapshots, quote taxonomy, unit, and bucket changes. The result should preserve this lineage.

```python
def backtest_curve_risk(risk, moves, actual_pnl, pnl_floor=1_000.0):
    if risk.taxonomy_version != moves.taxonomy_version:
        return {"status": "INCOMPLETE", "reason": "TAXONOMY_MISMATCH"}

    missing = set(risk.dv01_by_bucket) ^ set(moves.bp_by_bucket)
    if missing:
        return {"status": "INCOMPLETE", "missing_buckets": sorted(missing)}

    predicted = sum(
        risk.dv01_by_bucket[b] * moves.bp_by_bucket[b]
        for b in risk.dv01_by_bucket
    )
    residual = actual_pnl - predicted
    explained = 1.0 - abs(residual) / max(abs(actual_pnl), pnl_floor)

    status = "PASS" if abs(residual) <= 5_000 and explained >= 0.90 else "REVIEW"
    return {
        "status": status,
        "predicted_pnl": predicted,
        "actual_pnl": actual_pnl,
        "residual": residual,
        "explained_ratio": explained,
        "lineage": {
            "risk_market": risk.market_snapshot_id,
            "move_start": moves.start_snapshot_id,
            "move_end": moves.end_snapshot_id,
            "trade_snapshot": risk.trade_snapshot_id,
        },
    }
```

The exact thresholds are desk policy, not universal constants. More importantly, a missing bucket must never be silently filled with zero. “Unknown exposure” and “zero exposure” are different states; conflating them creates a falsely reassuring explain ratio.

## Data Quality and Production Considerations

Four controls carry most of the value:

1. **Snapshot alignment.** The risk market snapshot must equal the move set’s start snapshot. Both endpoints should be immutable and replayable.
2. **Static trade population.** Full revaluation must use the same trade snapshot, or the result must include an explicit activity adjustment.
3. **Taxonomy, unit, and sign consistency.** Bucket labels, bumped quote types, basis-point units, and signed-DV01 definitions must match.
4. **Completeness and thresholds.** Failed or missing buckets produce `INCOMPLETE`, while complete results use both absolute and relative tolerances.

Monitoring should show predicted PnL, actual PnL, residual, top bucket contributions, snapshot lineage, and the status reason. A persistent signed residual is especially informative: repeated underprediction in the same direction may indicate missing convexity or a systematic data mismatch, even when each day individually passes.

Useful tests include a missing bucket, a taxonomy-version mismatch, near-zero actual PnL, an intentionally reversed sign, and a trade added between snapshots. These cases test the control semantics, not just the arithmetic.

## Requirement Discovery and Interview Questions

Before implementing “use risk to explain PnL,” clarify:

- Is the target a static-book market move or live-book desk PnL?
- Which PnL is authoritative: close-to-close full revaluation, an intraday snapshot, or accounting PnL?
- Are moves measured in calibration-instrument quotes or zero rates? They must match the risk factors that were bumped.
- Are carry, theta, fixings, cash, and trade activity in scope?
- Are thresholds applied by trade, book, or desk, and are they absolute, relative, or both?
- Do nonlinear products require a gamma-aware backtest rather than a forced DV01 explain?

A strong interview answer is: “I first reconcile market snapshots, quote taxonomy, units, signs, and trade population. Only after those controls pass do I attribute the remaining residual to nonlinear or cross-factor effects.”

## Key Takeaways

- Bump-size stability establishes numerical robustness; risk-to-PnL backtesting establishes economic usefulness.
- The clean comparison uses yesterday’s signed bucket risk, observed moves in the same quotes, and full revaluation of the same trade population.
- The residual is a diagnostic signal, not automatically an error and never a number to hide in a plug.
- Lineage, completeness states, and explicit scope decisions are as important as the dot product.
- A production result should return `PASS`, `REVIEW`, or `INCOMPLETE` with evidence, not a context-free float.

