# What Does “The Bond Is Wider” Mean? Engineering Bond Spread Measures

## Abstract

Bond spread is not a single intrinsic field. G-spread, I-spread, Z-spread and option-adjusted spread answer different questions and depend on different benchmarks, curves and models. This article builds practical spread intuition, solves a numerical Z-spread example, connects spread moves to CS01, and shows how to engineer traceable calculations that survive benchmark changes, mixed snapshots and ambiguous vendor fields.

## Desk Context

A trader sees three values for one bond: 218bp from one vendor, 231bp from another and 227bp internally.

> “Which spread should I trust, and why did ours widen 9bp?”

The numbers may not be comparable. One may be a government spread, another a Z-spread, and a third may use a different settlement date or market cut. A developer should align definitions before reconciling values.

## Spread Intuition

A simple mental model is:

$$
BondYield=ReferenceRate+Spread
$$

Spread can reflect credit risk, liquidity, funding, optionality, supply and demand, plus benchmark methodology. It is not a pure default probability and does not by itself establish that a bond is cheap or rich.

On a long cash-bond position, spread widening generally lowers price; spread tightening generally raises it.

## Common Measures

**G-spread** compares bond yield to a government benchmark:

$$
GSpread=BondYTM-GovernmentYield
$$

It is simple but highly dependent on benchmark selection.

**I-spread** compares bond yield with an interpolated swap rate:

$$
ISpread=BondYTM-InterpolatedSwapRate
$$

The swap-curve family and interpolation method matter.

**Z-spread** is the constant spread added to each point of a risk-free spot curve so that discounted cash flows reproduce the observed dirty price:

$$
Price
=
\sum_i CF_iDF_{riskfree}(t_i)e^{-s t_i}
$$

It uses the full cash-flow schedule and curve rather than two summary yields.

**OAS** adjusts for embedded optionality. For callable or putable bonds, Z-spread and OAS are not interchangeable; OAS depends on an option model and volatility assumptions.

## Worked Example

### G-Spread

If a corporate bond YTM is 6.60% and its government benchmark yields 4.40%:

$$
GSpread=6.60%-4.40%=220bp
$$

If yesterday’s spread was 211bp:

$$
SpreadMove=220-211=+9bp
$$

The level is 220bp; the move is +9bp. Data contracts should not confuse them.

### Z-Spread

Consider a simplified bond with:

- a 1Y cash flow of 5;
- a 2Y cash flow of 105;
- dirty price of 96;
- risk-free discount factors of 0.96 and 0.91.

Solve for (s):

$$
96
=
5	imes0.96e^{-s}
+
105	imes0.91e^{-2s}
$$

At (s=2.27%):

$$
5	imes0.96e^{-0.0227}approx4.692
$$

$$
105	imes0.91e^{-0.0454}approx91.307
$$

The sum is approximately 95.999, so:

$$
ZSpreadapprox227bp
$$

An internal value of 227bp can therefore be correct even when a vendor’s G-spread is 218bp.

## Spread Risk and CS01

Spread sensitivity may be called CS01, spread DV01 or credit-spread DV01. The exact convention must be explicit.

$$
CS01_{signed}=PV(spread+1bp)-PV(spread)
$$

For a long bond, signed CS01 is normally negative. If CS01 is -GBP 8,000/bp and spread widens 9bp:

$$
SpreadPnLapprox-8{,}000	imes9=-GBP 72{,}000
$$

This is a linear explain, not complete daily PnL. Risk-free rates, carry, accrual, convexity, optionality, FX and position activity may also contribute.

## Benchmark Mapping Risk

A G-spread can change even when the bond does not. Suppose the benchmark mapping switches to a newer government security whose yield is 7bp higher. Reported G-spread mechanically tightens 7bp.

That benchmark-remapping effect should be separated from genuine bond-market movement.

Z-spread is also state-dependent: price, risk-free curve, interpolation, settlement date and reference data all matter.

## Data Contract

```python
@dataclass(frozen=True)
class BondSpreadResult:
    instrument_id: str
    spread_type: Literal[
        "G_SPREAD",
        "I_SPREAD",
        "Z_SPREAD",
        "OAS",
    ]
    spread_bp: Decimal | None

    price_input: Decimal
    price_type: str
    settlement_date: date

    benchmark_id: str | None
    curve_id: str | None
    curve_version: str | None

    model_version: str
    reference_data_version: str
    status: str
```

A field called spread without type, benchmark or curve lineage is unsafe.

## Z-Spread Solver

```python
def solve_z_spread(
    bond,
    dirty_price,
    risk_free_curve,
    settlement_date,
):
    cashflows = build_remaining_cashflows(
        bond=bond,
        settlement_date=settlement_date,
    )

    def price_error(spread):
        model_price = sum(
            cf.amount
            * risk_free_curve.df(cf.payment_date)
            * exp(
                -spread
                * year_fraction(
                    settlement_date,
                    cf.payment_date,
                )
            )
            for cf in cashflows
        )
        return model_price - dirty_price

    spread = root_solve(
        price_error,
        bracket=(-0.05, 0.50),
    )

    if abs(price_error(spread)) >= tolerance:
        raise SpreadCalibrationError()

    return spread
```

Solver completion is not enough; the resulting spread must reprice the input price within tolerance.

## Benchmark Resolution

```python
def calculate_g_spread(
    bond_yield,
    bond,
    benchmark_policy,
    as_of,
):
    benchmark = benchmark_policy.resolve(
        currency=bond.currency,
        maturity=bond.maturity_date,
        as_of=as_of,
    )

    return {
        "spread_bp": (
            bond_yield - benchmark.yield_value
        ) * Decimal("10000"),
        "benchmark_id": benchmark.instrument_id,
        "policy_version": benchmark_policy.version,
    }
```

Benchmark selection should be deterministic, versioned and explainable.

## Controls and Tests

Important controls include:

- mandatory spread type;
- explicit basis-point versus decimal units;
- dirty price for Z-spread;
- aligned settlement date and cash-flow schedule;
- eligible benchmark currency and maturity;
- compatible market cuts across price, curve and benchmark;
- solver residual within tolerance;
- no Z-spread mislabeled as OAS;
- explicit lineage when a benchmark changes;
- missing calculation represented as unavailable, not 0bp;
- stale-price/fresh-curve combinations rejected or clearly degraded.

```python
def test_z_spread_reprices_market_price():
    spread = solve_z_spread(
        bond, dirty_price, curve, settlement_date
    )
    assert_close(
        price_with_spread(bond, curve, spread),
        dirty_price,
    )

def test_higher_price_implies_lower_z_spread():
    low = solve_z_spread(bond, 95, curve, date)
    high = solve_z_spread(bond, 97, curve, date)
    assert high < low

def test_missing_benchmark_is_not_zero_spread():
    result = g_spread_without_benchmark()
    assert result.status == "FAILED"
    assert result.spread_bp is None
```

Useful metrics include calculation age, solver failures, repricing residual, benchmark changes, mapping failures, source differences, mixed-cut rejections and spread outliers.

## Production Failure Modes

1. G-spread, Z-spread and OAS share one untyped field.
2. A Z-spread solver receives clean rather than dirty price.
3. Benchmark currency or maturity mapping is wrong.
4. Benchmark replacement is reported as market spread movement.
5. Decimal 0.0227 is displayed as 0.0227bp instead of 227bp.
6. Yesterday’s price is combined with today’s curve.
7. A root solver returns success despite a large repricing residual.
8. A stale vendor message overwrites a fresh calculation.
9. YTM, YTW, Z-spread and OAS are mixed for callable bonds.
10. Stub, amortization or principal cash flow is missing.
11. Negative spreads are rejected by an invalid range rule.
12. Failure appears as a valid 0bp spread.

## Requirement Discovery

When a trader asks for spread, clarify:

- G-spread, I-spread, Z-spread or OAS?
- Specific benchmark security or interpolated curve?
- Clean/dirty and bid/ask/mid/evaluated price?
- Settlement date?
- Which risk-free or swap curve?
- Spread level or daily move?
- Is CS01 and spread PnL required?
- For callable bonds, YTM, YTW or option-adjusted measure?
- Should benchmark changes be isolated?
- What source-difference tolerance applies?
- How should missing and failed states appear?
- Do overrides require owner, reason and expiry?

A precise requirement might be:

```yaml
measure: g_spread
unit: basis_points
window: official_close_to_close

inputs:
  bond_yield:
    quote_side: mid
  benchmark:
    policy: approved_government_benchmark
    preserve_instrument_id: true

explain:
  components:
    - bond_yield_move
    - benchmark_yield_move
    - benchmark_mapping_change

risk:
  include_cs01: true
  sign: signed_pv_change_for_plus_1bp

controls:
  require_aligned_market_cut: true
  failed_as_zero: false
```

## Interview Questions

1. How does G-spread differ from Z-spread?
2. Why can a benchmark change move reported spread without moving the bond?
3. What does signed CS01 mean?
4. Which inputs must be aligned before comparing vendor spreads?
5. How do you validate a Z-spread solver?

Strong answers should mention measure definition, benchmark or curve lineage, dirty price, settlement, market cut, cash flows, units and repricing residual.

## Key Takeaways

- A spread is meaningful only with its measure and reference.
- Wider means spread up; tighter means spread down.
- G-spread uses a benchmark yield, while Z-spread uses the full spot curve and cash-flow schedule.
- Spread level and spread move are different fields.
- Benchmark remapping is a data/model effect, not necessarily a market move.
- CS01 provides a fast linear spread-PnL estimate.
- Production systems must preserve price, curve, benchmark, settlement and methodology lineage.
