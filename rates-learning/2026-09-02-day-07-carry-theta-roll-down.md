# Carry, Theta and Roll-Down on a Rates Desk

## Abstract

A Rates position can generate PnL even when the visible market barely moves. Time changes accrual, remaining maturity, fixing state, cash-flow population and the point at which a trade sits on the curve. This article explains carry, theta and roll-down through a practical swap example, then shows how to implement a reproducible time-PnL calculation with explicit curve-roll conventions, lineage and production controls.

## Desk Context

A trader sees a GBP 18,000 overnight gain on a receive-fixed swap book and asks:

> “Is that real carry, or did your curve move?”

The question is more subtle than it sounds. A useful answer must distinguish contractual accrual from curve roll-down, actual market movement, new fixings and cash-flow events. It must also state what “unchanged market” means.

## Carry, Roll-Down and Theta

**Carry** usually refers to the economic accrual earned or paid while holding a position. For a simplified swap, one-day net coupon carry can be approximated by:

[
Carry approx N(K-F)Delta t
]

where (N) is notional, (K) is the fixed coupon, (F) is the expected floating rate and (Delta t) follows the relevant day-count convention.

**Roll-down** is the change in value caused by a trade ageing to a different point on a non-flat curve. A five-year trade becomes slightly shorter tomorrow. Even if the market curve is unchanged in tenor coordinates, the par rate applicable to the aged trade may differ.

**Theta** is commonly defined as the PV change produced by advancing the valuation clock under a controlled frozen-market convention:

[
Theta = PV(t_1,Roll(M_0))-PV(t_0,M_0)
]

Terminology varies. One desk may define theta as carry plus roll-down; another may report those components separately. The methodology therefore belongs in the result contract, not in tribal knowledge.

## Worked Numerical Example

Consider a simplified receive-fixed swap:

- Notional: GBP 50 million
- Fixed rate: 4.50%
- Expected floating rate: 4.00%
- Swap annuity: 4.40
- PV01: GBP 22,000 per basis point
- Rolled par rate after one day: 0.8bp lower
- Day count: ACT/365

The coupon carry is:

[
50{,}000{,}000 	imes (0.045-0.040) / 365
= GBP 684.93
]

A receive-fixed position benefits when the applicable par rate falls. Its approximate roll-down PnL is:

[
GBP 22{,}000/bp 	imes 0.8bp
= GBP 17{,}600
]

If the desk defines theta as carry plus roll-down:

[
Theta approx 684.93 + 17{,}600
= GBP 18{,}284.93
]

The trader’s GBP 18,000 gain can therefore be economically plausible without an observed market move.

This is a linear estimate. Full revaluation will also capture changes in annuity, discounting, schedule and convexity.

A weekend matters too. Friday close to Monday close normally advances three calendar days. Coupon carry alone becomes approximately GBP 2,054.79, not GBP 684.93. Treating this as one business day is a common production defect.

## A Reproducible Time-PnL Bridge

Use three valuation states:

```text
S0: opening positions + Friday close market + Friday clock
S1: opening positions + rolled Friday market + Monday clock
S2: opening positions + Monday close market + Monday clock
```

Then:

[
TimePnL = PV(S1)-PV(S0)
]

[
MarketPnL = PV(S2)-PV(S1)
]

S1 is counterfactual: time has advanced, but market inputs are derived from the prior snapshot through an approved roll rule.

Possible curve-roll conventions include constant zero rates, constant instantaneous forwards, rolled discount factors, or static market quotes followed by recalibration. They need not produce the same result. The convention and its version must be stored with every output.

## Engineering Design

```python
@dataclass(frozen=True)
class TimeRollScenario:
    from_time: datetime
    to_time: datetime
    elapsed_calendar_days: int
    curve_roll_method: str
    calendar_version: str
    fixing_policy_version: str
    cashflow_policy: str
    method_version: str


@dataclass(frozen=True)
class TimePnLResult:
    trade_id: str
    from_state_id: str
    to_state_id: str
    carry_pnl: Decimal | None
    roll_down_pnl: Decimal | None
    total_theta: Decimal
    currency: str
    status: str
    scenario_id: str
```

A calculation can be structured as follows:

```python
def calculate_time_pnl(trade, base_context, next_time, policy):
    base_pv = price(trade, base_context)

    rolled_market = roll_market(
        market=base_context.market,
        from_time=base_context.as_of,
        to_time=next_time,
        method=policy.curve_roll_method,
    )

    aged_trade = advance_trade_state(
        trade=trade,
        to_time=next_time,
        calendars=policy.calendars,
        fixing_policy=policy.fixing_policy,
    )

    rolled_context = base_context.replace(
        as_of=next_time,
        market=rolled_market,
    )
    rolled_pv = price(aged_trade, rolled_context)

    return TimePnLResult(
        trade_id=trade.id,
        from_state_id=base_context.state_id,
        to_state_id=rolled_context.state_id,
        carry_pnl=None,
        roll_down_pnl=None,
        total_theta=rolled_pv - base_pv,
        currency=trade.currency,
        status="SUCCESS",
        scenario_id=policy.scenario_id,
    )
```

The trade-state transition must process accrual, maturity, fixing publication, payment events, holidays and settlement rules. Advancing only a timestamp is insufficient.

## Data Quality and Production Controls

A trustworthy implementation should verify:

- identical position population at both ends of the time transition;
- elapsed calendar days consistent with valuation timestamps;
- all rolled curves derived from one base market snapshot;
- explicit curve, calendar, fixing and methodology versions;
- each fixing or cash-flow transition applied exactly once;
- theta, market and other components reconcile to total PnL;
- failed results remain unavailable rather than becoming zero.

Business-invariant tests should cover:

```python
def test_weekend_uses_three_calendar_days():
    result = theta(friday_close, monday_close)
    assert result.elapsed_calendar_days == 3

def test_flat_curve_has_little_roll_down():
    result = roll_down(par_trade, flat_curve)
    assert abs(result.roll_down_pnl) < tolerance

def test_time_scenario_is_reproducible():
    assert theta(run_context) == theta(run_context)
```

Useful operational metrics include run age, elapsed-day distribution, theta by book, roll-down by tenor, method-version usage, cash-flow and fixing transition counts, and time-PnL residual.

## Common Failure Modes

1. **Weekend undercount** — Friday-to-Monday is treated as one day.
2. **Curve not rolled** — the date changes while original date-indexed discount factors are reused incorrectly.
3. **Accrual double count** — dirty PV already contains accrual, but carry is added again.
4. **Cash double count** — a paid cash flow leaves PV and is also charged to theta.
5. **Fixing boundary error** — a timezone error changes coupon state too early or too late.
6. **Method drift** — a library upgrade changes the roll rule without a methodology-version change.
7. **Stale cache** — valuation date is missing from the cache key.
8. **Mixed snapshots** — discount and projection curves derive from different market cuts.
9. **Maturity bug** — expired trades continue to generate carry or risk.

## Requirement Discovery

When a trader asks for carry, clarify:

- Should carry, theta and roll-down be separate?
- What are the from/to valuation timestamps?
- Are calendar days or business days used?
- Which curve-roll convention is approved?
- Are coupon accrual, funding, fixings and cash included?
- Is PV clean or dirty?
- Does a new fixing belong to theta or fixing PnL?
- What sign, currency and aggregation level are required?
- How are weekends and holidays handled?
- Is this forecast carry, realized carry or an official PnL component?

A concise requirement translation might be:

```yaml
window: friday_close_to_monday_close
elapsed_calendar_days: 3

time_component:
  curve_roll_method: constant_forwards
  split:
    - coupon_carry
    - roll_down

exclude_from_theta:
  - new_fixings
  - trade_activity
  - actual_market_move

controls:
  preserve_opening_population: true
  reconcile_to_total_pnl: true
  failed_as_zero: false
```

## Interview Questions

1. Why can a Rates trade change value when quoted market rates are unchanged?
2. How would you separate time PnL from market PnL?
3. Why is a curve-roll convention required?
4. Which bugs are especially likely across a weekend?
5. What metadata would make theta reproducible?

Strong answers should mention ageing, accrual, roll-down, cash-flow and fixing transitions; counterfactual states; versioned curve-roll methodology; calendar and timezone controls; and exact snapshot lineage.

## Key Takeaways

- Unchanged market quotes do not imply unchanged PV.
- Carry is economic accrual; roll-down is the effect of ageing along the curve.
- Theta is only meaningful when its frozen-market and component conventions are explicit.
- Time PnL should be computed through reproducible counterfactual valuation states.
- Calendar, fixing, cash-flow and cache-key defects can create plausible but incorrect PnL.
- A front-office developer should translate “show me carry” into an exact clock, population, roll method, component boundary and reconciliation policy.
