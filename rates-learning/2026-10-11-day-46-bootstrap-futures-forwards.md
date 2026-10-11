# Bootstrapping Short-End Curve Nodes from Futures-Adjusted Forwards

## Abstract

Once a short-rate futures quote has been converted into an adjusted FRA forward, a curve builder still needs to turn that rate into usable curve nodes. This article explains the recursive bootstrap from consecutive simple forwards to discount factors. It focuses on the engineering details that make the calculation reliable: exact accrual periods, labelled node lineage, repricing checks, dependency-aware failure handling, and clear separation between projection factors and collateral discount factors.

## Desk Context

Assume yesterday's workflow has already transformed two futures quotes into convexity-adjusted three-month forwards:

- first period forward: 4.20%;
- second period forward: 4.35%;
- accrual fraction for each period: 0.25;
- known factor at the first period start: 0.970000.

A trader asks:

> “The futures strip is loaded. Why can’t the pricer see the next two curve nodes?”

The adjusted forwards are interval rates, not point values. Pricing requires a curve representation from which forward cash flows can be projected consistently. A bootstrap converts each interval quote into the next factor, using the previous solved node as an anchor.

## From an Interval Forward to the Next Node

For a simple-compounded forward over $[T_i,T_{i+1}]$:

$$
F_i=\frac{1}{\alpha_i}\left(\frac{P(T_i)}{P(T_{i+1})}-1\right)
$$

Rearranging gives the recursive bootstrap equation:

$$
P(T_{i+1})=\frac{P(T_i)}{1+F_i\alpha_i}
$$

Here, $P(T)$ is a factor on the curve being built. In a pedagogical single-curve setting it can be read as a discount factor. In a multi-curve production system, the same algebra may build pseudo-discount factors for an index projection curve. Those factors must not be confused with collateral discount factors used to present-value cash flows.

The dependency is sequential. The second new node cannot be solved until the first new node exists. A stale or incorrect upstream node therefore contaminates every downstream node.

## Worked Numerical Example

Start with:

$$
P(T_1)=0.970000
$$

For the first three-month period, $F_1=4.20\%=0.0420$ and $\alpha_1=0.25$:

$$
\begin{aligned}
P(T_2)
&=\frac{0.970000}{1+0.0420\times0.25}\\
&=0.9599208313
\end{aligned}
$$

For the next period, $F_2=4.35\%=0.0435$:

$$
\begin{aligned}
P(T_3)
&=\frac{0.9599208313}{1+0.0435\times0.25}\\
&=0.9495939966
\end{aligned}
$$

The essential acceptance test is to reprice the original forwards from the solved nodes:

$$
\widehat{F}_1
=\frac{1}{0.25}
\left(\frac{0.970000}{0.9599208313}-1\right)
=4.20\%
$$

$$
\widehat{F}_2
=\frac{1}{0.25}
\left(\frac{0.9599208313}{0.9495939966}-1\right)
=4.35\%
$$

The repricing residuals are zero within rounding. That is stronger evidence than merely observing a smooth, decreasing sequence of factors.

If the first forward is accidentally supplied as 4.20 rather than 0.0420, the first denominator becomes $2.05$ instead of $1.0105$. The calculation still returns a positive number, but the node collapses to approximately 0.473. Type checking alone cannot protect the curve.

## Engineering Design

The bootstrap should consume ordered, labelled intervals rather than anonymous rate arrays.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ForwardInterval:
    start: str
    end: str
    forward_rate: Decimal
    accrual_fraction: Decimal
    source_quote_id: str


def bootstrap_forward_nodes(
    anchor_date: str,
    anchor_factor: Decimal,
    intervals: list[ForwardInterval],
) -> dict:
    nodes = {anchor_date: anchor_factor}
    current_date = anchor_date
    current_factor = anchor_factor
    repricing = []

    for row in intervals:
        if row.start != current_date:
            raise ValueError("gap or overlap in intervals")
        if row.accrual_fraction <= 0:
            raise ValueError("invalid accrual fraction")

        denominator = (
            Decimal("1")
            + row.forward_rate
            * row.accrual_fraction
        )
        if denominator <= 0:
            raise ValueError("invalid simple-compounding denominator")

        next_factor = current_factor / denominator
        implied = (
            current_factor / next_factor
            - Decimal("1")
        ) / row.accrual_fraction

        nodes[row.end] = next_factor
        repricing.append({
            "quote_id": row.source_quote_id,
            "input_forward": row.forward_rate,
            "repriced_forward": implied,
            "residual": implied - row.forward_rate,
        })
        current_date = row.end
        current_factor = next_factor

    return {"nodes": nodes, "repricing": repricing}
```

The compact function makes the dependency chain visible. A production implementation would additionally carry curve role, currency, index, calendar, day-count convention, snapshot ID, and methodology version.

## Data Quality and Production Controls

The most relevant controls are:

1. **Contiguous periods.** Each interval start must equal the preceding interval end. A missing contract must not be silently bridged as if a market quote existed.
2. **Contract-derived accruals.** Generate $\alpha_i$ from adjusted dates and the correct day-count rule; do not hard-code 0.25 for every contract.
3. **Quote and adjustment lineage.** Retain the raw futures price, implied rate, convexity adjustment, adjusted forward, and source quote ID.
4. **Repricing tolerance.** Every calibration instrument must reprice from the final curve within an approved tolerance.
5. **Atomic publication.** If a required upstream node fails, do not publish downstream nodes from a partially updated curve.

A particularly subtle failure occurs when contracts are sorted by ticker text rather than economic start date. The dimensions remain correct and every rate is valid, but the bootstrap associates quotes with the wrong intervals.

Useful observability includes maximum quote-repricing residual, missing-period count, first failed node, number of downstream nodes invalidated, and curve age relative to the market snapshot.

## Requirement Discovery and Interview Questions

When a trader or quant says “bootstrap the futures strip,” clarify:

- Are the input rates raw futures rates or convexity-adjusted forwards?
- Which curve role is being built: index projection or collateral discounting?
- What anchors the first futures period?
- How are contract start and end dates generated and adjusted?
- What is the day-count convention for each interval?
- How should gaps, illiquid contracts, and outliers be handled?
- What repricing tolerance blocks publication?
- If one node fails, may the last good curve remain active, and how is that status displayed?

The strongest interview answer combines the recursion with the production contract: solve one labelled node at a time, preserve input lineage, reprice every calibration quote, and publish the curve only as a coherent snapshot.

## Key Takeaways

- An adjusted futures forward is an interval constraint, not yet a complete curve node.
- Bootstrapping solves each next factor recursively from the previous node.
- In multi-curve systems, projection pseudo-factors and collateral discount factors require explicit roles.
- Exact dates, accruals, ordering, and quote lineage matter as much as the formula.
- Repricing the calibration instruments is the decisive curve-build acceptance test.

