# Discounting DV01 After an RFR Coupon Is Fully Fixed

## Abstract

When the final RFR observation becomes official, the coupon amount no longer depends on the projection curve. Its projection PV01 should be zero. Yet an unpaid coupon remains a future cashflow, so its present value still depends on the discount curve. This article derives the discounting DV01 of a known cashflow, explains how it decays toward payment, and translates the lifecycle into explicit risk APIs, controls, tests, and desk requirements.

## Desk Context

Assume the next net coupon on a receive-floating swap is fully fixed:

- known receivable: GBP 8 million;
- time to payment: 0.25 years;
- flat continuously compounded discount rate: 4.00%;
- projection risk: zero;
- settlement has not occurred.

The trader asks: “The coupon is fully fixed. Why does it still show DV01?”

The answer is that **fully fixed describes the amount**, not the present value of receiving that amount in the future.

## Present Value of a Known Cashflow

For known future cashflow \(C\):

$$
PV=C\times DF(t,T).
$$

Under a flat continuously compounded zero rate \(z\):

$$
DF(t,T)=e^{-z\tau},
$$

where \(\tau=T-t\). Differentiating with respect to the zero rate:

$$
\frac{\partial PV}{\partial z}
=-C\tau e^{-z\tau}
=-PV\tau.
$$

The first-order PV change for a 1bp upward shift is:

$$
DiscountDV01
\approx -PV\tau\times10^{-4}.
$$

For a future receivable, a higher discount rate lowers the discount factor and PV, so signed discount DV01 is negative. A future payable has the opposite sign.

This sensitivity differs from projection PV01. Projection risk changes the forecast cashflow amount; discounting risk changes the present value of an amount that is already known.

## Worked Numerical Example

The discount factor is:

$$
DF=e^{-0.04\times0.25}=0.99004983.
$$

The present value is:

$$
PV
=8{,}000{,}000\times0.99004983
=GBP\ 7{,}920{,}398.67.
$$

Its discount DV01 is:

$$
\begin{aligned}
DiscountDV01
&\approx
-7{,}920{,}398.67
\times0.25
\times0.0001\\
&=-GBP\ 198.01/bp.
\end{aligned}
$$

If the discount rate rises by 7bp:

$$
DiscountPnL
\approx-198.01\times7
=-GBP\ 1{,}386.07.
$$

A full revaluation gives:

$$
PV_{new}
=8{,}000{,}000
\times e^{-0.0407\times0.25}
\approx GBP\ 7{,}919{,}012.72.
$$

The exact change is approximately -GBP 1,385.95, close to the linear estimate. The small difference reflects curvature and rounding.

## Risk Decays Toward Payment

Suppose the same GBP 8 million cashflow is only 0.05 years from payment:

$$
|DV01|
\approx
8{,}000{,}000
\times e^{-0.04\times0.05}
\times0.05
\times10^{-4}
\approx GBP\ 39.92/bp.
$$

The sensitivity has fallen from about GBP 198/bp to GBP 40/bp because less discounting time remains.

At the agreed ex-cash boundary, the receivable is removed from trade valuation and becomes expected or settled cash. After that transition, the coupon should not continue contributing trade discount DV01. A delayed settlement may create a cash-reconciliation issue, but it should not resurrect projection risk or automatically be labelled as rates-market PnL.

## Three Distinct States

A desk system must distinguish:

1. **Projection PV01:** sensitivity of unfixed observations to the projection curve.
2. **Discount PV01:** sensitivity of future cashflows to the discount curve.
3. **Cash settlement:** whether payment has actually occurred.

After full fixing, the first is zero, the second may remain non-zero, and the third may still be pending.

Therefore, “risk is zero,” “cashflow amount is known,” and “cash is settled” are not equivalent states. In a multi-curve framework, the API must identify the curve’s economic role. A generic curve ID does not reveal whether a bump forecasts the amount or discounts it.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class KnownCashflow:
    cashflow_id: str
    amount: Decimal
    year_fraction_to_payment: Decimal
    discount_factor: Decimal
    fixing_status: str
    settlement_status: str
    discount_curve_id: str
    market_snapshot_id: str


def known_cashflow_discount_dv01(
    x: KnownCashflow,
) -> dict:
    if x.fixing_status != "FULLY_FIXED":
        raise ValueError("known cashflow required")

    if x.settlement_status == "SETTLED":
        raise ValueError(
            "settled cashflow has no trade PV01"
        )

    pv = x.amount * x.discount_factor
    dv01 = (
        -pv
        * x.year_fraction_to_payment
        * Decimal("0.0001")
    )

    return {
        "cashflow_id": x.cashflow_id,
        "pv": pv,
        "projection_pv01": Decimal("0"),
        "discount_pv01": dv01,
        "curve_role": "DISCOUNT",
        "discount_curve_id": x.discount_curve_id,
        "market_snapshot_id": x.market_snapshot_id,
    }
```

The compact formula is useful for intuition and controls. A production engine should also bump and rebuild the contractual discount curve because node interpolation and curve construction determine actual bucketed sensitivity.

## Production Controls and Observability

The most relevant controls are:

- require zero projection PV01 for fully fixed coupons;
- ensure a discount shock changes discount factors without re-projecting known amounts;
- align payment date, valuation timestamp, and year-fraction convention;
- remove trade PV and DV01 consistently at the ex-cash or settlement-policy boundary;
- reconcile analytic PV01 to +1bp bump-and-revalue within tolerance.

Useful exception metrics include fully fixed coupons with non-zero projection PV01, settled cashflows with non-zero trade PV, discount-DV01 jumps near ex-cash cutoff, and curve-role mismatches.

A dangerous failure occurs when a generic risk engine bumps the discount curve and rebuilds the projection curve simultaneously. The combined DV01 may look plausible, but the trader cannot tell whether exposure comes from the cashflow amount or its discount factor.

## Requirement Discovery and Interview Questions

When a trader says a fully fixed coupon “should have no risk,” clarify:

- Do they mean projection risk or all present-value risk?
- Is the coupon receivable or payable, and what is the cash-sign convention?
- Which discount curve applies?
- Is parallel DV01 sufficient, or is bucketed discount risk required?
- What is the contractual ex-cash cutoff?
- Is the cashflow included in dirty PV until payment?
- Is settlement confirmed or merely expected?
- Should risk disappear at ex-cash time, actual settlement, or business-date close?

An interview-quality answer separates amount uncertainty from present-value sensitivity and connects both to the cashflow lifecycle.

For a quant developer, the important design principle is to expose these components rather than collapse them into one convenient number. Separate fields make sign conventions testable, curve ownership visible, and lifecycle transitions auditable. They also let traders distinguish a legitimate discount exposure from a stale fixing state or delayed settlement feed.

## Key Takeaways

- Fully fixed means the coupon amount no longer carries projection risk.
- An unpaid known cashflow can still carry discounting DV01.
- A future receivable normally has negative signed discount DV01.
- Discounting risk decays as payment approaches.
- Projection state, valuation state, and settlement state must remain distinct in APIs and controls.
