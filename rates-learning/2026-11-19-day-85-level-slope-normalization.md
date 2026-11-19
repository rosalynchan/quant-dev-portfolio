# Level and Slope Risk: The Factor-of-Two Trap

## Abstract

Two-tenor curve risk can be expressed as sensitivity to a common rate move and sensitivity to a change in the long-minus-short spread. The transformation is simple, but its normalization matters: moving each end by one basis point in opposite directions changes the spread by two basis points. This article derives a transparent level-and-slope convention, reconciles it to bucketed PnL, and shows how a small semantic mismatch can double a dashboard's scenario result.

## The desk problem

A trader asks for the book's “one-basis-point steepener risk.” One report shows minus GBP 5,000, while another shows minus GBP 10,000. Both calculations may be arithmetically consistent. They may simply define one unit of steepening differently.

Yesterday's lesson established that zero total DV01 does not eliminate curve-shape exposure. Today's task is not to repeat that warning. It is to build a precise vocabulary for the remaining exposure, so a trader and developer can agree on a risk number before discussing a hedge.

We use two specified quote factors, two-year and ten-year, on one curve. Reporting currency is GBP, FX is frozen, and all sensitivities are signed. Positive sensitivity means a PV gain for a positive rate move. This is a deterministic coordinate transformation, not principal-component analysis or a statistical prediction of market behavior.

## Define the coordinates

Let $s_2$ and $s_{10}$ be scenario quote changes, measured numerically in basis points. Define the level move $L$ as their average and the slope move $S$ as long-end change minus short-end change:

$$
L = (s_2+s_{10})/2
$$

$$
S = s_{10}-s_2
$$

This convention makes one basis point of slope mean exactly one basis point of change in the ten-year-minus-two-year spread. Holding level fixed, that requires the short end to fall by half a basis point and the long end to rise by half a basis point.

The original shocks can be recovered without information loss:

$$
s_2=L-S/2,\qquad s_{10}=L+S/2
$$

A one-basis-point level move is different: both rates rise by one basis point, leaving the spread unchanged. The definition of level as an average does not mean that each rate moves by half a basis point.

These choices are conventions. Another system can use a different scaling, but the scaling must travel with the values. A label such as “slope01” cannot establish its own unit.

## Transform the sensitivities, not only the shocks

Let $d_2$ and $d_{10}$ be signed quote sensitivities in GBP per basis point. The familiar linear PnL is the sum of each sensitivity multiplied by its corresponding quote move.

Substituting the reconstructed shocks gives:

$$
P_{lin}=(d_2+d_{10})L+\frac{d_{10}-d_2}{2}S
$$

Therefore level sensitivity is the sum of bucket sensitivities, while slope sensitivity under our spread-unit convention is half the long-minus-short sensitivity difference.

The division by two is not a cosmetic reporting adjustment. It follows from the shock definition: one unit of spread change is shared between the two ends when average level is held fixed.

If a system instead defines its steepener unit as short minus one and long plus one, its scenario unit widens the spread by two basis points. The corresponding result is twice our per-spread-basis-point sensitivity. Neither convention is inherently invalid; comparing them without normalization is invalid.

## Worked example: reconcile both representations

Assume the following synthetic risk vector:

| Quote factor | Signed risk, GBP/bp |
| --- | ---: |
| Two-year | +6,000 |
| Ten-year | -4,000 |

Level sensitivity is GBP 2,000 per basis point of common movement. Slope sensitivity is minus GBP 5,000 per basis point of spread widening at fixed average level.

Now shock the two-year quote by minus three basis points and the ten-year quote by plus five basis points. The average move is plus one basis point; the spread widens by eight basis points.

The bucket calculation gives minus GBP 18,000 at the short end and minus GBP 20,000 at the long end, totaling minus GBP 38,000.

The transformed calculation gives positive GBP 2,000 of level contribution and negative GBP 40,000 of slope contribution. The total is again minus GBP 38,000.

The components changed because the explanatory coordinates changed. The total linear PnL did not. This is a basis-change invariant, not evidence that one explanation is uniquely the economic truth.

For the normalization test, use zero level and a one-basis-point slope move. The actual quote shocks are minus 0.5 and plus 0.5, giving minus GBP 5,000. Using minus one and plus one instead gives minus GBP 10,000 because the spread move is two basis points.

## A compact implementation and its strongest test

The engineering contract should name the coordinates and explicitly state that slope units are basis points of long-minus-short spread at fixed average level. Persist the factor pair in order; swapping short and long reverses slope signs.

```python
from decimal import Decimal

def level_slope(d_short, d_long, s_short, s_long):
    two = Decimal("2")
    level_move = (s_short + s_long) / two
    slope_move = s_long - s_short
    level_risk = d_short + d_long
    slope_risk = (d_long - d_short) / two
    level_pnl = level_risk * level_move
    slope_pnl = slope_risk * slope_move
    bucket_pnl = d_short * s_short + d_long * s_long
    assert bucket_pnl == level_pnl + slope_pnl
    return {
        "level_risk": level_risk,
        "slope_risk_per_spread_bp": slope_risk,
        "level_pnl": level_pnl,
        "slope_pnl": slope_pnl,
        "total_pnl": bucket_pnl,
    }

result = level_slope(*map(Decimal, ["6000", "-4000", "-3", "5"]))
```

This function transforms a supplied linear risk model. It neither computes bucket risks from a pricer nor performs full revaluation. If bucket inputs are finite-bump estimates, the approximation already exists upstream.

Test pure level, pure slope, and mixed scenarios, plus reconstruction of both original shocks. For floating-point implementations use an explicit tolerance. Matching bucket and transformed PnL should be a required invariant, not a visual spot-check.

## Four selective production controls

1. Version the normalization convention with the risk result. Do not let a UI label silently change the scenario unit.
2. Preserve ordered factor identity: curve, quote identifiers, short tenor, and long tenor.
3. Enforce basis-point units on both coordinates. Decimal rate changes require conversion before this calculation.
4. Keep coordinate reconciliation separate from pricing accuracy. Exact linear reconciliation does not imply agreement with full revaluation for a large move.

The dashboard should show the actual two quote shocks beside the level and slope coordinates. That small addition often resolves a disagreement faster than another risk-engine run.

## Requirement discovery and key takeaways

Ask: “Does one basis point mean one basis point of spread widening, or one basis point at each end? What remains fixed? Which two quote factors define the spread?”

A precise acceptance criterion is: zero level and positive one spread basis point map to short minus 0.5 and long plus 0.5; the example returns minus GBP 5,000; all mixed scenarios reconcile to the original bucket calculation.

Level and slope are useful explanatory coordinates, not new sources of PnL. Declare their scaling, transform sensitivities consistently, and preserve the original factor pair. All examples here are synthetic, public-safe, and educational, with no proprietary information or investment advice.
