# Weighted Least-Squares Hedging for Key-Rate DV01

## Abstract

A key-rate hedge is simple when the number of instruments equals the number of target buckets: solve a square system and neutralise every bucket. Real desks often have more risk buckets than liquid hedges. Exact neutrality is then impossible, so the system must define what “as flat as possible” means. This article develops a weighted least-squares hedge for three key-rate buckets using two swaps and separates mathematical optimality from desk acceptance.

## Desk Context

Assume a bond portfolio has signed key-rate DV01 of:

- 5Y: -GBP 3,000/bp;
- 7Y: -GBP 5,000/bp;
- 10Y: -GBP 4,000/bp.

Only liquid 5Y and 10Y pay-fixed swaps are eligible. The trader asks: “Get the curve risk as flat as possible, but the 7Y bucket matters most.”

That is not yet an implementation-ready requirement. “Flat” could mean minimum raw DV01, minimum limit utilisation, or minimum stressed PnL. “Matters most” must become a weight, a hard constraint, or both.

## From Exact Matching to Residual Minimisation

Let $d$ be the portfolio-risk vector, $A$ the hedge-risk matrix, and $n$ the hedge-notional units. Post-hedge residual risk is:

$$
r=d+An
$$

With three buckets and two instruments, the system is overdetermined. Unless $-d$ lies in the span of the two hedge-risk vectors, no notionals make every residual zero.

Ordinary least squares minimises:

$$
\min_n \sum_i r_i^2
$$

Weighted least squares minimises:

$$
\min_n \sum_i w_i r_i^2
$$

A larger $w_i$ makes the solver more reluctant to leave risk in bucket $i$. The weight is not a probability or an innocent technical default. It represents an approved business preference such as tighter risk appetite or greater stress relevance.

A useful convention is tolerance normalisation. If bucket $i$ has tolerance $T_i$, choosing $w_i=1/T_i^2$ minimises squared limit utilisation rather than raw currency risk.

## Hedge Matrix

Assume each GBP 10 million pay-fixed swap has the following signed KRDV01:

| Hedge instrument | 5Y | 7Y | 10Y |
|---|---:|---:|---:|
| 5Y swap | +3,500 | +1,200 | +200 |
| 10Y swap | +200 | +1,800 | +4,200 |

$$
A=
\begin{bmatrix}
3500 & 200\\
1200 & 1800\\
200 & 4200
\end{bmatrix},
\qquad
d=
\begin{bmatrix}
-3000\\
-5000\\
-4000
\end{bmatrix}
$$

To prioritise 7Y, use:

$$
W=\operatorname{diag}(1,4,1)
$$

The theoretical solution is:

$$
n=(A^TWA)^{-1}A^TW(-d)
$$

This documents the methodology; production code should use stable numerical solvers rather than explicitly calculating an inverse.

## Worked Numerical Example

The weighted solution is:

$$
x=1.1971,\qquad y=1.3451
$$

The theoretical trades are GBP 11.971 million in the 5Y pay-fixed swap and GBP 13.451 million in the 10Y pay-fixed swap.

Rounding to GBP 100,000 increments gives GBP 12.0 million and GBP 13.5 million. The residuals are:

$$
r_{5Y}=-3000+3500(1.20)+200(1.35)=+GBP\ 1{,}470/bp
$$

$$
r_{7Y}=-5000+1200(1.20)+1800(1.35)=-GBP\ 1{,}130/bp
$$

$$
r_{10Y}=-4000+200(1.20)+4200(1.35)=+GBP\ 1{,}910/bp
$$

No bucket is neutral. The result is optimal only for the chosen objective.

With equal weights, theoretical residuals are approximately +GBP 599/bp, -GBP 1,877/bp, and +GBP 776/bp. Raising the 7Y weight improves the 7Y residual while worsening the outer buckets. The trader should see this trade-off rather than only an “optimal” badge.

## Optimal Is Not Acceptable by Definition

A solver success means the objective reached its minimum. It does not prove compliance with desk policy.

A separate acceptance layer may impose per-bucket limits, a maximum weighted score, a gross-notional cap, direction constraints, and eligible-instrument rules. If the 5Y hard limit is GBP 1,000/bp, the rounded solution breaches it at +GBP 1,470/bp. Its status should be LIMIT_BREACH even though the optimisation ran correctly.

The optimiser proposes; the policy layer accepts, warns, or rejects.

## Engineering Design

```python
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class HedgeProblem:
    portfolio_risk: np.ndarray
    hedge_matrix: np.ndarray
    weights: np.ndarray
    bucket_limits: np.ndarray
    snapshot_id: str
    methodology_version: str


def weighted_key_rate_hedge(x: HedgeProblem) -> dict:
    if x.hedge_matrix.shape[0] != x.portfolio_risk.size:
        raise ValueError("bucket dimension mismatch")
    if np.any(x.weights <= 0):
        raise ValueError("weights must be positive")

    root_w = np.sqrt(x.weights)
    weighted_matrix = x.hedge_matrix * root_w[:, None]
    weighted_target = -x.portfolio_risk * root_w

    notionals, _, rank, singular_values = np.linalg.lstsq(
        weighted_matrix, weighted_target, rcond=None
    )
    if rank < x.hedge_matrix.shape[1]:
        raise ValueError("rank-deficient hedge matrix")

    residual = x.portfolio_risk + x.hedge_matrix @ notionals
    within_limits = np.abs(residual) <= x.bucket_limits

    return {
        "notional_units": notionals.tolist(),
        "residual_by_bucket": residual.tolist(),
        "within_limits": within_limits.tolist(),
        "status": "ACCEPTABLE" if within_limits.all() else "LIMIT_BREACH",
        "smallest_singular_value": float(singular_values[-1]),
        "snapshot_id": x.snapshot_id,
        "methodology_version": x.methodology_version,
    }
```

Production APIs should retain explicit bucket labels. Shape validation cannot detect a portfolio ordered as 5Y, 7Y, 10Y being combined with matrix rows ordered as 5Y, 10Y, 7Y.

## Data Quality and Production Considerations

Four controls matter most:

- Portfolio risk, hedge matrix, weights, and limits must share canonical bucket ordering.
- All inputs must use the same curve, currency, bump methodology, and snapshot.
- Rank and conditioning must be checked; nearly redundant hedge profiles can create unstable notionals.
- Risk and policy checks must be rerun after tradable rounding.

Useful observability includes residuals before and after rounding, limit utilisation, gross notional, conditioning statistics, methodology version, and excluded instruments. Missing bucket risk must never be silently converted to zero.

## Requirement Discovery and Interview Questions

When a trader says “as flat as possible,” clarify:

- Is the objective raw KRDV01, limit utilisation, or stressed PnL?
- Which buckets receive higher weights, and who owns the methodology?
- Are weights soft preferences or are some residuals hard constraints?
- Which instruments and directions are eligible?
- What increments and gross-notional caps apply?
- What happens when the optimum still breaches a limit?
- Should the UI compare weighted and unweighted solutions?
- Is manual override allowed, and how is it audited?

A strong interview answer distinguishes objective, constraints, and acceptance. Weights redistribute residual risk; they do not create extra hedging capacity.

## Key Takeaways

- More buckets than hedge instruments usually makes exact neutrality impossible.
- Weighted least squares makes residual-risk priorities explicit.
- Weights need business ownership, versioning, and explanation.
- Mathematical optimality does not imply compliance with hard limits.
- Labels, scenario lineage, diagnostics, rounding, and re-risking are essential.
- A concise desk summary is: “I optimise the approved weighted residual, then independently validate the tradable hedge against every hard limit.”