# Futures Convexity Adjustment: From a Short-Rate Futures Quote to an FRA Forward

## Abstract

A short-rate futures quote and an FRA forward can reference a similar future interest period yet imply different rates. The difference is not a data error: futures are marked to market daily, while an FRA settles under a different cash-flow convention. This article develops the practical intuition for the futures convexity adjustment, works through a numerical example, and shows how a quant developer can make the adjustment explicit, versioned, and testable.

## Desk Context

Suppose a short-rate futures contract is quoted at 95.70. Under the standard price convention, the futures-implied rate is:

$$
R_{fut}=100-95.70=4.30\%
$$

A trader wants to use the liquid futures strip to build or validate an FRA curve. They ask:

> “Can I put 4.30% directly into the FRA forward curve?”

Usually, not without checking the modelling convention. Futures gains and losses are settled through daily variation margin. An FRA does not exchange the same path-dependent sequence of cash flows. When rates are stochastic, this timing difference creates a convexity adjustment.

## The Economic Difference

An FRA fixes one future interest rate and generates a contractual payoff. A futures position is revalued and margined every day before expiry. Daily gains can be reinvested, and daily losses must be funded.

If high futures gains tend to arrive when short-term reinvestment rates are also high, the value of daily settlement differs from receiving a single payoff later. Consequently, a futures-implied rate is not automatically the same object as a forward rate derived from discount factors.

For a simple positive-rate model, a common desk approximation is:

$$
CA \approx \frac{1}{2}\sigma^2T_1T_2
$$

where:

- $CA$ is expressed as a decimal rate;
- $\sigma$ is the model volatility in decimal units;
- $T_1$ is the time to the start of the reference period;
- $T_2$ is the time to its end.

The corresponding relationship is often written:

$$
F_{FRA}\approx R_{fut}-CA
$$

Under this convention, the futures-implied rate is above the comparable FRA forward. The exact formula and even the appropriate inputs depend on the model, contract, index, collateral framework, and market convention. The approximation is a teaching and control tool, not a universal pricing law.

## Worked Numerical Example

Assume:

- futures price: 95.70;
- futures-implied rate: 4.30%;
- model volatility: $\sigma=1.00\%=0.01$;
- reference period starts in $T_1=1.00$ years;
- reference period ends in $T_2=1.25$ years.

The convexity adjustment is:

$$
\begin{aligned}
CA
&=\frac{1}{2}\times0.01^2\times1.00\times1.25\\
&=0.0000625\\
&=6.25bp
\end{aligned}
$$

Therefore, the adjusted FRA forward is:

$$
F_{FRA}
\approx4.30\%-0.0625\%
=4.2375\%
$$

If a curve builder inserts 4.30% directly, the forward is 6.25bp too high under this methodology.

For a GBP 100 million receive-floating FRA with accrual fraction 0.25 and period-end discount factor 0.96, the approximate PV impact is:

$$
\begin{aligned}
PVImpact
&\approx N\alpha DF\times6.25bp\\
&=100{,}000{,}000\times0.25\times0.96\times0.000625\\
&=GBP\ 15{,}000
\end{aligned}
$$

That amount is not “convexity profit.” It is the valuation difference caused by using two different forward inputs.

The adjustment grows approximately with volatility squared and with the time horizons. Doubling volatility from 1% to 2% would multiply this simplified adjustment by four, from 6.25bp to 25bp.

## Engineering Design

The calculation should expose both the raw market quote and the methodology-derived forward. Replacing the market rate silently destroys lineage.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FuturesConvexityInput:
    futures_price: Decimal
    volatility: Decimal
    period_start_years: Decimal
    period_end_years: Decimal
    model_version: str
    market_snapshot_id: str


def futures_to_fra_forward(
    x: FuturesConvexityInput,
) -> dict:
    futures_rate = (
        Decimal("100") - x.futures_price
    ) / Decimal("100")

    adjustment = (
        Decimal("0.5")
        * x.volatility
        * x.volatility
        * x.period_start_years
        * x.period_end_years
    )

    return {
        "raw_futures_rate": futures_rate,
        "convexity_adjustment": adjustment,
        "adjusted_fra_forward": (
            futures_rate - adjustment
        ),
        "model_version": x.model_version,
        "market_snapshot_id": (
            x.market_snapshot_id
        ),
    }
```

The API returns three separate fields because each answers a different question: what the market quoted, what the model adjusted, and what the curve builder consumed.

## Data Quality and Production Controls

The most important controls are:

1. **Quote convention validation.** Confirm whether the input is a price such as 95.70 or a decimal rate such as 0.0430. Confusing them can produce a plausible-looking but meaningless output.
2. **Model and parameter lineage.** Store volatility source, calibration time, model version, time convention, and market snapshot.
3. **Sign convention test.** Under the chosen methodology, verify whether the adjustment is subtracted from or added to the futures rate. Do not encode the sign only in documentation.
4. **Instrument-period alignment.** The futures reference period, index, dates, day count, and the target FRA period must match.
5. **Materiality monitoring.** Alert on stale volatility, abnormal day-on-day adjustment changes, or an adjustment outside approved bounds.

A common production failure is a volatility feed supplied in percentage points. The model expects 0.01 but receives 1.00. Because volatility is squared, the adjustment becomes 10,000 times too large.

## Requirement Discovery and Interview Questions

When a trader says “use futures to build the forward curve,” clarify:

- Which futures contract and reference index are in scope?
- Is the input a quoted price, an implied percentage rate, or a decimal rate?
- Which convexity model and calibration source are approved?
- What are the exact start and end times used in the formula?
- Does the desk want the raw futures strip, adjusted FRA forwards, or both?
- How should negative rates or regime changes affect the model?
- Is the adjustment recalculated intraday or fixed at an official market cut?
- What fallback applies when volatility calibration is missing?

A good interview answer starts with the cash-flow distinction, not the formula: daily margining makes a futures rate economically different from a single-settlement forward. The formula is then a versioned transformation with observable inputs and controls.

## Key Takeaways

- A futures-implied rate and an FRA forward are not automatically interchangeable.
- Daily variation margin creates a timing effect that becomes a convexity adjustment under stochastic rates.
- In the stated approximation, subtract the adjustment from the futures rate to estimate the FRA forward.
- Volatility units are especially dangerous because the input is squared.
- Preserve the raw quote, adjustment, adjusted forward, model version, and snapshot as separate data fields.
