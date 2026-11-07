# Explaining Large-Move Rates PnL with DV01 and Gamma

## Abstract

Bucketed DV01 can explain a small rates move well and still leave a systematic residual when the market moves farther. The reason is geometric: DV01 is a local slope, while portfolio value is generally curved with respect to rates. A second-order gamma term can identify how much of the residual is ordinary convexity rather than bad data or broken risk. This article develops a practical single-factor gamma explain, illustrates it numerically, and translates the desk request into a controlled Python workflow with stable bumps, full lineage, and clear limits.

## Desk Context

Assume yesterday’s 10Y DV01 is stable and all basic controls have passed: the market snapshots align, quote units and signs match, the same trade population is used, and the full revaluation is reproducible. The 10Y quote then rises by 6 basis points.

DV01 predicts a GBP 48,000 loss, but full revaluation shows only GBP 45,600 of loss. Is the risk wrong?

Not necessarily. DV01 describes the tangent to the PV function at yesterday’s market point. For a sufficiently large move, the slope itself changes. Gamma, often discussed as convexity in rates, measures that local change in slope.

The objective is not to replace full revaluation. It is to determine whether an observed first-order residual has the size and sign expected from curvature.

## From a Linear Explain to a Quadratic Explain

For an observed quote move $\Delta q$ measured in basis points, the first-order approximation is

$$
\Delta V_{linear}\approx D\Delta q,
$$

where $D$ is signed DV01 in currency per basis point.

Adding a second-order term gives

$$
\Delta V_{quadratic}
\approx
D\Delta q+\frac{1}{2}\Gamma(\Delta q)^2.
$$

Gamma has units of currency per basis-point squared. Because the move is squared, the gamma contribution can have the same sign for upward and downward moves. It captures curvature rather than simple direction.

Using symmetric bumps of $h$ basis points around the same base market, both quantities can be estimated from three valuations:

$$
D(h)\approx\frac{V(q+h)-V(q-h)}{2h},
$$

$$
\Gamma(h)\approx
\frac{V(q+h)-2V(q)+V(q-h)}{h^2}.
$$

This construction inherits the bump-size problem. An extremely small $h$ magnifies solver residuals, PV rounding, and floating-point noise. An excessively large $h$ may average curvature across a region that is no longer local. The approved gamma configuration therefore needs its own bump ladder and stability tolerance.

This article deliberately stops at single-factor gamma. When several curve factors move together, cross-gamma terms can matter, but they should not become the first explanation offered for every residual.

## Worked Numerical Example

Suppose the portfolio has:

- signed 10Y DV01 $D=-8{,}000$ GBP/bp;
- gamma $\Gamma=+150$ GBP/bp²;
- an observed 10Y quote move $\Delta q=+6$bp.

The linear estimate is

$$
\Delta V_{linear}=(-8{,}000)(6)=-48{,}000\text{ GBP}.
$$

The convexity component is

$$
\Delta V_{gamma}
=\frac{1}{2}(150)(6^2)
=+2{,}700\text{ GBP}.
$$

The quadratic prediction becomes

$$
\Delta V_{quadratic}
=-48{,}000+2{,}700
=-45{,}300\text{ GBP}.
$$

If full revaluation produces GBP -45,600, the comparison is:

| Explain | Predicted PnL | Residual: actual minus predicted |
|---|---:|---:|
| DV01 only | -48,000 | +2,400 |
| DV01 plus gamma | -45,300 | -300 |

The absolute residual falls from GBP 2,400 to GBP 300. Gamma explains most of the first-order miss. Positive gamma offsets part of the linear loss in this example, but the portfolio still loses money because the DV01 term dominates.

Residual contraction is important evidence. Simply computing a gamma number is not enough: if adding it makes the explain worse, the bump construction, factor definition, curve builds, and snapshot lineage should be reviewed before invoking more exotic effects.

## Engineering Design

The calculation should retain the three source valuations, not only the derived gamma. Required lineage includes the base market snapshot, trade snapshot, curve version, bump size, bump direction, solver status, and PV precision.

```python
def explain_with_gamma(
    base_pv: float,
    pv_up: float,
    pv_down: float,
    bump_bp: float,
    observed_move_bp: float,
    actual_pnl: float,
) -> dict:
    if bump_bp <= 0:
        raise ValueError("bump_bp must be positive")

    dv01 = (pv_up - pv_down) / (2.0 * bump_bp)
    gamma = (
        pv_up - 2.0 * base_pv + pv_down
    ) / (bump_bp ** 2)

    linear = dv01 * observed_move_bp
    convexity = 0.5 * gamma * observed_move_bp ** 2
    predicted = linear + convexity

    return {
        "dv01_pnl": linear,
        "gamma_pnl": convexity,
        "predicted_pnl": predicted,
        "actual_pnl": actual_pnl,
        "residual": actual_pnl - predicted,
        "dv01": dv01,
        "gamma": gamma,
    }
```

A production response should place `DV01_PNL`, `GAMMA_PNL`, `FULL_REVAL_PNL`, and `RESIDUAL` side by side. Gamma should explain a residual, not conceal it inside a single adjusted number.

## Data Quality and Production Considerations

Five controls are especially relevant:

1. **Symmetric-bump integrity.** The up and down curves must be built independently from the same immutable base snapshot. A cache collision between bump directions can create a plausible but false gamma.
2. **Gamma stability.** Evaluate an approved bump ladder. An unstable result should be `UNSTABLE_GAMMA`, never silently replaced with zero.
3. **Explain-improvement gate.** Adding gamma should materially reduce the absolute residual. A larger residual triggers review.
4. **Movement-range warning.** If the observed move is many times larger than the calibration bump, local gamma may not represent the whole path.
5. **Valuation lineage.** Preserve base, up, and down PVs, curve-build states, solver diagnostics, and model versions.

Useful tests include a linear payoff with near-zero gamma, a known quadratic PV function, a failed bumped curve, incorrect cache reuse, and equal-magnitude positive and negative observed moves. A particularly dangerous failure is allowing the up and down valuations to use different base snapshots: ordinary market drift is then misclassified as curvature.

## Requirement Discovery and Interview Questions

When the desk says, “Large moves never explain,” clarify:

- Does the residual remain small for small moves and grow approximately with the square of move size?
- Is gamma defined against calibration quotes, zero rates, or a parallel curve shift?
- Does it use the same curve build, taxonomy, and snapshot as official DV01?
- Should gamma PnL be shown by trade, book, or risk factor?
- What reduction in residual is material enough to accept?
- Beyond what move size must the system rely on full revaluation rather than a quadratic approximation?

A concise interview answer is: “I validate the aligned first-order explain first. If the residual grows with move size, I add a stable symmetric-bump gamma term and require the residual to contract. Full revaluation remains authoritative.”

## Key Takeaways

- DV01 is a local slope; gamma measures local curvature.
- The second-order PnL term is $\frac{1}{2}\Gamma(\Delta q)^2$.
- Symmetric bumps must share the same base snapshot and pass a stability policy.
- A useful gamma explain reduces the residual and remains fully traceable to its source valuations.
- Gamma improves diagnosis, but it does not replace full revaluation for large market moves.

