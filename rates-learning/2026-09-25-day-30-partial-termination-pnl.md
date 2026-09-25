# Explaining PnL on a Partial Swap Termination

## Abstract

A partial termination is not simply a full close followed by a smaller new trade. It is a lifecycle event that stops one slice of an existing position while the remaining slice continues without losing its pre-event history. This article develops a practical PnL attribution method for that event, separates market movement from termination execution, and shows how versioned trade data prevents double counting and ghost PnL.

## Desk Context

Assume a GBP 50 million receive-fixed swap has an opening clean PV of GBP 100,000 and signed DV01 of -GBP 5,000 per basis point. Rates rise 2bp before 11:00. At 11:00, the trader terminates 40% of the current notional for GBP 36,100. Rates then rise another 3bp before the close.

The desk asks: how much PnL belongs to the terminated 40%, and how much belongs to the continuing 60%?

A system that closes the original trade and books the remaining 60% as a new trade creates a timing error. The continuing slice existed before 11:00 and must retain its morning PnL. Conversely, leaving the full original position active after 11:00 and adding a 60% version double counts post-event risk.

## The Lifecycle Timeline

Let $f$ be the terminated fraction. Before the event, the full trade bears market risk. After the event, only $1-f$ remains.

The slice view follows each economic slice:

$$
MarketPnL=DV01_{terminated}\Delta r_{open,event}+DV01_{remaining}\Delta r_{open,close}
$$

The piecewise view follows the position through time:

$$
MarketPnL=DV01_{full}\Delta r_{open,event}+DV01_{remaining}\Delta r_{event,close}
$$

These expressions should agree. Their equality is an excellent production invariant because it tests fractions, event timing, signs, and lifecycle version boundaries at once.

The remaining slice is not a new trade. It is a new version of the same economic trade family, effective at the termination timestamp.

## Worked Numerical Example

Under a proportional-scaling assumption:

$$
DV01_{terminated}=-5{,}000\times40\%=-GBP\ 2{,}000/bp
$$

$$
DV01_{remaining}=-5{,}000\times60\%=-GBP\ 3{,}000/bp
$$

The terminated slice experiences only the 2bp open-to-event move:

$$
MarketPnL_{terminated}=(-2{,}000)\times2=-GBP\ 4{,}000
$$

Its opening PV is GBP 40,000. If carry accrued to the event is GBP 400, its event-time fair PV is:

$$
FairPV_{event}=40{,}000-4{,}000+400=GBP\ 36{,}400
$$

The desk receives termination cash of GBP 36,100, so execution PnL is:

$$
ExecutionPnL=36{,}100-36{,}400=-GBP\ 300
$$

The terminated slice therefore contributes -GBP 3,900. The remaining 60% exists from open to close and experiences the full 5bp move:

$$
MarketPnL_{remaining}=(-3{,}000)\times5=-GBP\ 15{,}000
$$

With GBP 600 of full-day carry, its PnL is -GBP 14,400. Total explained PnL is -GBP 18,300. If actual PnL is -GBP 18,350, the residual is -GBP 50.

The market component can be independently checked in piecewise form:

$$
(-5{,}000)\times2+(-3{,}000)\times3=-GBP\ 19{,}000
$$

That equals the slice result of -GBP 4,000 plus -GBP 15,000.

## Engineering Design

A robust design represents the termination as an event. The pre-event version is superseded exactly when the remaining version becomes active. Both versions share a stable trade-family identifier, while the event has its own immutable identifier.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PartialTermination:
    opening_pv: Decimal
    opening_dv01: Decimal
    terminated_fraction: Decimal
    open_rate_bp: Decimal
    event_rate_bp: Decimal
    close_rate_bp: Decimal
    terminated_carry: Decimal
    remaining_carry: Decimal
    termination_cash: Decimal
    event_id: str
    old_version_id: str
    remaining_version_id: str


def explain_partial_termination(x: PartialTermination) -> dict:
    f = x.terminated_fraction
    if not Decimal("0") < f < Decimal("1"):
        raise ValueError("invalid partial-termination fraction")

    term_dv01 = x.opening_dv01 * f
    remain_dv01 = x.opening_dv01 * (Decimal("1") - f)
    term_market = term_dv01 * (x.event_rate_bp - x.open_rate_bp)
    remain_market = remain_dv01 * (x.close_rate_bp - x.open_rate_bp)

    fair_event_pv = x.opening_pv * f + term_market + x.terminated_carry
    execution_pnl = x.termination_cash - fair_event_pv

    slice_market = term_market + remain_market
    piecewise_market = (
        x.opening_dv01 * (x.event_rate_bp - x.open_rate_bp)
        + remain_dv01 * (x.close_rate_bp - x.event_rate_bp)
    )
    if slice_market != piecewise_market:
        raise ValueError("lifecycle PnL invariant failed")

    return {
        "terminated_market_pnl": term_market,
        "remaining_market_pnl": remain_market,
        "execution_pnl": execution_pnl,
        "explained_pnl": slice_market + x.terminated_carry
        + x.remaining_carry + execution_pnl,
        "event_id": x.event_id,
        "superseded_version": x.old_version_id,
        "active_version": x.remaining_version_id,
    }
```

The code keeps market PnL, carry, and execution separate. It also exposes version lineage rather than flattening the lifecycle into unrelated records.

## Data Quality and Production Controls

Four controls matter most.

First, the termination fraction needs a basis. Forty percent may mean original notional, current notional, or selected future cashflows. A bare decimal is insufficient.

Second, the event timestamp must be economic and timezone-aware. Booking or approval time may lag execution and create false exposure windows.

Third, termination cash and fair PV must share the same clean-versus-dirty convention. Accrued interest, fees, and taxes should not silently migrate into execution PnL.

Fourth, proportional scaling is only safe when economics are linear in notional. Amortising schedules, selected-period cancellations, embedded options, or simultaneous changes to rate and dates require rebuilding and repricing the resulting trade.

Useful observability includes overlapping-version counts, gaps between version effective times, the slice-versus-piecewise break, and residual PnL by lifecycle event type.

## Requirement Discovery

When a trader says, “We cut 40%,” a developer should ask:

- Forty percent of original notional, current notional, or a cashflow schedule?
- Is execution time or booking time the economic event time?
- Is termination cash clean or dirty, and does it include fees or accrued interest?
- Are coupon, dates, index, and the remaining schedule unchanged?
- May PV and risk scale proportionally, or is full revaluation required?
- How should late-booked events reopen historical PnL?
- Should the dashboard show one trade family with versions or separate records?

An interview-quality answer distinguishes mathematical allocation from lifecycle truth. Even correct arithmetic fails if event semantics are wrong.

## Trader–Developer Translation

**Trader:** “We cut 40% at 11. The report shows the whole swap closed and a new 60% trade.”

**Developer:** “That classification removes the remaining slice’s morning PnL. Should the 60% remain the continuing version of the same economic trade?”

**Trader:** “Yes. Only the terminated slice stops at 11, and show execution separately.”

**Developer:** “I will supersede the old version and activate the 60% version at the same timestamp, preserve the trade family, and reconcile slice-based PnL to the piecewise timeline.”

This translation produces testable requirements: non-overlapping versions, an explicit fraction basis, event-time valuation, and separate execution PnL.

## Key Takeaways

- A partial termination stops only the terminated slice; the remainder preserves its full history.
- Slice and piecewise calculations are economically equivalent and should reconcile.
- Termination execution is cash minus event-time fair PV, not market movement.
- A remaining trade is a lifecycle version, not automatically a new trade.
- Proportional scaling is a methodology choice, not a universal property.
- Version boundaries, timestamps, and valuation conventions are as important as the formula.
