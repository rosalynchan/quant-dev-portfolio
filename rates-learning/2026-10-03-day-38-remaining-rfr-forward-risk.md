# Measuring the Remaining Forward Risk of a Partially Fixed RFR Coupon

## Abstract

As an overnight-compounded RFR coupon moves through its observation period, official fixings replace projected daily rates. The coupon forecast becomes more certain, but its remaining market risk does not decline according to a simple fixing-coverage percentage. This article derives the projection PV01 of the unfixed observations, shows how that risk steps down when a fixing arrives, and separates forward risk from the discounting risk that can remain after the coupon amount is fully known.

## Desk Context

Consider a GBP 100 million receive-floating SONIA coupon. Three of five calendar days are already fixed; the remaining two days are projected at 4.20%. The contract uses ACT/365, the payment-date discount factor is 0.998, and the compounded growth factor from official observations is:

$$
A_{fixed}=1.000334271195.
$$

The trader asks: “The coupon is 60% fixed. What PnL do I get if the remaining SONIA projection moves by one basis point?”

This is not answered by multiplying the coupon’s original DV01 by 40%. Fixing coverage measures data state. Remaining PV01 depends on projected day weights, forward rates, compounding interactions, discounting, and pay/receive direction.

## Only Projected Observations Carry Forward Risk

A partially fixed forecast factor is:

$$
F=A_{fixed}
\prod_{j\in projected}
\left(1+f_j\frac{d_j}{B}\right)-1.
$$

Official observations are embedded in \(A_{fixed}\). They are historical facts and must remain frozen when the projection curve is bumped. Only future forwards \(f_j\) respond.

For projected observation \(k\):

$$
\frac{\partial Coupon}{\partial f_k}
=N A_{fixed}\frac{d_k}{B}
\prod_{j\ne k}
\left(1+f_j\frac{d_j}{B}\right).
$$

Multiplying by \(10^{-4}\) converts the derivative into an amount per basis point. Multiplying again by the payment-date discount factor gives projection PV01. Receive-floating normally has positive signed projection PV01; pay-floating reverses the sign.

## Worked Numerical Example

Treat the remaining two days as one projected observation:

$$
\begin{aligned}
\frac{\partial Coupon}{\partial f}
&=100{,}000{,}000
\times1.000334271195
\times\frac{2}{365}\\
&=GBP\ 548{,}128.37
\text{ per unit rate}.
\end{aligned}
$$

The coupon amount changes by:

$$
548{,}128.37\times0.0001
=GBP\ 54.81/bp.
$$

After discounting:

$$
ProjectionPV01
=54.81\times0.998
=GBP\ 54.70/bp.
$$

If the remaining projection rises by 6bp, first-order PnL is:

$$
54.70\times6=+GBP\ 328.20
$$

for receive-floating, or approximately -GBP 328.20 for pay-floating.

When the next observation becomes official, only one projected day remains. Ignoring immaterial compounding differences:

$$
100{,}000{,}000
\times1.00045
\times\frac{1}{365}
\times0.0001
\times0.998
\approx GBP\ 27.36/bp.
$$

Risk is roughly halved because projected day weight fell from two days to one—not because a dashboard converted 60% coverage into 40% residual risk.

## Where Does the Risk Go?

When an observation transitions from **PROJECTED** to **OFFICIAL**:

- its projection-curve sensitivity becomes zero;
- actual fixing minus prior projection enters fixing PnL;
- other unfixed observations retain projection risk;
- the known or partially known cashflow can still carry discounting risk.

Once every observation is official, the coupon amount is known, but payment may still be in the future:

$$
PV=KnownCoupon\times DF(t,T).
$$

A discount-curve move can therefore change PV even when projection PV01 is zero. An API field called **coupon_dv01** is ambiguous unless it identifies projection sensitivity, discount sensitivity, or a joint parallel shock.

A useful desk view shows fixing coverage, projection PV01 by observation or curve bucket, discounting DV01, next fixing date, and fixing-set and curve-snapshot lineage.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProjectedObservation:
    observation_id: str
    forward_rate: Decimal
    calendar_days: int
    curve_bucket: str
    status: str


def remaining_projection_pv01(
    notional: Decimal,
    fixed_growth_factor: Decimal,
    projected: list[ProjectedObservation],
    discount_factor: Decimal,
    receive_float: bool,
    basis: Decimal = Decimal("365"),
) -> dict:
    if any(x.status != "PROJECTED" for x in projected):
        raise ValueError("projected rows required")

    direction = Decimal("1") if receive_float else Decimal("-1")
    one_bp = Decimal("0.0001")
    result = {}

    for target in projected:
        other_growth = Decimal("1")
        for row in projected:
            if row.observation_id != target.observation_id:
                other_growth *= (
                    Decimal("1")
                    + row.forward_rate * row.calendar_days / basis
                )

        result[target.observation_id] = (
            direction * notional * fixed_growth_factor
            * Decimal(target.calendar_days) / basis
            * other_growth * one_bp * discount_factor
        )

    return {
        "pv01_by_observation": result,
        "total_projection_pv01": sum(
            result.values(), Decimal("0")
        ),
    }
```

The service must bump only rows in **PROJECTED** state. Fixed growth factor, projected forwards, discount factor, observation convention, and curve-bucket mapping all require versioned lineage.

Analytic PV01 should reconcile to bump-and-revalue within tolerance. Valuable invariant tests include:

- projection PV01 becomes zero after the last fixing;
- receive/pay reversal flips signed PV01;
- reducing projected day weight reduces risk;
- a projection bump does not change official observations.

## Production Failure Mode

A dangerous implementation applies a parallel projection bump to the whole coupon, including official observations. It then reports nearly unchanged forward DV01 as the coupon approaches the end of its observation period.

The trader may hedge risk that no longer exists. The hedge creates genuine exposure while the dashboard appears neutral.

Stale state can cause the same result: a fixing is ingested, but a valuation cache keyed only by trade ID and date retains the projected schedule. Fixing-set version must participate in cache identity and invalidation.

## Requirement Discovery and Interview Questions

When a trader asks for “remaining coupon risk,” clarify:

- Is the request for projection risk, discounting risk, or both?
- Is total PV01 sufficient, or is observation- or tenor-bucket risk required?
- Is the shock a parallel 1bp move or a key-rate bump?
- Which fixing cutoff and fixing-set version define official observations?
- How should a weekend-weighted observation map to the projection curve?
- Should the engine use analytic derivatives or bump-and-revalue?
- After full fixing, should the view continue to show discounting DV01?
- How quickly must risk refresh after a fixing arrives?

An interview-quality response should state that official rows are frozen, remaining forwards alone carry projection sensitivity, and fully fixed does not necessarily mean zero PV sensitivity.

That distinction is central to reliable desk communication and defensible production risk.

## Key Takeaways

- Fixing coverage is not a DV01 scaling rule.
- Only projected observations contribute projection-curve PV01.
- Each new fixing removes its observation’s forward sensitivity and creates a fixing-PnL event.
- A fully fixed but unpaid coupon can still carry discounting risk.
- Versioned fixing state, cache invalidation, and bump-and-revalue reconciliation are essential controls.
