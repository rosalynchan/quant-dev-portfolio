# Explaining Floating-Rate Fixing PnL on an Interest Rate Swap

## Abstract

Before a floating coupon fixes, its value is based on a projected forward rate. Once the official fixing is published, that forecast is replaced by a known coupon amount. The difference between the actual fixing and the forward embedded in the prior valuation creates a distinct PnL component. This article develops the fixing-surprise calculation, separates it from ordinary curve PnL, and outlines a production design with explicit fixing states, source lineage, and correction handling.

## Desk Context

Consider a GBP receive-fixed, pay-floating swap with a GBP 50 million notional. The next floating coupon has a 0.25 accrual factor. Yesterday's official-close valuation projected the relevant rate at 4.10%. Today's official fixing is 4.16%, and the discount factor to the payment date is 0.995.

Because the desk pays floating, a higher-than-expected fixing increases the future payment and reduces the swap's PV. The important comparison is not the fixing against zero, nor against a newly rebuilt close curve. It is the fixing against the projected rate already embedded in the prior valuation.

## From Forecast Cashflow to Known Cashflow

Before fixing, the simplified projected coupon is:

$$
ProjectedCoupon=N\times\alpha\times F_{prior}
$$

After publication, the coupon becomes:

$$
FixedCoupon=N\times\alpha\times L_{actual}
$$

For a receive-floating position, the approximate fixing-surprise PV is:

$$
FixingPnL=N\times\alpha\times(L_{actual}-F_{prior})\times DF
$$

For pay-floating, the sign is reversed. The calculation identifies the value of new fixing information while holding other valuation inputs conceptually separate.

This component is not the entire daily PnL. Other projected coupons can still respond to curve movement, discount factors can change, and the trade continues to accrue carry.

## Worked Numerical Example

Yesterday's projected coupon is:

$$
50{,}000{,}000\times0.25\times4.10\%=GBP\ 512{,}500
$$

The coupon implied by the official fixing is:

$$
50{,}000{,}000\times0.25\times4.16\%=GBP\ 520{,}000
$$

The desk must therefore pay GBP 7,500 more than yesterday's valuation expected. Discounting that difference gives:

$$
FixingPnL_{pay}=-7{,}500\times0.995=-GBP\ 7{,}462.50
$$

Suppose actual full-revaluation PnL is -GBP 9,000. A separate curve component explains -GBP 1,300 and carry explains -GBP 200. Total explained PnL is:

$$
-7{,}462.50-1{,}300-200=-GBP\ 8{,}962.50
$$

The residual is only -GBP 37.50. This bridge is meaningful because the fixing and curve components answer different questions. The fixing component measures forecast-to-realised information for one coupon; the curve component revalues exposures that remain market-sensitive.

## Choosing the Correct Forward Baseline

The phrase "actual minus forward" is incomplete unless the forward snapshot is specified. A daily PnL explain will normally use the projected rate stored in the prior official-close valuation.

Using the live forward immediately before publication may produce a smaller surprise, but it reallocates overnight market movement into another component. Rebuilding a historical-looking forward after the fixing is known is worse: it introduces hindsight and can manufacture a near-zero surprise. Using a different projection curve makes the component incomparable to the prior PV.

The output should therefore retain the prior valuation snapshot, projected rate, projection curve ID, official fixing value and source, publication timestamp, observation date, index definition, accrual factor, and discounting basis.

For overnight-index coupons, the simplified single-rate example must not be copied literally into production. A compounded coupon may depend on a schedule of daily observations, lookback or lag rules, observation shift, lockout, non-business-day treatment, and a mixture of known and still-projected fixings. The same principle applies, but the engine must compare full projected and realised coupon amounts under the contract's exact convention.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class FixingStatus(Enum):
    PROJECTED = "PROJECTED"
    OFFICIAL = "OFFICIAL"
    CORRECTED = "CORRECTED"
    MISSING = "MISSING"


@dataclass(frozen=True)
class FixingExplainInput:
    notional: Decimal
    accrual_factor: Decimal
    prior_forward: Decimal
    actual_fixing: Decimal
    discount_factor: Decimal
    receive_float: bool
    status: FixingStatus
    index_id: str
    observation_date: str
    prior_snapshot_id: str
    fixing_source_id: str


def explain_fixing_pnl(x: FixingExplainInput) -> dict:
    if x.status not in {
        FixingStatus.OFFICIAL,
        FixingStatus.CORRECTED,
    }:
        raise ValueError("official fixing required")

    coupon_surprise = (
        x.notional
        * x.accrual_factor
        * (x.actual_fixing - x.prior_forward)
    )
    direction = Decimal("1") if x.receive_float else Decimal("-1")
    fixing_pnl = (
        direction * coupon_surprise * x.discount_factor
    )

    return {
        "prior_forward": x.prior_forward,
        "actual_fixing": x.actual_fixing,
        "coupon_surprise": coupon_surprise,
        "fixing_pnl": fixing_pnl,
        "status": x.status.value,
        "index_id": x.index_id,
        "observation_date": x.observation_date,
        "prior_snapshot_id": x.prior_snapshot_id,
        "fixing_source_id": x.fixing_source_id,
    }
```

## Data Quality and Production Controls

First, index, observation date, publication calendar, and timezone must agree. Second, the prior forward must come from the frozen prior valuation snapshot. Third, rate units must be explicit: 4.16% is `0.0416`, not `4.16`. Fourth, a missing fixing must not silently become zero or today's curve value. Fifth, a corrected official fixing must create a new version and replay affected valuations without destroying the previous lineage.

A dangerous failure occurs when a vendor returns null before publication and a numeric pipeline converts it to zero. On a large notional, the resulting false fixing surprise can overwhelm the real daily PnL while still passing basic type and range checks unless the status is validated.

Useful observability includes missing official fixings after expected publication time, fallback usage, vendor disagreements, corrected fixings, PnL materiality by index, and replay completion after corrections.

## Requirement Discovery and Interview Questions

When a trader asks for fixing PnL, clarify:

- Is the baseline yesterday's close forward, today's pre-fixing forward, or trade inception?
- Which index, observation date, and publication source apply?
- Is the coupon simple, term-based, or compounded overnight?
- Do lookback, lag, observation shift, or lockout rules apply?
- What fallback is permitted before an official value is available?
- Does a vendor correction reopen prior PnL?
- Which snapshot supplies discounting?
- Should results aggregate by coupon, trade, index, or book?

An interview-quality answer should connect the component to the prior PV: the projected coupon was already priced yesterday, so today's new information is only the realised-versus-projected difference.

## Trader–Developer Translation

**Trader:** "We lost about 7.5k on the fixing. Show me why."

**Developer:** "Should the surprise be measured against yesterday's official-close projected coupon?"

**Trader:** "Yes. Keep today's curve movement separate."

**Developer:** "The fixing was 4.16% versus a 4.10% prior forward. On GBP 50 million for a 0.25 accrual period, the pay-floating coupon increased by GBP 7,500; discounted fixing PnL is -GBP 7,462.50."

## Key Takeaways

- Fixing PnL measures actual fixing versus the projection embedded in prior PV.
- Pay/receive direction and payment-date discounting determine the signed result.
- Fixing surprise and curve PnL describe different economic drivers.
- The forward baseline must be frozen, named, and reproducible.
- Overnight coupons require their full contractual observation convention.
- Missing, provisional, and corrected fixings require explicit states and lineage.
