# Late Market-Data Corrections: Restating Futures PnL Without Inventing a Market Move

## Abstract

Market-data vendors sometimes issue cancel/correct messages after a price has already been used for live valuation. A naïve cache update can make the correction appear as a new market move at its arrival time, while ignoring it leaves historical PnL and controls wrong. This article presents an event-revision design for futures marks. It separates economic effective time from system known-at time, preserves both as-observed and corrected timelines, calculates an explicit correction PnL component, and limits recomputation to the affected interval using point-in-time positions.

## Desk Context

A Rates desk is long 120 short-rate futures contracts with a multiplier of GBP 2,500 per point. At 10:00, the valuation service receives a mark of 95.210. At 10:12, the vendor sends a correction stating that the 10:00 mark should have been 95.207. The current valid mark at 10:15 is 95.214.

The correction is known by the system at 10:12, but its economic effective time remains 10:00. Treating 95.207 as a new 10:12 price creates a false path in which the market appears to fall and then recover. Overwriting the original record is also unsafe because support can no longer reconstruct what the trader actually saw before the correction arrived.

The required behaviour is a PnL restatement with explicit revision lineage.

## A Correction Is Not a New Tick

The original observation can be written as:

$$
P_{10{:}00}^{v1}=95.210
$$

The message arriving at 10:12 does not mean:

$$
P_{10{:}12}=95.207
$$

It means that the earlier event has a new version:

$$
P_{10{:}00}^{v2}=95.207
$$

Two timestamps are therefore essential. The effective or event time identifies the market state being corrected. The known-at or ingestion time identifies when the system learned about the revision.

This distinction supports a simple principle: a correction changes what the system believes about an earlier market state; it is not a new market move at arrival time.

## Worked Numerical Example

Assume:

- quantity: +120 contracts;
- multiplier: GBP 2,500 per point;
- original 10:00 mark: 95.210;
- corrected 10:00 mark: 95.207;
- current 10:15 mark: 95.214.

Using the original anchor, the as-observed PnL is:

$$
\begin{aligned}
\text{PnL}_{observed}
&=120(95.214-95.210)(2{,}500)\\
&=\text{GBP }1{,}200
\end{aligned}
$$

Using the corrected anchor, the economic PnL becomes:

$$
\begin{aligned}
\text{PnL}_{corrected}
&=120(95.214-95.207)(2{,}500)\\
&=\text{GBP }2{,}100
\end{aligned}
$$

The restatement component is:

$$
\begin{aligned}
\text{MarkCorrectionPnL}
&=\text{PnL}_{corrected}-\text{PnL}_{observed}\\
&=\text{GBP }900
\end{aligned}
$$

The same result can be obtained from the anchor correction:

$$
120(95.210-95.207)(2{,}500)=\text{GBP }900
$$

Because the position is long and its historical starting mark moved down, cumulative profit to the current mark increases by GBP 900. That amount should be labelled `MARK_CORRECTION`, effective from 10:00 and recognized at 10:12. It is not a 10:12 rally and should not enter unexplained PnL.

## Preserve Two Timelines

The as-observed timeline answers: what did the system know and display at each point in time? Between 10:00 and 10:12, the service used 95.210. Trader decisions, alerts, and dashboard states during that period were based on that value. An incident replay must preserve this fact and cannot use later information as if it had been available earlier.

The corrected timeline answers: given the latest complete information, what should the economic history be? It selects revision 2 at 10:00, recalculates affected downstream results, and publishes the GBP 900 correction delta.

Both views are valid for different purposes. As-observed data supports operational audit and prevents look-ahead in replay. Corrected data supports economic reconciliation, official reporting, and research. One must not silently replace the other.

## Limit the Affected Window

Correcting an anchor does not imply unlimited recomputation. The service should determine an affected window beginning at the event's effective time and ending at the next independent anchor, settlement reset, or defined business cutoff.

In this example, a new valid mark exists at 10:15, so the affected interval is 10:00–10:15. If a trade changed the position at 10:05, the correction must be applied to the position that actually existed in each sub-interval. Multiplying the entire correction by the latest position would be wrong.

This is an important front-office engineering lesson: market-data revisions and position timelines must meet through point-in-time joins, not current-state lookups.

## Engineering Design

The original event should be immutable. A correction creates a new version linked to the record it supersedes.

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class MarkRevision:
    event_id: str
    supersedes_event_id: str | None
    price: Decimal
    effective_at: datetime
    known_at: datetime
    revision: int


def correction_pnl(
    original: MarkRevision,
    corrected: MarkRevision,
    quantity: int,
    multiplier: Decimal,
) -> dict:
    if corrected.supersedes_event_id != original.event_id:
        raise ValueError("broken revision lineage")
    if corrected.effective_at != original.effective_at:
        raise ValueError("correction changed economic timestamp")
    if corrected.revision != original.revision + 1:
        raise ValueError("unexpected revision sequence")

    delta = (
        Decimal(quantity)
        * (original.price - corrected.price)
        * multiplier
    )

    return {
        "component": "MARK_CORRECTION",
        "pnl_delta": delta,
        "effective_at": corrected.effective_at,
        "recognized_at": corrected.known_at,
        "revision": corrected.revision,
    }
```

The function is deliberately strict about lineage, timestamp, and revision sequence. Production code would additionally split the affected window by position changes and aggregate the sub-interval deltas.

## Data Quality and Production Controls

Four controls are particularly important.

First, never update the original event in place. Revision and `supersedes_event_id` fields provide the audit trail. Second, processing must be idempotent: a repeated vendor correction must not generate GBP 900 twice. Third, recomputation must use point-in-time positions and a bounded affected window. Fourth, a correction that crosses an official cutoff or exceeds a materiality threshold should enter an approval and republication workflow.

Observability should report correction count, revision gaps, duplicate messages, affected-result count, restatement amount, and processing latency. A useful dashboard distinguishes “corrected economic PnL” from “what the desk saw at the time.”

A common failure is an in-place database update that destroys evidence needed for incident analysis. Another is applying a correction using the current position even though the desk traded during the affected interval. Both can produce internally consistent but economically false PnL.

## Requirement Discovery and Interview Questions

When a trader asks to “apply the corrected price,” clarify:

- Does the correction affect live views, official PnL, or both?
- Must the as-observed history remain available?
- What are the effective and received timestamps?
- Which outputs require recomputation: PnL, limits, alerts, or risk snapshots?
- Where does the affected window end?
- How are position changes inside that window handled?
- What materiality requires trader or control acknowledgement?
- Should an issued official report receive a delta or a full restatement?
- How is a later reversal of the correction represented?

A strong interview answer connects bitemporal data to desk controls: “I would append an immutable revision, link it to the superseded event, preserve as-observed and corrected views, recompute only the affected interval with point-in-time positions, and publish an explicit correction component.”

## Key Takeaways

- Arrival time and economic effective time are different for a late correction.
- The original market-data event should remain immutable.
- As-observed and corrected timelines serve different control purposes.
- Correction PnL belongs in an explicit restatement component, not current market PnL.
- Recalculation must use a bounded affected window and point-in-time positions.
- Revision lineage and idempotency prevent silent overwrites and duplicate PnL.

Suggested repository filename: `2026-10-30-day-65-market-data-correction.md`.
