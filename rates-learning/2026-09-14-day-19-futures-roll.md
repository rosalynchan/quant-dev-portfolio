# Rolling a Bond-Futures Hedge: Preserve DV01, Not Contract Count

## Abstract

Rolling a bond-futures hedge is not a clerical replacement of one expiry with another. The next contract can have a different cheapest-to-deliver bond, conversion factor, carry profile, liquidity, and DV01 per contract. A robust roll therefore begins with the hedge objective, recalculates the required quantity, measures rounding risk, and tracks both legs from actual fills. This article shows how a quant developer can translate “roll 200 lots” into an auditable risk and execution workflow.

## Desk Context

A rates desk holds a long cash-bond portfolio with signed curve DV01 of GBP -15,800 per basis point. It is hedged with 200 short front-month government-bond futures. Each short front contract currently contributes GBP +79/bp, so the opening package is approximately DV01-neutral:

$$
-15{,}800 + 200 \times 79 = 0
$$

The front contract is approaching expiry. The trader asks to “roll the 200 lots” into the next contract.

That instruction is operationally clear enough to identify the two instruments, but economically incomplete. Does the trader want the same number of contracts, or the same interest-rate sensitivity? Those are different targets when the next contract has a different per-contract DV01.

## What a Futures Roll Actually Does

A short hedge roll has two legs:

1. Buy the front contract to close the existing short.
2. Sell the next contract to establish the replacement short.

The legs may be executed together as a calendar spread to reduce leg risk. Risk and control systems should still retain the individual contract identifiers, signed quantities, prices, multipliers, CTD assumptions, and fills.

The contract DV01 can change across expiries because each contract has its own deliverable basket and delivery economics. Its current CTD may have a different duration and conversion factor. Time to delivery, repo conditions, and liquidity also differ. Preserving contract count can therefore introduce a material hedge error.

## Preserve the Intended Risk

Let signed cash DV01 be $D_{cash}<0$, and let one short next-contract future contribute positive sensitivity $d_{next}>0$. The theoretical quantity that offsets the cash risk is:

$$
N_{next}^{*}
=
\frac{-D_{cash}}{d_{next}}
$$

Because futures quantities are integers, the implemented quantity requires a rounding policy:

$$
N_{next}
=
Round(N_{next}^{*})
$$

The residual package risk is:

$$
ResidualDV01
=
D_{cash}
+
N_{next}d_{next}
$$

Nearest-integer rounding is common, but it is not universal. A desk may prefer to avoid over-hedging, use another instrument for the remainder, or apply a portfolio-specific hedge beta. The policy belongs in the requirement, not as a hidden library default.

## Worked Example

Assume the next contract provides GBP +84/bp per short contract.

Copying the old quantity produces:

$$
ResidualDV01_{same\ count}
=
-15{,}800
+
200\times84
=
+GBP\ 1{,}000/bp
$$

The package becomes over-hedged. A one-basis-point rate rise would produce an estimated GBP 1,000 gain rather than approximately zero PnL.

Recalculating the quantity gives:

$$
N_{next}^{*}
=
\frac{15{,}800}{84}
=
188.095
$$

Rounding to 188 short contracts gives:

$$
ResidualDV01
=
-15{,}800
+
188\times84
=
-GBP\ 8/bp
$$

The rounding residual is small and visible. The same-count roll would have created a GBP 1,000/bp mismatch.

Now estimate execution cost. Suppose closing the front contract costs 0.015 price points of half-spread, opening the next costs 0.020 points, and each contract has a GBP 1,000 multiplier:

$$
FrontCost
=
200\times1{,}000\times0.015
=
GBP\ 3{,}000
$$

$$
NextCost
=
188\times1{,}000\times0.020
=
GBP\ 3{,}760
$$

$$
TotalExecutionCost
=
GBP\ 6{,}760
$$

This amount belongs in execution or slippage attribution. It should not be hidden in rates PnL. The quoted calendar spread, or roll price, is the price difference between two contracts with different carry and delivery economics; it is not by itself an instantaneous profit or loss.

## Engineering the Roll Workflow

A useful service calculates the target and estimated cost, but completion status must be driven by fills. Submission is not completion: one leg can fill while the other is rejected or partially executed.

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class RollRequest:
    cash_dv01: Decimal
    front_quantity: int
    next_dv01_per_short: Decimal
    front_half_spread: Decimal
    next_half_spread: Decimal
    multiplier: Decimal
    snapshot_id: str


def plan_dv01_roll(x: RollRequest) -> dict:
    if x.next_dv01_per_short <= 0:
        raise ValueError("next-contract DV01 must be positive")

    target = -x.cash_dv01 / x.next_dv01_per_short
    next_quantity = int(
        target.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )

    residual = (
        x.cash_dv01
        + Decimal(next_quantity) * x.next_dv01_per_short
    )

    estimated_cost = (
        abs(x.front_quantity) * x.multiplier * x.front_half_spread
        + abs(next_quantity) * x.multiplier * x.next_half_spread
    )

    return {
        "close_front_quantity": x.front_quantity,
        "open_next_quantity": next_quantity,
        "residual_dv01": residual,
        "estimated_execution_cost": estimated_cost,
        "snapshot_id": x.snapshot_id,
    }
```

The resulting plan should be joined to an execution record containing order IDs, actual quantities, average fill prices, timestamps, and status for both legs. After every fill event, the system should rebuild the live package DV01 rather than assuming the target position exists.

## Data Quality and Production Considerations

The highest-value controls are specific to the roll:

- Validate both contract months and use fresh CTD, conversion-factor, and DV01 inputs.
- Make quantity sign, price units, multipliers, and DV01 sign conventions explicit.
- Track remaining front exposure and acquired next exposure after every partial fill.
- Alert when residual DV01 or realized slippage breaches its tolerance.
- Never replace a failed next-contract risk calculation with zero or the old contract’s DV01.

A common failure occurs when the close leg fills and the open leg does not. If the system marks the roll complete at order submission, the desk can be left with an unhedged cash portfolio while the dashboard displays the intended position. Fill-driven state and observable leg risk are essential.

## Requirement Discovery

When a trader says “roll 200 lots,” a developer should clarify:

- Is the objective same count, same DV01, or beta-adjusted DV01?
- Which risk snapshot should drive the quantity: live, official close, or stressed?
- Is the roll triggered by a fixed date, liquidity threshold, or manual decision?
- Will it be executed as a calendar spread or as separate orders?
- Should cost use mid prices, executable quotes, or actual fills?
- What rounding rule and residual-DV01 tolerance apply?
- What should happen after a partial fill, rejection, or cancellation?

A concise conversation might be:

**Trader:** “Roll the 200 September shorts into December.”

**Developer:** “Do you want the same count or the same DV01? December is GBP 84/bp per short versus GBP 79 for September.”

**Trader:** “Keep DV01 flat and show the cost.”

**Developer:** “The target is 188 December shorts, leaving about GBP -8/bp residual. I’ll track both fills, separate slippage from market PnL, and alert if either leg remains incomplete.”

## Interview Questions

1. Why can equal contract counts across expiries produce unequal hedge risk?
2. How would you calculate and report the residual created by integer rounding?
3. Why should roll execution cost be separated from rates PnL?
4. What state transition proves that a two-leg roll is complete?
5. Which inputs must be refreshed when the next contract has a different CTD?

## Key Takeaways

A futures roll should preserve the desk’s intended economic exposure, not blindly preserve contract count. Recalculate the next quantity using current CTD-adjusted contract DV01, expose the integer-rounding residual, and retain the assumptions that produced it. Treat the close and open legs as observable execution states driven by actual fills. Finally, separate calendar-spread pricing and execution slippage from market PnL so both hedge effectiveness and trading quality remain explainable.