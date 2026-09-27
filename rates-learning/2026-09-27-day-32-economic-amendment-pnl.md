# Attributing PnL to a Genuine Economic Swap Amendment

## Abstract

A genuine swap amendment changes contractual economics during the PnL window. The old trade version therefore earns PnL only until the event, while the amended version earns PnL afterwards. The change in event-time fair value is normally offset by a negotiated cash transfer; it is not automatically profit. This article develops a practical attribution bridge, shows how to calculate amendment execution, and translates the economics into versioned data and production controls.

## Desk Context

Suppose a desk holds a receive-fixed swap with opening clean PV of GBP 120,000 and signed DV01 of -GBP 5,000 per basis point. Rates rise 2bp before 11:00. At 11:00, the parties genuinely renegotiate the fixed rate and reduce the notional.

Immediately before the amendment, the old version has fair PV of GBP 110,200. Valued on the same market snapshot, the new version has fair PV of GBP 92,000. The counterparty pays the desk GBP 17,800. The amended swap has signed DV01 of -GBP 3,500/bp, and rates rise another 3bp before the close.

The desk needs to know how much PnL came from market movement before and after the event, and whether the negotiated cash was fair.

## The Event-Time Economics

The old version is economically valid from the opening snapshot to the amendment. The new version is valid from the amendment to the close:

$$
MarketPnL=PnL_{old,open\rightarrow event}+PnL_{new,event\rightarrow close}
$$

If the new version is worth less to the desk than the old version, the desk gives up value. Under a fair amendment, the counterparty should compensate it:

$$
TheoreticalCash=PV_{old,event}-PV_{new,event}
$$

This article uses a desk-centric sign convention: cash received by the desk is positive.

The difference between actual negotiated cash and theoretical cash is amendment execution PnL:

$$
AmendmentExecutionPnL=ActualCash-TheoreticalCash
$$

The fair-value discontinuity itself is not market PnL. In a fair transaction it is offset by the theoretical cash transfer.

## Worked Numerical Example

Before the event, rates rise 2bp. The old version contributes:

$$
OldMarketPnL=(-5{,}000)\times2=-GBP\ 10{,}000
$$

Assume pre-event carry is +GBP 200. The old event-time PV is therefore consistent with:

$$
PV_{old,event}=120{,}000-10{,}000+200=GBP\ 110{,}200
$$

The new version is worth GBP 92,000 on the same snapshot. The theoretical cash receivable is:

$$
TheoreticalCash=110{,}200-92{,}000=GBP\ 18{,}200
$$

The desk actually receives GBP 17,800, so amendment execution is:

$$
AmendmentExecutionPnL=17{,}800-18{,}200=-GBP\ 400
$$

This means the negotiated amendment was GBP 400 worse for the desk than the selected event-time fair-value benchmark.

After the event, rates rise another 3bp. The amended version contributes:

$$
NewMarketPnL=(-3{,}500)\times3=-GBP\ 10{,}500
$$

Assume post-event carry is +GBP 300. The full-day explained PnL is:

$$
\begin{aligned}
ExplainedPnL
&=OldMarketPnL+NewMarketPnL\\
&\quad+Carry+AmendmentExecutionPnL\\
&=-10{,}000-10{,}500+500-400\\
&=-GBP\ 20{,}400
\end{aligned}
$$

If actual economic PnL is -GBP 20,450, the residual is -GBP 50.

The GBP 18,200 theoretical cash must not be added as extra profit. It offsets the GBP 18,200 reduction from old event PV to new event PV. Only the GBP 400 shortfall versus theoretical value belongs in execution attribution.

## One Snapshot, Two Versions

Both event-time PVs must use the same curve snapshot, fixings, model version, currency, and clean-or-dirty convention. Otherwise, market movement between snapshots becomes embedded in the amendment value transfer.

For example, valuing the old trade at 10:59 and the new trade at 11:05 can make execution appear unusually good or bad. The cash reconciliation may still add up, but the driver attribution will be wrong: part of the market move has been labelled as negotiated value.

If an exact event snapshot is unavailable, the system needs a governed policy such as nearest snapshot, first validated snapshot after execution, or interpolation. The timestamp gap and fallback method should remain visible.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class EconomicAmendment:
    old_opening_dv01: Decimal
    new_event_dv01: Decimal
    open_rate_bp: Decimal
    event_rate_bp: Decimal
    close_rate_bp: Decimal
    old_event_pv: Decimal
    new_event_pv: Decimal
    actual_cash_received: Decimal
    carry_before_event: Decimal
    carry_after_event: Decimal
    event_snapshot_id: str
    old_version_id: str
    new_version_id: str


def explain_economic_amendment(x: EconomicAmendment) -> dict:
    old_market = x.old_opening_dv01 * (
        x.event_rate_bp - x.open_rate_bp
    )
    new_market = x.new_event_dv01 * (
        x.close_rate_bp - x.event_rate_bp
    )

    theoretical_cash = x.old_event_pv - x.new_event_pv
    execution_pnl = x.actual_cash_received - theoretical_cash
    explained = (
        old_market
        + new_market
        + x.carry_before_event
        + x.carry_after_event
        + execution_pnl
    )

    return {
        "old_version_market_pnl": old_market,
        "new_version_market_pnl": new_market,
        "theoretical_cash": theoretical_cash,
        "actual_cash_received": x.actual_cash_received,
        "amendment_execution_pnl": execution_pnl,
        "explained_pnl": explained,
        "event_snapshot_id": x.event_snapshot_id,
        "superseded_version": x.old_version_id,
        "active_version": x.new_version_id,
    }
```

This design deliberately carries both theoretical and actual cash. Defaulting an unconfirmed cash amount to theoretical value would force execution PnL to zero and hide settlement risk.

## Data Quality and Production Controls

Five controls provide most of the value.

First, old and new event PVs must share one market and methodology snapshot. Second, cash sign convention must be explicit. Third, the old version's valid-to and new version's valid-from must equal the economic event time without overlap or gap. Fourth, theoretical cash, actual cash, and execution PnL must satisfy their arithmetic invariant. Fifth, missing actual cash should produce `PENDING_SETTLEMENT`, not a fabricated zero difference.

Useful monitoring includes event-snapshot gaps, amendments with overlapping versions, unsettled cash after value date, and execution PnL outside desk tolerance.

## Requirement Discovery and Interview Questions

When a trader says, “We amended the swap,” ask:

- Which terms changed: rate, notional, maturity, schedule, or index?
- What are the economic execution time and booking time?
- Are both event PVs clean or dirty?
- Is the upfront fair-value compensation, a fee, or a combined amount?
- Is cash received or paid by the desk, and on what value date?
- What status applies while actual cash is unconfirmed?
- Which snapshot starts post-event risk?
- Must the amended trade be re-hedged or rechecked against limits?

A strong interview answer separates the contractual change, the fair-value transfer, the negotiated execution difference, and subsequent market PnL.

## Trader–Developer Translation

**Trader:** “We reduced the notional and changed the fixed rate at 11. Why does the dashboard show an 18.2k profit?”

**Developer:** “That amount compensates the move from the old event PV to the new event PV. It offsets the value discontinuity; it is not profit by itself.”

**Trader:** “We actually received 17.8k.”

**Developer:** “Then amendment execution is -GBP 400. I will apply old risk before 11, new risk afterwards, and expose theoretical and actual cash separately.”

## Key Takeaways

- A genuine amendment creates an old-version and new-version risk window.
- Both versions must be valued on the same event snapshot.
- Theoretical cash compensates the event-time PV discontinuity.
- Only actual cash minus theoretical cash is amendment execution PnL.
- Unconfirmed cash is a state, not permission to invent settlement.
- Version timing and cash conventions are part of the pricing requirement, not implementation details.
