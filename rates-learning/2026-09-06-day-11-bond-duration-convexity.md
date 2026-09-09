# From Duration to Convexity: Engineering Bond Rate Risk

## Abstract

Duration and DV01 turn the inverse price–yield relationship into usable desk risk. They are deliberately local approximations: excellent for small moves and rapid aggregation, but incomplete when yields move materially or the curve changes shape. This article connects modified duration, monetary DV01, convexity and key-rate risk to a production-quality design with explicit shock semantics, lineage, controls and failure handling.

## Desk Context

A trader holds a GBP 10 million long fixed-rate bond position. The screen reports signed yield DV01 of approximately -GBP 7,000 per basis point. Yields rise by 50bp. The linear estimate is a GBP 350,000 loss, while full revaluation shows a loss near GBP 342,300.

The useful questions are:

- Was the move applied to one yield or a full curve?
- Was spread risk handled separately?
- How much difference is expected convexity?
- Did risk and PnL share the same position, settlement date and snapshot?
- Is the residual economic or operational?

## Duration as First-Order Sensitivity

Macaulay duration is the PV-weighted average timing of cash flows:

\[
D_{Mac}=\frac{\sum_i t_iPV(CF_i)}{P}
\]

Modified duration converts it to price sensitivity:

\[
D_{mod}=\frac{D_{Mac}}{1+y/m}
\]

For a small yield change:

\[
\frac{\Delta P}{P}\approx-D_{mod}\Delta y
\]

Duration is not maturity. Equal-maturity bonds can have different durations because coupons, yields, amortisation and embedded options differ.

## Monetary DV01

Signed DV01 can be defined by bump-and-revalue:

\[
DV01_{signed}=PV(y+1bp)-PV(y)
\]

For a long option-free bond it is normally negative. The duration approximation is:

\[
DV01\approx-PD_{mod}0.0001
\]

The value \(P\) must be the agreed position value. A per-100 clean price cannot be treated as monetary position PV.

“DV01” is not a complete contract. It may mean yield DV01, curve PV01, key-rate DV01 or spread DV01. Every result needs a shock target and methodology.

## Worked Example

Assume a GBP 10,000,000 position, modified duration 7.0, convexity 65 and a +50bp yield move.

\[
DV01\approx-10,000,000\times7.0\times0.0001
=-GBP\ 7,000/bp
\]

Linear PnL is:

\[
-7,000\times50=-GBP\ 350,000
\]

For a larger move, add convexity:

\[
\frac{\Delta P}{P}
\approx-D_{mod}\Delta y+\frac{1}{2}C(\Delta y)^2
\]

\[
\frac{1}{2}\times65\times0.005^2=0.0008125
\]

The convexity contribution is GBP 8,125, so:

\[
EstimatedPnL=-350,000+8,125=-GBP\ 341,875
\]

If full revaluation gives -GBP 342,300, the residual is -GBP 425. Higher-order effects, a non-parallel curve move, cash-flow timing, compounding or convention differences may explain it. DV01 was useful; it was never intended as exact large-move valuation.

## Convexity and Embedded Options

An option-free bond normally has positive convexity. When yields rise, its loss tends to be smaller than the duration-only estimate; when yields fall, its gain tends to be larger.

A callable bond may exhibit negative convexity because falling yields increase the probability of early redemption and limit price appreciation. Positive convexity must not be imposed as a universal invariant across product types.

## Yield, Curve and Spread Risk

For a credit bond, yield is approximately a risk-free rate plus a credit spread, but the sensitivities are not interchangeable:

- Yield DV01 bumps the summary yield.
- Curve DV01 bumps risk-free curve inputs.
- Key-rate DV01 shocks a selected tenor.
- CS01 bumps a spread input or curve.

| Measure | Signed risk |
|---|---:|
| Risk-free curve DV01 | -GBP 4,500/bp |
| CS01 | -GBP 2,300/bp |
| Simple yield DV01 | -GBP 6,700/bp |

Yield DV01 need not equal curve DV01 plus CS01. Interpolation, rebuilds, spread definitions, optionality and cross-effects create differences. Reconciliation is meaningful only with compatible scenarios and a stated tolerance.

## Key-Rate Risk

A parallel DV01 hides location:

| Curve tenor | Signed +1bp PV change |
|---|---:|
| 2Y | -GBP 400 |
| 5Y | -GBP 1,600 |
| 10Y | -GBP 5,100 |
| Sum | -GBP 7,100 |

The exposure is dominated by 10Y. A steepening or twist will not be explained well by one total DV01 and one move. Preserve curve and tenor dimensions before aggregation.

## Engineering Design

\`\`\`python
@dataclass(frozen=True)
class BondRiskDefinition:
    measure: Literal[
        "YIELD_DV01", "CURVE_DV01",
        "KEY_RATE_DV01", "CS01", "CONVEXITY",
    ]
    shock_target: str
    bump_bp: Decimal
    bump_method: Literal["FORWARD", "CENTRAL"]
    rebuild_curve: bool
    price_basis: Literal["CLEAN", "DIRTY"]
    settlement_policy_version: str
    scenario_version: str
\`\`\`

\`\`\`python
@dataclass(frozen=True)
class BondRiskResult:
    instrument_id: str
    position_id: str
    measure: str
    bucket: str | None
    base_pv: Decimal
    signed_pv_change: Decimal | None
    currency: str
    market_snapshot_id: str
    reference_data_version: str
    scenario_id: str
    status: Literal["SUCCESS", "FAILED"]
\`\`\`

A central bump estimates first- and second-order effects:

\`\`\`python
def calculate_bond_risk(position, context, definition):
    base = price(position, context)

    up = apply_shock(
        context,
        target=definition.shock_target,
        bp=definition.bump_bp,
        rebuild=definition.rebuild_curve,
    )
    down = apply_shock(
        context,
        target=definition.shock_target,
        bp=-definition.bump_bp,
        rebuild=definition.rebuild_curve,
    )

    pv_up = price(position, up)
    pv_down = price(position, down)

    return {
        "signed_dv01": (pv_up - pv_down) / Decimal("2"),
        "one_bp_convexity_pnl": pv_up + pv_down - 2 * base,
        "base_pv": base,
        "scenario_version": definition.scenario_version,
    }
\`\`\`

Central differences are often more accurate than one-sided bumps, but require two revaluations. The choice is a versioned methodology decision.

## Data Quality, Controls and Testing

Enforce:

- identical positions for base, up and down;
- one snapshot and one reference-data version;
- explicit basis-point/decimal conversion;
- correct per-100 to position-value conversion;
- explicit clean or dirty basis;
- separate names for yield, curve and spread shocks;
- curve-build checks after quote bumps;
- key-rate/parallel reconciliation;
- visible failed or missing buckets;
- model-appropriate callable-bond handling;
- currency-aware aggregation.

\`\`\`python
def test_long_option_free_bond_has_negative_dv01():
    assert yield_dv01(long_bond).signed_pv_change < 0

def test_key_rate_sum_reconciles():
    assert abs(
        sum(key_rate_dv01(bond))
        - parallel_curve_dv01(bond)
    ) < tolerance

def test_failure_is_not_zero():
    result = risk_with_missing_curve_node()
    assert result.status == "FAILED"
    assert result.signed_pv_change is None
\`\`\`

Monitor calculation age, bucket coverage, scenario-version usage, mixed-snapshot rejections, key-rate reconciliation and the duration-convexity versus full-revaluation residual.

## Common Production Failure Modes

1. Treating 50bp as 0.50 instead of 0.005.
2. Displaying per-100 risk as position-level currency risk.
3. Using clean price for risk and dirty PV for PnL.
4. Storing yield DV01, curve DV01 and CS01 in one ambiguous field.
5. Explaining current PnL with stale positions or risk.
6. Changing bump methodology without changing scenario version.
7. Aggregating a failed key-rate bucket as zero.
8. Summing different currencies directly.
9. Applying option-free risk to callable bonds.
10. Treating duration as exact under a large curve twist.
11. Double-counting through hierarchy joins.
12. Using different settlement dates for risk and valuation.

## Requirement Discovery and Interview Questions

When asked for “bond DV01,” clarify:

1. Yield DV01, risk-free curve DV01 or CS01?
2. One-sided +1bp or central ±1bp?
3. Parallel or key-rate?
4. Zero-node bump or market-quote bump and rebuild?
5. Clean price, dirty price or full position PV?
6. Signed or absolute; local or reporting currency?
7. Include convexity and full-revaluation comparison?
8. Which model and volatility apply to callable bonds?
9. What reconciliation tolerance is acceptable?
10. How should partial failures appear?

A strong interview answer is:

> DV01 is a local first-order sensitivity. I define the shock target and methodology explicitly, retain curve-tenor dimensions, add convexity for larger moves, and compare the approximation with full revaluation. Failed buckets remain unknown rather than becoming zero.

## Key Takeaways

- Modified duration expresses first-order percentage sensitivity.
- DV01 converts it into currency PnL for a 1bp move.
- Convexity explains an important part of large-move linear error.
- Yield DV01, curve DV01, key-rate DV01 and CS01 are different contracts.
- Full revaluation is the benchmark; approximations are fast diagnostics.
- Units, settlement basis, lineage, completeness and failure semantics matter as much as the number.
- Signed curve-tenor risk improves hedging conversations and PnL explain.