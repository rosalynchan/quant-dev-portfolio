# Forecasting a Partially Fixed RFR Coupon

## Abstract

An overnight-compounded RFR coupon is often valued before its observation period has finished. Some daily rates are then official fixings, while the remaining days depend on a projection curve. This article shows how to combine both states in one compound chain, measure fixing coverage without confusing it with risk reduction, and separate a new fixing surprise from the same day’s curve movement. It also translates the economics into a compact Python design with explicit lineage and production controls.

## Desk Context

Suppose a GBP 100 million receive-floating SONIA swap has a simplified five-calendar-day coupon period. At the valuation cut, three days are fixed and two remain projected:

| Segment | Rate | Calendar days | Status |
|---|---:|---:|---|
| Official fixing | 4.00% | 1 | `OFFICIAL` |
| Official fixing | 4.10% | 2 | `OFFICIAL` |
| Forward projection | 4.20% | 2 | `PROJECTED` |

The day-count basis is ACT/365. A trader asks two apparently simple questions: “What is the coupon forecast?” and “How much is already fixed?”

The first is a valuation question. The second is a data-state question. Treating them as the same thing is a common source of misleading dashboards.

## One Coupon, Two Information States

The coupon still has one compound factor. Official observations and projected observations occupy different rows of the same contractual schedule:

$$
\text{ForecastFactor}
=
\prod_{i\in fixed}
\left(1+r_i^{actual}\frac{d_i}{B}\right)
\prod_{j\in future}
\left(1+f_j^{projected}\frac{d_j}{B}\right)-1.
$$

The forecast coupon is the notional multiplied by this factor. The two segments should not be calculated as independent coupon amounts and then added. Their growth factors multiply, so there is a small cross-product between the realised and projected portions.

A useful operational metric is calendar-day coverage:

$$
\text{CalendarCoverage}
=
\frac{\sum_{i\in fixed}d_i}{\sum_{all}d_i}.
$$

This tells the desk how much of the accrual schedule is supported by official observations. It does not say that the same percentage of market risk has disappeared. Residual risk depends on the remaining day weights, forward-rate sensitivity, discounting, notional, and compounding interaction.

## Worked Numerical Example

The realised growth factor is:

$$
\left(1+0.0400\frac{1}{365}\right)
\left(1+0.0410\frac{2}{365}\right)-1
=0.000334271195.
$$

The projected growth factor is:

$$
\left(1+0.0420\frac{2}{365}\right)-1
=0.000230136986.
$$

Combining them gives:

$$
\begin{aligned}
\text{ForecastFactor}
&=(1+0.000334271195)(1+0.000230136986)-1\\
&=0.000564485110.
\end{aligned}
$$

Therefore:

$$
\text{ForecastCoupon}
=100{,}000{,}000\times0.000564485110
=GBP\ 56{,}448.51.
$$

Three of five calendar days are official, so coverage is 60%.

Now assume the next one-day observation fixes at 4.30%, while the prior valuation projected 4.20%. A first-order receive-floating fixing surprise is:

$$
100{,}000{,}000\times\frac{1}{365}
\times(4.30\%-4.20\%)
\approx GBP\ 273.97.
$$

For a production explain, the more robust method is a controlled revaluation: replace only the newly published observation, freeze the prior valuation’s remaining forwards and discount factors, and calculate the PV difference. A separate revaluation then moves the surviving projections and discount curve to the current snapshot.

## The State Transition Matters

When a fixing arrives, one schedule row transitions from `PROJECTED` to `OFFICIAL`. Previously official observations must not be rebuilt from the current curve.

A clean daily explain therefore has two stages:

1. **Fixing roll:** substitute the new actual fixing into the prior snapshot while freezing all other projected rates.
2. **Curve revaluation:** keep the updated fixing set constant and move the remaining projections and discount factors to the current snapshot.

Subtracting today’s complete coupon forecast from yesterday’s complete forecast mixes fixing surprise, forward-curve movement, discounting movement, and possibly schedule changes. The number may reconcile, but it does not answer the trader’s driver question.

Status also needs more precision than fixed versus unfixed. Useful states include `OFFICIAL`, `PROJECTED`, `PROVISIONAL`, and `CORRECTED`. A missing official fixing may be replaced by an approved projection fallback, but that choice must reduce reported official coverage and carry a reason. A corrected fixing should create a new version and trigger a controlled replay rather than overwrite history.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CouponObservation:
    observation_id: str
    rate: Decimal
    calendar_days: int
    status: str
    source_id: str


def forecast_partial_coupon(
    notional: Decimal,
    rows: list[CouponObservation],
    expected_total_days: int,
    basis: Decimal = Decimal("365"),
) -> dict:
    allowed = {"OFFICIAL", "PROJECTED"}
    if any(row.status not in allowed for row in rows):
        raise ValueError("unsupported observation status")

    total_days = sum(row.calendar_days for row in rows)
    if total_days != expected_total_days:
        raise ValueError("incomplete accrual-day coverage")

    factor = Decimal("1")
    fixed_days = 0
    for row in rows:
        factor *= Decimal("1") + row.rate * row.calendar_days / basis
        if row.status == "OFFICIAL":
            fixed_days += row.calendar_days

    compound_factor = factor - Decimal("1")
    return {
        "forecast_coupon": notional * compound_factor,
        "compound_factor": compound_factor,
        "calendar_coverage": Decimal(fixed_days) / Decimal(total_days),
        "fixed_days": fixed_days,
        "projected_days": total_days - fixed_days,
    }
```

The API should carry labelled observation IDs rather than anonymous arrays. Every accrual day must map to exactly one observation, with no gap or overlap. Official rows need fixing-source and version lineage; projected rows need the projection-curve snapshot. The output should retain the schedule-generation version and fixing-set version.

One subtle production failure is stale caching. If a valuation cache key contains only trade ID and valuation date, the arrival of a new official fixing may not invalidate the cached coupon. The desk continues to see the old projection until a later full rebuild creates a sudden, confusing jump. The fixing-set version belongs in the dependency graph and cache identity.

## Data Quality and Production Controls

The most relevant controls are:

- validate complete, non-overlapping accrual-day coverage;
- require source lineage for official rates and curve lineage for projections;
- enforce auditable state transitions and version corrected fixings;
- isolate fixing roll from curve revaluation using frozen prior inputs;
- display official coverage, projected coverage, fallback warnings, and forecast amount together.

Observability should focus on changed state: newly official observations, valuation cache invalidations, provisional fallbacks, corrections, and unexplained coupon-forecast jumps.

## Requirement Discovery and Interview Questions

When a trader asks for a “partially fixed coupon,” clarify:

- Is coverage measured by calendar days, business observations, or PV sensitivity?
- Which publication source and cutoff make a fixing official?
- Which projection curve and snapshot value the remaining observations?
- Is a projected fallback allowed when an expected fixing is missing?
- Are lookback, observation shift, and holiday weights already embedded in the schedule?
- Must fixing surprise be separated from same-day curve movement?
- Do corrected fixings reopen historical PnL?

An interview-quality answer should emphasise that coverage is not risk, that the coupon remains one compound chain, and that PnL attribution requires controlled state transitions rather than a raw difference of two forecasts.

## Key Takeaways

- Compound official and projected observations in one contractual schedule.
- Treat fixing coverage as a data-state measure, not a percentage of risk removed.
- Explain a new fixing against the prior projected observation while freezing other inputs.
- Revalue remaining projections separately under the current curve snapshot.
- Version fixing sets, schedules, and cache dependencies so the result is reproducible and operationally safe.
