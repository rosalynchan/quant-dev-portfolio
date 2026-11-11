# Fixing PnL: Isolating the Transition from Forecast Rate to Known Coupon

## Abstract

A floating coupon changes state when its reference rate becomes known. Replacing a projected rate with an official fixing can change present value even when the discount curve and every other trade input remain frozen. That transition deserves an explicit PnL component rather than an unexplained market residual. This article develops a controlled fixing bridge for a simple term-rate coupon, gives a numerical example, and distinguishes missing observations from valid forecasts. It also explains why a fixed coupon loses its own projection-rate exposure but can retain discounting risk.

## The Desk Scenario

A developer investigates an intraday PV jump on a receive-floating swap. The coupon was projected at 4.20%; the official fixing is 4.24%. No payment occurs today, and the discount curve has barely moved.

Calling the entire jump “curve PnL” misses an important state transition. The cashflow amount was uncertain in the pricing representation and is now known. A reproducible explain should isolate the replacement of the stored forecast by the published observation at a common valuation timestamp.

This complements payment-day reconciliation. Fixing determines an amount; payment transfers value into cash or a settlement asset. They are different events and should not share one generic lifecycle label.

## Define a Narrow Product Boundary

Consider a plain term-rate coupon with no cap, floor, compounding, optionality, or settlement-in-advance adjustment. Its cashflow is notional times accrual fraction times reference rate, with any unchanged spread cancelling in the comparison.

Let N be notional, a the accrual fraction, F the stored forecast, L the official fixing, D the discount factor to the payment date, and s the direction: positive for receipt and negative for payment.

At a common valuation time and frozen discount state, the fixing-only PV change is

$$
P_{fix}=sNaD(L-F)
$$

This is exact for the stipulated linear coupon, not a universal formula for all floating-rate instruments. FRA settlement-in-advance introduces a denominator; compounded overnight coupons require replacement inside the compounding product. Neither should be approximated silently by the term-coupon shortcut.

The reference forecast must be defined. A forecast stored immediately before publication isolates a local fixing surprise. Yesterday’s closing forecast produces a broader opening-to-fixing comparison. Those are different report conventions, even when both reconcile.

## Worked Numerical Example

Assume the portfolio receives the floating coupon:

| Input | Value |
|---|---:|
| Notional | GBP 100,000,000 |
| Accrual fraction | 0.25 |
| Stored forecast | 4.20% |
| Official fixing | 4.24% |
| Frozen discount factor | 0.99 |

The fixing exceeds forecast by 4 basis points, or 0.0004 in decimal-rate units. The contractual cashflow increase is

$$
100{,}000{,}000 \times 0.25 \times 0.0004=10{,}000
$$

Discounting gives GBP 9,900 of fixing-only PV gain. A pay-floating position would have GBP -9,900 under the same sign convention.

Before fixing, this coupon’s PV is GBP 1,039,500. After replacement by the official observation, it becomes GBP 1,049,400 at the frozen discount factor. If a subsequent discount-market update makes actual closing PV GBP 1,048,900, the remaining selected effect is GBP -500.

| Explain component | GBP |
|---|---:|
| Fixing replacement, frozen discount state | +9,900 |
| Subsequent discount-market update | -500 |
| Total selected PV change | +9,400 |

The ordering is explicit. Fixing is applied first and the discount update second. As with any nonlinear attribution ladder, reversing input changes can redistribute interaction. The report should preserve the approved sequence rather than pretend the components are uniquely determined.

## Risk Changes After Fixing

Before publication, the coupon amount depends on a forward rate. After fixing, that specific amount no longer responds to projection-curve bumps. Its own projection-rate sensitivity should disappear.

However, the payment is still in the future. Its PV can continue to respond to discount-curve movements. “The coupon is fixed” therefore does not mean “the coupon has zero DV01,” and it certainly does not imply that every future coupon on the swap has lost projection risk.

A useful regression checks the targeted coupon’s projected-rate sensitivity before and after the transition, while separately validating its remaining discounting sensitivity.

## Engineering Connection

The calculation should operate only after the fixing identity and publication state have been validated:

```python
def fixing_pnl(
    notional,
    accrual_fraction,
    forecast_rate,
    fixing_rate,
    discount_factor,
    receive=True,
):
    if fixing_rate is None:
        return {"status": "MISSING_FIXING"}

    sign = 1 if receive else -1
    cashflow_delta = (
        sign * notional * accrual_fraction
        * (fixing_rate - forecast_rate)
    )

    return {
        "status": "COMPLETE",
        "cashflow_delta": cashflow_delta,
        "fixing_pnl": cashflow_delta * discount_factor,
    }
```

Rates are decimal values in this interface. A legitimate zero or negative fixing must not be rejected by a truthiness check. The production wrapper also supplies stable identities and lineage rather than allowing an unlabelled rate value to select a coupon implicitly.

## Selective Production Controls

Four controls matter especially:

1. Match the observation correctly. Index, tenor, fixing date, calendar conventions, and coupon identity must align; payment date is not the fixing lookup key.
2. Preserve the reference forecast. Store its timestamp and market snapshot so a rerun cannot replace it with today’s latest forward and erase the original explain.
3. Enforce publication-state semantics. Before scheduled availability, projection can be normal. After the required cutoff, an absent official observation is a missing-fixing exception, not a silent forecast fallback.
4. Version observations. Preserve publication time, ingestion time, source, and revisions. A correction changes the existing observation lineage rather than generating a duplicate economic fixing event.

Tests should include receive and pay direction, positive and negative surprises, a valid zero fixing, missing data after cutoff, and a revised observation. Monitor missing-fixing exposure and top fixing PnL alongside the forecast-to-actual rate difference.

## Requirement Discovery

Ask the trader or quant which forecast anchors the comparison, when an observation is considered available, and what happens if the vendor arrives late. Confirm whether revisions restate the original fixing component or appear as a separately labelled correction delta.

Also establish the product scope. A simple term-rate coupon, a settlement-in-advance FRA, and an overnight-compounded coupon do not share the same cashflow transformation.

A concise interview answer is: “I isolate fixing PnL by replacing a versioned forecast with the official observation at a common valuation time and frozen discount state. I preserve missing-data exceptions and verify that the fixed coupon loses projection risk but retains discounting risk.”

## Key Takeaways

- Fixing determines a rate; payment settles value. They are different lifecycle events.
- A fixing bridge requires a stored forecast and a versioned official observation.
- Missing after cutoff is not equivalent to a valid projected rate.
- The simple formula applies only to the stated linear term coupon.
- Fixing removes that coupon’s projection exposure, not necessarily all interest-rate risk.

All numbers are generic educational examples, with no confidential employer or client information and no investment advice.
