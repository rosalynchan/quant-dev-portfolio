# Pricing an Interest Rate Swap: From Par Rate to Present Value

## Abstract

An interest rate swap turns a fixed-versus-floating rate difference into cash flows and monetary value. For a front-office developer, a swap quote, a par rate, and PV are related but not interchangeable outputs. This article derives the par swap rate, values an off-market coupon, and maps the economics into a reproducible pricing service with controls that catch plausible-looking production errors.

## Desk Context

A trader asks: “Where is the two-year swap rate? If I receive 5%, how much am I above par?”

The answer depends on direction, notional, schedule conventions, reference index, curve set, fixings, valuation timestamp, and whether “above par” means a rate difference or monetary PV.

## Swap Economics

A vanilla fixed-for-floating interest rate swap has a fixed leg and a floating leg. For notional (N), fixed rate (K), and accrual fraction (alpha_i):

[
Fixed\ Coupon_i=N K\alpha_i
]

A floating coupon is generally:

[
Floating\ Coupon_i=N(L_i+s)\alpha_i
]

where (L_i) is an observed fixing or projected forward and (s) is a contractual spread. Standard swaps normally use notional as a calculation base rather than exchanging principal.

Direction is fundamental. Receive-fixed/pay-floating trades generally gain when rates fall; pay-fixed/receive-floating trades generally gain when rates rise.

## Leg PVs and the Swap Annuity

For a receive-fixed trade:

[
PV_{swap}=PV_{fixed}-PV_{floating}
]

The fixed leg is:

[
PV_{fixed}=N K\sum_i\alpha_iDF(t_i)
]

Define the swap annuity:

[
A=\sum_i\alpha_iDF(t_i)
]

Then (PV_{fixed}=NKA). Some desks use PV01 for notional times annuity times one basis point. An API should make clear whether it returns an annuity, an unsigned currency-per-bp amount, or signed risk.

Under a simplified single-curve framework:

[
PV_{floating}=N(1-DF(t_n))
]

## Deriving the Par Rate

The par swap rate makes net PV zero:

[
K_{par}=\frac{1-DF(t_n)}
{\sum_i\alpha_iDF(t_i)}
]

It is therefore not an isolated quote. It is a curve- and convention-dependent break-even rate.

## Worked Example

Consider a two-year receive-fixed swap with:

- GBP 10,000,000 notional;
- annual payments and unit accrual fractions;
- (DF(1Y)=0.96);
- (DF(2Y)=0.91);
- single-curve assumptions.

The annuity is:

[
A=0.96+0.91=1.87
]

The floating-leg PV is:

[
PV_{floating}=10{,}000{,}000(1-0.91)=GBP\ 900{,}000
]

The par rate is:

[
K_{par}=0.09/1.87=4.8128\%
]

At par, fixed-leg PV is also approximately GBP 900,000 and net PV is near zero.

If the trader receives 5%:

[
PV_{fixed}=10{,}000{,}000\times0.05\times1.87
=GBP\ 935{,}000
]

Therefore:

[
PV_{swap}=+GBP\ 35{,}000
]

The coupon is 18.72bp above par. Equivalently:

[
PV\approx N A(K-K_{par})\approx GBP\ 35{,}000
]

This provides an effective desk bridge from a rate difference to a monetary valuation.

## Beyond the Single-Curve Shortcut

Production pricing usually separates:

- a projection curve for future floating coupons;
- a discount curve for present-valuing cash flows;
- historical fixings for reset dates already observed;
- collateral- and currency-specific discounting;
- index-specific projection curves.

The general floating-leg value is:

[
PV_{float}=N\sum_i(F_i+s)\alpha_iDF(t_i)
]

Here (F_i) comes from the projection curve and (DF(t_i)) from the discount curve. The single-curve formula remains valuable for intuition, while the curve set must be explicit in production.

## Engineering Contract

```python
@dataclass(frozen=True)
class VanillaSwap:
    trade_id: str
    currency: str
    notional: Decimal
    direction: Literal["RECEIVE_FIXED", "PAY_FIXED"]
    fixed_rate: Decimal
    float_index: str
    float_spread: Decimal
    effective_date: date
    maturity_date: date
    fixed_frequency: str
    float_frequency: str
    fixed_day_count: str
    float_day_count: str
    calendar: str
    business_day_rule: str
```

Sparse fields such as rate and maturity cannot reproduce a schedule reliably. Calendars, frequencies, day-count rules, business-day adjustments, and stub conventions are valuation inputs.

```text
Trade economics
      |
Schedule generation <--- calendars and conventions
      |
Fixing resolution <------ historical fixing store
      |
Forward projection <----- projection curve
      |
Discounting <------------ discount curve
      |
Leg PVs -> Net PV -> Risk -> PnL
```

```python
def price_receive_fixed_swap(trade, curves, fixings, as_of):
    fixed_pv = sum(
        trade.notional * trade.fixed_rate
        * year_fraction(p.start, p.end, trade.fixed_day_count)
        * curves.discount.df(p.payment_date)
        for p in build_fixed_schedule(trade)
    )

    float_pv = 0.0
    for p in build_float_schedule(trade):
        rate = (
            fixings.require(trade.float_index, p.fixing_date)
            if p.fixing_date <= as_of.date()
            else curves.projection.forward_rate(p.start, p.end)
        )
        float_pv += (
            trade.notional * (rate + trade.float_spread)
            * year_fraction(p.start, p.end, trade.float_day_count)
            * curves.discount.df(p.payment_date)
        )

    return {
        "fixed_leg_pv": fixed_pv,
        "floating_leg_pv": float_pv,
        "signed_net_pv": fixed_pv - float_pv,
    }
```

Leg-level results make reconciliation considerably easier than a net value alone.

## Controls and Business-Invariant Tests

Controls should verify schedule completeness, adjusted dates, fixing availability, index-to-curve mapping, snapshot consistency, direction, rate scale, currency, and units.

```python
def test_par_swap_has_near_zero_pv():
    par = par_rate(template, curves)
    trade = template.with_fixed_rate(par)
    assert abs(price(trade, curves).signed_net_pv) < 0.01

def test_receive_fixed_value_increases_with_coupon():
    low = price(template.with_fixed_rate(0.04), curves)
    high = price(template.with_fixed_rate(0.05), curves)
    assert high.signed_net_pv > low.signed_net_pv
```

These tests express business meaning rather than internal implementation.

## Production Failure Modes

Plausible but wrong results can arise from:

1. an incorrect calendar changing a payment or fixing date;
2. a missing published fixing silently replaced by a forward;
3. an index mapped to the wrong projection curve;
4. receive/pay direction inverted between UI and calculation service;
5. discount and projection curves from different snapshots;
6. 5% transmitted as 5 when the pricer expects 0.05;
7. a stub cash flow omitted during schedule generation.

Useful observability includes curve IDs and versions, fixing provenance, schedule hashes, cash-flow counts, stale-data indicators, timestamps, fallback status, and leg-level reconciliation.

## Requirement Discovery

When asked to “price a two-year swap,” clarify:

- receive fixed or pay fixed;
- spot-starting, forward-starting, or seasoned;
- notional, currency, index, and leg frequencies;
- contractual fixed rate or requested par rate;
- spread, stub, or broken-date conventions;
- market-data snapshot and curve set;
- required outputs: leg PVs, net PV, par rate, or DV01;
- desk or counterparty sign perspective;
- precision, latency, and missing-fixing behavior.

```yaml
product: vanilla_interest_rate_swap
direction: receive_fixed
notional: GBP_10000000
fixed_rate: 0.05
valuation:
  market_data_cut: live
  discounting: collateral_curve
  projection: index_curve
  fixing_policy:
    confirmed_fixing_required_when_published: true
outputs: [fixed_leg_pv, floating_leg_pv, signed_net_pv, par_rate]
controls:
  missing_required_fixing: hard_error
```

## Interview Prompts

- Why does a newly traded par swap have approximately zero PV?
- How does an off-market coupon translate into monetary value?
- Why are projection and discounting separate concerns?
- Which attributes are required to reproduce a swap schedule?
- How would you diagnose a swap PV difference between two systems?

Strong answers connect formulas to direction, conventions, cash-flow comparison, curve lineage, fixings, snapshots, and units.

## Key Takeaways

- A swap is the net value of fixed and floating cash-flow legs.
- The par rate makes the two leg PVs equal at inception.
- Notional times annuity times coupon-minus-par gives a useful PV approximation.
- Single-curve formulas build intuition; production pricing generally requires projection and discount curves.
- Schedule conventions, fixings, curve mappings, direction, and rate scaling are first-class engineering concerns.
- Leg-level outputs and business-invariant tests make pricing discrepancies easier to diagnose.

*All examples are simplified, generic, and for educational purposes only. They do not constitute investment advice.*
