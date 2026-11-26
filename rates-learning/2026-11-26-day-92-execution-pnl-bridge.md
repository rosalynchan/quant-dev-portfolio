# Execution PnL and Market PnL: Do Not Deduct the Spread Twice

## Abstract

An executed swap can begin with negative value when marked against contemporaneous mid curves. That inception value already captures the coupon disadvantage relative to the benchmark. Subtracting an estimated spread cost again from the same marked result double counts the effect. This article builds an exact valuation bridge between inception and a later snapshot, distinguishes execution attribution from subsequent valuation change, and turns the distinction into a small reconciliation contract.

## The desk question

A receive-fixed swap is executed below the contemporaneous mid par rate. At inception, the mid-based pricer reports negative EUR 900. Later, the same executed trade is worth positive EUR 1,100. A dashboard adds “execution cost minus EUR 900” beneath the closing mark and reports only EUR 200.

The arithmetic is easy; the economic boundary is wrong. If the closing value is already for the actual executed coupon, the original coupon disadvantage is embedded in it. The spread estimate is an explanation of part of the result, not an additional deduction.

Yesterday's lesson monetized a mid-to-side coupon difference using coupon PV01. Today we connect that estimate to an executed trade's valuation history.

## Fix the scope first

Let $T$ denote the actual executed trade, including its fixed coupon, direction, notional, and schedule. Let $M_0$ be the contemporaneous inception valuation snapshot and $M_1$ a later snapshot.

Assume zero upfront payment, no fees, no intervening cashflows, no amendments, and one local valuation currency. This is a desk valuation illustration, not a statement about formal accounting recognition rules.

The trade did not exist in the opening portfolio. Under these assumptions, its contribution since inception is its closing value:

$$
P_{total}=V(T,M_1)
$$

A useful bridge inserts its inception mark:

$$
P_{total}=V(T,M_0)+[V(T,M_1)-V(T,M_0)]
$$

The first term is the inception mid mark. The bracketed term is the subsequent valuation change of the same executed trade. The identity is exact because an identical intermediate value is added and subtracted.

Calling the second term pure “market PnL” requires additional discipline. If time, fixings, or model methodology also changed between snapshots, they are included in that valuation change. Today the name market contribution refers to a controlled example with those other drivers held fixed.

## Link inception value to the coupon benchmark

At inception, construct a benchmark swap with the same direction, notional, schedule, and conventions, but with its coupon equal to the mid par rate under $M_0$. Its model PV is zero by construction.

For a receiver, the actual coupon is lower by 0.2 basis points. With notional EUR 10 million and fixed-leg annuity 4.5, coupon PV01 is EUR 4,500 per basis point. Therefore the actual trade's inception mark is negative EUR 900.

The positive cost magnitude is EUR 900; the signed execution contribution is negative EUR 900. Keep the sign convention explicit. A field named cost should not ambiguously switch between positive expense magnitude and signed PnL.

If the supposedly par benchmark is not zero, investigate its construction or show the nonzero benchmark separately. Do not force the inception mark to equal a spread estimate through a balancing adjustment.

## Worked example

Use the following synthetic valuations:

| Item | Value, EUR |
| --- | ---: |
| Benchmark par trade at inception | 0 |
| Actual executed trade at inception | -900 |
| Actual executed trade at later snapshot | +1,100 |

The subsequent valuation contribution is EUR 2,000: closing value EUR 1,100 minus inception value minus EUR 900.

The bridge is negative EUR 900 of inception execution contribution plus positive EUR 2,000 of subsequent valuation contribution, giving total positive EUR 1,100.

Subtracting EUR 900 again from the closing EUR 1,100 produces EUR 200 and is wrong under the stated scope. It treats the same coupon disadvantage once inside the valuation and once as an external expense.

Do not confuse this with a genuinely separate fee. A distinct paid fee, not included in the valuation, would require an additional cash term. Nor does a nonzero upfront payment disappear: it changes the since-inception PnL boundary. Those cases are outside today's zero-cash example and should trigger a different calculation path.

## Why a closing benchmark comparison is different

A developer might instead compare the actual closing trade with a hypothetical trade carrying the original mid coupon. That is a counterfactual comparison at the closing snapshot, not necessarily the inception execution contribution.

Its coupon-value gap uses the closing annuity, which may differ from the inception annuity. It must not silently replace the frozen inception mark in the bridge. Attribution depends on the stated intermediate state, even when the endpoint total remains unchanged.

This is a practical reason to retain inception benchmark provenance rather than recompute “execution PnL” from whatever current curve is available.

## Compact engineering connection

Store the actual trade version and both valuation identifiers. Keep standalone cost analytics marked as informational when the same spread effect is already embedded in PV.

```python
from decimal import Decimal

def new_trade_bridge(inception_pv, closing_pv, *, zero_cash_scope):
    if not zero_cash_scope:
        raise ValueError("Use a cash-inclusive bridge")
    subsequent = closing_pv - inception_pv
    total = inception_pv + subsequent
    assert total == closing_pv
    return {
        "inception_mid_mark": inception_pv,
        "subsequent_valuation_pnl": subsequent,
        "total_since_inception": total,
        "spread_cost_extra_deduction": False,
    }

result = new_trade_bridge(
    Decimal("-900"), Decimal("1100"), zero_cash_scope=True
)
```

The scope flag represents upstream validation, not a substitute for checking actual cash records. Production code also needs finite-value checks and explicit currency and trade-version matching. The function does not calculate the valuation snapshots; it reconciles supplied values.

## Four selective production controls

1. Use the same actual executed trade version in both marks. Replacing the coupon with a benchmark changes the experiment.
2. Freeze the inception mark and its benchmark snapshot; do not update it from current curves without an explicit restatement policy.
3. Classify a spread estimate as embedded attribution or a separate cash expense. Never deduct the same effect in both categories.
4. Reject the simplified bridge when upfront payments, fees, or intervening cashflows are present.

Tests should include unchanged snapshots, where subsequent PnL is zero and total remains minus EUR 900; the positive EUR 1,100 example; and a nonzero-cash case routed away from this function.

## Requirement dialogue and takeaways

When a trader asks for “PnL net of execution cost,” ask whether the displayed PnL already marks the actual executed trade, which benchmark applies, and whether separate fees are included.

A clear response is: “The closing mark already contains the executed coupon. We can show minus EUR 900 as inception attribution, but we must not subtract it again.”

Execution attribution explains the total; it is not automatically another charge. All figures and workflows here are synthetic educational examples, with no confidential information, proprietary architecture, or investment advice.
