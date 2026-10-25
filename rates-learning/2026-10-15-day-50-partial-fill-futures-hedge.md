# Re-Risking a Futures Hedge After Partial Fills

## Abstract

A hedge recommendation is not a hedge position. Between calculation and execution, futures orders may be partially filled, filled at different times, or rejected. A production front-office workflow must therefore distinguish recommended quantity, ordered quantity, filled quantity, and remaining quantity, then re-risk the portfolio using the actual fills. This article develops that workflow with a numerical example, a compact Python design, and the controls needed to prevent stale recommendations from being reported as completed hedges.

## Desk Context

Suppose a rates portfolio has a signed market-quote DV01 of GBP -11,260 per basis point in a target futures bucket. One short futures contract contributes GBP +24.75 per basis point on the same rate-up convention. The theoretical hedge is 454.95 contracts, so the desk submits an order to short 455 contracts.

The order is not immediately completed. Only 300 contracts fill. A dashboard that displays the original projected residual of GBP +1.25 per basis point is now misleading: it describes the recommendation, not the live position.

The primary concept is **fill-aware re-risking**. The related operational distinction is between order state and economic position state.

## Recommendation, Order, and Fill Are Different Facts

The recommendation engine solves for a target quantity. The order-management system records what was submitted. The execution venue reports fills. Only confirmed fills change the economic position.

For portfolio risk $R_P$, signed risk per filled contract $R_H$, and cumulative filled quantity $n_f$, the live residual is:

$$
R_{live}=R_P+n_fR_H
$$

The recommended residual is a separate quantity:

$$
R_{recommended}=R_P+n^*R_H
$$

These values coincide only when the recommended quantity is fully filled under the assumptions used to calculate the hedge.

This leads to four quantities that should never be collapsed into one field:

- **recommended quantity**: the risk-derived target;
- **ordered quantity**: what was submitted to execution;
- **filled quantity**: the cumulative confirmed execution;
- **remaining quantity**: the unfilled part of the active order.

An order can be `PARTIALLY_FILLED` while the hedge remains materially incomplete. Conversely, a cancelled remainder does not undo the contracts already filled.

## Worked Numerical Example

The portfolio and contract risks are:

$$
R_P=-GBP\ 11{,}260/bp
$$

$$
R_H=+GBP\ 24.75/bp
$$

The desk recommends and orders 455 short contracts. The execution venue confirms an initial fill of 300 contracts.

The filled hedge risk is:

$$
300\times24.75=+GBP\ 7{,}425/bp
$$

The live residual is therefore:

$$
R_{live}=-11{,}260+7{,}425=-GBP\ 3{,}835/bp
$$

Only 66.0% of the original absolute risk has been neutralised:

$$
1-\frac{3{,}835}{11{,}260}=65.94\%
$$

The remaining active order is 155 contracts. If a second fill confirms 100 contracts, cumulative fills become 400 and the live residual becomes:

$$
-11{,}260+400\times24.75=-GBP\ 1{,}360/bp
$$

If the final 55 contracts are then cancelled, the position stays at 400 contracts. The residual remains GBP -1,360 per basis point; cancellation changes the order state, not the filled economic position.

If a trader instead sends a replacement order for 55 contracts and all of it fills, cumulative economic fills reach 455:

$$
-11{,}260+455\times24.75=+GBP\ 1.25/bp
$$

The originally projected residual is achieved only at this point.

## Why Fill Price Is Not the Only Update

For a linear futures hedge, contract count is the first-order driver of DV01. Execution price affects realised and mark-to-market PnL, but a contract filled later may also have a different effective DV01 because market levels, time to expiry, curve mapping, or convexity inputs have changed.

Two operational modes are therefore common:

1. **Fast fill update:** multiply the confirmed fill quantity by the pre-trade contract DV01. This gives a low-latency residual estimate.
2. **Authoritative re-risk:** add the actual filled position to the current portfolio and run the approved risk engine on a consistent market snapshot.

The first result should be labelled estimated. The second should replace it when available. A dashboard must not silently mix a live portfolio risk with yesterday's contract risk.

## Engineering Design

The safest design is event-driven and idempotent. Fill events carry stable execution identifiers. The service maintains cumulative economic quantity, ignores exact duplicates, and recalculates residual risk after each accepted event.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Fill:
    execution_id: str
    signed_quantity: int
    contract_dv01: Decimal


def apply_fills(
    portfolio_dv01: Decimal,
    fills: list[Fill],
    residual_limit: Decimal,
) -> dict:
    seen: set[str] = set()
    filled_risk = Decimal("0")
    filled_quantity = 0

    for fill in fills:
        if fill.execution_id in seen:
            continue
        seen.add(fill.execution_id)

        filled_quantity += fill.signed_quantity
        filled_risk += (
            Decimal(fill.signed_quantity)
            * fill.contract_dv01
        )

    residual = portfolio_dv01 + filled_risk

    return {
        "filled_quantity": filled_quantity,
        "filled_hedge_dv01": filled_risk,
        "residual_dv01": residual,
        "status": (
            "WITHIN_TOLERANCE"
            if abs(residual) <= residual_limit
            else "HEDGE_INCOMPLETE"
        ),
        "processed_execution_ids": sorted(seen),
    }
```

The sign of `signed_quantity` must follow an explicit contract convention—for example, positive for short contracts when short rate-up DV01 is positive. In a larger system, fill ingestion and risk calculation should be separated: the position ledger owns the authoritative filled quantity, while the risk service owns valuation.

## Data Quality and Production Controls

The most relevant controls are:

- **Idempotency:** duplicate execution messages must not double the position. Use a stable execution ID, not arrival timestamp, as the deduplication key.
- **Correction handling:** a bust or correction must reverse or replace the original fill through a linked lifecycle event; deleting history destroys auditability.
- **Instrument identity:** contract code, expiry, currency, multiplier, and position direction must match the recommendation.
- **Risk lineage:** estimated residuals must retain the portfolio snapshot and contract-risk snapshot; authoritative results must state the new common snapshot.
- **State separation:** order status, fill status, and risk status require separate fields. `FILLED` does not automatically mean `WITHIN_TOLERANCE` if portfolio risk moved while execution was in progress.

A classic failure occurs when an execution gateway retries the same fill after a timeout. If the consumer is not idempotent, 100 actual contracts may be booked as 200. The system will display a dramatically smaller residual—or even an opposite-sign over-hedge—while the exchange position remains unchanged.

Useful observability is selective: duplicate-fill count, unprocessed-fill age, position breaks between the execution ledger and risk position, and time from fill confirmation to refreshed residual.

## Requirement Discovery and Interview Questions

When a trader asks to “keep the hedge updated,” clarify:

- Does the live residual use last confirmed fills or ordered quantity?
- What event makes a fill authoritative: venue execution, broker confirmation, or internal booking?
- How are partial fills, busts, corrections, and cancel-replace chains represented?
- Should a quick estimated residual appear before full re-risking completes?
- What snapshot and staleness limit apply to contract DV01 during execution?
- Does the system automatically recommend a top-up, or only display the remaining risk?
- Is over-hedging or a residual sign flip allowed?
- What happens if portfolio risk changes because another trade arrives during execution?

A concise interview answer is:

> I separate recommendation, order, and execution state. Each confirmed fill updates the economic position through an idempotent event, after which I recalculate the signed residual. I expose a fast estimate if needed, but the authoritative status comes from re-risking the actual filled portfolio on a consistent snapshot.

## Key Takeaways

- A recommended hedge is not an executed hedge.
- Only confirmed economic fills should change live residual risk.
- Partial fills require immediate residual recalculation; cancelled remainders do not reverse prior fills.
- Duplicate, corrected, and busted executions need explicit lifecycle handling.
- Fast quantity-times-DV01 estimates are useful, but authoritative risk should revalue the actual filled position.
- A production dashboard must show recommended, ordered, filled, remaining, and residual quantities separately.

