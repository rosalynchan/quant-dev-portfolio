# Marking a Forward Rate Agreement Before Fixing

## Abstract

Before a Forward Rate Agreement fixes, its payoff is not known. The trade is marked from the market-implied forward rate for the underlying accrual period, compared with the contractual FRA rate and discounted to the valuation date. This article builds the pre-fixing mark-to-market of a receive-floating 3x6 FRA, derives its forward PV01, and shows how a robust implementation separates projection risk, discount risk, and the later official settlement state.

## Desk Context

Consider a GBP 100 million receive-floating, pay-fixed 3x6 FRA. The contractual rate is 4.00%, the current projected three-month forward is 4.35%, the accrual fraction is 0.25, and the discount factor to the end of the underlying period is 0.985. The reference rate has not fixed.

The trader asks two questions: “What is the FRA worth?” and “How much does that value change if the projected forward rises by one basis point?”

Those questions concern current valuation and projection risk. They are different from the fixing-date cash settlement calculated once an official rate exists.

## From Forward Rate to Present Value

Before fixing, the future reference rate $L$ is unknown. The pricing system instead obtains a market-implied forward rate $F(t;T_1,T_2)$ from the designated projection curve.

For a receive-floating, pay-fixed FRA, a practical period-end-equivalent valuation is:

$$
PV=N\alpha(F-K)DF(t,T_2)
$$

where $T_1$ is the underlying period start, $T_2$ is its end, and $DF(t,T_2)$ comes from the discount curve.

Under a single-curve intuition, this is consistent with first converting the interest difference into a start-date settlement and then discounting it to today:

$$
DF(t,T_2)
\approx
\frac{DF(t,T_1)}{1+F\alpha}
$$

In a collateralised multi-curve framework, the projection forward and discount factors play different economic roles and may come from different curves. The API must therefore preserve curve role, not merely a generic curve identifier.

## Worked Numerical Example

The forward-strike difference is:

$$
F-K=4.35\%-4.00\%=0.35\%=0.0035
$$

The period-end-equivalent interest value is:

$$
100{,}000{,}000\times0.25\times0.0035
=GBP\ 87{,}500
$$

Discounting to the valuation date gives:

$$
PV=87{,}500\times0.985
=+GBP\ 86{,}187.50
$$

The value is positive because the position receives a projected floating rate above the fixed rate it pays.

### Forward PV01

If the target forward is bumped by one basis point while the discount curve is held fixed, the first-order sensitivity is:

$$
ForwardPV01=N\alpha DF(t,T_2)\times10^{-4}
$$

For the example:

$$
100{,}000{,}000
\times0.25
\times0.985
\times0.0001
=+GBP\ 2{,}462.50/bp
$$

A 4bp increase in the forward therefore produces approximately:

$$
ProjectionPnL
\approx2{,}462.50\times4
=+GBP\ 9{,}850
$$

The simplified expression is linear in the forward, so an isolated full revaluation gives the same change. A production curve rebuild may also move discount factors or neighbouring forwards unless the risk scenario explicitly freezes them.

## Present Value Is Not Final Settlement

Pre-fixing PV uses a projected forward under today’s market snapshot. Once the official fixing $L$ is published, a standard settlement-in-advance FRA uses:

$$
Settlement_{T_1}
=\frac{N\alpha(L-K)}{1+L\alpha}
$$

The two numbers should not be compared without aligning their dates and information states:

- today’s PV is discounted to the valuation date;
- fixing-date cash occurs at $T_1$;
- $F$ is a market projection, while $L$ is a realised official observation;
- projection risk exists before fixing and disappears after fixing.

A daily PnL explain should isolate the `PROJECTED -> OFFICIAL` fixing roll from any same-day discount-curve move. Otherwise the apparent fixing component includes unrelated discounting effects.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FraMarkInput:
    trade_id: str
    notional: Decimal
    fixed_rate: Decimal
    forward_rate: Decimal
    accrual_fraction: Decimal
    end_discount_factor: Decimal
    receive_floating: bool
    fixing_status: str
    projection_curve_id: str
    discount_curve_id: str
    market_snapshot_id: str


def mark_fra_before_fixing(x: FraMarkInput) -> dict:
    if x.fixing_status != "PROJECTED":
        raise ValueError("pre-fixing valuation required")

    direction = (
        Decimal("1")
        if x.receive_floating
        else Decimal("-1")
    )
    pv = (
        direction
        * x.notional
        * x.accrual_fraction
        * (x.forward_rate - x.fixed_rate)
        * x.end_discount_factor
    )
    forward_pv01 = (
        direction
        * x.notional
        * x.accrual_fraction
        * x.end_discount_factor
        * Decimal("0.0001")
    )

    return {
        "trade_id": x.trade_id,
        "pv": pv,
        "forward_pv01": forward_pv01,
        "fixing_status": x.fixing_status,
        "projection_curve_id": x.projection_curve_id,
        "discount_curve_id": x.discount_curve_id,
        "market_snapshot_id": x.market_snapshot_id,
    }
```

This function deliberately refuses an official fixing state. Once fixing occurs, the trade should transition to the settlement calculation rather than continuing to consume a projection forward.

## Data Quality and Production Controls

The most relevant controls are:

1. **State-specific valuation:** projected observations use forwards; official observations use settlement logic.
2. **Period alignment:** index tenor, forward start and end dates, and contractual FRA dates must match.
3. **Curve-role lineage:** projection and discount curves must be labelled and tied to a coherent market snapshot.
4. **Unit validation:** rates, accrual fraction, discount factor, notional, and currency require explicit units and bounds.
5. **Bump reconciliation:** analytic forward PV01 should agree with an isolated +1bp bump-and-revalue within tolerance.

A dangerous failure occurs when the official fixing arrives but a cache still returns the previous `PROJECTED` state. The risk service continues to report GBP 2,462.50 per basis point of forward exposure. A trader may hedge a risk that no longer exists, creating a new real exposure through the hedge itself.

Useful observability includes projected FRAs past the fixing publication cutoff, official FRAs with non-zero projection PV01, projection and discount snapshots that do not align, and analytic-versus-bumped risk breaks.

## Requirement Discovery and Interview Questions

When asked to “mark the FRA,” clarify:

- Has the trade fixed, and which valuation state applies?
- Is the requested number economic PV, settlement value, or an accounting mark?
- Which index projection curve supplies the forward?
- Which collateral or OIS curve supplies discount factors?
- Is risk required as one forward PV01 or as curve-node buckets?
- Does the forward bump freeze the discount curve?
- How quickly should publication of the official fixing clear projection risk?
- Which market snapshot and valuation timestamp define the result?

In an interview, a strong answer distinguishes projected $F$ from realised $L$, explains why pre-fixing PV is not the later cash settlement, and designs the state transition so projection risk becomes zero when fixing is official.

## Key Takeaways

- Before fixing, a FRA is valued from the current forward versus its contractual strike.
- The projection forward and discount factor have separate curve roles.
- A receive-floating FRA has positive forward PV01 under the stated sign convention.
- Pre-fixing PV and fixing-date settlement differ in both date and information state.
- Official fixing publication must switch valuation logic and remove projection risk.
- Explicit snapshot lineage and isolated bump tests prevent plausible but economically incorrect risk.
