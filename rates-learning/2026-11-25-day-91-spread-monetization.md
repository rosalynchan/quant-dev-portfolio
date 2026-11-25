# From a Swap Rate Spread to a Monetary Execution Cost

## Abstract

A bid/ask width quoted in rate basis points cannot be inserted directly into a monetary hedge-ranking score. It must first be interpreted relative to a benchmark and converted using the appropriate sensitivity. For a vanilla fixed-for-floating swap with fixed valuation curves, changing the contractual fixed coupon changes PV through the fixed-leg annuity. This article uses that relationship to estimate one-way cost from mid, distinguishes it from market-curve DV01, and identifies the common factor-of-two error.

## Desk context

Yesterday's hedge-ranking exercise assumed that each instrument already had a monetary one-way cost per quantity unit. Today the input feed instead provides a swap-rate quote: bid 3.998%, ask 4.002%. A developer multiplies the width by a risk number, but two dashboards disagree by exactly a factor of two.

Before blaming rounding, inspect the benchmark. Crossing from mid to one side costs half the full spread in a symmetric quote. Charging the full width for one mid-to-side trade counts both sides.

This lesson is deliberately about a synthetic vanilla swap quotation and coupon economics at frozen curves. It does not prescribe universal dealer quote-side naming. A production adapter must map the executable side to the requested pay/receive direction explicitly.

## Define the valuation sensitivity that belongs here

For a receive-fixed swap, holding valuation curves and schedules fixed, let $N$ be positive notional, $K$ the contractual fixed coupon, and $A$ the discounted fixed-leg annuity. The annuity is the sum of accrual fractions multiplied by discount factors.

A change in fixed coupon produces:

$$
\Delta V=N A\Delta K
$$

For pay-fixed the sign reverses. The positive monetary magnitude for a one-basis-point coupon change is:

$$
PV01_{coupon}=NA\times10^{-4}
$$

This is a coupon sensitivity, not automatically the same as the desk's signed market-quote DV01. Bumping market quotes and rebuilding curves can affect discounting, projected floating cashflows, and the annuity itself. Here the curves are fixed and the contractual coupon changes.

The distinction matters even when two numbers happen to be similar. A convenient field named DV01 is not sufficient evidence that it is the correct conversion coefficient.

## Establish the mid-to-side distance

For our illustrative rate quote, the full width is 0.004 percentage points, or 0.4 basis points. Mid is 4.000%, and each side is 0.2 basis points away.

Assume the directional quote adapter confirms that the requested position executes at the unfavorable side relative to this mid benchmark. The positive one-way estimated cost is:

$$
C_{oneway}=PV01_{coupon}\times h_{bp}
$$

Here $h_{bp}$ is the unfavorable coupon distance from mid, expressed numerically in basis points. In a symmetric quote it is half the full width. For an asymmetric benchmark or side-specific quote, calculate the actual distance rather than dividing blindly by two.

For a receiver, accepting a lower fixed coupon than mid reduces value. For a payer, accepting a higher fixed coupon than mid reduces value. This economic check is safer than inferring direction from an undocumented bid or ask label.

## Worked numerical example

Take notional EUR 10 million and a fixed-leg annuity of 4.5 years under the frozen valuation setup. Coupon PV01 is EUR 4,500 per basis point.

With a 0.2-basis-point unfavorable distance from mid, estimated one-way spread cost is EUR 900. If costs are reported in GBP and the frozen translation rate is 0.85 GBP per EUR, the amount is GBP 765.

| Step | Calculation | Result |
| --- | --- | ---: |
| Coupon PV01 | 10,000,000 × 4.5 × 0.0001 | EUR 4,500/bp |
| Full quote width | 4.002% minus 3.998% | 0.4 bp |
| One-way distance | 0.4 divided by 2 | 0.2 bp |
| One-way cost | 4,500 × 0.2 | EUR 900 |
| Reporting amount | 900 × 0.85 | GBP 765 |

Using the full 0.4 basis points for a single mid-to-side trade gives EUR 1,800, twice the intended estimate. Under unchanged quotes and the same annuity, that full-width amount corresponds to an idealized entry-and-immediate-offset spread cost, not one-way cost.

That round-trip comparison excludes fees, market moves, and changes in trade terms. It is a unit and benchmark check, not a guarantee about realized execution.

## Engineering the conversion boundary

Normalize rate quotes to decimal rates before calculation. For example, 3.998% is 0.03998, not 3.998. One rate basis point is 0.0001 in decimal units.

```python
from decimal import Decimal

def symmetric_mid_cost(notional, annuity, bid_rate, ask_rate, fx):
    if notional <= 0 or annuity <= 0 or fx <= 0:
        raise ValueError("Positive magnitudes required")
    if ask_rate < bid_rate:
        raise ValueError("Crossed quote")
    bp = Decimal("0.0001")
    coupon_pv01 = notional * annuity * bp
    half_width_bp = (ask_rate - bid_rate) / (2 * bp)
    local_cost = coupon_pv01 * half_width_bp
    return {
        "coupon_pv01": coupon_pv01,
        "one_way_distance_bp": half_width_bp,
        "local_cost": local_cost,
        "reporting_cost": local_cost * fx,
    }

result = symmetric_mid_cost(*map(Decimal, [
    "10000000", "4.5", "0.03998", "0.04002", "0.85"
]))
```

This function computes the symmetric magnitude after directional interpretation has been established upstream. It does not select the execution side. Production validation should reject non-finite inputs, verify currencies and schedules, and retain quote and curve provenance.

A useful independent check is to value the same directional trade at the benchmark coupon and executable coupon using frozen curves. The PV deterioration should equal the calculated local cost for this vanilla coupon-only change.

## Four selective production checks

1. Label width semantics explicitly: full bid/ask, half-spread, or already-monetized one-way cost. Never halve an input that is already a half-spread.
2. Use coupon PV01 from matching notional, schedule, and frozen curves; do not substitute a generic market-risk DV01.
3. Verify directional economics and quote units before converting. A plausible positive result can still represent the wrong side.
4. Keep benchmark cost separate from execution-based valuation. Do not subtract the same spread effect twice in a PnL report.

The annuity scales with the trade schedule; notional scales the amount. A cost for EUR 10 million cannot be attached unchanged to one unit defined as EUR 1 million.

## Requirements and key takeaways

Ask whether the request is one-way or round-trip, which benchmark applies, whether fees are included, how quote sides map to pay/receive direction, and whether the quote covers the proposed size.

The desk-ready explanation is: “The feed width is 0.4 basis points, but the one-way distance from symmetric mid is 0.2. We monetize it with coupon PV01 at frozen curves, then translate the amount once.”

All figures are synthetic educational examples. No confidential employer data, client information, proprietary architecture, or investment advice is included.
