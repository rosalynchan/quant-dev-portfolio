# DV01 Bump-Size Stability: Separating Real Risk Migration from Numerical Noise

## Abstract

A change in bucketed DV01 should not automatically trigger a hedge rebalance. Finite-difference risk depends on bump size, difference scheme, curve-solver tolerance, and valuation precision. If a bump is too large, the estimate includes curvature; if it is too small, numerical noise is divided by a tiny denominator and amplified. This article develops a practical bump-ladder stability check that distinguishes credible curve-risk migration from unstable computation.

## Desk Context

Following a curve methodology release, a desk sees these 10Y bucket DV01 estimates on the same frozen portfolio and market:

- 1.00bp central bump: GBP -8,200/bp
- 0.50bp: GBP -8,205/bp
- 0.25bp: GBP -8,210/bp
- 0.01bp: GBP -7,600/bp

The first three agree closely, while the smallest bump differs by more than GBP 600/bp. A smaller finite-difference step is theoretically more local, but is not automatically more accurate in a production valuation stack.

## DV01 as a Numerical Derivative

For quote $q$, value $V(q)$, and bump $h$ measured in basis points, a forward estimate is

$$
DV01_{fwd}(h)
\approx
\frac{V(q+h)-V(q)}{h}.
$$

A central estimate is

$$
DV01_{central}(h)
\approx
\frac{V(q+h)-V(q-h)}{2h}.
$$

Central differences often reduce first-order curvature bias, but require two bumped valuations. Large bumps include more nonlinearity. Very small bumps make solver residuals, cash-flow rounding, and floating-point error large relative to the bumped PV difference.

The goal is to identify a region where the estimate is both economically local and numerically stable.

## Worked Numerical Example

Assume:

$$
V(q)=\text{GBP }10{,}000{,}000,
$$

$$
V(q+1bp)=\text{GBP }9{,}991{,}900,
$$

$$
V(q-1bp)=\text{GBP }10{,}008{,}300.
$$

The forward estimate is

$$
9{,}991{,}900-10{,}000{,}000
=-\text{GBP }8{,}100/\text{bp}.
$$

The backward estimate, expressed as sensitivity to a one-basis-point rise, is

$$
10{,}000{,}000-10{,}008{,}300
=-\text{GBP }8{,}300/\text{bp}.
$$

The central estimate is

$$
\frac{9{,}991{,}900-10{,}008{,}300}{2}
=-\text{GBP }8{,}200/\text{bp}.
$$

The GBP 200/bp forward-versus-backward difference indicates local curvature or numerical asymmetry.

Across the bump ladder, 1bp, 0.5bp, and 0.25bp estimates differ by at most GBP 10/bp. The 0.01bp result differs from the 0.25bp result by

$$
|-7{,}600-(-8{,}210)|
=\text{GBP }610/\text{bp}.
$$

That discontinuity is stronger evidence of noise amplification than of a sudden economic sensitivity change.

## Define Stability Before Seeing the Result

A production policy should predefine:

- an approved bump ladder;
- a reference estimator such as central difference;
- absolute and relative stability tolerances;
- minimum bumped-PV movement;
- failed curve-rebuild handling.

For adjacent estimates, define relative dispersion:

$$
Dispersion
=
\frac{|D(h_1)-D(h_2)|}
{\max(|D(h_1)|,|D(h_2)|)}.
$$

For -8,200 and -8,205:

$$
Dispersion
=\frac{5}{8{,}205}
\approx0.061\%.
$$

This passes a hypothetical 1% tolerance. The threshold must be versioned by risk family and materiality, not widened after an inconvenient result appears.

## Connecting Stability to Risk Migration

Before approving methodology-driven risk migration, both old and new methodologies must pass the same stability policy. Otherwise the comparison is not like-for-like.

Useful states are STABLE, UNSTABLE, INCOMPLETE, and NOT_MATERIAL. The last state matters because a tiny DV01 can produce an enormous relative percentage from an immaterial absolute difference.

Only stable, complete buckets should enter hedge-migration approval. Zero after a failed bump is especially dangerous: downstream users interpret it as a successful calculation with no sensitivity.

## Engineering Design

```python
from decimal import Decimal


def assess_bump_stability(
    estimates: dict[Decimal, Decimal],
    max_relative_dispersion: Decimal,
) -> dict:
    ordered = sorted(
        estimates.items(),
        key=lambda item: item[0],
        reverse=True,
    )
    if len(ordered) < 2:
        return {"status": "INCOMPLETE"}

    dispersions = []
    for (_, left), (_, right) in zip(
        ordered,
        ordered[1:],
    ):
        scale = max(abs(left), abs(right))
        if scale == 0:
            continue
        dispersions.append(abs(left - right) / scale)

    worst = max(dispersions, default=Decimal("0"))
    return {
        "status": (
            "STABLE"
            if worst <= max_relative_dispersion
            else "UNSTABLE"
        ),
        "worst_dispersion": worst,
        "estimates": estimates,
    }
```

The result should preserve market and trade snapshot IDs, methodology version, bump definition, solver configuration, valuation precision, bumped-curve build IDs, and residual diagnostics.

## Data Quality and Production Considerations

The most relevant controls are:

- **Versioned numerical policy:** bump ladder, difference scheme, solver tolerance, and rounding are explicit.
- **Bumped-curve diagnostics:** each build retains status, residual vector, and curve version.
- **Correct cache identity:** keys include bump size, direction, methodology version, and snapshot.
- **Visible quality state:** dashboards show the stable region, worst dispersion, and failed buckets.
- **Targeted regression tests:** cover linear trades, convex trades, and injected solver noise.

A common failure is caching by instrument ID alone, causing positive and negative bumps to reuse one curve. Central DV01 then appears close to zero. Another is exposing PV only to whole-currency precision: a 0.01bp move can approach rounding resolution, and division by 0.01 magnifies the error.

## Requirement Discovery and Interview Questions

When a trader says “10Y DV01 changed by ten percent,” clarify:

- Did old and new runs use the same bump and difference scheme?
- Were market, trade, and fixing snapshots identical?
- Did all bumped curves build and pass residual validation?
- Is PV precision sufficient for the chosen bump?
- Is stability measured in absolute or relative terms?
- How are tiny-risk buckets protected from percentage explosion?
- Does an unstable bucket block release or use an approved fallback?
- Which configuration defines official desk risk?
- Does the dashboard display value and quality state together?

A strong interview response is: “I would not treat the change as economic until both methodologies pass the same predefined bump ladder on frozen inputs. I would inspect central-difference convergence, build residuals, PV precision, and failed bumps before approving hedge migration.”

## Key Takeaways

- DV01 is a numerical derivative, not directly observed data.
- Smaller bumps reduce truncation bias but amplify numerical noise.
- A bump ladder identifies a stable estimation region.
- Old and new methodologies must pass the same stability policy.
- Failed bumps require an incomplete state, never a false zero.
- Cache identity and valuation precision can corrupt risk materially.
- Hedge decisions should use approved stable risk with visible lineage.

