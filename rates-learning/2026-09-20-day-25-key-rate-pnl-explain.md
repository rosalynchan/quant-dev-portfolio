# Explaining Swap-Hedge PnL with Key-Rate DV01

## Abstract

A hedge recommendation is incomplete until its realised PnL can be explained. This article shows how a quant developer can use frozen opening key-rate DV01 and aligned curve-node moves to build a daily PnL bridge for a swap-hedged bond portfolio. The example separates curve PnL, carry, and residual, then translates the methodology into an auditable Python design.

## Desk Context

The previous hedge left rounded key-rate DV01 of +GBP 1,470/bp at 5Y, -GBP 1,130/bp at 7Y, and +GBP 1,910/bp at 10Y.

During the official close-to-close window, the 5Y rate rises 2bp, the 7Y rate falls 1bp, and the 10Y rate rises 3bp. Carry is +GBP 600, while actual clean PnL is +GBP 10,650.

The trader asks: “The hedged book made GBP 10.65k. Can the opening key-rate risk explain it?”

## The Key-Rate PnL Bridge

For a frozen opening population:

$$
CurvePnL\approx\sum_i KRDV01_i\Delta r_i
$$

Here, key-rate DV01 is the PV change when the relevant node rises by 1bp, and the market move is close minus open in basis points. Positive risk times a positive move produces positive PnL. Negative risk times a negative move also produces positive PnL.

Bucketed explain is preferable to total DV01 times an average move. A curve can steepen, flatten, or twist; averaging destroys the structure that the hedge was designed to manage.

A compact bridge is:

$$
ActualPnL=CurvePnL+CarryPnL+OtherExplained+Residual
$$

This lesson keeps other explained components at zero to focus on curve mapping and carry.

## Worked Numerical Example

$$
PnL_{5Y}=1{,}470\times2=+GBP\ 2{,}940
$$

$$
PnL_{7Y}=(-1{,}130)\times(-1)=+GBP\ 1{,}130
$$

$$
PnL_{10Y}=1{,}910\times3=+GBP\ 5{,}730
$$

Therefore:

$$
CurvePnL=2{,}940+1{,}130+5{,}730=+GBP\ 9{,}800
$$

Adding carry gives:

$$
ExplainedPnL=9{,}800+600=+GBP\ 10{,}400
$$

Against actual clean PnL of GBP 10,650:

$$
Residual=10{,}650-10{,}400=+GBP\ 250
$$

With an absolute tolerance of GBP 500, the bridge is reconciled.

An explain ratio can be defined as:

$$
ExplainRatio=1-\frac{|Residual|}{\max(|ActualPnL|,\epsilon)}
$$

The result is approximately 97.65%. This ratio becomes unstable when actual PnL is near zero, so controls should also use an absolute threshold.

## Why Opening Risk Matters

Daily PnL measures value change from opening to closing snapshot. Closing risk contains information created during the window: market moves may change sensitivities, trades may be booked or closed, swaps age through fixings and cash flows, and nonlinear exposure evolves.

Using closing risk to explain the full day introduces hindsight. The normal first-order methodology is a frozen opening population with opening risk.

If the desk trades intraday, the explain may require separate treatment for opening-position market PnL, new-trade PnL from trade time to close, and realised or activity PnL. The service must state its population policy explicitly.

## Understanding Residual

Residual is not automatically model error. It may contain convexity, cross-gamma, curve reconstruction effects, intraday activity, fixing or cash-flow timing, and mismatches in positions, market cuts, or pricing models.

The correct workflow is to verify scope and lineage first, then decide whether a dedicated nonlinear or activity component is needed. Forcing residual back into curve buckets creates a tidy chart but destroys auditability.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BucketExplain:
    bucket: str
    opening_krdv01: Decimal
    rate_move_bp: Decimal


def explain_key_rate_pnl(
    rows: list[BucketExplain],
    carry_pnl: Decimal,
    actual_pnl: Decimal,
    residual_tolerance: Decimal,
    position_snapshot_id: str,
    market_window_id: str,
) -> dict:
    contributions = {
        row.bucket: row.opening_krdv01 * row.rate_move_bp
        for row in rows
    }

    curve_pnl = sum(contributions.values(), Decimal("0"))
    explained_pnl = curve_pnl + carry_pnl
    residual = actual_pnl - explained_pnl

    return {
        "bucket_contributions": contributions,
        "curve_pnl": curve_pnl,
        "carry_pnl": carry_pnl,
        "explained_pnl": explained_pnl,
        "actual_pnl": actual_pnl,
        "residual": residual,
        "status": (
            "RECONCILED"
            if abs(residual) <= residual_tolerance
            else "BREAK"
        ),
        "position_snapshot_id": position_snapshot_id,
        "market_window_id": market_window_id,
    }
```

## Data Quality and Production Considerations

The most relevant controls are:

- Join risk and moves by canonical bucket identifier, never array position.
- Require opening position, opening risk, and market window to share one valuation scope.
- Store moves explicitly in basis points; decimal-rate confusion creates a 10,000-fold error.
- Do not convert missing or failed buckets to zero.
- Reconcile component totals to actual PnL and preserve reasons for breaks.

A useful dashboard is a waterfall showing 5Y, 7Y, 10Y, carry, and residual, with drill-down to trades and snapshots.

A common failure is mixing opening risk from one curve build with node moves from another. Bucket names match and arithmetic succeeds, but the explain no longer represents one methodology.

## Requirement Discovery and Interview Questions

When a trader asks to “explain today’s rates PnL,” clarify:

- Is actual PnL clean, dirty, economic, or accounting PnL?
- Should the explain use opening, average, or closing risk?
- Is the window official close-to-close or intraday?
- Which curve and node definitions produce the moves?
- Does carry include accrual, roll-down, fixings, and cash payments?
- How are intraday trades attributed?
- Is tolerance an absolute amount, an explain ratio, or both?
- Does incomplete bucket coverage block publication?

A strong interview answer distinguishes official revaluation PnL from sensitivity-based explanation. Risk times move is diagnostic; actual PnL still comes from valuation.

## Key Takeaways

- Use bucketed risk for a curve twist; total DV01 times an average move loses information.
- Freeze opening positions and opening risk for a standard daily first-order explain.
- Keep curve PnL, carry, and residual as separate components.
- Align buckets, units, curves, snapshots, and windows explicitly.
- Residual is an investigation signal, not a balancing amount to hide.
- A clear desk summary is: “I explain the hedged book with opening key-rate risk, aligned node moves, explicit carry, and residual reconciled to actual PnL.”