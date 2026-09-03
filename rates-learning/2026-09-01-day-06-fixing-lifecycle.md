# From Projected Forward to Fixed Cash Flow: Engineering the Fixing Lifecycle

## Abstract

A floating coupon changes state when its reference rate is published: before fixing it is curve-projected; afterwards it is a known contractual cash flow. This transition affects PV, projection risk, settlement processing, and PnL explain. This article develops the lifecycle numerically and designs explicit handling for publication timing, missing data, corrections, and lineage.

## Desk Context

A trader reports that a receive-floating coupon fixed 30bp above the prior forward, yet fixing PnL is zero. Possible causes include a missing observation, stale cache, wrong fixing date, incorrect index mapping, or explain endpoints using the same fixing state.

## Coupon Lifecycle

[
Coupon=N(L+s)\alpha
]

Before fixing, (L) is unknown and the coupon uses projected forward (F):

[
ProjectedCoupon=N(F+s)\alpha
]

After publication:

[
FixedCoupon=N(L_{obs}+s)\alpha
]

The fixed amount no longer depends on the projection curve, although discount risk remains until payment. After settlement, the cash flow leaves future PV and enters cash accounting.

Accrual dates, fixing date, publication timestamp, and payment date are distinct. A valuation on the fixing date may still precede publication.

## Worked Example

Consider a receive-floating coupon with GBP 20,000,000 notional, 0.25 accrual fraction, prior forward 4.20%, observed fixing 4.50%, and payment discount factor 0.995.

[
ProjectedCF=20{,}000{,}000\times0.042\times0.25
=GBP\ 210{,}000
]

[
FixedCF=20{,}000{,}000\times0.045\times0.25
=GBP\ 225{,}000
]

[
FixingPnL\approx(225{,}000-210{,}000)\times0.995
=+GBP\ 14{,}925
]

Before fixing, approximate forward sensitivity is:

[
20{,}000{,}000\times0.25\times0.0001\times0.995
=GBP\ 497.50/bp
]

After fixing, that projection sensitivity should be near zero. Discount sensitivity remains.

## Isolating Fixing PnL

```text
S0: prior positions + prior curves + fixing projected
S1: same positions + current curves + fixing still projected
S2: same positions + current curves + observed fixing applied
```

[
MarketPnL=PV(S1)-PV(S0)
]

[
FixingPnL=PV(S2)-PV(S1)
]

This isolates the projected-to-observed replacement under the same current curves.

## Engineering Contract

```python
@dataclass(frozen=True)
class FixingObservation:
    index_id: str
    fixing_date: date
    value: Decimal | None
    unit: Literal["DECIMAL_RATE"]
    status: Literal[
        "PUBLISHED", "MISSING", "PRELIMINARY", "CORRECTED"
    ]
    source: str
    published_at: datetime | None
    received_at: datetime
    version: int
    supersedes_version: int | None
```

```python
@dataclass(frozen=True)
class FloatingCouponState:
    trade_id: str
    coupon_id: str
    fixing_date: date
    payment_date: date
    state: Literal["PROJECTED", "FIXED", "SETTLED"]
    applied_rate: Decimal
    rate_source: str
    fixing_version: int | None
    cashflow_amount: Decimal
```

```python
def resolve_coupon_rate(coupon, as_of, curves, fixings, policy):
    if as_of < coupon.expected_publication_time:
        return ProjectedRate(
            value=curves.projection.forward_rate(
                coupon.accrual_start, coupon.accrual_end
            ),
            reason="NOT_YET_PUBLISHED",
        )

    fixing = fixings.latest(coupon.index_id, coupon.fixing_date)

    if fixing and fixing.status in {"PUBLISHED", "CORRECTED"}:
        return ObservedRate(fixing.value, fixing.version)

    if policy.missing_fixing == "HARD_FAIL":
        raise MissingFixingError(coupon.id)

    return ProjectedRate(
        value=curves.projection.forward_rate(
            coupon.accrual_start, coupon.accrual_end
        ),
        reason="MISSING_FIXING_FALLBACK",
        degraded=True,
    )
```

Indicative pricing may allow a labelled fallback; official PnL may require hard failure. The policy must be explicit.

## Controls and Tests

Controls should validate index identity, fixing calendar, publication timezone, source, version, correction lineage, and coupon state. Fixed coupons must stop reading projection rates, and settled coupons must leave future cash flows.

```python
def test_fixed_coupon_ignores_forward_bump():
    base = price(fixed_coupon, base_curves)
    bumped = price(fixed_coupon, bumped_projection_curve)
    assert abs(bumped-base) < tolerance

def test_missing_published_fixing_is_visible():
    result = resolve_after_publication_without_fixing()
    assert result.status in {"FAILED", "DEGRADED"}

def test_receive_float_fixing_pnl_sign():
    assert fixing_pnl(observed=0.045, projected=0.042) > 0
```

## Production Failure Modes

1. Missing official fixing silently replaced by a projection.
2. Publication timezone interpreted incorrectly.
3. Holiday calendar produces the wrong fixing date.
4. Stale cache continues serving the old value.
5. Official correction does not trigger revaluation.
6. Trade index alias fails to match the fixing-store key.
7. Projection risk remains after fixing.
8. Paid cash flow is double counted in PV and cash PnL.
9. Correction overwrites history and breaks reproducibility.
10. Distributed workers apply inconsistent fixing versions.

## Requirement Discovery

Clarify index and fixing date, official versus preliminary status, valuation cut relative to publication, missing-data behavior, official-PnL fallback policy, correction reruns, fixing-component separation, coupon-level drill-down, and dashboard statuses.

```yaml
fixing_policy:
  accepted_statuses: [PUBLISHED, CORRECTED]
  before_publication: use_projection
  missing_after_publication: hard_fail
  preserve_versions: true
explain:
  separate_fixing_component: true
risk:
  projection_risk_after_fixing: near_zero
dashboard:
  show_status_and_source: true
```

## Interview Prompts

- What changes when a floating coupon fixes?
- Why can fixing PnL differ from the raw cash-flow difference?
- Which risk rolls off after fixing and which remains?
- How should missing differ from not-yet-published?
- Why must fixing corrections be versioned?
- When is a projected fallback acceptable?

## Key Takeaways

- Before fixing, a floating coupon is projected; after fixing, its amount is contractual.
- Observed-minus-prior-forward drives fixing PnL after direction, accrual, notional, and discounting.
- Projection risk rolls off after fixing; discount risk remains until payment.
- Fixing date and publication timestamp are different controls.
- Missing, preliminary, published, and corrected are distinct states.
- Corrections require immutable versions and historical lineage.
- An unlabelled forecast fallback can create plausible but wrong official PnL.

*All examples are simplified, generic, and for educational purposes only. They do not constitute investment advice.*
