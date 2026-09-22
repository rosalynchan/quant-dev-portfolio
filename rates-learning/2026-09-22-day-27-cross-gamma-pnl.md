# Cross-Gamma in a Key-Rate PnL Explain

## Abstract

A key-rate PnL explain often starts with opening DV01 and then adds diagonal gamma for curvature at individual curve nodes. That still omits interactions between different nodes. Cross-gamma captures the non-additive PnL created when two rates move together. This article develops the desk intuition, works through a numerical example, and shows how a quant developer can prevent the most common production error: double-counting symmetric off-diagonal terms.

## Desk Context

Assume yesterday's explain contains linear key-rate PnL of GBP 9,800, carry of GBP 600, diagonal gamma PnL of GBP 230, and actual full-revaluation PnL of GBP 10,650. The explained amount is GBP 10,630, leaving GBP 20 residual.

The opening risk also contains a 5Y-by-10Y cross-gamma coefficient. The desk question is narrow: does the interaction between those two curve moves explain the remaining difference?

Cross-gamma is useful only under an explicit convention. A field named gamma is not enough. The implementation must specify units, snapshot, bucket identities, matrix representation, and where the Taylor half factor is applied.

## From Diagonal Gamma to Cross-Gamma

For a vector of rate moves, the second-order Taylor term is

$$
\frac{1}{2}\Delta r^T\Gamma\Delta r.
$$

A diagonal contribution for node \(i\) is

$$
\frac{1}{2}\Gamma_{ii}(\Delta r_i)^2.
$$

If the Hessian is symmetric, the full matrix contains both \(\Gamma_{ij}\) and \(\Gamma_{ji}\). Expanding the quadratic form produces two identical off-diagonal terms, and the leading one-half cancels that duplication. For one unique pair,

$$
CrossPnL_{ij}
=
\Gamma_{ij}\Delta r_i\Delta r_j,
\qquad i<j.
$$

This leads to two valid representations:

- A full symmetric matrix, evaluated as one-half times the complete quadratic form.
- A unique-pair list containing only \(i<j\), where each cross contribution is calculated without another half factor.

Mixing the conventions creates a plausible but wrong result. Summing both symmetric cells as unique pairs doubles the PnL. Applying one-half to a unique pair understates it by half.

## Sign Intuition

Diagonal gamma uses a squared move, so the move's sign disappears. Cross-gamma uses the product of two moves. For a positive coefficient, two rates moving in the same direction produce a positive contribution; rates moving in opposite directions produce a negative contribution.

A cross term can therefore distinguish a parallel-like move from a curve twist. It is not automatically a positive convexity benefit.

## Worked Numerical Example

Suppose the 5Y rate moves +2bp, the 10Y rate moves +3bp, and their cross-gamma coefficient is +GBP 3/bp squared.

$$
CrossPnL_{5Y,10Y}
=
3\times2\times3
=
+GBP\ 18.
$$

Adding it to the existing explain gives

$$
ExplainedPnL
=
9{,}800+600+230+18
=
GBP\ 10{,}648.
$$

Against actual PnL of GBP 10,650,

$$
Residual
=
10{,}650-10{,}648
=
+GBP\ 2.
$$

The cross term reduces the residual from GBP 20 to GBP 2.

Now reverse the 10Y move to -3bp:

$$
CrossPnL_{5Y,10Y}
=
3\times2\times(-3)
=
-GBP\ 18.
$$

The same risk coefficient contributes with the opposite sign because the market move has changed from same-direction to twist-like.

## Engineering Design

A production API should prefer labelled unique pairs over anonymous matrix coordinates when downstream consumers need transparent attribution.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CrossGammaPair:
    left_bucket: str
    right_bucket: str
    gamma_per_bp2: Decimal


def explain_cross_gamma(
    pairs: list[CrossGammaPair],
    moves_bp: dict[str, Decimal],
    explained_before_cross: Decimal,
    actual_pnl: Decimal,
) -> dict:
    contributions = {}
    seen = set()

    for pair in pairs:
        key = tuple(sorted((
            pair.left_bucket,
            pair.right_bucket,
        )))
        if key[0] == key[1]:
            raise ValueError("diagonal is not cross-gamma")
        if key in seen:
            raise ValueError("duplicate symmetric pair")
        if key[0] not in moves_bp or key[1] not in moves_bp:
            raise ValueError("missing node move")

        seen.add(key)
        contributions["|".join(key)] = (
            pair.gamma_per_bp2
            * moves_bp[key[0]]
            * moves_bp[key[1]]
        )

    cross_total = sum(
        contributions.values(),
        Decimal("0"),
    )
    explained = explained_before_cross + cross_total

    return {
        "cross_gamma_by_pair": contributions,
        "cross_gamma_total": cross_total,
        "explained_pnl": explained,
        "residual": actual_pnl - explained,
        "pair_convention": "UNIQUE_I_LT_J",
    }
```

The canonical key ensures that 5Y|10Y and 10Y|5Y cannot both enter the result. The response publishes the representation rather than forcing clients to infer it.

## Data Quality and Production Considerations

The most relevant controls are:

1. **Representation and half-factor lineage.** Record whether the source is a full Hessian or unique-pair list and which service applies the half factor.
2. **Canonical pair identifiers.** Sort or otherwise canonicalise each pair and reject symmetric duplicates.
3. **Aligned risk inputs.** Cross-gamma, rate moves, curve definition, opening snapshot, currency, and bp-squared scale must agree.
4. **Coverage disclosure.** Label the result as full-grid, adjacent-only, or selected-pair coverage. A missing pair must not silently mean zero.
5. **Residual-improvement monitoring.** Compare residual before and after cross-gamma. A material deterioration can signal a sign, unit, snapshot, or duplication error.

With \(n\) nodes there are

$$
\frac{n(n-1)}{2}
$$

unique pairs. Ten nodes create 45 pairs; thirty create 435. A dashboard should usually show the largest contributors and aggregate the rest, while preserving full drill-down and coverage metadata.

A common failure occurs when an upstream service emits a full symmetric matrix and the explain service treats every off-diagonal cell as a unique pair. No field is missing and the dimensions are correct, yet interaction PnL is exactly doubled.

## Requirement Discovery and Interview Questions

When a trader asks to include cross-gamma, clarify:

- Does the desk want the full curve grid, adjacent pairs, or selected material pairs?
- Is the source a full Hessian or a unique-pair representation?
- Is the half factor already embedded in the coefficient?
- Are moves and coefficients expressed in decimal-rate units or basis points?
- Must risk come from the frozen opening snapshot?
- Should the dashboard show all pairs, a top-N list, or only a total?
- Is materiality based on absolute PnL or improvement in unexplained residual?
- Does incomplete coverage block publication or generate a warning?

A strong interview answer connects the mathematics to the data contract: cross-gamma is difficult because representation, units, symmetry, and coverage can be ambiguous across services.

## Testing Strategy

Unit tests should cover same-direction and opposite-direction moves, duplicate pair rejection, missing move detection, and a hand-calculated quadratic-form comparison. A valuable property test builds a random symmetric matrix and verifies that the full-matrix calculation equals the diagonal-plus-unique-pairs calculation within numerical tolerance. Integration tests should confirm that the risk snapshot, curve version, bucket taxonomy, and market window survive unchanged from risk production to the final explain response.

Observability should focus on pair coverage, duplicate rejection counts, the largest absolute pair contribution, and residual change after the component is enabled. A sudden two-times jump in cross-gamma is especially diagnostic of a representation mismatch.

## Key Takeaways

- Cross-gamma measures interaction between two different rate moves.
- A unique-pair contribution is \(\Gamma_{ij}\Delta r_i\Delta r_j\), without another half factor.
- Its sign depends on the coefficient and whether the two rates move together or in opposite directions.
- Canonical pair IDs prevent symmetric duplicates and double counting.
- Full-grid versus partial coverage must be visible in the API and dashboard.
- Cross-gamma is an explain component reconciled to full-revaluation PnL, not additional profit.