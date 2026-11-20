# Hedging Slope Risk Without Changing Level Exposure

## Abstract

“Remove the slope risk” is incomplete unless the desk also specifies what should happen to level exposure. A single instrument generally changes both. This article translates that request into two linear constraints, solves a small two-instrument hedge, and validates the result in both level/slope and original quote coordinates. The purpose is to make a hedge calculator's assumptions testable, not to recommend an executable trade.

## From risk description to target risk

The previous lesson defined level as the average of two quote moves and slope as their long-minus-short difference. Under that convention, one basis point of slope widening at fixed average level means the short quote falls by half a basis point and the long quote rises by half a basis point.

We now use those coordinates to specify a target. Suppose a book has positive GBP 2,000 of level sensitivity and negative GBP 5,000 of slope sensitivity. The trader wants slope sensitivity reduced to zero while preserving the positive GBP 2,000 level exposure.

This is different from hedging every risk to zero. The required change is zero level sensitivity and positive GBP 5,000 slope sensitivity. A calculator that automatically targets zero level would implement a different economic instruction.

All sensitivities below are signed, expressed in GBP per basis point of their explicitly defined coordinate. FX, the valuation date, and the market snapshot are fixed.

## Why one instrument is usually insufficient

A hedge instrument has a risk vector, not merely a maturity label. An instrument described as “long-end” can still affect several quote buckets and both level and slope coordinates.

If instrument A adds positive level sensitivity and negative slope sensitivity per unit, selling it can improve negative slope exposure but also reduce the book's level exposure. That may satisfy one objective while violating the other.

Two independently shaped instruments can provide two degrees of freedom. Let $q_A$ and $q_B$ be signed quantities, with negative quantity meaning the opposite direction to each instrument's documented positive-unit position. Their sensitivities must satisfy:

$$
a_Lq_A+b_Lq_B=0
$$

$$
a_Sq_A+b_Sq_B=5{,}000
$$

The right-hand sides describe changes required from the hedge, not final book risk. Mixing those meanings is an easy source of an otherwise plausible but incorrect result.

## Worked example

Define a unit as one million of notional in a specified positive trade direction. The following risk values are synthetic:

| Position | Level risk | Slope risk |
| --- | ---: | ---: |
| Existing book | +2,000 | -5,000 |
| A, per positive unit | +1,000 | -200 |
| B, per positive unit | +500 | +400 |

Preserving level gives $1{,}000q_A+500q_B=0$, hence $q_B=-2q_A$. Substituting into the slope equation gives minus $1{,}000q_A=5{,}000$. Therefore sell five positive-direction units of A and buy ten positive-direction units of B.

The hedge's level contribution is minus GBP 5,000 plus GBP 5,000, exactly zero. Its slope contribution is positive GBP 1,000 plus GBP 4,000, exactly GBP 5,000.

The final book retains level risk of GBP 2,000 and has zero slope risk. The requested target is reached in this two-factor linear model.

The quantity signs are not sufficient booking instructions. “Sell A” only has meaning after defining A's positive position. A swap-oriented implementation should map the signed quantity to the documented pay/receive direction and positive notional, rather than send a negative notional to a booking interface without an explicit contract.

## Validate in the original quote coordinates

A robust check should not stop at the two target totals. Under our convention, short-quote sensitivity equals half level sensitivity minus slope sensitivity; long-quote sensitivity equals half level sensitivity plus slope sensitivity.

The initial book therefore has short sensitivity GBP 6,000 and long sensitivity minus GBP 4,000. Instrument A has short sensitivity GBP 700 and long sensitivity GBP 300 per unit. Instrument B has short sensitivity minus GBP 150 and long sensitivity GBP 650.

The proposed hedge contributes minus GBP 5,000 to the short bucket and positive GBP 5,000 to the long bucket. The final book has GBP 1,000 in each bucket. Their sum is GBP 2,000 and their half-difference is zero, confirming the target independently.

Under a pure one-basis-point slope shock, these equal bucket risks cancel. Under a common one-basis-point level move, they contribute GBP 2,000. Neither check claims that nonlinear or additional-factor risk has disappeared.

## Compact engineering design

Represent hedge-unit risks as columns and risk objectives as rows. Pass the required risk change to a linear solver, then recompute final risk from the proposed quantities. Do not explicitly invert a matrix in production code.

```python
import numpy as np

def hedge_quantities(book, target, unit_risk):
    # Rows: level, slope. Columns: A, B.
    if not all(np.isfinite(x).all() for x in (book, target, unit_risk)):
        raise ValueError("Non-finite risk input")
    required_change = target - book
    quantities = np.linalg.solve(unit_risk, required_change)
    final_risk = book + unit_risk @ quantities
    if not np.allclose(final_risk, target, atol=1e-8, rtol=0):
        raise ValueError("Hedge target reconciliation failed")
    return quantities, final_risk

book = np.array([2000.0, -5000.0])
target = np.array([2000.0, 0.0])
unit_risk = np.array([[1000.0, 500.0], [-200.0, 400.0]])
quantities, final_risk = hedge_quantities(book, target, unit_risk)
```

The function assumes input shapes, factor order, normalization, currency, and snapshots have already been validated. It is a proposal calculator, not an execution service. A singular matrix should fail visibly; silently returning zero quantities would misrepresent failure as “no hedge needed.”

## Four targeted controls

1. **Target semantics:** distinguish preserving existing level from setting level to zero. Store the target and required change separately.
2. **Unit and direction:** attach notional size, positive trade direction, and signed sensitivity convention to each instrument column.
3. **Independent hedge shapes:** reject singular or policy-defined poorly conditioned systems. Nearly identical risk directions can demand unstable, very large offsetting quantities.
4. **Post-constraint risk:** after lot rounding or notional limits, recompute residual risk. The continuous mathematical solution is not necessarily an executable solution.

Conditioning deserves its own later lesson. A nonzero determinant establishes algebraic invertibility, not practical robustness.

## Trader requirements and acceptance tests

Ask whether the slope target is exactly zero or a tolerance band, which level exposure must remain, which instruments are permitted, and whether short positions or fractional units are allowed. Clarify whether the output is a proposal requiring approval.

For this example, acceptance requires quantities minus five and plus ten, final risk positive GBP 2,000 level and zero slope, and consistent original-bucket reconstruction. If A is unavailable, report the unsatisfied constraint rather than claim that a single-instrument approximation meets both objectives.

## Key takeaways

A hedge request is a target vector plus constraints, not merely “negative current risk.” Instruments affect multiple factors. Solve for the required change, validate the final risk in both coordinate systems, and distinguish a continuous proposal from an approved executable trade.

All examples are generic educational illustrations, with no confidential employer data, proprietary architecture, or investment advice.
