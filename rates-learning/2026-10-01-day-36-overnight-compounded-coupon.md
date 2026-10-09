# Engineering an Overnight-Compounded RFR Coupon

## Abstract

An overnight-indexed swap coupon is not produced by taking a simple average of business-day fixings. Each rate applies to a contractual number of calendar days, and the resulting accrual factors are compounded. Weekend weights, holiday calendars, lookback rules, and observation shifts therefore belong to trade economics, not presentation logic. This article develops a worked SONIA-style example and an engineering design for reproducible observation schedules, validation, and reconciliation.

## Desk Context

Day 35 treated a floating coupon as if one fixing determined the whole accrual period. That simplification is useful for understanding fixing PnL, but a real RFR coupon usually uses many overnight observations.

Consider a simplified five-calendar-day accrual period on a GBP 100 million receive-floating swap. It contains three observation rows:

| Observation | Rate | Calendar-day weight |
|---|---:|---:|
| Monday | 4.00% | 1 |
| Tuesday | 4.10% | 1 |
| Wednesday | 4.20% | 3 |

The final observation covers three days before the next business day, representing weekend weighting. The contract uses ACT/365.

## The Compounding Rule

For observation $i$, let $r_i$ be the overnight rate, $d_i$ its calendar-day weight, and $B$ the day-count basis. The period compound factor is:

$$
CompoundFactor=
\prod_i\left(1+r_i\frac{d_i}{B}\right)-1
$$

The coupon amount is:

$$
Coupon=N\times CompoundFactor
$$

If a screen needs an annualised compounded rate, it can report:

$$
AnnualisedRate=
\frac{CompoundFactor}{\sum_i d_i/B}
$$

The order matters conceptually: compound the daily accrual factors first, then annualise for display. Averaging rates first is a different calculation.

## Worked Numerical Example

The correct factor is:

$$
\begin{aligned}
CompoundFactor
&=\left(1+0.0400\frac{1}{365}\right)
\left(1+0.0410\frac{1}{365}\right)\\
&\quad\times
\left(1+0.0420\frac{3}{365}\right)-1\\
&=0.000567212209
\end{aligned}
$$

The coupon is therefore:

$$
GBP\ 100{,}000{,}000\times0.000567212209
=GBP\ 56{,}721.22
$$

The total accrual fraction is $5/365$, producing an annualised compounded rate of approximately 4.14065%.

A weighted simple-interest approximation produces:

$$
SimpleFactor=
\frac{0.0400(1)+0.0410(1)+0.0420(3)}{365}
=0.000567123288
$$

That gives GBP 56,712.33, which is GBP 8.89 below the correctly compounded amount. The difference is small over five days, but it grows with notional, rate level, and accrual length. More importantly, it is a deterministic implementation error, not harmless residual noise.

## Lookback Is Not Observation Shift

RFR products often move observation dates earlier so that the coupon can be known before payment. The precise convention determines which rates and day weights enter the calculation.

With lookback without observation shift, rate observation dates move backwards, while day weights normally remain those of the original accrual period. With observation shift, both the rate dates and the weighting period move. The same set of rates can therefore produce different coupons when weekends or holidays fall differently in the shifted period.

An API field such as `lookback_days=5` is insufficient. The contract needs an explicit convention type, accrual and observation calendars, business-day adjustments, labelled mapping between observation and accrual dates, and any lockout or cutoff rule.

This is why schedule generation should be a first-class, versioned component. The coupon engine should consume a resolved schedule rather than independently reconstructing contractual dates from a few scalar flags.

## Engineering Design

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import prod


@dataclass(frozen=True)
class OvernightObservation:
    observation_date: date
    accrual_start: date
    accrual_end: date
    rate: Decimal
    calendar_days: int
    fixing_status: str


def compounded_coupon(
    notional: Decimal,
    observations: list[OvernightObservation],
    basis: Decimal = Decimal("365"),
) -> dict:
    if not observations:
        raise ValueError("empty observation schedule")

    if any(x.fixing_status != "OFFICIAL" for x in observations):
        raise ValueError("non-official fixing in realised coupon")

    total_days = sum(x.calendar_days for x in observations)
    factors = [
        Decimal("1")
        + x.rate * Decimal(x.calendar_days) / basis
        for x in observations
    ]
    compound_factor = prod(factors) - Decimal("1")
    accrual_fraction = Decimal(total_days) / basis

    return {
        "compound_factor": compound_factor,
        "coupon_amount": notional * compound_factor,
        "annualised_rate": compound_factor / accrual_fraction,
        "total_calendar_days": total_days,
        "observation_count": len(observations),
    }
```

In production, the schedule rows should also carry index and calendar versions, fixing source lineage, rate status, and a stable cashflow ID. Projected and official observations may coexist before the period is fully fixed, but a realised-coupon calculation should not silently treat projected values as official.

## Data Quality and Production Controls

Five controls catch most high-impact failures.

First, observation rows must be uniquely labelled and ordered, with no gaps or overlaps in accrual coverage. Second, the sum of calendar-day weights must equal the contractual accrual period. Third, rates must use decimal units and retain official, projected, or corrected status. Fourth, calendar and schedule-generation versions must be stored. Fifth, the coupon should reconcile by cashflow ID against an independent cashflow or settlement calculation.

A classic failure sets every business-day observation weight to one. The rates look complete, but the Friday or pre-holiday fixing does not accrue across non-business days. The coupon is systematically understated without any missing-data alert.

Rounding is another source of avoidable breaks. Intermediate factors should retain high precision, with rounding applied only at the final stage required by the contract or settlement convention.

## Requirement Discovery and Interview Questions

When a trader says the compounded coupon is wrong, ask:

- Which RFR index and day-count basis apply?
- Is the convention lookback with or without observation shift?
- Which accrual and observation calendars are used?
- How many calendar days should each pre-weekend or pre-holiday rate cover?
- Is there a lockout, rate cutoff, or payment delay?
- Is the current period fully fixed or partly projected?
- Is the comparison about coupon amount, compound factor, or annualised rate?
- At which step does the confirmation round?

An interview-quality answer should begin with the labelled observation schedule. If the dates and weights are wrong, a mathematically correct compounding loop still produces the wrong coupon.

For testing, include ordinary weekdays, weekends, consecutive holidays, month-end boundaries, leap years, and corrected fixings. Golden cases should verify both the resolved schedule and the final cash amount, so a calendar regression cannot hide behind an unchanged calculation formula.

## Trader–Developer Translation

**Trader:** "Your SONIA coupon is slightly below the confirmation."

**Developer:** "Are we applying the Wednesday fixing to all three calendar days before the next business day?"

**Trader:** "Yes, and this trade uses lookback with observation shift."

**Developer:** "I will regenerate the labelled observation schedule under that convention, verify that the weights sum to five days, and compare the compound factor and coupon rather than only the displayed annualised rate."

## Key Takeaways

- RFR coupons compound daily accrual factors; they do not simply average fixings.
- Weekend and holiday weights are contractual economic inputs.
- Lookback and observation shift can use different day weights.
- Schedule generation should be explicit, labelled, and versioned.
- Complete date coverage matters before the compounding arithmetic begins.
- High precision with final-stage rounding improves reproducibility and reconciliation.
