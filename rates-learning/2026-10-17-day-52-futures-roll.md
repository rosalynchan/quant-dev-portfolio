# Rolling a Futures Hedge Across Expiries

## Abstract

A futures hedge must be moved before its contract expires. The desk closes the old expiry and opens a later one, but equal contract counts do not necessarily preserve risk. This article develops a DV01-preserving roll, separates calendar-spread execution from hedge residual, and shows how a front-office system should control temporary exposure when the two legs fill at different times.

## Desk Context

A portfolio is hedged with 455 short front-month futures. The roll date is approaching. Each old short contract has GBP +24.75/bp of signed rate-up DV01, while the next expiry has GBP +25.10/bp.

The trader asks: “Roll the hedge into the next expiry without changing our target rate risk.”

The primary concept is the **futures hedge roll**. The related operational concept is legging risk.

## Two Legs, One Objective

Let $N_{old}$ be the current short quantity and $D_{old}$ and $D_{new}$ the DV01 per short old and new contract. Existing hedge risk is:

$$
R_{old}=N_{old}D_{old}
$$

To preserve that risk:

$$
N_{new}^{*}=\frac{N_{old}D_{old}}{D_{new}}
$$

Execution requires buying the old contract to close the short and selling the new contract to establish its replacement. Together they form a calendar spread, but the business objective is risk migration rather than a speculative spread trade.

## Worked Numerical Example

Existing hedge risk is:

$$
455\times24.75=+GBP\ 11{,}261.25/bp
$$

The risk-equivalent new quantity is:

$$
N_{new}^{*}=\frac{11{,}261.25}{25.10}=448.6554
$$

Nearest-integer rounding gives 449 new short contracts. Their risk is:

$$
449\times25.10=+GBP\ 11{,}269.90/bp
$$

With portfolio risk of GBP -11,260/bp, the final residual is:

$$
-11{,}260+11{,}269.90=+GBP\ 9.90/bp
$$

This is inside a hypothetical GBP 15/bp tolerance.

A one-for-one roll into 455 new contracts produces GBP +11,420.50/bp of hedge risk and a GBP +160.50/bp residual. The difference is caused by unequal contract DV01, not rounding noise.

## Roll Price Is Not Roll Risk

The calendar spread may be quoted as:

$$
Spread=P_{new}-P_{old}
$$

The achieved spread determines execution quality. Quantities determine migrated risk. A useful explain separates:

- **roll slippage** relative to a decision or arrival spread;
- **quantity residual** after integer rounding;
- **post-roll basis risk** because the new expiry may track the portfolio differently.

A favourable spread does not prove the hedge quantity is correct. A near-zero DV01 residual does not prove execution was cheap.

## Legging Risk

If the old short is closed before the new short opens, the portfolio is temporarily under-hedged. Closing all 455 old contracts removes GBP +11,261.25/bp of hedge risk, returning the portfolio to roughly GBP -11,260/bp until the new leg fills.

If the new short fills first, the desk temporarily holds both hedges and becomes over-hedged. Controls may use a native exchange spread order, synchronised child orders, proportional fills, temporary-DV01 limits, and maximum legging time.

Submitted quantities are not positions. Temporary risk must use confirmed fills on each leg.

For proportional execution, the service can convert each confirmed old-leg fill into a target new-leg quantity using the DV01 ratio. For example, closing 100 old shorts removes GBP 2,475/bp. Replacing that risk requires about 98.61 new shorts, so the policy may submit 99 while monitoring the small temporary over-hedge. This calculation must use cumulative fills rather than rounding every tiny child fill independently; repeated local rounding can drift materially from the parent-order target. If either leg is rejected or halted, the workflow should stop automatic replenishment, expose the current economic position, and require an explicit trader decision instead of assuming the other leg will eventually execute.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class FuturesRollRequest:
    old_short_contracts: int
    old_short_dv01: Decimal
    new_short_dv01: Decimal
    portfolio_dv01: Decimal
    residual_limit: Decimal
    risk_snapshot_id: str


def plan_futures_roll(x: FuturesRollRequest) -> dict:
    if x.old_short_dv01 <= 0 or x.new_short_dv01 <= 0:
        raise ValueError("short-contract DV01 must be positive")

    migrated_risk = (
        Decimal(x.old_short_contracts) * x.old_short_dv01
    )
    theoretical = migrated_risk / x.new_short_dv01
    new_contracts = theoretical.quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    residual = (
        x.portfolio_dv01
        + new_contracts * x.new_short_dv01
    )

    return {
        "close_old_contracts": x.old_short_contracts,
        "open_new_short_contracts": int(new_contracts),
        "theoretical_new_contracts": theoretical,
        "final_residual_dv01": residual,
        "status": (
            "ACCEPTABLE"
            if abs(residual) <= x.residual_limit
            else "RESIDUAL_BREACH"
        ),
        "risk_snapshot_id": x.risk_snapshot_id,
    }
```

This produces a plan, not a live position. Execution events must update old-leg and new-leg fills independently and recalculate temporary and final residuals.

## Production Controls

- Old and new DV01 must share risk coordinate, bump method, currency, and snapshot.
- Reference data must validate expiry, multiplier, tick size, and eligibility.
- The roll must store explicit contract IDs and a versioned trigger policy.
- Fills on both legs must be deduplicated and corrected independently.
- Final acceptance must re-risk actual filled positions.

A dangerous failure occurs when the alias FRONT changes overnight. The recommendation refers to the old contract, while execution later resolves the alias to the new one. The system may open the replacement without closing the original position.

Useful observability includes days to expiry, roll coverage, peak temporary DV01, leg-imbalance age, and final residual.

## Requirement Discovery

Clarify the roll trigger, risk objective, eligible next expiry, spread-versus-separate execution, temporary-risk limit, maximum legging time, rounding policy, spread benchmark, and ownership of residual basis risk.

> I treat a futures roll as a two-leg execution with one risk objective. I size the new expiry by signed DV01 rather than contract count, track confirmed fills on both legs, enforce temporary-risk limits, and re-risk the completed position. Spread slippage and hedge residual remain separate.

## Key Takeaways

- Equal contract counts do not imply equal risk across expiries.
- Size the new expiry by risk, then round and re-risk.
- Spread execution quality and hedge residual are separate.
- Partial execution can create temporary under- or over-hedging.
- Explicit contract identifiers prevent front-alias errors.

