# Managing Partial Fills and Temporary Exposure During a Futures Roll

## Abstract

A futures roll is often described as one clean transition from an expiring contract into the next expiry. Real execution is less tidy: one leg may complete first, the other may fill only partially, and the portfolio can carry an unintended exposure gap while the remainder waits. This article explains how a front-office system should distinguish targets, orders, fills, and positions; replay contract-level position states from execution events; separate temporary-exposure PnL from execution slippage; and control late, duplicate, or corrected fills.

## Desk Context

A strategy intends to replace 100 long FRONT futures with 100 long NEXT futures. The desk sells all 100 FRONT contracts, but initially buys only 60 NEXT contracts. The remaining 40 are filled twenty minutes later.

During those twenty minutes the portfolio has exposure to 60 contracts, not 100. A system that updates positions from the order target will overstate market risk and calculate PnL on contracts that were never held. A system that waits until end of day and observes the final 100-contract position will also lose the intraday path.

The governing principle is simple:

> An order expresses intent; a confirmed fill creates economic exposure.

## Four Quantities That Must Remain Distinct

A production workflow usually contains four related but non-interchangeable quantities:

- **Target quantity:** the strategy's desired final holding.
- **Order quantity:** the amount submitted to an execution venue.
- **Filled quantity:** the amount confirmed as executed.
- **Position quantity:** the economic holding after applying confirmed fills.

Orders may be rejected, partially filled, cancelled, replaced, busted, or corrected. Position state should therefore evolve through execution events:

$$
Q_{after}=Q_{before}+q_{signed\ fill}
$$

For a roll executed as two outright legs, the old- and new-contract fill streams are independent. The system must not represent the roll as a single Boolean state such as `ROLLED=true`. It needs explicit quantities by contract and time.

## Worked Numerical Example

Assume the strategy begins with:

- FRONT position: +100;
- NEXT position: 0;
- target NEXT position: +100;
- contract multiplier: GBP 2,500 per price point.

Execution events are:

1. At 10:00:00, sell 100 FRONT.
2. At 10:00:05, buy 60 NEXT at 95.200.
3. At 10:20:00, buy the remaining 40 NEXT at 95.188.

Between 10:00:05 and 10:20:00, the actual NEXT position is +60 while the target is +100. If one NEXT contract carries GBP 25/bp of signed DV01, the exposure gap is:

$$
TemporaryDV01=(60-100)\times25=-GBP\ 1{,}000/bp
$$

The negative sign means the strategy is GBP 1,000/bp less long than intended. It does not necessarily mean the absolute portfolio is short.

NEXT falls from 95.200 to 95.188 during the interval:

$$
\Delta P=95.188-95.200=-0.012
$$

The 60 contracts actually held produce:

$$
ActualPnL=60\times(-0.012)\times2{,}500=-GBP\ 1{,}800
$$

A target-based engine incorrectly assumes all 100 contracts were held:

$$
TargetBasedPnL=100\times(-0.012)\times2{,}500=-GBP\ 3{,}000
$$

The temporary-exposure effect relative to the target is therefore:

$$
(-1{,}800)-(-3{,}000)=+GBP\ 1{,}200
$$

This amount is not execution slippage. It arose because 40 intended long contracts did not participate in the price fall. Had the market risen, the same underfill would have produced an opportunity loss. Temporary exposure is path-dependent, not automatically a cost.

## Separate Exposure Effect from Slippage

Two PnL components must have non-overlapping boundaries:

1. **Execution slippage** compares each fill with a frozen benchmark.
2. **Temporary-exposure effect** compares actual and target quantities over the market move between fill events.

For piecewise intervals $i$:

$$
TemporaryExposureEffect
=\sum_i(Q_i^{actual}-Q_i^{target})\Delta P_iM
$$

Every confirmed fill changes $Q_i^{actual}$ and creates a new interval. End-of-day positions cannot reconstruct this path without event timestamps. Equally, the later 40-contract fill may have its own favorable or adverse fill-versus-benchmark slippage; that price-quality measure should not be added twice through the exposure component.

## Engineering Design

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Fill:
    execution_id: str
    timestamp: datetime
    contract_id: str
    signed_quantity: int
    price: Decimal


def replay_positions(
    opening: dict[str, int],
    fills: list[Fill],
) -> list[dict]:
    positions = opening.copy()
    seen: set[str] = set()
    states: list[dict] = []

    for fill in sorted(
        fills,
        key=lambda x: (x.timestamp, x.execution_id),
    ):
        if fill.execution_id in seen:
            continue
        seen.add(fill.execution_id)

        positions[fill.contract_id] = (
            positions.get(fill.contract_id, 0)
            + fill.signed_quantity
        )
        states.append({
            "effective_at": fill.timestamp,
            "execution_id": fill.execution_id,
            "positions": positions.copy(),
        })

    return states
```

The returned states form the position timeline used by intraday risk and PnL. A production implementation would also link every child execution to an economic roll identifier and retain both exchange event time and internal ingestion time.

## Data Quality and Production Controls

The highest-value controls are selective:

- **Idempotency:** use stable execution IDs so a duplicate fill message cannot change the position twice.
- **Event ordering:** calculate economics by exchange event time while retaining ingestion time for latency investigations.
- **Corrections:** represent a bust or correction as an auditable reversal and replacement event rather than silently overwriting history.
- **Visible completion state:** show target, filled, remaining, and explicit positions together.
- **Exposure timeout:** alert when a remaining quantity or target-risk gap exceeds a desk-approved duration or threshold.

A common failure occurs when the final 40-contract fill reaches the internal system late. The live dashboard temporarily shows 60 contracts. If the end-of-day replay then processes messages in ingestion order rather than exchange event order, it may place the exposure gap in the wrong market interval and generate an incorrect explain even though the final position is correct.

## Requirement Discovery

Before implementing “support partial rolls,” a developer should ask:

- Is the roll executed as an exchange spread or two outright orders?
- If the old leg completes first, may the strategy temporarily be flat or directional?
- How long may a remaining quantity wait before alerting or human intervention?
- Should the dashboard show actual exposure, target exposure, or both and their gap?
- Is the slippage benchmark frozen at parent-order, child-order, or individual-fill level?
- Do cancel/replace orders retain the same economic roll identifier?
- Does a late fill or bust reopen published intraday PnL?
- Is temporary-exposure effect an official PnL component or an execution diagnostic?

These questions convert an apparently simple execution request into explicit state, accounting, and control requirements.

## Interview Discussion

A concise interview answer might be:

> I would not update the position from the order target. Confirmed fills drive a time-ordered position state by explicit contract. Between fills, I calculate risk and PnL on the actual quantity, while separately measuring the gap to the target. Fill-versus-benchmark slippage and temporary-exposure PnL have distinct boundaries. Stable execution IDs, event-time replay, auditable corrections, and reconciliation to the final clearing position keep the workflow reliable.

Useful follow-up questions include:

1. Why is an order quantity not an economic position?
2. How would you distinguish execution slippage from opportunity PnL caused by an underfill?
3. Why must partial-fill PnL be calculated piecewise?
4. How should duplicate and corrected fills affect an event-sourced ledger?
5. Which timestamp drives economics, and which timestamp supports operational monitoring?

## Key Takeaways

- Targets and orders describe intent; confirmed fills create positions.
- A partial roll creates a time-varying exposure gap that must be measured between fill events.
- Temporary-exposure PnL is distinct from fill-versus-benchmark slippage.
- Explicit contract IDs and an event-driven position timeline preserve the intraday path.
- Idempotency, event-time ordering, auditable corrections, and visible remaining quantity are essential production controls.
