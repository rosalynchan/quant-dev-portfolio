# Engineering a Reproducible Daily PnL Explain

## Abstract

Daily PnL explain is a controlled bridge between two valuations. Its purpose is not merely to make component numbers add up, but to isolate market movement, time, trade activity, cash, fixings, and other state changes using reproducible counterfactual valuations. This article presents a numerical bridge and an engineering design that preserves ordering, lineage, completeness, and residual diagnostics.

## Desk Context

A GBP Rates book moves from GBP 2.40 million at the prior official close to GBP 2.29 million today, producing negative GBP 110,000 of PnL. The trader estimates that rates explain roughly GBP 80,000 and asks where the remainder came from.

The investigation must align scope, position population, valuation cuts, curves, fixings, sign, and reporting currency before interpreting components.

## Total PnL and Explained PnL

[
Total\ PnL=PV_{close}-PV_{open}
]

A practical bridge is:

[
Total=
Market+Carry+Activity+Cash+Fixing+FX+Model/Data+Residual
]

Market PnL should normally hold the opening population fixed while replacing opening market data with closing market data:

[
MarketPnL=PV(P_{open},M_{close})-PV(P_{open},M_{open})
]

This prevents new trades, cancellations, amendments, and population-feed differences from contaminating the market component.

## Worked Numerical Bridge

Opening PV is GBP 2,400,000 and closing PV is GBP 2,290,000:

[
TotalPnL=-GBP\ 110k
]

| Component | PnL |
|---|---:|
| Market move | -GBP 84k |
| Carry/theta | +GBP 12k |
| New trades | +GBP 35k |
| Amendments | -GBP 8k |
| Cash/settlements | -GBP 50k |
| Fixings | -GBP 10k |

Explained PnL is:

[
-84+12+35-8-50-10=-GBP\ 105k
]

Residual is:

[
-110-(-105)=-GBP\ 5k
]

The bridge identifies market movement and settlements as the main losses, partly offset by new trades and carry. The remaining negative GBP 5,000 is a diagnostic amount to compare with tolerance.

Suppose bucketed DV01 multiplied by market moves predicts negative GBP 81,000 while full revaluation market PnL is negative GBP 84,000. The negative GBP 3,000 difference may reflect convexity, cross-curve effects, or bucket approximation. This is an internal market-explain residual, distinct from the residual of the complete daily bridge.

## Explain as Counterfactual Valuation States

A reproducible engine stores state transitions:

```text
S0: opening positions + opening market + opening time
S1: opening positions + closing market + opening time
S2: opening positions + closing market + closing time
S3: closing positions + closing market + closing time
S4: cash, fixing, FX, and model-data adjustments
```

Each component is:

[
Component_i=PV(S_{i+1})-PV(S_i)
]

Some effects are path-dependent. Moving market first and rolling time second may allocate cross-effects differently from the reverse order. The explain method and component order must therefore be versioned.

## Engineering Design

```python
@dataclass(frozen=True)
class ValuationState:
    state_id: str
    position_snapshot_id: str
    market_snapshot_id: str
    fixing_set_id: str
    model_version: str
    valuation_time: datetime
    pv: Decimal

@dataclass(frozen=True)
class ExplainComponent:
    run_id: str
    book_id: str
    component: str
    from_state_id: str
    to_state_id: str
    pnl: Decimal | None
    currency: str
    status: Literal["SUCCESS", "FAILED", "NOT_APPLICABLE"]
    method_version: str
```

```python
def explain_pnl(open_ctx, close_ctx, policy):
    states = build_counterfactual_states(
        open_ctx=open_ctx,
        close_ctx=close_ctx,
        ordered_steps=policy.component_order,
    )

    components = []
    for before, after, label in adjacent_transitions(states):
        components.append(ExplainComponent(
            run_id=policy.run_id,
            book_id=open_ctx.book_id,
            component=label,
            from_state_id=before.id,
            to_state_id=after.id,
            pnl=after.pv-before.pv,
            currency=policy.reporting_currency,
            status="SUCCESS",
            method_version=policy.version,
        ))

    total = close_ctx.pv-open_ctx.pv
    explained = sum(x.pnl for x in components)
    return PnLExplain(total, components, total-explained)
```

State identifiers turn a component into an auditable transition rather than an untraceable number.

## Controls and Observability

Controls should require consistent scope, currency, sign, valuation cuts, position hashes, and curve versions. State transitions must be continuous, components must not be applied twice, and a failed calculation must remain unknown rather than becoming zero.

Cash handling deserves special attention: if the valuation naturally removes a paid cash flow and the bridge also subtracts the settlement, the result is double counted.

```python
assert states[0].pv == opening_pv
assert states[-1].pv == reconstructed_closing_pv
assert abs(total_pnl - explained_pnl - residual) < Decimal("0.01")
assert all_transition_ids_are_continuous(components)
```

Useful metrics include explain age, coverage ratio, residual amount and ratio, component failures, population differences, and top unexplained trades.

## Production Failure Modes

1. Market PnL includes intraday trade activity.
2. Cash is removed through valuation and subtracted again.
3. Accounting and desk sign conventions are mixed.
4. Opening and closing sides use inconsistent fixing cuts.
5. Component order changes without a method-version change.
6. Failed components appear as zero and the explain looks complete.
7. A transition mixes market or curve snapshots.
8. A late trade feed makes the closing population incomplete.
9. Residual is forcibly assigned to a large component.
10. Trade-level rounding accumulates into a material book residual.

## Requirement Discovery

For “explain today's PnL,” clarify:

- close-to-close or close-to-live;
- official, flash, or intraday result;
- book scope, currency, and sign perspective;
- whether market PnL freezes the opening population;
- whether activity separates new, cancelled, and amended trades;
- separate cash, fees, fixings, FX, carry, and model-data components;
- absolute and relative residual thresholds;
- book, curve, tenor, or trade-level drill-down;
- whether partial results are allowed and how they are marked.

```yaml
window: official_close_to_close
market_component:
  population: frozen_opening
activity_components: [new_trades, cancellations, amendments]
separate_components: [carry, cash, fixings, fx, model_data]
reporting_currency: GBP
residual_tolerance:
  absolute: 10000
granularity: [book, component, trade]
failure_policy:
  failed_as_zero: false
lineage:
  include_state_ids: true
```

## Interview Prompts

- Why should market PnL use a frozen opening population?
- What is the difference between actual and explained PnL?
- Why can explain order affect component allocation?
- How would you prevent settlement double counting?
- Is residual necessarily a pricing-model error?
- How should partial explain results appear in an API?

Strong answers connect counterfactual states, immutable snapshots, population control, ordering, completeness, and diagnostic residuals.

## Key Takeaways

- Total PnL measures change; explain attributes causes.
- Market PnL should isolate market movement on a frozen population.
- Activity, cash, fixing, time, FX, and model-data changes require explicit components.
- Explain is an ordered series of counterfactual valuations.
- Every component should preserve state lineage and method version.
- Failed is not zero, and residual is a diagnostic rather than an automatic model-error label.

*All examples are simplified, generic, and for educational purposes only. They do not constitute investment advice.*
