# Isolating Curve Methodology-Change PnL with Frozen Market Inputs

## Abstract

A Rates curve release can move portfolio PV even when market inputs are unchanged. New interpolation, bootstrap ordering, conventions, or numerical libraries may alter forwards and discount factors between calibration pillars. A clean PnL explain therefore needs a counterfactual valuation: run the old and new methodologies on exactly the same immutable market and trade snapshots. This article develops the methodology-versus-market bridge and translates it into practical engineering controls and requirement questions.

## Desk Context

A quant team replaces the interpolation method in a production curve builder. Both old and new curves reprice calibration instruments within approved bid/ask-aware tolerances, yet their interpolated forwards between seven and nine years differ.

Yesterday's official portfolio PV was GBP 1,250,000. After today's market move and the release, official PV is GBP 1,258,000. The endpoint gain is GBP 8,000, but that does not answer the trader's question: did the market generate the gain, or did the methodology release re-mark the portfolio?

## Change One Dimension at a Time

Represent valuation as $V(M,C)$, where $M$ is an immutable market snapshot and $C$ is a complete curve methodology version. The direct comparison

$$
V(M_1,C_{new})-V(M_0,C_{old})
$$

changes both dimensions. Introduce a counterfactual run of the new methodology on the old market:

$$
MethodologyPnL=
V(M_0,C_{new})-V(M_0,C_{old}).
$$

Then hold the new methodology fixed while moving the market:

$$
MarketPnL=
V(M_1,C_{new})-V(M_0,C_{new}).
$$

The bridge must reconcile:

$$
TotalPnL=MethodologyPnL+MarketPnL.
$$

This path is intuitive when the new methodology becomes official. For nonlinear instruments, alternative paths can allocate interaction differently, so the chosen ordering must be documented.

## Worked Numerical Example

Assume three full revaluations:

- Old methodology, old market: GBP 1,250,000
- New methodology, old market: GBP 1,264,000
- New methodology, new market: GBP 1,258,000

The methodology component is

$$
1{,}264{,}000-1{,}250{,}000
=+\text{GBP }14{,}000.
$$

This is a re-mark caused by implementation change, not yield-curve market PnL. The market component under one consistent methodology is

$$
1{,}258{,}000-1{,}264{,}000
=-\text{GBP }6{,}000.
$$

The bridge gives

$$
+14{,}000-6{,}000=+\text{GBP }8{,}000,
$$

equal to the official endpoint difference. The desk experienced a GBP 14,000 methodology gain and a GBP 6,000 market loss, not simply a GBP 8,000 market profit.

## What Frozen Market Really Means

Using data from “the same day” is insufficient. Both methodology runs must reference the same immutable snapshot: quote identifiers, values, sources, event times, revisions, fixings, calendars, FX inputs, and valuation timestamp.

The trade population must also be frozen. If the shadow run includes a late-booked trade absent from the old official run, the difference mixes methodology impact with activity PnL. Amendments, terminations, and lifecycle states must remain identical. Only one experimental dimension should change.

## Validity and Materiality Are Separate Gates

Calibration validation asks whether the new curve is economically acceptable. The methodology bridge asks how much portfolio value changes when the desk adopts it. Neither substitutes for the other.

A valid methodology may still have a material impact. Curves can agree at calibration pillars but differ between them, revaluing off-pillar cash flows and forward-starting or nonlinear trades. Conversely, small methodology PnL does not prove implementation correctness.

Release evidence should combine calibration checks, regression tests, portfolio impact distributions, and approval thresholds. Net impact is inadequate: a GBP 2,000 desk total may hide offsetting GBP 200,000 changes across books. Reports need drill-down by book, currency, product, tenor, and trade.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ValuationRun:
    run_id: str
    market_snapshot_id: str
    trade_snapshot_id: str
    methodology_version: str
    pv: Decimal


def methodology_bridge(old_run, shadow_run, new_run) -> dict:
    if old_run.market_snapshot_id != shadow_run.market_snapshot_id:
        raise ValueError("methodology leg changed market")
    if old_run.trade_snapshot_id != shadow_run.trade_snapshot_id:
        raise ValueError("methodology leg changed trades")
    if shadow_run.methodology_version != new_run.methodology_version:
        raise ValueError("market leg changed methodology")

    method = shadow_run.pv - old_run.pv
    market = new_run.pv - shadow_run.pv
    total = new_run.pv - old_run.pv

    if method + market != total:
        raise ValueError("non-reconciling bridge")

    return {
        "methodology_pnl": method,
        "market_pnl": market,
        "total_pnl": total,
    }
```

The methodology version must identify more than a Git commit. It should resolve builder code, configuration, conventions, interpolation choices, calibration definitions, and relevant dependency versions. Otherwise a supposedly repeatable shadow run can drift when a library or reference-data bundle changes.

## Data Quality and Production Considerations

The most relevant controls are:

- **Immutable inputs:** lock market and trade snapshot identifiers for the methodology leg.
- **Complete lineage:** capture code, configuration, conventions, and dependencies as one versioned bundle.
- **Reconciliation:** require methodology plus market components to equal the endpoint difference.
- **Impact distribution:** inspect book, tenor, product, and trade-level changes, not just net total.
- **Controlled rollback:** restore the complete prior bundle; reverting one flag may create a hybrid state.

A common failure is letting the shadow builder read a live quote cache. Its methodology PnL then changes on every rerun. Another is displaying only net GBP 8,000 and hiding the GBP 14,000 methodology gain and GBP 6,000 market loss.

Useful observability includes shadow-run completion rate, snapshot mismatch count, unreconciled bridge amount, impact-threshold breaches, and results by methodology version.

## Requirement Discovery and Interview Questions

Before implementing “compare old and new curves,” clarify:

- Which immutable market snapshot and valuation timestamp should be used?
- Must fixings, reference data, and trade population also be frozen?
- What belongs to a methodology version?
- Is impact required by trade, book, tenor, currency, or product?
- Which thresholds require trader, quant, or model-control approval?
- Will rollout use simultaneous cutover, canary books, or parallel running?
- When does the new method become official?
- How should rollback appear in PnL explain?
- Should dashboards separate METHODOLOGY_CHANGE from MARKET_MOVE?

A strong interview answer is concise: “I would freeze market and trade snapshots, value them under both versioned methodologies, then keep the new methodology fixed for the market leg. I would preserve full lineage and reconcile both components to the official endpoint.”

## Key Takeaways

- Direct before-and-after PV mixes market and methodology effects.
- A frozen-input counterfactual isolates methodology-change PnL.
- The market leg must use one fixed methodology.
- Market and trade snapshots must both be immutable.
- Calibration validity and portfolio materiality are separate gates.
- Net impact can hide concentrated book or tenor changes.
- Release and rollback must version the complete methodology bundle.

