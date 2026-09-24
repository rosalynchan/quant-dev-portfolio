# Attributing PnL to an Intraday Swap Termination

## Abstract

A closing position snapshot cannot explain every daily PnL event. A swap terminated at noon is absent at the close, but it still generated market, carry, and execution PnL while it existed. This article shows how to reconstruct the open-to-termination interval, distinguish settlement cash from economic PnL, and design lifecycle-driven attribution that survives position disappearance.

## Desk Context

Consider a receive-fixed swap held at yesterday's close. Its opening PV is +GBP 20,000 and its signed DV01 is -GBP 1,500 per basis point. Rates rise 3bp during the morning. At noon, the desk terminates the swap and agrees to receive GBP 15,400. The trade is absent from the closing active-position snapshot.

A system driven only by closing positions sees no trade and may assign zero market PnL. The desk, however, lost value before termination. The correct question is not whether the trade exists at the close, but during which part of the day it carried exposure.

## The Correct Market Window

A position held at the open and terminated intraday should receive market attribution from open to its economic termination time:

$$
ClosedTradeMarketPnL
\approx
DV01_{open}
\times
(r_{termination}-r_{open}).
$$

It must not receive termination-to-close PnL because it no longer exists after close-out.

The daily population rules now become:

- positions held throughout the day: open to close;
- new trades: execution to close;
- closed trades: open to termination;
- amended or cancelled trades: reconstructed from the relevant lifecycle events.

This is why two end-of-day position tables are insufficient. A robust explain needs the event timeline between them.

## Settlement Cash Is Not the Entire PnL

The termination payment settles the swap's value at close-out. Receiving GBP 15,400 does not mean the desk earned GBP 15,400 today. The desk already carried an asset worth GBP 20,000 at the opening snapshot.

Ignoring intermediate cashflows, the balance-view calculation is

$$
ClosedTradePnL
=
TerminationCash-OpeningPV.
$$

Therefore,

$$
15{,}400-20{,}000
=
-GBP\ 4{,}600.
$$

Positive cash and negative PnL are entirely consistent: an asset worth GBP 20,000 fell to GBP 15,400 and was then converted into cash.

The distinction resembles futures variation-margin reconciliation. Cash movement and PnL are related economic views, but cash cannot be treated as incremental profit without considering the opening carrying value.

## Worked Numerical Example

The morning rate move produces

$$
MarketPnL_{open\rightarrow termination}
=
(-1{,}500)\times3
=
-GBP\ 4{,}500.
$$

Assume carry and accrual to termination are +GBP 100. The model fair value at termination is

$$
FairValueAtTermination
=
20{,}000-4{,}500+100
=
GBP\ 15{,}600.
$$

The executable termination cash is GBP 15,400, giving

$$
TerminationExecutionPnL
=
15{,}400-15{,}600
=
-GBP\ 200.
$$

The component bridge is

$$
\begin{aligned}
ExplainedClosedTradePnL
&=-4{,}500+100-200\\
&=-GBP\ 4{,}600.
\end{aligned}
$$

It reconciles to the balance view:

$$
15{,}400-20{,}000
=
-GBP\ 4{,}600.
$$

If actual clean PnL is -GBP 4,650, the residual is -GBP 50.

The two views serve different purposes. The component bridge explains market, carry, and execution. The balance bridge proves that termination cash correctly derecognises the opening asset. They reconcile to one PnL amount and must not be added together.

## Termination Is Not the Same as an Offsetting Trade

Several events may reduce net DV01 while having different economics:

- **Early termination:** the original future rights and obligations are extinguished, normally with a termination payment.
- **Offsetting trade:** the original trade remains, while a new opposite trade is booked.
- **Cancel or correct:** the original record may have been invalid and replaced by a corrected version.
- **Partial termination:** only part of the notional is extinguished; the remaining version continues.

Net risk alone cannot classify these events. Treating an offsetting trade as a termination loses independent cashflows, counterparty exposure, and lifecycle lineage.

## Engineering Design

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ClosedTradeEvent:
    trade_id: str
    event_type: str
    termination_time: datetime
    opening_pv: Decimal
    opening_dv01: Decimal
    open_rate_bp: Decimal
    termination_rate_bp: Decimal
    carry_to_termination: Decimal
    termination_cash: Decimal
    event_version: int


def explain_closed_trade(x: ClosedTradeEvent) -> dict:
    if x.event_type != "FULL_TERMINATION":
        raise ValueError("unsupported lifecycle event")

    market_pnl = (
        x.opening_dv01
        * (
            x.termination_rate_bp
            - x.open_rate_bp
        )
    )
    fair_value = (
        x.opening_pv
        + market_pnl
        + x.carry_to_termination
    )
    execution_pnl = (
        x.termination_cash - fair_value
    )
    explained = (
        market_pnl
        + x.carry_to_termination
        + execution_pnl
    )

    return {
        "trade_id": x.trade_id,
        "market_window": "OPEN_TO_TERMINATION",
        "market_pnl": market_pnl,
        "carry_pnl": x.carry_to_termination,
        "termination_execution_pnl": execution_pnl,
        "explained_pnl": explained,
        "cash_minus_opening_pv": (
            x.termination_cash - x.opening_pv
        ),
        "event_version": x.event_version,
    }
```

The lifecycle event is the source of the economic interval. The final active-position table is only one state, not a history.

## Data Quality and Production Controls

The most important controls are:

1. **Event identity and versioning.** Each event needs a type, effective timestamp, immutable version, and link to the original trade.
2. **Opening lineage.** Opening PV and risk must come from the daily opening snapshot, not a later recomputation under changed economics.
3. **Cash semantics.** Termination amount, sign, currency, value date, and settlement status must be explicit.
4. **Lifecycle classification.** Full termination, partial termination, cancel/correct, and offsetting trades cannot share an ambiguous CLOSED flag.
5. **Dual reconciliation.** Component PnL must reconcile both to actual PnL and, under the defined scope, to termination cash minus opening carrying value.

A common failure occurs when a risk service queries only closing active trades. The dashboard correctly shows zero closing risk but leaves the morning loss unexplained—or omits it entirely.

Useful observability includes terminated trades missing opening snapshots, events without cash amounts, booking delay, unsettled termination cash, and breaks between component and balance views.

## Requirement Discovery and Interview Questions

When a trader requests closed-trade PnL, clarify:

- Does closed mean full termination, partial termination, or offsetting hedge?
- Which timestamp defines close-out: execution, booking, or settlement?
- Is termination cash agreed, expected, or settled?
- Are accrued interest and paid cashflows included in clean or economic PnL?
- Is execution measured against model mid, executable quote, or another benchmark?
- Does cancel/rebook rewrite a prior business date?
- How is the remaining version created after partial termination?
- Can PnL publish before the cash settlement completes?

## Testing and Observability

A useful property test verifies that the component bridge equals termination cash minus opening PV when no intermediate cashflows are present. Scenario tests should cover positive and negative carrying values, multiple currencies, a termination after the market close, and an event received after the daily run. Integration tests should prove that rerunning the same event version and snapshots produces an identical result.

Operational metrics should track missing opening states, unsupported event types, unsettled cash, and reconciliation breaks by lifecycle category. A zero closing position is never, by itself, a successful explain.

## Key Takeaways

- A trade absent at the close can still generate material daily PnL.
- Closed-trade market attribution runs from open to economic termination.
- Termination cash must be compared with opening carrying value.
- Market, carry, and termination execution effects form one explain bridge.
- Lifecycle events—not final position state—determine the exposure interval.
- Net-zero risk does not prove that the original trade was terminated.