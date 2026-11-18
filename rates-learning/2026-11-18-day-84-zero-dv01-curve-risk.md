# Zero Total DV01 Does Not Mean Zero Curve Risk

## Abstract

A zero total rate sensitivity describes cancellation under a particular common shock. It does not guarantee protection against a change in curve shape. This article connects a two-tenor risk vector to explicit parallel and steepening scenarios, shows how a neutral-looking total can hide material PnL, and defines a compact calculation contract that preserves factor identity. The focus is interpretation and scenario validation, not a new curve-calibration method.

## Desk context

A trader sees zero total DV01 and asks why a curve steepening produced a loss. The developer should first inspect what “total” actually aggregates. If short-end and long-end sensitivities have opposite signs, adding them compresses a vector into one number. The compression preserves information about a common move but discards information needed for independent moves.

The previous lesson distinguished reporting currency from risk-factor currency. Today the reporting currency remains GBP and FX remains frozen. We move one level deeper: two tenors on the same curve are also distinct factors. A common currency and a common curve name do not make them interchangeable.

This is not a recommendation to enter a curve trade. It is an educational explanation of what a risk report can and cannot establish.

## Define the risk and shock together

Use signed sensitivities: positive means a PV gain for a positive rate move. Let $d_2$ and $d_{10}$ denote local linear sensitivities, expressed in GBP per basis point, to independently defined two-year and ten-year quote factors. The other market inputs remain fixed.

For a scenario with moves $s_2$ and $s_{10}$ measured numerically in basis points, the first-order PnL estimate is:

$$
P_{lin}=d_2s_2+d_{10}s_{10}
$$

The total sensitivity is:

$$
D_{total}=d_2+d_{10}
$$

Multiplying that total by a single move is justified only when both factors receive that same move. Zero total therefore means zero first-order response to the chosen equal-move direction. It does not mean that the two entries of the risk vector are zero.

In practice a reported one-basis-point bump difference approximates the derivative used in this formula. Summing separate finite-bump results need not exactly reproduce a simultaneous bumped valuation when nonlinearities matter. Keep that distinction explicit rather than calling the sum an exact scenario result.

Also distinguish a common move in selected market quotes from a parallel shift of every zero rate. They are different scenario definitions. Our two-factor model is intentionally simplified, and all scenario names refer to its specified quote factors.

## Worked example: the hidden shape exposure

Consider the following synthetic risk:

| Factor | Signed sensitivity, GBP/bp |
| --- | ---: |
| Two-year quote | +5,000 |
| Ten-year quote | -5,000 |
| Sum | 0 |

Under a common positive five-basis-point move, the short-end contribution is GBP 25,000 and the long-end contribution is minus GBP 25,000. The first-order total is zero.

Now define a symmetric steepening scenario explicitly: the two-year rate falls by five basis points and the ten-year rate rises by five basis points. The ten-year-minus-two-year spread widens by ten basis points.

The short-end contribution is now minus GBP 25,000. The long-end contribution is also minus GBP 25,000. Total estimated PnL is minus GBP 50,000 despite the zero sensitivity sum.

The sign follows directly from the risk vector. The position likes a higher two-year rate and a lower ten-year rate; this steepening moves both factors against it. Do not infer gain or loss merely from the word “steepener,” which may refer to a position rather than a market movement.

Finally consider a long-end-only steepening: the two-year rate is unchanged and the ten-year rate rises by ten basis points. The spread again widens by ten basis points. This particular zero-total linear example also loses GBP 50,000. That equality follows from its special risk cancellation, not from a universal property of spread moves.

For a book with nonzero total sensitivity, two scenarios with the same spread change can generate different PnL because their common-move components differ. Always store both tenor shocks rather than only the spread change.

## Translate “steepening” into an executable requirement

A trader asking for “a ten-basis-point steepener” has not yet specified a complete scenario. Ask which spread, which instruments or curve coordinates, whether the short end falls, the long end rises, or both move, and whether the desired output is a linear estimate or full revaluation.

An executable requirement might read: shock the specified two-year quote by minus five basis points and the specified ten-year quote by plus five basis points; rebuild using the agreed curve configuration; freeze all other inputs; display factor contributions and the full-revaluation comparison.

The linear calculation should use risk computed at the same base snapshot. Using yesterday's risk against today's scenario changes the experiment and can create a residual unrelated to the scenario engine.

## Compact engineering design

Keep risk and scenario entries keyed by the same stable factor identifiers. Validate exact key agreement for this intentionally complete two-factor exercise; a broader system may use an explicit policy for unshocked factors. Never silently replace missing risk with zero.

```python
from decimal import Decimal

def linear_scenario(risk_gbp_per_bp, shock_bp):
    if risk_gbp_per_bp.keys() != shock_bp.keys():
        raise ValueError("Risk/scenario factor mismatch")
    contributions = {
        factor: risk_gbp_per_bp[factor] * shock_bp[factor]
        for factor in risk_gbp_per_bp
    }
    return {
        "currency": "GBP",
        "method": "first_order",
        "contributions": contributions,
        "pnl": sum(contributions.values(), Decimal("0")),
    }

risk = {"EUR_2Y": Decimal("5000"), "EUR_10Y": Decimal("-5000")}
shock = {"EUR_2Y": Decimal("-5"), "EUR_10Y": Decimal("5")}
result = linear_scenario(risk, shock)
```

EUR in these identifiers denotes the underlying curve factors; GBP denotes the output amount. Retain the snapshot, quote identifiers, sign convention, and curve configuration alongside this compact result. The snippet does not rebuild a curve or claim to implement full pricing.

## Four targeted production checks

1. **Factor alignment:** join by stable identifiers, not row position or a tenor label shared by multiple curves.
2. **Shock units:** sensitivities per basis point multiply numeric basis-point moves, not decimal rate changes such as 0.0005.
3. **Scenario completeness:** preserve the explicit two-factor move; “ten-basis-point steepening” is not an adequate serialized specification.
4. **Approximation status:** label linear estimates and compare material scenarios with full revaluation rather than forcing agreement with a plug.

Tests should cover the equal-move cancellation, the symmetric steepening loss, opposite shocks reversing linear PnL, and deliberate factor mismatch. The dashboard should show the risk vector and factor contributions beside the total.

## Interview questions and takeaways

Why can total DV01 be zero while risk remains? Because zero is the projection onto one shock direction, not proof that every factor exposure vanishes.

Why keep full revaluation? Finite moves can introduce curvature and interactions that the first-order estimate omits. A residual is a diagnostic observation, not automatically a data defect.

A useful desk response is: “The book is neutral to the specified common first-order move, but it retains shape exposure. Let us agree the tenor shocks and inspect the contributions.”

All figures are synthetic, public-safe educational examples. No employer data, proprietary architecture, or investment advice is included.
