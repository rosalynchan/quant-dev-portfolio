# Curve Calibration Residuals: Why Solver Convergence Is Not Enough

## Abstract

An interest-rate curve builder can report `CONVERGED` and still fail to reproduce the market instruments used to construct it. Numerical convergence describes an algorithmic stopping condition; it is not proof of economic calibration. This article explains post-build repricing controls for Rates curves. It converts quote residuals into basis points and approximate PV residuals, shows why aggregate fit statistics can hide a broken tenor, and outlines a production design in which solver status and curve-validity status are separate publication gates.

## Desk Context

Assume the market quote for a 5Y par swap is 3.250%. A curve build completes successfully and the solver returns `CONVERGED`. When the same 5Y swap is repriced from the resulting curve, however, the implied par rate is 3.253%.

The difference is only 0.003 percentage points, but desk conventions matter: that is 0.3 basis points. If the receive-fixed calibration swap has a PV01 of GBP 1,800 per basis point, the miss corresponds to approximately GBP 540 of PV residual.

The curve has a clean numerical status and an economically unacceptable fit. If it is published, pricing, risk, and PnL consumers inherit the error.

## The Real Calibration Acceptance Test

For calibration instrument $i$, store the observed market quote:

$$
q_i^{market}
$$

After constructing curve $C$, use the same instrument definition and conventions to recover the model quote:

$$
q_i^{model}(C)
$$

The quote residual is:

$$
r_i=q_i^{model}(C)-q_i^{market}
$$

The residual should be close to zero, where “close” is determined by an explicit, instrument-specific tolerance.

This creates an important distinction. Solver convergence is a numerical status. Repricing residual is an economic validation. An optimizer may stop because its step size is small, its iteration limit has been reached, or its objective cannot improve further. None of those conditions guarantees that desk market quotes are reproduced accurately.

## Worked Numerical Example

Assume:

- market 5Y par swap rate: 3.250%;
- curve-implied par rate: 3.253%;
- receive-fixed calibration swap PV01: GBP 1,800/bp;
- allowed quote residual: 0.05bp.

The percentage-point difference is:

$$
3.253\%-3.250\%=0.003\%
$$

Because one basis point equals 0.01%, the quote residual is:

$$
r=\frac{0.003\%}{0.01\%/\text{bp}}=0.3\text{bp}
$$

The residual is six times the 0.05bp tolerance, so the calibration check fails.

For a receive-fixed instrument struck at the market rate, the fixed rate is 0.3bp below the model par rate. Its approximate signed PV residual is:

$$
\begin{aligned}
\text{PVResidual}
&\approx-(0.3)(1{,}800)\\
&=-\text{GBP }540
\end{aligned}
$$

The sign depends on the instrument direction; a quality dashboard may additionally report the absolute amount of GBP 540.

If portfolio PnL moves by roughly this amount when the curve is published, it should not automatically be called a market move. The desk should first determine whether the change is a fit residual, a convention mismatch, or a builder-version effect.

## Quote Residual Versus PV Residual

Quote residual is useful for comparing calibration quality across instruments with different notionals. A 0.3bp miss has a consistent market meaning regardless of the particular calibration trade size.

PV residual translates the miss into monetary materiality:

$$
\text{PVResidual}_i\approx-r_i\times\text{PV01}_i
$$

It is useful for escalation, control thresholds, and PnL explanation, but it depends on direction and scale. A robust result therefore stores signed quote residual, absolute quote residual, PV residual, tolerance, and pass/fail status.

## Why Aggregate Fit Can Be Misleading

Suppose 19 of 20 calibration instruments have almost zero residual, while the 30Y swap misses by 0.8bp. The aggregate root-mean-square error may still look acceptable, yet long-end pricing and hedging can be materially wrong.

Validation should include per-instrument residuals, maximum absolute residual, instrument-family tolerances, consecutive failed-build counts, and changes relative to the previous curve version.

Deposits, futures, OIS, and long-dated swaps have different quote units, liquidity, and numerical scales. A single unnormalised global tolerance is rarely appropriate. The tolerance policy is part of the curve specification and should be versioned with the builder configuration.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CalibrationCheck:
    instrument_id: str
    market_quote: Decimal
    model_quote: Decimal
    quote_unit: str
    tolerance_bp: Decimal
    pv01: Decimal


def validate_curve_fit(checks: list[CalibrationCheck]) -> dict:
    results = []
    for check in checks:
        if check.quote_unit != "RATE_DECIMAL":
            raise ValueError("unsupported quote unit")

        residual_bp = (
            check.model_quote - check.market_quote
        ) * Decimal("10000")
        pv_residual = -residual_bp * check.pv01
        passed = abs(residual_bp) <= check.tolerance_bp

        results.append({
            "instrument_id": check.instrument_id,
            "residual_bp": residual_bp,
            "pv_residual": pv_residual,
            "passed": passed,
        })

    failed = [r for r in results if not r["passed"]]
    return {
        "status": "VALID" if not failed else "REJECTED",
        "results": results,
        "failed_count": len(failed),
    }
```

The publication workflow should require both a satisfactory solver status and successful per-instrument repricing. The entire residual vector should be stored with the curve version, input manifest, and builder configuration.

## Production Controls and Failure Modes

Five controls matter most. Make repricing a hard publication gate. Source quote units, calendars, day counts, index tenors, and effective-date conventions from versioned instrument definitions. Persist the complete residual vector. Show failed instruments and PV materiality on the operational dashboard instead of only a green convergence flag. Finally, use golden tests that bootstrap known quotes and verify that every instrument reprices within tolerance.

A common failure is a unit mismatch: the market input is represented as percentage `3.250`, while the model API returns decimal `0.03250`. Both are valid numeric values, so static typing may not detect the error.

Another failure occurs when the solver uses ACT/365 but the independent repricing check uses ACT/360. The builder may converge consistently while the economic validation fails consistently. That disagreement is valuable evidence of broken convention lineage, not a reason to weaken the tolerance.

## Requirement Discovery and Interview Questions

When a trader says “the curve is off by half a basis point,” clarify:

- Which calibration instrument and tenor are affected?
- Is the comparison a par rate, price, spread, or PV?
- Do market and model quotes use identical conventions?
- Is tolerance measured in basis points, ticks, bid/ask fractions, or PV?
- Do illiquid instruments receive wider tolerances?
- Does one failed tenor reject the full curve or create a `DEGRADED` state?
- While rejected, does live risk use the previous valid version or stop?
- Does a builder or configuration change require residual regression approval?

A strong interview answer separates numerical and economic controls: “I would reprice every calibration instrument after the solve, convert residuals into explicit units, apply instrument-family tolerances, and publish only when the complete residual vector passes.”

## Key Takeaways

- `CONVERGED` is not the same as economically calibrated.
- Every calibration instrument should be repriced after curve construction.
- Quote residual measures fit; PV residual measures monetary materiality.
- Per-instrument checks prevent aggregate statistics from hiding broken tenors.
- Quote units and instrument conventions require explicit versioned lineage.
- Curve publication should require both solver and repricing-validation gates.

Suggested repository filename: `2026-11-01-day-67-curve-calibration-residuals.md`.
