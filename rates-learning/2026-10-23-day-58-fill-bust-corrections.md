# Replaying Futures Positions and PnL After Fill Busts and Corrections

## Abstract

Confirmed futures fills sometimes change after they have already reached risk and PnL systems. An exchange or broker may bust a trade completely or correct its quantity, price, or contract. Overwriting the original record destroys the ability to explain what users previously saw. This article presents an append-only execution ledger in which busts and replacements are linked economic events, shows how to calculate a PnL restatement, and explains why both effective time and ingestion time are required for reliable replay.

## Desk Context

At 10:00, a front-office system receives a confirmed purchase of 100 NEXT futures at 95.200. The position becomes +100. At 11:00 the market price is 95.212, and the dashboard reports GBP 3,000 of PnL.

At noon, the broker reports that the confirmed quantity was wrong. The correct trade was 60 contracts, not 100.

The platform must now answer two different questions:

- What is the currently corrected position and PnL?
- What did the system genuinely know and display at 11:00?

A mutable trade row can answer the first only by erasing evidence for the second. An event ledger can answer both.

## Duplicate, Bust, and Correction

These messages have different economic meanings.

### Duplicate

The same message arrives again with the same execution or event identifier and identical economics. Nothing changed. The consumer should process it idempotently and avoid applying the quantity twice.

### Bust

The original fill is formally cancelled. The ledger appends a new event with the opposite signed quantity:

$$
q_{bust}=-q_{original}
$$

The original record remains visible and the bust explicitly references it.

### Correction

A field such as quantity or price was wrong. A robust general model is:

1. append a bust that reverses the original fill;
2. append a replacement fill with corrected economics;
3. link all records through the original execution ID and a correction-group ID.

The principle is not merely technical. People acted on the previous state, so the system must preserve it:

> Do not rewrite the event that users previously observed; append the economic change that explains the new truth.

## Effective Time and Knowledge Time

Two timestamps are necessary:

- **Effective time** states when the execution economically occurred.
- **Ingestion time** states when the internal system learned about the fill, bust, or correction.

The correction may arrive at noon, while the replacement's effective time remains 10:00. The currently corrected economic timeline therefore contains a +60 position from 10:00. However, an incident replay with an 11:00 knowledge cutoff must still return the +100 position that the system knew at that time.

This bitemporal distinction supports both corrected truth and an honest as-was view.

## Worked Numerical Example

The original fill is buy 100 NEXT at 95.200. The multiplier is GBP 2,500 per price point, and the 11:00 market price is 95.212.

The originally published PnL is:

$$
OriginalPnL
=100(95.212-95.200)(2{,}500)
=GBP\ 3{,}000
$$

At noon, the quantity is corrected to 60. The ledger appends:

- a bust with signed quantity -100, linked to the original fill;
- a replacement fill with signed quantity +60 at 95.200.

The corrected economic PnL is:

$$
CorrectedPnL
=60(95.212-95.200)(2{,}500)
=GBP\ 1{,}800
$$

The restatement delta is:

$$
RestatementDelta
=1{,}800-3{,}000
=-GBP\ 1{,}200
$$

If each contract carries GBP 25/bp of signed DV01, risk changes from GBP 2,500/bp to GBP 1,500/bp. The risk restatement is therefore -GBP 1,000/bp.

The GBP 1,200 PnL change is not fresh market PnL or execution slippage. It corrects a result previously calculated from invalid execution economics. A dashboard should label it `EXECUTION_CORRECTION`; otherwise the user may infer that the market produced an unexplained loss at noon.

## Restatement Policy

The calculation is easier than the publication policy. A desk commonly distinguishes:

- **Live provisional PnL**, which may change as late or corrected events arrive;
- **official close PnL**, published after a defined cutoff and reconciliation;
- **post-close adjustments**, which may reopen a prior day or appear as a separately labelled current-day item.

Developers should not invent this policy. Trading, Operations, Product Control, and Finance need to define:

- the correction cutoff;
- whether historical dashboards are restated;
- whether the originally published number remains available;
- whether downstream consumers receive replacement snapshots, delta events, or both;
- how cross-business-date corrections enter activity PnL.

## Engineering Design

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ExecutionEvent:
    event_id: str
    event_type: str  # FILL, BUST, REPLACEMENT
    original_execution_id: str
    correction_group_id: str | None
    contract_id: str
    signed_quantity: int
    price: Decimal
    effective_at: datetime
    ingested_at: datetime


def replay_position(
    events: list[ExecutionEvent],
    knowledge_cutoff: datetime,
) -> dict[str, int]:
    position: dict[str, int] = {}
    seen: set[str] = set()

    eligible = [
        e for e in events
        if e.ingested_at <= knowledge_cutoff
    ]
    for event in sorted(
        eligible,
        key=lambda e: (
            e.effective_at,
            e.ingested_at,
            e.event_id,
        ),
    ):
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        position[event.contract_id] = (
            position.get(event.contract_id, 0)
            + event.signed_quantity
        )

    return position
```

The function supports as-was replay through the knowledge cutoff. A current corrected view uses the latest cutoff. PnL and risk services should consume the same replayed position state rather than implementing independent correction logic.

## Production Controls and Failure Modes

The most relevant controls are:

- **Unique event identity:** a bust receives a new event ID even though it references the original execution.
- **Exact reversal:** bust quantity and economics must reverse the referenced event according to a documented policy.
- **Lineage completeness:** replacements must reference both the original execution and correction group.
- **Bitemporal completeness:** effective and ingestion timestamps must be timezone-aware and immutable.
- **Impact reporting:** every correction triggers position, risk, and PnL replay and reports the restatement delta and affected books.

A particularly dangerous failure occurs when an upstream source sends the bust using the original event ID. A consumer's idempotency check may classify it as a duplicate and discard it, leaving the original 100-contract position active. Idempotency and economic lineage are both necessary; they are not the same control.

## Requirement Discovery and Interview Questions

Before implementing corrected executions, ask:

- Is a bust a complete cancellation, or will it always be followed by a replacement?
- Are price and quantity corrections both represented as bust-and-rebook?
- Does the replacement retain the original economic time?
- Does live PnL restate immediately, and what happens after official close?
- Should the API publish corrected snapshots, delta events, or both?
- Which reports must preserve the originally published value?
- Do corrections require trader acknowledgement?
- How are corrections crossing a business-date boundary attributed?

A concise interview explanation is:

> I model fills, busts, and replacements as immutable linked events. Effective time rebuilds the corrected economic position, while ingestion time reconstructs what the system knew at any historical cutoff. I replay position, risk, and PnL through one shared ledger and expose the difference as an execution-correction restatement rather than new market PnL.

## Key Takeaways

- A duplicate is a transport repeat; a bust is a new economic reversal.
- A correction is safely represented as bust plus replacement with explicit lineage.
- Append-only events preserve both current corrected truth and the previous as-was view.
- Effective time and ingestion time solve different replay problems.
- Restatement deltas must be labelled separately from market PnL and slippage.
- Official close and post-close correction policies require explicit desk and control-function agreement.
