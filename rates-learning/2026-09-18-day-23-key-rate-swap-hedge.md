# Hedging Key-Rate DV01 with Two Interest Rate Swaps

## Abstract

A single interest-rate swap can neutralise a bond portfolio's total DV01 while leaving material curve-shape exposure hidden across tenors. This article shows how a quant developer can size two swap hedges against 5-year and 10-year key-rate DV01 using a small linear system. It also explains why the mathematically exact solution is only a starting point: production design must address signed risk, curve and scenario consistency, matrix stability, tradable rounding, liquidity constraints, and residual-risk validation.

## Desk Context

Suppose a cash-bond portfolio has the following signed key-rate DV01:

- 5Y bucket: -GBP 5,000 per basis point;
- 10Y bucket: -GBP 10,800 per basis point.

Under the convention used here, signed DV01 is the PV change after the relevant curve node is shifted upward by one basis point. A fixed-rate bond portfolio is therefore normally negative: higher rates reduce its value.

The trader asks: "Use 5Y and 10Y swaps to flatten the curve risk."

That request is more precise than "flatten total DV01," but it is not yet implementation-ready. A developer still needs the target buckets, curve and bump methodology, allowed hedge instruments, notional increments, residual tolerances, and the market snapshot.

## Why Total DV01 Is Not Enough

Parallel DV01 compresses the portfolio's rate sensitivity into one number. Key-rate DV01, or KRDV01, asks a more local question: how does PV change when a specific curve tenor is bumped, with a defined interpolation or taper around that node?

A portfolio can be close to zero in total DV01 while carrying a large negative 5Y exposure and a large positive 10Y exposure. Those buckets cancel under a parallel aggregation, but they do not cancel under a steepening, flattening, or twist.

Key-rate risk is also not a simple maturity classification. A 10Y swap has cash flows before maturity, so its valuation can respond to several curve nodes. The hedge input must therefore be the instrument's measured bucket-risk profile, not merely its contractual tenor.

## Building the Hedge Matrix

Assume each GBP 10 million pay-fixed swap has the following signed KRDV01:

| Hedge instrument | 5Y bucket | 10Y bucket |
|---|---:|---:|
| 5Y pay-fixed swap | +4,500 | +300 |
| 10Y pay-fixed swap | +500 | +8,000 |

Let $x$ be the number of GBP 10 million units of the 5Y swap and $y$ the number of units of the 10Y swap. Neutralising both portfolio buckets requires:

$$
4{,}500x+500y=5{,}000
$$

$$
300x+8{,}000y=10{,}800
$$

In matrix form:

$$
A n=-d
$$

Here, $d$ is the portfolio risk vector, $A$ is the hedge-instrument risk matrix, and $n$ is the vector of hedge-notional units. This compact representation scales naturally: more buckets produce more rows, while more eligible hedges produce more columns.

With two buckets and two hedges, the system can have an exact solution. Real desks often have more buckets than instruments, constraints on direction or size, and transaction-cost considerations. Those extensions lead to least-squares or constrained optimisation, but the two-by-two case establishes the essential data contract.

## Worked Numerical Example

Solving the equations gives:

$$
x=0.9651,\qquad y=1.3138
$$

The theoretical hedge is therefore approximately:

- GBP 9.651 million pay fixed in the 5Y swap;
- GBP 13.138 million pay fixed in the 10Y swap.

Suppose notionals must be traded in GBP 100,000 increments. Rounding produces GBP 9.7 million and GBP 13.1 million, or $x=0.97$ and $y=1.31$.

The rounded 5Y residual is:

$$
-5{,}000+4{,}500(0.97)+500(1.31)=+GBP\ 20/bp
$$

The rounded 10Y residual is:

$$
-10{,}800+300(0.97)+8{,}000(1.31)=-GBP\ 29/bp
$$

The total residual is only -GBP 9/bp, but the acceptance test should be applied to each bucket. If the desk tolerance is GBP 50/bp per bucket, both pass.

For a simplified twist in which the 5Y node rises 4bp and the 10Y node rises 9bp, the residual first-order PnL is:

$$
20(4)-29(9)=-GBP\ 181
$$

Before hedging, the same approximation would have been:

$$
-5{,}000(4)-10{,}800(9)=-GBP\ 117{,}200
$$

This is a local sensitivity estimate, not a complete valuation. It excludes convexity, spread risk, execution costs, and any change in the risk profile as markets move.

## Engineering Design

A robust service should accept signed portfolio risk and a versioned instrument-risk matrix, solve for theoretical notionals, round to tradable increments, and then recalculate residuals from the rounded trades.

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class TwoBucketHedge:
    portfolio_5y: Decimal
    portfolio_10y: Decimal
    swap5_5y: Decimal
    swap5_10y: Decimal
    swap10_5y: Decimal
    swap10_10y: Decimal
    reference_notional: Decimal
    notional_increment: Decimal
    snapshot_id: str


def solve_two_swap_hedge(x: TwoBucketHedge) -> dict:
    det = x.swap5_5y*x.swap10_10y - x.swap10_5y*x.swap5_10y
    if abs(det) < Decimal("1"):
        raise ValueError("unstable hedge matrix")

    u5 = ((-x.portfolio_5y)*x.swap10_10y
          - x.swap10_5y*(-x.portfolio_10y)) / det
    u10 = (x.swap5_5y*(-x.portfolio_10y)
           - (-x.portfolio_5y)*x.swap5_10y) / det

    def round_notional(units: Decimal) -> Decimal:
        raw = units * x.reference_notional
        lots = (raw / x.notional_increment).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return lots * x.notional_increment

    n5, n10 = round_notional(u5), round_notional(u10)
    q5, q10 = n5/x.reference_notional, n10/x.reference_notional

    return {
        "swap_5y_notional": n5,
        "swap_10y_notional": n10,
        "residual_5y": x.portfolio_5y + q5*x.swap5_5y + q10*x.swap10_5y,
        "residual_10y": x.portfolio_10y + q5*x.swap5_10y + q10*x.swap10_10y,
        "snapshot_id": x.snapshot_id,
    }
```

The explicit two-by-two calculation is useful for pedagogy and deterministic tests. A general implementation would use a numerical linear-algebra library and report condition numbers rather than relying only on a determinant threshold.

## Data Quality and Production Considerations

The most relevant controls are selective but strict.

First, all risks must share the same curve, market snapshot, bucket labels, bump size, and interpolation methodology. Combining a portfolio vector from one scenario definition with a hedge matrix from another can produce a clean numerical answer that has no coherent economic meaning.

Second, preserve signs and instrument direction. A positive notional is not a universal substitute for "pay fixed." The API should state direction explicitly and validate that the resulting signed sensitivities offset the target risks.

Third, test matrix stability. If two hedge instruments have nearly identical bucket profiles, the matrix is close to singular. Tiny input changes can then create enormous, offsetting notionals. A production service should report conditioning, cap gross notional, and reject unstable recommendations.

Fourth, recalculate after rounding. The theoretical solution is not the executed portfolio. Residuals, limit checks, and the trader display must all use tradable notionals.

Finally, missing risk is not zero. A failed 10Y bucket calculation should block the recommendation or mark it incomplete; silently inserting zero can reverse the hedge decision.

Useful tests include an exact synthetic system, a rounding-boundary case, a sign-reversal case, a stale-snapshot rejection, and a nearly singular matrix that must fail safely.

## Requirement Discovery and Interview Questions

When a trader asks to "flatten the curve risk," a developer should clarify:

- Which buckets are in scope: only 5Y and 10Y, or the full tenor grid?
- Which curve and key-rate bump methodology define the risk?
- Which swaps or other hedges are eligible, and are both pay-fixed and receive-fixed directions allowed?
- Is the objective an exact match, a least-squares minimum, or simply residuals inside limits?
- What notional increments, liquidity caps, and gross-notional constraints apply?
- Are tolerances defined per bucket, on total DV01, or by stressed PnL?
- Must portfolio and hedge risks come from the same snapshot?
- Who approves a rounded solution that passes total risk but misses one bucket?

A strong interview answer should also mention that the system may be underdetermined or overdetermined. More hedges than buckets can produce many solutions; more buckets than hedges may prevent exact matching. The objective function and constraints then become part of the business requirement, not merely a technical choice.

## Key Takeaways

- Total DV01 can hide large offsetting key-rate exposures.
- Hedge sizing should use measured signed bucket risks, not instrument maturity labels.
- Two swaps and two target buckets form a transparent linear system.
- A theoretical solution must be converted into tradable notionals and re-risked.
- Matrix conditioning, common scenario lineage, and per-bucket residual limits are core production controls.
- The clearest desk statement is: "I solve the signed bucket-risk system, reject unstable profiles, and validate the rounded hedge against every target bucket under one snapshot."