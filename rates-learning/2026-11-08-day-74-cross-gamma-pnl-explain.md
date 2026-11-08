# Cross-Gamma PnL: Explaining Interaction Risk in Curve Twists

## Abstract

DV01 and single-factor gamma can explain parallel or isolated curve moves yet still leave a material residual during a twist. The missing term may be cross-gamma: the change in sensitivity to one curve factor caused by movement in another. This article develops a practical two-factor PnL explain, shows how to estimate cross-gamma from four corner valuations, and addresses the central engineering trade-off—capturing material interactions without generating an expensive and opaque full matrix of tenor pairs.

## Desk Context

Yesterday’s risk-to-PnL process has already passed its basic controls. Market and trade snapshots align, signed DV01 is stable, and the individual 5Y and 10Y gamma estimates are reliable. Today, however, the curve twists: the 5Y quote rises by 4 basis points while the 10Y quote falls by 3 basis points.

DV01 plus the two self-gamma terms predicts a GBP 22,635 loss. Full revaluation shows a GBP 21,000 loss, leaving GBP 1,635 unexplained. This is the type of residual that a cross-factor interaction may explain.

Cross-gamma is not a replacement for full revaluation. It is a diagnostic and local approximation that answers a precise question: does the joint movement of two factors create PnL that cannot be reconstructed by adding their standalone effects?

## The Off-Diagonal Part of Curvature

For two market-quote factors, 5Y and 10Y, a second-order approximation is

$$
\Delta V\approx
D_5\Delta q_5+D_{10}\Delta q_{10}
+\frac{1}{2}\Gamma_{55}(\Delta q_5)^2
+\frac{1}{2}\Gamma_{10,10}(\Delta q_{10})^2
+\Gamma_{5,10}\Delta q_5\Delta q_{10}.
$$

The self-gamma terms are diagonal elements of the Hessian. Cross-gamma is an off-diagonal element: it describes how the portfolio’s sensitivity to one factor changes when the other factor moves.

The cross term does not carry an additional one-half. In the full Taylor expansion, the symmetric $(5,10)$ and $(10,5)$ terms each receive one-half; when the Hessian is symmetric, they combine into one term.

The PnL sign depends both on the sign of cross-gamma and on whether the market factors move in the same or opposite directions. That makes cross-gamma particularly relevant to steepeners, flatteners, and butterflies.

Using bump sizes $h_5$ and $h_{10}$, cross-gamma can be estimated from four corner valuations:

$$
\Gamma_{5,10}\approx
\frac{V(+,+)-V(+,-)-V(-,+)+V(-,-)}{4h_5h_{10}}.
$$

Every corner must be generated independently from the same immutable base market, trade, fixing, and methodology snapshots. Adding two standalone bumped valuations cannot recover the interaction; that construction removes the very effect being measured.

## Worked Numerical Example

Assume the portfolio has:

- 5Y DV01 $D_5=-4{,}000$ GBP/bp;
- 10Y DV01 $D_{10}=+2{,}500$ GBP/bp;
- 5Y self-gamma $\Gamma_{55}=+80$ GBP/bp²;
- 10Y self-gamma $\Gamma_{10,10}=+50$ GBP/bp²;
- 5Y–10Y cross-gamma $\Gamma_{5,10}=-120$ GBP/bp².

The observed moves are $\Delta q_5=+4$bp and $\Delta q_{10}=-3$bp.

Linear PnL is

$$
(-4{,}000)(4)+(2{,}500)(-3)=-23{,}500\text{ GBP}.
$$

The self-gamma contribution is

$$
\frac{1}{2}(80)(4^2)+\frac{1}{2}(50)(-3)^2
=640+225=+865\text{ GBP}.
$$

Without cross-gamma, the prediction is GBP -22,635. The interaction contribution is

$$
(-120)(4)(-3)=+1{,}440\text{ GBP}.
$$

The complete quadratic prediction becomes GBP -21,195. If full revaluation is GBP -21,000, the residual comparison is:

| Explain | Predicted PnL | Residual: actual minus predicted |
|---|---:|---:|
| DV01 plus self-gamma | -22,635 | +1,635 |
| Including cross-gamma | -21,195 | +195 |

The interaction reduces the absolute residual from GBP 1,635 to GBP 195. Because cross-gamma is negative and the factor moves have opposite signs, the interaction PnL is positive.

Residual contraction is evidence, not proof. If adding cross-gamma makes the explain worse, the first investigation should cover corner valuations, cache keys, factor definitions, and bump stability—not the addition of still more Greeks.

## Engineering Design

A naive full matrix is expensive. With $n$ curve factors, there are $n(n-1)/2$ distinct pairs. Production systems should generally select a sparse set using material DV01, historical co-movement, desk scenarios, adjacency, and evidence from unexplained PnL.

```python
def cross_gamma_from_corners(
    pv_pp: float,
    pv_pm: float,
    pv_mp: float,
    pv_mm: float,
    bump_i_bp: float,
    bump_j_bp: float,
) -> float:
    if bump_i_bp <= 0 or bump_j_bp <= 0:
        raise ValueError("bumps must be positive")

    return (
        pv_pp - pv_pm - pv_mp + pv_mm
    ) / (4.0 * bump_i_bp * bump_j_bp)


def cross_gamma_pnl(
    cross_gamma: float,
    move_i_bp: float,
    move_j_bp: float,
) -> float:
    return cross_gamma * move_i_bp * move_j_bp
```

The result needs a quality state and lineage for all four corner runs. “Not calculated” is not zero exposure and must remain a distinct state.

## Data Quality and Production Considerations

Five controls carry most of the value:

1. **Common-base corners.** All four valuations must reference identical base market, trade, fixing, and methodology snapshots.
2. **Directional cache keys.** Keys include both factor identifiers, both directions, and both bump sizes. A collision between $(+,+)$ and $(+,-)$ can create convincing but false interaction risk.
3. **Symmetry check.** Estimates of $\Gamma_{i,j}$ and $\Gamma_{j,i}$ should agree within tolerance; otherwise return `UNSTABLE_CROSS_GAMMA`.
4. **Sparse selection policy.** Calculate approved material pairs and record why each was selected. Missing coverage is explicit.
5. **Residual-improvement test.** Admit the term into official explain only when it materially reduces out-of-sample full-revaluation residuals.

Tests should include a known quadratic function with a non-zero off-diagonal Hessian, a failed corner build, reversed pair ordering, and mixed bump sizes. A dashboard should favor top interaction PnL, pair lineage, coverage, and residual before versus after—not an unreadable matrix.

## Requirement Discovery and Interview Questions

When a trader says, “The twist is still unexplained,” clarify:

- Which factor pairs correspond to actual desk hedges and scenarios?
- Are the factors calibration quotes or zero-rate nodes?
- Should calculation be limited to adjacent tenors, top-DV01 pairs, or approved scenarios?
- Is materiality measured from the Greek or from realized interaction PnL?
- Does a failed corner make the explain incomplete or trigger a full-revaluation fallback?
- Beyond what move size is the local quadratic approximation no longer accepted?

A strong interview answer is: “I compute cross-gamma selectively for material factor pairs, validate common-base corner valuations and symmetry, and retain the term only when it improves out-of-sample PnL explain. Full revaluation remains authoritative.”

## Key Takeaways

- Self-gamma is diagonal curvature; cross-gamma is interaction between two factors.
- Curve twists can expose interaction PnL that standalone DV01 and gamma omit.
- Four common-base corner valuations are required for a stable estimate.
- Sparse, policy-driven pair selection is more useful than an indiscriminate full matrix.
- Cross-gamma belongs in official explain only when it is stable, traceable, and demonstrably reduces residuals.

