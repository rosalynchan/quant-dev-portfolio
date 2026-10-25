# Pricing a Forward Rate Agreement with Settlement in Advance

## Abstract

A Forward Rate Agreement locks a simple interest rate for a future accrual period, but its cash settlement often occurs at the beginning of that period. The familiar notional-times-accrual-times-rate-difference expression therefore describes a period-end interest difference, not necessarily the cash paid on the fixing date. This article derives the settlement-in-advance adjustment, works through a GBP 100 million example, and translates the product convention into a testable Python design with clear production controls.

## Desk Context

Consider a GBP 100 million 3x6 FRA with a contractual rate of 4.00%. The position receives floating and pays fixed. At the three-month fixing date, the official reference rate is 4.60%, and the underlying three-month accrual fraction is 0.25.

The trader observes a 60bp favourable difference and expects to receive GBP 150,000. The settlement instruction, however, is approximately GBP 148,295. The difference is not a fee or unexplained PnL. It arises because the FRA settles before the interest period ends.

## What a 3x6 FRA Represents

A 3x6 FRA references an accrual period beginning roughly three months after trade date and ending roughly six months after trade date. Exact dates depend on the spot convention, calendars, business-day adjustment, and contractual day count.

For a receive-floating, pay-fixed position, the interest difference measured at period end is:

$$
InterestDifference=N\alpha(L-K)
$$

where:

- $N$ is notional;
- $\alpha$ is the contractual accrual fraction;
- $L$ is the official fixing rate;
- $K$ is the FRA fixed rate.

When $L>K$, the receive-floating position receives cash. Reversing the direction reverses the sign.

Many standard FRAs settle at the start of the underlying period. The period-end interest difference must therefore be converted into an economically equivalent start-date amount:

$$
Settlement=
\frac{N\alpha(L-K)}{1+L\alpha}
$$

The denominator represents the growth of the start-date cash amount over the underlying money-market period. It is not an arbitrary valuation adjustment.

## Worked Numerical Example

The unadjusted interest difference is:

$$
\begin{aligned}
InterestDifference
&=100{,}000{,}000
\times0.25
\times(0.0460-0.0400)\\
&=GBP\ 150{,}000
\end{aligned}
$$

The settlement denominator is:

$$
1+L\alpha
=1+0.0460\times0.25
=1.0115
$$

The fixing-date cash receipt is therefore:

$$
Settlement
=\frac{150{,}000}{1.0115}
=GBP\ 148{,}294.61
$$

Paying GBP 150,000 immediately would overstate the economic value by:

$$
150{,}000-148{,}294.61
=GBP\ 1{,}705.39
$$

To see why, invest GBP 148,294.61 for the underlying period at the 4.60% fixing rate:

$$
148{,}294.61\times(1+0.0460\times0.25)
\approx GBP\ 150{,}000
$$

The start-date amount and period-end difference are economically equivalent under the contractual convention.

If the position is changed to pay floating and receive fixed, the denominator remains 1.0115, while both the interest difference and signed settlement become negative. That sign symmetry is a useful invariant test.

## Convention Is Part of the Product

The formula should not be selected merely because a trade is labelled `FRA`. A product definition should specify:

- exact start and end date generation;
- reference index and fixing source;
- fixing publication time and fallback policy;
- day-count basis;
- settlement at period start or period end;
- business-day adjustment and payment calendar;
- negative-rate and rounding treatment.

A period-end-settled contract generally pays the interest difference without the start-date denominator. Applying settlement-in-advance discounting to such a contract understates cash. Omitting it from a standard period-start FRA overstates cash.

The denominator also requires unit discipline. A fixing of 4.60% must enter the calculation as `0.0460`, not `4.60`. Because the incorrect rate appears in both numerator and denominator, the resulting error is not always a clean factor of 100 and can be harder to diagnose than a simple scale mistake.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FraSettlementInput:
    trade_id: str
    notional: Decimal
    fixed_rate: Decimal
    fixing_rate: Decimal
    accrual_fraction: Decimal
    receive_floating: bool
    settlement_timing: str
    fixing_status: str
    convention_version: str


def calculate_fra_settlement(
    x: FraSettlementInput,
) -> dict:
    if x.fixing_status != "OFFICIAL":
        raise ValueError("official fixing required")

    direction = (
        Decimal("1")
        if x.receive_floating
        else Decimal("-1")
    )
    period_end_amount = (
        direction
        * x.notional
        * x.accrual_fraction
        * (x.fixing_rate - x.fixed_rate)
    )

    if x.settlement_timing == "PERIOD_START":
        denominator = (
            Decimal("1")
            + x.fixing_rate * x.accrual_fraction
        )
        settlement = period_end_amount / denominator
    elif x.settlement_timing == "PERIOD_END":
        denominator = Decimal("1")
        settlement = period_end_amount
    else:
        raise ValueError("unsupported timing")

    return {
        "trade_id": x.trade_id,
        "period_end_interest_difference": (
            period_end_amount
        ),
        "discount_denominator": denominator,
        "signed_settlement": settlement,
        "convention_version": x.convention_version,
    }
```

The result exposes both the period-end amount and final cash. This is useful for desk support: a trader can see immediately whether a difference comes from the rate payoff or settlement timing.

## Data Quality and Production Controls

The most relevant controls are:

1. **Rate units:** require decimal rates and reject implausible values rather than guessing scale.
2. **Schedule lineage:** generate $\alpha$ from contractual dates, day count, calendars, and adjustment rules.
3. **Fixing status:** use an official fixing for final settlement; label any provisional or fallback value explicitly.
4. **Direction symmetry:** reversing receive/pay direction must reverse both signed outputs without changing the denominator.
5. **Independent reconciliation:** compare the final amount with an independent cashflow calculator within the contractual rounding tolerance.

A production dashboard should show fixed rate, fixing rate, accrual fraction, period-end difference, denominator, final settlement, fixing source, and convention version. Hiding the intermediate amount makes the most common timing error unnecessarily difficult to diagnose.

## Requirement Discovery and Interview Questions

When asked to “calculate the FRA payoff,” clarify:

- Is the position receive floating or pay floating?
- How are spot, start, and end dates generated?
- Which index and official fixing source apply?
- What day-count convention determines the accrual fraction?
- Does settlement occur at period start or period end?
- Does the contract use the fixing rate or another settlement rate in the denominator?
- How are negative rates and an invalid denominator handled?
- At which stage is rounding applied?

In an interview, the strongest explanation separates the period-end interest difference from the actual payment date. It derives the denominator by growing the start-date settlement at the fixing rate until period end, then connects the convention to explicit fields, validation, sign tests, and independent reconciliation.

## Key Takeaways

- A FRA locks a rate for a future accrual period; 3x6 identifies that period, not a six-month instrument maturity.
- $N\alpha(L-K)$ is the period-end interest difference.
- A standard period-start FRA discounts that amount by $1+L\alpha$.
- Receive/pay direction changes the sign, not the discount denominator.
- Dates, day count, fixing source, rate scale, timing, and rounding are contractual inputs.
- Exposing both the interest difference and final cash makes desk reconciliation substantially easier.
