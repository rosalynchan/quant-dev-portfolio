# From One Curve to Many: Projection, Discounting and Basis Risk

## Abstract

Production swap pricing separates two questions: what will a floating coupon be, and what is that future cash flow worth today? Projection curves answer the first; discount curves answer the second. This article develops the multi-curve intuition with a numerical example and shows how a quant developer can model curve sets, calculate curve-specific risk, prevent mixed-snapshot failures and translate ambiguous trader requests into testable requirements.

## Desk Context

A trader reports that a swap par rate barely changed while PV moved by GBP 40,000:

> “Did discounting move, or is the pricer wrong?”

A single total DV01 cannot answer this. The investigation needs curve-family attribution: projection, discounting and any cross-curve residual, all calculated on a consistent position population and market-data cut.

## Projection and Discounting Are Different Jobs

For an unfixed floating coupon:

[
FloatingCF_i=N(F_i+s)alpha_i
]

The forward (F_i) comes from an index-specific **projection curve**. It estimates the future contractual rate.

The cash flow is then discounted:

[
PV_i=FloatingCF_i	imes DF(t_i)
]

The discount factor comes from the **discount curve**. It converts a future amount into present value.

Therefore:

[
PV_{float}=Nsum_i(F_i+s)alpha_iDF(t_i)
]

A single-curve model uses one curve for both jobs. It remains useful for intuition, but production systems normally make the curve set explicit because collateral context, reference indices, basis spreads and hedge instruments differ.

## Worked Example

Consider a simplified receive-floating leg:

- Notional: GBP 10 million
- Two semi-annual periods
- Accrual fraction: 0.5 for each period
- Projected forwards: 4.00% and 4.20%
- Discount factors: 0.980 and 0.955
- Spread: zero
- Both coupons are unfixed

The first cash flow and PV are:

[
CF_1=10{,}000{,}000	imes0.0400	imes0.5
=GBP 200{,}000
]

[
PV_1=200{,}000	imes0.980=GBP 196{,}000
]

The second cash flow and PV are:

[
CF_2=10{,}000{,}000	imes0.0420	imes0.5
=GBP 210{,}000
]

[
PV_2=210{,}000	imes0.955=GBP 200{,}550
]

Total floating-leg PV is GBP 396,550.

If both projected forwards rise by 1bp:

[
ProjectionDV01
=
10{,}000{,}000	imes0.5	imes0.0001
	imes(0.980+0.955)
]

[
ProjectionDV01=+GBP 967.50/bp
]

Now keep forwards unchanged but move discount factors to 0.9798 and 0.9546:

[
PV'_{float}
=
200{,}000	imes0.9798
+
210{,}000	imes0.9546
=
GBP 396{,}426
]

Discounting PnL is:

[
396{,}426-396{,}550=-GBP 124
]

Projection changes alter expected cash-flow amounts. Discount changes alter the present value of those cash flows. A production explain should preserve that distinction.

## Multi-Curve Par Rate

For a receive-fixed swap:

[
PV_{swap}
=
NKsum_ialpha_iDF_i
-
Nsum_jF_jalpha_jDF_j
]

Setting PV to zero gives:

[
K_{par}
=
rac{sum_jF_jalpha_jDF_j}
{sum_ialpha_iDF_i}
]

The par rate therefore depends on projected forwards, discount factors, both schedules, accrual conventions and known fixings. A wrong par rate may be caused by curve mapping or coupon state, not only by a bad displayed quote.

## Basis Risk

Basis is the relative movement between related rate or curve families. Consider:

| Curve family | Signed DV01 |
|---|---:|
| Projection | +GBP 25k/bp |
| Discount | -GBP 24k/bp |
| Net total | +GBP 1k/bp |

The net number appears small, but gross curve exposure is large. If projection and discount curves move relative to each other, PnL can be material.

A useful risk view therefore includes net and gross exposure, curve family, index, tenor, leg and scenario definition.

## Engineering the Curve Set

```python
@dataclass(frozen=True)
class CurveRef:
    curve_id: str
    version: str
    purpose: Literal["DISCOUNT", "PROJECTION"]
    currency: str
    index_id: str | None
    market_snapshot_id: str


@dataclass(frozen=True)
class CurveSet:
    curve_set_id: str
    discount_curve: CurveRef
    projection_curves: dict[str, CurveRef]
    collateral_context_id: str
    mapping_version: str
```

Pricing should resolve the projection curve by index and use one explicit discount curve:

```python
def price_floating_leg(trade, curve_set, fixings, as_of):
    projection = curve_set.projection_curves[
        trade.float_index
    ]
    discount = curve_set.discount_curve
    pv = Decimal("0")

    for coupon in build_float_schedule(trade):
        if coupon.is_fixed(as_of):
            rate = fixings.require(
                trade.float_index,
                coupon.fixing_date,
            )
        else:
            rate = projection.forward_rate(
                coupon.accrual_start,
                coupon.accrual_end,
            )

        cashflow = (
            trade.notional
            * (rate + trade.float_spread)
            * coupon.accrual_fraction
        )
        pv += cashflow * discount.df(
            coupon.payment_date
        )

    return pv
```

Curve-specific bump-and-revalue risk can be calculated by changing one curve at a time while holding the remaining curve set fixed:

```python
def curve_family_risk(trade, curve_set):
    base_pv = price(trade, curve_set)
    results = []

    for curve in curve_set.all_curves():
        bumped = bump_one_curve(
            curve_set=curve_set,
            curve_id=curve.curve_id,
            bp=Decimal("1"),
        )
        results.append({
            "curve_id": curve.curve_id,
            "purpose": curve.purpose,
            "index_id": curve.index_id,
            "signed_pv_change": (
                price(trade, bumped) - base_pv
            ),
        })

    return results
```

The risk contract must state whether the bump applies to zero nodes or market quotes, whether the curve is rebuilt, and whether the scenario is parallel or bucketed.

## Controls and Tests

Key controls include:

- exactly one projection curve for every floating index;
- a discount curve consistent with currency and collateral context;
- a single market-data cut across all curve-set members;
- immutable curve IDs, versions and mapping version;
- no projection of already fixed coupons;
- explicit curve purpose, index, tenor, bump and currency in risk results;
- no silent fallback to an arbitrary default curve;
- par-trade repricing near zero under the same curve set;
- reconciliation between total risk and curve-family buckets.

Business-invariant tests:

```python
def test_projection_bump_changes_unfixed_coupon():
    assert (
        price(unfixed_trade, bumped_projection)
        != price(unfixed_trade, base_curves)
    )

def test_projection_bump_does_not_change_fixed_coupon():
    assert_close(
        price(fixed_coupon, bumped_projection),
        price(fixed_coupon, base_curves),
    )

def test_discount_bump_affects_both_legs():
    result = discount_curve_risk(swap)
    assert result.fixed_leg != 0
    assert result.floating_leg != 0
```

Operational metrics should cover curve-set version usage, mapping failures, mixed-snapshot rejections, missing projection curves, basis risk by curve pair, reconciliation error and fallback usage.

## Production Failure Modes

1. Wrong floating-index mapping.
2. Discount and projection curves reversed during API transformation.
3. Live discount curve combined with a prior-close projection curve.
4. Missing mapping silently replaced by a currency default.
5. Fixed coupons incorrectly reprojected.
6. Material basis risk hidden by net total DV01.
7. Cache keys missing collateral context or mapping version.
8. A partial curve rebuild published as a complete curve set.
9. Pricing and risk using different curve-set versions.
10. The same market quote shocked twice across linked curve scenarios.

## Requirement Discovery

When a trader asks for curve risk, clarify:

- Which curve families and indices are in scope?
- What collateral or discounting context applies?
- Should risk be grouped by curve, tenor, leg or trade?
- Are both net and gross exposures required?
- Are market quotes or internal zero nodes bumped?
- Are curves bumped separately or through basis scenarios?
- Have fixed coupons rolled off projection risk?
- Is the curve set live, close or historical?
- Does a missing curve hard-fail or produce a degraded result?

A clear requirement translation is:

```yaml
population: frozen_opening

curve_set:
  projection_index: specified_trade_index
  discounting_context: collateralized
  require_single_market_cut: true

pnl_components:
  - projection_curve_move
  - discount_curve_move
  - cross_curve_residual

risk_output:
  dimensions:
    - curve_family
    - index
    - tenor
    - leg
    - trade
  show_net_and_gross: true

failure_policy:
  missing_curve_as_zero: false
  hidden_default_fallback: false
```

## Interview Questions

1. What is the difference between projection and discounting?
2. Why can a book with small total DV01 still have material basis risk?
3. What happens to projection and discount risk after a coupon fixes?
4. How would you ensure pricing and risk use a consistent curve set?
5. Which metadata is required to reproduce multi-curve valuation?

Strong answers should connect cash-flow projection, present-value discounting, fixing state, gross versus net risk, explicit index mapping, collateral context, versioned snapshots and controlled failure semantics.

## Key Takeaways

- Projection curves determine unfixed floating coupons.
- Discount curves value every future cash flow.
- A multi-curve par rate depends on both projection and discounting inputs.
- Net DV01 can hide large offsetting basis exposures.
- Curve sets should be immutable, versioned and aligned to one market-data cut.
- A front-office developer should translate “curve risk” into curve family, index, collateral context, bump definition, aggregation and failure policy.
