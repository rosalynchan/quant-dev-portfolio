# Explaining Futures PnL Catch-Up After a Stale Mark Recovers

## Abstract

Freezing the last valid price is safer than publishing an invalid futures midpoint, but it creates a new explain problem. When market data recovers, the mark can jump directly to the current level and produce a large PnL update at one timestamp. The market did not necessarily move at that instant; the platform recognized an accumulated move after a period of blindness. This article defines stale-mark catch-up PnL, separates the economic interval from the recognition time, and designs an idempotent recovery event that reconciles to total market PnL without double counting.

## Desk Context

A desk is long 150 short-rate futures contracts with a multiplier of GBP 2,500 per price point.

- At 10:00, the last valid midpoint is 95.200.
- From 10:00 to 10:15, the quote feed is unavailable and the dashboard freezes the mark.
- At 10:15, the feed recovers with a valid midpoint of 95.212.
- By 10:20, the market reaches 95.216.

If the PnL engine reacts only to newly observed prices, it reports a GBP 4,500 gain at 10:15. The total is economically valid, but the apparent timing is misleading. A trader looking at the chart may infer a sudden market shock at recovery.

The engineering objective is not to smooth away real PnL. It is to explain when the exposure earned the PnL and when the system became able to observe it.

## A Data Outage Changes Observation, Not Exposure

For a futures position, price-move PnL is:

$$
PnL=Q(P_1-P_0)M
$$

While the displayed mark is frozen, the observed change is zero:

$$
ObservedPnL_{stale}=Q(P_{frozen}-P_{frozen})M=0
$$

This does not mean the economic exposure stopped. The contract remained in the portfolio while the external market continued to trade.

Once a valid price returns, catch-up PnL is:

$$
CatchUpPnL=Q(P_{recovery}-P_{last\ valid})M
$$

Catch-up is not an additional profit, a model correction or necessarily a trade event. It is market PnL whose recognition was delayed by data quality.

## Worked Numerical Example

Assume:

- quantity: long 150;
- multiplier: GBP 2,500 per price point;
- last valid midpoint: 95.200;
- recovery midpoint: 95.212;
- 10:20 midpoint: 95.216.

The accumulated move over the stale interval produces:

$$
CatchUpPnL
=150(95.212-95.200)(2{,}500)
=GBP\ 4{,}500
$$

This component belongs economically to the 10:00–10:15 interval, although the platform recognizes it when the recovery price arrives.

The new movement after recovery is:

$$
PostRecoveryPnL
=150(95.216-95.212)(2{,}500)
=GBP\ 1{,}500
$$

Total PnL from the last valid price is:

$$
TotalPnL=4{,}500+1{,}500=GBP\ 6{,}000
$$

The direct calculation confirms the reconciliation:

$$
150(95.216-95.200)(2{,}500)=GBP\ 6{,}000
$$

Catch-up and post-recovery PnL are non-overlapping components of the same total. Adding catch-up on top of the full market move would double count it; omitting it would push a valid economic change into residual.

## Economic Interval Versus Recognition Time

A recovery event needs two time concepts.

The economic interval runs from the last valid mark to the event time of the recovered mark. It describes the period over which the accumulated market move occurred.

Recognition time is when the local system received, validated and accepted the recovery state. It describes when the PnL became available to the dashboard and downstream consumers.

For example:

- economic interval: 10:00–10:15;
- recognition time: 10:15:01;
- component: **MARK_CATCH_UP**;
- reason: **QUOTE_FEED_RECOVERY**.

The dashboard can update total PnL at 10:15:01, but its explain should make clear that the amount covers a 15-minute window rather than a one-second shock.

This distinction follows the same bitemporal discipline used for late trades and corrected market data: economic time and knowledge time answer different questions.

## A Frozen Price Does Not Mean Zero Risk

During the outage, position and risk remain real. A dashboard should not interpret an unchanged mark as evidence that the market is stable or that exposure has declined.

A controlled degraded view should show the last valid price, an explicit **FROZEN_STALE** quality state, stale duration, and current position or DV01. A platform may also show a separately labelled uncertainty estimate, but it must not present an estimate as official observed PnL.

The important semantic distinction is between zero and unknown. Encoding missing market observability as zero movement creates false confidence.

## Engineering Design

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class MarkState:
    price: Decimal
    event_time: datetime
    status: str


def recovery_pnl(
    last_valid: MarkState,
    recovered: MarkState,
    quantity: int,
    multiplier: Decimal,
    recognized_at: datetime,
) -> dict:
    if last_valid.status != "VALID":
        raise ValueError("missing valid anchor")
    if recovered.status != "VALID":
        raise ValueError("recovery mark is not valid")
    if recovered.event_time <= last_valid.event_time:
        raise ValueError("non-forward recovery interval")

    catch_up = (
        Decimal(quantity)
        * (recovered.price - last_valid.price)
        * multiplier
    )

    return {
        "component": "MARK_CATCH_UP",
        "pnl": catch_up,
        "economic_from": last_valid.event_time,
        "economic_to": recovered.event_time,
        "recognized_at": recognized_at,
    }
```

The anchor must be the last validated price before the outage, not simply whichever value remains in a generic cache. A production event should also carry contract, source, outage identifier and policy version.

## Production Controls and Failure Modes

Five controls are particularly important.

First, generate exactly one catch-up event for one stale interval. Feed retransmission and replay must be idempotent.

Second, ensure the catch-up interval does not overlap the normal post-recovery interval. Interval overlap causes double counting.

Third, retain the last valid anchor and the recovered observation with full source and timestamp lineage.

Fourth, expose stale duration and recognition time on the dashboard. A large catch-up without outage context looks like unexplained market PnL.

Fifth, if the feed remains stale through the official cutoff, create a valuation exception. Silently carrying the old mark into official reporting changes the economic meaning of the result.

A common failure is duplicate recovery delivery: the consumer emits the same GBP 4,500 catch-up twice. Another is assigning the entire move to the recovery second, causing false alerts and misleading intraday charts.

## Requirement-Discovery and Interview Questions

When a trader asks to “smooth the jump,” clarify:

- Is the request only about chart presentation, or should official PnL recognition change?
- Should catch-up remain market PnL with a data-quality tag, or become a separate displayed component?
- Which last-valid snapshot anchors the stale interval?
- How many valid updates confirm recovery?
- Should late historical quotes reconstruct a corrected intraday path?
- Must both as-observed and corrected charts be retained?
- Who approves a fallback if the outage crosses the official cutoff?
- What catch-up amount or stale duration requires acknowledgement?

A strong interview answer preserves economic PnL, avoids inventing an artificial smooth path, and separates economic time from system knowledge time.

## Key Takeaways

- A frozen mark hides observation; it does not remove exposure.
- Catch-up PnL is accumulated market PnL recognized after data recovery.
- Economic interval and recognition time must both be retained.
- Catch-up plus post-recovery movement must reconcile to total market PnL.
- Recovery events require idempotency and non-overlapping intervals.
- Stale data crossing an official cutoff should become an explicit valuation exception.
