# Building a Rates Curve: From Market Quotes to Discount Factors

## Abstract

A Rates curve is a versioned transformation from observable instrument quotes into discount factors and forward rates. It sits beneath pricing, DV01, and PnL, so a stale or semantically inconsistent curve can create plausible but wrong results across an entire desk. This article develops bootstrapping intuition with a two-node example and translates curve construction into an auditable engineering workflow.

## Desk Context

A trader reports: “The two-year swap moved 6bp, but the book PV barely changed. Is the curve live?”

Possible causes include a missing quote update, silent fallback to an earlier curve, incorrect instrument mapping, mixed curve versions, or interpolation behavior. Diagnosing the issue requires separating the displayed quote, calibration inputs, constructed nodes, and the curve snapshot actually consumed by pricing.

## Four Related Representations

A curve may be represented as:

- discount factors (DF(t));
- zero rates (z(t));
- forward rates (F(t_1,t_2));
- par rates for standard instruments.

With annual compounding:

[
DF(t)=\frac{1}{(1+z(t))^t}
]

A one-year forward between years one and two satisfies:

[
1+F(1Y,2Y)=\frac{DF(1Y)}{DF(2Y)}
]

Markets usually quote instruments, not a complete daily discount-factor function. A curve builder finds nodes that reproduce those market instruments.

## Bootstrapping Intuition

Bootstrapping proceeds from short maturities to long maturities:

1. solve the first unknown node from the shortest instrument;
2. use known nodes to solve the next node;
3. continue along the maturity ladder;
4. reprice every calibration instrument;
5. reject or degrade the build when residuals exceed tolerance.

The central invariant is:

[
ModelQuote_i(Curve)\approx MarketQuote_i
]

A process-level success signal is insufficient if the curve cannot reprice its own inputs.

## Worked Example

Assume annual payments, unit notional, a single-curve framework, a 1Y par swap rate of 4.00%, and a 2Y par swap rate of 4.50%.

For the 1Y instrument:

[
0.04DF(1)+DF(1)=1
]

Therefore:

[
DF(1)=1/1.04=0.961538
]

For the 2Y par swap:

[
0.045[DF(1)+DF(2)]+DF(2)=1
]

Solving the next node:

[
DF(2)=\frac{1-0.045DF(1)}{1.045}=0.915532
]

The corresponding two-year zero rate is:

[
z(2)=DF(2)^{-1/2}-1=4.5113\%
]

The implied one-year forward from year one to year two is:

[
F(1Y,2Y)=\frac{DF(1)}{DF(2)}-1=5.0251\%
]

This illustrates why par, zero, and forward rates must not be treated as interchangeable fields. The 2Y par quote is 4.50%, the 2Y zero rate is approximately 4.51%, and the second-year forward is approximately 5.03%.

Substituting the solved nodes back into both pricing equations produces one, confirming exact repricing under the simplified assumptions.

## Interpolation Is Part of the Model

Cash-flow dates rarely coincide with every calibration node, so the curve needs interpolation. Common choices include linear interpolation on zero rates, linear or log-linear interpolation on discount factors, and methods based on instantaneous forwards.

Two builders may match every calibration quote yet produce different values between nodes. Interpolation can also affect forward smoothness and bucketed DV01 allocation. The method and its parameters must therefore be versioned curve-definition fields, not hidden library defaults.

## Engineering the Inputs and Outputs

```python
@dataclass(frozen=True)
class MarketQuote:
    instrument_id: str
    instrument_type: str
    tenor: str
    quote_type: str
    value: Decimal
    unit: str
    source: str
    observed_at: datetime
    received_at: datetime
    quality_status: str
```

Observed time and received time are distinct. A message can arrive now while carrying an old observation.

```python
@dataclass(frozen=True)
class CurveDefinition:
    curve_name: str
    currency: str
    purpose: Literal["DISCOUNT", "PROJECTION"]
    index: str | None
    calibration_instruments: tuple[str, ...]
    interpolation: str
    extrapolation: str
    conventions_version: str

@dataclass(frozen=True)
class CurveSnapshot:
    curve_id: str
    definition_version: str
    market_snapshot_id: str
    built_at: datetime
    status: str
    max_repricing_error_bp: float
    node_dates: tuple[date, ...]
    discount_factors: tuple[float, ...]
```

A simplified construction flow is:

```python
def bootstrap_curve(definition, quotes, valuation_date):
    validate_quotes(definition, quotes, valuation_date)
    nodes = []

    for instrument in ordered_instruments(definition, quotes):
        node = solve_next_node(
            instrument=instrument,
            known_nodes=nodes,
            interpolation=definition.interpolation,
        )
        nodes.append(node)

    curve = Curve(nodes, definition.interpolation)
    diagnostics = reprice_inputs(curve, quotes)

    if diagnostics.max_error_bp > definition.tolerance_bp:
        raise CurveBuildError(diagnostics)

    return CurveSnapshot.from_build(curve, diagnostics)
```

## Data Quality and Controls

Pre-build controls should cover quote completeness, observation freshness, duplicate conflicts, units, ranges, source priority, and out-of-order updates.

Post-build controls should cover calibration residuals, positive discount factors, node jumps, forward-rate guardrails, node counts, moves from the previous snapshot, and explicit fallback status.

Useful metrics include:

```text
curve_build_success_total
curve_build_failure_total
curve_snapshot_age_seconds
quote_age_seconds{instrument}
curve_repricing_error_bp{instrument}
curve_node_move_bp{tenor}
curve_fallback_total{reason}
pricing_requests_by_curve_version
```

## Production Failure Modes

1. **Stale-but-green:** construction succeeds on expired inputs.
2. **Partial update:** short-end quotes are current while long-end quotes remain on an earlier cut.
3. **Unit error:** 4.5% is parsed as 4.5 instead of 0.045.
4. **Convention mismatch:** calibration schedules use the wrong day count or frequency.
5. **Mixed versions:** pricing and risk consume different curve snapshots.
6. **Silent fallback:** a failed build reuses yesterday's curve without a degraded status.
7. **Interpolation regression:** a dependency update changes the default method.
8. **Ambiguous duplicate selection:** the wrong source wins when multiple quotes exist.

The correct response to a failed live build is a business decision: hard failure, continue with a clearly marked stale snapshot, or serve partial functionality. That policy must be explicit.

## Requirement Discovery

When a trader says “the curve is wrong,” clarify:

- which discount or projection curve and which index;
- which tenor or trades demonstrate the issue;
- whether the wrong output is a quote, zero, forward, par rate, PV, or risk;
- which live, close, or historical snapshot is expected;
- the comparison benchmark;
- source priority and fallback rules;
- recent changes to instruments, conventions, or interpolation;
- whether degraded data may continue to serve.

A useful investigation contract is:

```yaml
investigation:
  curve: GBP_projection_curve
  tenor: 2Y
  expected_market_move_bp: 6
checks:
  - quote_observed_at
  - quote_value_and_unit
  - market_snapshot_id
  - calibration_instrument_inclusion
  - repricing_residual_bp
  - pricing_curve_version
  - fallback_status
output:
  include_lineage: true
  distinguish_stale_from_failed: true
```

## Interview Questions

- What is the economic objective of bootstrapping?
- Why are par, zero, and forward rates different?
- How would you prove that a curve build is economically successful?
- How can a green curve job still provide stale risk?
- Why might two systems match all calibration instruments but disagree on a trade PV?

Strong answers mention repricing, timestamp semantics, fallbacks, versioned conventions, interpolation, curve mapping, and cash-flow dates.

## Key Takeaways

- A curve transforms market instruments into discount factors and forwards.
- Bootstrapping solves nodes sequentially and must reprice calibration instruments.
- Par, zero, and forward rates are related but distinct.
- Interpolation and conventions are versioned model inputs.
- Freshness, completeness, lineage, residuals, and fallback status matter as much as process success.
- Pricing investigations must identify the exact curve snapshot consumed downstream.

*All examples are simplified, generic, and for educational purposes only. They do not constitute investment advice.*
