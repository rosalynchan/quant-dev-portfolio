# Engineering a Bond PnL Explain: Rates, Spread, Carry and Data Effects

## Abstract

A bond PnL explain is more than DV01 multiplied by a yield move. A credible bridge separates risk-free curve movement, credit spread, carry, roll-down, accrued interest, cash, activity, FX and data or model changes. This article shows how to construct that bridge as a reproducible sequence of counterfactual valuations, use DV01 and CS01 as diagnostics, and design the controls needed to distinguish economic residuals from production failures.

## Desk Context

A GBP corporate-bond position reports close-to-close PnL of -GBP 126,000. The trader expects a government-curve rally to help, spread widening to hurt and carry to be positive. The dashboard shows only “market PnL: -GBP 121,000.”

A developer needs to establish whether:

- rates and spread effects use the frozen opening position;
- the curve and spread transitions follow an approved order;
- actual and explained PnL share a clean or dirty basis;
- accrued interest and coupon cash are double-counted;
- a price source, benchmark or settlement convention changed;
- the residual is convexity or cross-effect, or a data-quality failure.

## The Bond PnL Bridge

A generic bridge is:

$$
TotalPnL=
Rates+Spread+Time+Accrual+Cash+Activity+FX+Model/Data+Residual
$$

Rates PnL captures risk-free or government-curve movement. Spread PnL captures credit-spread movement. Time includes carry, ageing and roll-down. Accrual captures the change in accrued coupon when reported separately. Cash contains coupons, principal and settlements. Activity isolates changes in position population. Model/Data covers methodology, benchmark, reference-data and price-source changes.

Desk conventions differ. Some combine accrual with carry; others embed it in dirty-value movement. Component labels are meaningful only when tied to a methodology version.

## Approximation Versus Full Revaluation

First-order checks are useful:

$$
RatesPnL\approx CurveDV01\times CurveMove
$$

$$
SpreadPnL\approx CS01\times SpreadMove
$$

With signed risk, a long bond normally has negative curve DV01 and CS01. A rally is a negative rate move and therefore creates positive rate PnL; spread widening is a positive spread move and creates negative spread PnL.

These calculations are diagnostics, not complete official explain. Full revaluation can capture convexity, curve shape, spread-curve shape, cross-effects and optionality.

## Worked Example

Assume the opening risk and market moves are:

- Curve DV01: -GBP 6,000/bp
- CS01: -GBP 4,000/bp
- Government-curve move: -8bp
- Spread move: +15bp
- Carry and accrual: +GBP 9,000
- Coupon cash: +GBP 20,000
- Activity: -GBP 2,000
- Actual total PnL: -GBP 126,000

The rate estimate is:

$$
(-6,000)\times(-8)=+GBP\ 48,000
$$

The spread estimate is:

$$
(-4,000)\times15=-GBP\ 60,000
$$

Linear explained PnL is:

$$
48-60+9+20-2=+GBP\ 15,000
$$

The residual is -GBP 141,000. That is too large to dismiss as ordinary convexity.

Investigation finds that the risk feed covered GBP 10 million face while the actual position was GBP 30 million. Corrected risks are -GBP 18,000/bp and -GBP 12,000/bp:

$$
RatesPnL=+GBP\ 144,000
$$

$$
SpreadPnL=-GBP\ 180,000
$$

The corrected explained amount is -GBP 9,000, leaving -GBP 117,000.

The closing evaluated price also fell by 0.39 points because of a source-methodology change:

$$
30,000,000\times\frac{-0.39}{100}
=-GBP\ 117,000
$$

The bridge now reconciles:

$$
-126=144-180+9+20-2-117
$$

The important lesson is operational: a large residual often identifies scope, units, source or lineage problems. “Markets are nonlinear” is not a sufficient explanation.

## Counterfactual Valuation States

A reproducible engine stores states, not only component numbers:

\`\`\`text
S0: opening position + opening curves
    + opening spreads + opening time

S1: opening position + closing risk-free curves
    + opening spreads + opening time

S2: opening position + closing curves
    + closing spreads + opening time

S3: opening position + closing market
    + closing time

S4: closing position + closing market
    + closing time

S5: apply model, reference-data
    and price-source changes
\`\`\`

Each component is the PV difference between adjacent states. Rates is S1 minus S0; spread is S2 minus S1; time is S3 minus S2; activity is S4 minus S3; model/data is S5 minus S4.

The order matters. Applying spread first and rates second may allocate cross-effects differently. Total PnL can agree while component attribution differs. Transition order and cross-effect policy must therefore be versioned.

## Clean Price, Dirty Price, Accrual and Cash

Because:

$$
DirtyPrice=CleanPrice+AccruedInterest
$$

a bridge comparing dirty actual PnL with clean-price market moves must explain accrued-interest movement separately.

Coupon dates are especially dangerous. Accrued interest resets, a cash coupon is paid and future PV changes. Without explicit state and cash policies, one event can be counted twice or omitted.

A requirement must state the price basis, accrual treatment, cash sign, settlement date, ex-coupon convention and coupon entitlement.

## Engineering Design

\`\`\`python
@dataclass(frozen=True)
class BondValuationState:
    state_id: str
    position_snapshot_id: str
    curve_snapshot_id: str
    spread_snapshot_id: str
    price_snapshot_id: str

    valuation_time: datetime
    settlement_date: date

    reference_data_version: str
    model_version: str
    dirty_pv: Decimal
\`\`\`

\`\`\`python
@dataclass(frozen=True)
class BondPnLComponent:
    run_id: str
    position_id: str
    component: Literal[
        "RATES", "SPREAD", "TIME",
        "ACCRUAL", "CASH", "ACTIVITY",
        "FX", "MODEL_DATA", "RESIDUAL",
    ]

    from_state_id: str
    to_state_id: str
    pnl: Decimal | None
    currency: str
    status: Literal["SUCCESS", "FAILED"]
    method_version: str
\`\`\`

\`\`\`python
def explain_bond_pnl(open_ctx, close_ctx, policy):
    states = build_ordered_states(
        open_context=open_ctx,
        close_context=close_ctx,
        transitions=policy.transition_order,
    )

    components = [
        component_from_transition(before, after, label, policy)
        for before, after, label in adjacent(states)
    ]

    require_all_success(components)

    total = close_ctx.total_value - open_ctx.total_value
    explained = sum(c.pnl for c in components)
    residual = total - explained

    return {
        "total": total,
        "components": components,
        "residual": residual,
    }
\`\`\`

DV01 and CS01 checks should remain parallel diagnostics:

\`\`\`python
def linear_market_check(risk, moves):
    return {
        "rates": risk.curve_dv01 * moves.curve_move_bp,
        "spread": risk.cs01 * moves.spread_move_bp,
    }
\`\`\`

They should never overwrite the full-revaluation component.

## Data Quality and Production Controls

A robust bridge requires:

- frozen opening population for market effects;
- complete quantity and face-amount coverage;
- aligned curve, spread, price and FX cuts;
- explicit clean or dirty basis;
- exactly-once treatment of coupon cash and accrued reset;
- continuous from/to state lineage;
- consistent currency, sign and units;
- failure represented as unknown, not zero;
- total equal to explained plus residual;
- absolute and relative residual thresholds;
- explicit price-source and benchmark-change events.

Useful tests include:

\`\`\`python
def test_bridge_reconciles():
    result = explain_bond_pnl(open_ctx, close_ctx)
    assert_close(
        result.total,
        sum(result.components) + result.residual,
    )

def test_coupon_is_not_double_counted():
    result = explain_coupon_date_pnl()
    assert count_cashflow_effect(result, coupon_id) == 1

def test_partial_coverage_is_not_complete():
    result = explain_with_missing_positions()
    assert result.status != "SUCCESS"
    assert result.coverage_ratio < 1
\`\`\`

Operational metrics should cover run age, position coverage, component failures, residual amount and ratio, source changes, population differences and cash reconciliation.

## Common Failure Modes

1. Risk covers only part of the position quantity.
2. Actual PnL uses dirty value while explain uses clean price.
3. Coupon cash is counted in both PV movement and cash.
4. Accrual is omitted when clean and dirty measures are compared.
5. Fresh curves are combined with stale spreads or prices.
6. Desk and accounting sign conventions are mixed.
7. Transition order changes without a method-version change.
8. A price-source jump is hidden inside spread PnL.
9. Benchmark remapping is treated as genuine spread movement.
10. A failed component is reported as zero.
11. Early rounding creates a large book residual.
12. FX is counted in both local PnL and reporting-currency conversion.
13. A late trade feed makes the closing population incomplete.
14. A call, redemption or amortisation event is missing.

## Requirement Discovery

When a trader asks to “explain bond PnL,” clarify:

- official close-to-close or intraday;
- frozen opening or closing population;
- government, swap or discount curve for rates;
- G-spread, Z-spread, OAS or spread curve;
- full revaluation or risk approximation;
- separate carry, roll-down and accrual;
- treatment of cash, fees, activity and FX;
- clean or dirty basis;
- explicit price-source changes;
- transition order and cross-effect policy;
- residual tolerance;
- publication policy for partial results.

A strong desk response is:

> I will freeze the opening population, separate risk-free curve, spread, time, accrual, cash and source effects, use DV01 and CS01 as diagnostics, and preserve every state transition. Failed or missing components remain unknown, and the residual stays visible.

## Key Takeaways

- Bond PnL is multi-dimensional; yield movement alone is insufficient.
- DV01 and CS01 are fast diagnostics, while full revaluation is the attribution benchmark.
- Counterfactual states make components reproducible and auditable.
- Clean/dirty, accrual and coupon cash require an explicit exactly-once policy.
- Large residuals should trigger scope, units, snapshot and source-lineage checks.
- Transition order is methodology and must be versioned.
- Coverage and failure semantics matter as much as numerical reconciliation.