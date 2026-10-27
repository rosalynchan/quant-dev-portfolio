# Building a Time-Consistent Futures Mid from Asynchronous Quotes

## Abstract

A midpoint appears trivial: average the bid and ask. In a live futures system, however, the two sides arrive independently and may carry different event times, sequence numbers and network delays. Averaging the latest cached values can create a market state that never existed, including a crossed market and a false PnL jump. This article defines a synchronized-mid policy using quote freshness, event-time skew and market-shape validation. It also shows how to preserve as-observed and corrected replay views without introducing look-ahead bias.

## Desk Context

Consider a desk long 200 short-rate futures contracts. At 16:29:59, the market is 95.200 bid and 95.202 ask. At 16:30:00, the bid updates to 95.206, while the ask feed is delayed and the cache still contains 95.202.

A naive service calculates:

$$
P_{mid}=\frac{95.206+95.202}{2}=95.204
$$

The arithmetic is correct, but the input state is not. The new bid is above the stale ask, producing a crossed market. If this value enters live PnL, the dashboard publishes an economically unreliable mark.

This is common because bid and ask are independent events. A shared cache makes them look like one record only after the system has discarded their timing and lineage.

## A Midpoint Needs a Common Time Meaning

The textbook formula is:

$$
P_{mid,t}=\frac{P_{bid,t}+P_{ask,t}}{2}
$$

The subscript matters. “Latest bid” and “latest ask” do not necessarily describe the same market state.

Each quote update should retain contract, source, side, normalized price, exchange event time, local ingestion time and source sequence number.

Event time describes when the source says the market event occurred. Ingestion time describes when the local platform learned about it. The distinction is essential for both live decisions and later replay.

## Three Validation Conditions

### Quote Freshness

For each side, measure age relative to the valuation cutoff:

$$
Age_{side}=CutoffTime-EventTime_{side}
$$

A live-risk policy may require both sides to be no more than two seconds old. The threshold depends on product liquidity, feed characteristics and the consumer's purpose.

### Bid-Ask Event-Time Skew

Measure the distance between the source event times:

$$
Skew=|EventTime_{bid}-EventTime_{ask}|
$$

Both quotes can pass a broad freshness test while still being too far apart to represent one market state. A liquid contract may need a tighter skew limit than an illiquid instrument.

### Market Shape

A normal two-sided state should satisfy:

$$
Bid<Ask
$$

A crossed market may indicate asynchronous updates, mixed sources or bad data. Whether a locked market is valid should be explicit product policy rather than an accidental inequality choice.

## Worked PnL Example

Assume:

- position: long 200 contracts;
- multiplier: GBP 2,500 per price point;
- previous live mark: 95.201;
- new bid: 95.206 at 16:30:00.000;
- stale ask: 95.202 at 16:29:55.000;
- synchronized new ask: 95.208 at 16:30:00.020.

The mixed-cache midpoint is:

$$
P_{mixed}=\frac{95.206+95.202}{2}=95.204
$$

It implies:

$$
\Delta PnL_{mixed}
=200(95.204-95.201)(2{,}500)
=GBP\ 1{,}500
$$

When the synchronized ask arrives 20 milliseconds later, the valid midpoint is:

$$
P_{sync}=\frac{95.206+95.208}{2}=95.207
$$

The corresponding PnL change is:

$$
\Delta PnL_{sync}
=200(95.207-95.201)(2{,}500)
=GBP\ 3{,}000
$$

The asynchronous combination understates live PnL by GBP 1,500:

$$
GhostDifference=1{,}500-3{,}000=-GBP\ 1{,}500
$$

More importantly, the mixed state is crossed. It should fail validation before any PnL is calculated.

## As-Observed Versus Corrected Replay

Suppose the new ask has exchange event time 16:30:00.020 but reaches the platform at 16:30:01 because of network delay.

At 16:30:00.500, a live as-observed view must not pretend that the system already knew the future ask. It should mark the quote incomplete or freeze the last valid mark under an explicit stale status.

After all events arrive, a corrected event-time replay can reconstruct the economic sequence for incident analysis. That replay is useful, but it must not overwrite what the system knew when a trader or algorithm made a decision.

This is the same point-in-time discipline used in backtesting: later information cannot be inserted into an earlier decision state.

## Engineering Design

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class Quote:
    side: str
    price: Decimal
    event_time: datetime
    sequence: int


def synchronized_mid(
    bid: Quote,
    ask: Quote,
    cutoff: datetime,
    max_age: timedelta,
    max_skew: timedelta,
) -> Decimal:
    if bid.side != "BID" or ask.side != "ASK":
        raise ValueError("invalid quote sides")

    if cutoff - bid.event_time > max_age:
        raise ValueError("stale bid")
    if cutoff - ask.event_time > max_age:
        raise ValueError("stale ask")
    if abs(bid.event_time - ask.event_time) > max_skew:
        raise ValueError("bid/ask event-time skew")
    if bid.price >= ask.price:
        raise ValueError("locked or crossed market")

    return (bid.price + ask.price) / Decimal("2")
```

The function deliberately refuses to invent a mark. The surrounding service may retain the previous valid value, but the response should then carry a status such as **FROZEN_STALE**, together with bid age, ask age and the rejection reason.

## Production Controls and Failure Modes

Five controls are especially relevant.

First, apply updates by contract, source and sequence number. A delayed old message must not overwrite a newer side.

Second, validate freshness, event-time skew and market shape as one publication decision. Passing only a price-range check is insufficient.

Third, make frozen marks visibly stale. Reusing the last valid value without changing its status makes downstream users believe risk is live.

Fourth, monitor source latency separately from quote invalidation. Ingestion time minus event time identifies transport delay, while invalidation reasons explain why a mark was not published.

Fifth, test delayed, out-of-order and duplicate messages. Deterministic event streams are more valuable here than isolated unit tests of the midpoint formula.

A typical failure occurs when a user interface polls a shared cache every 500 milliseconds while bid and ask are updated by separate threads. A read between the writes publishes a mixed state that never existed at the source.

## Requirement-Discovery and Interview Questions

When a trader says “just use mid,” a quant developer should clarify:

- What is the maximum age for each side?
- What bid-ask event-time skew is acceptable?
- Is a locked market valid, and must a crossed market always be rejected?
- If one side is missing, should the platform freeze, use a one-sided proxy or show unavailable?
- Can a frozen mark enter aggregated risk?
- May bid and ask come from different sources?
- Should a late quote restate previously published intraday PnL?
- Is live-mid fallback forbidden in official end-of-day workflows?

A strong interview answer distinguishes market event order from system knowledge order, avoids future information in historical decisions, and makes degraded states explicit rather than silently returning a decimal.

## Key Takeaways

- A midpoint is a time-consistent market state, not merely two cached numbers.
- Freshness and bid-ask skew are separate controls.
- Crossed states should fail before valuation.
- Event time reconstructs market order; ingestion time reconstructs system knowledge.
- Freezing the last valid mark is acceptable only with an explicit stale status.
- Replay tests should cover delayed, out-of-order and duplicate events.
