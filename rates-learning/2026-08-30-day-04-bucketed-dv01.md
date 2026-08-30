# Beyond Total DV01: Engineering Bucketed Curve Risk

## Abstract

Total DV01 is useful but lossy: it compresses an entire curve-risk profile into one number. Two portfolios with identical total DV01 can react very differently to a steepening, flattening, or localized tenor move. This article develops bucketed DV01 intuition, compares zero-node and market-quote bumps, and designs a risk pipeline that preserves scenario semantics, lineage, and completeness.

## Desk Context

A trader asks why Book B lost nearly twice as much as Book A even though both showed total DV01 of negative GBP 10,000 per basis point. The answer is not necessarily a pricing error. It may be hidden in the tenor distribution and internal offsets removed by aggregation.

## Parallel DV01

Parallel DV01 is the PV change when the relevant curve is shifted upward by one basis point:

[
DV01_{parallel}=PV(C+1bp)-PV(C)
]

It is concise, useful for direction and scale, and effective for a quick sanity check. Its weakness is information loss: it does not identify where along the curve the exposure resides.

## Bucketed DV01

Bucketed or key-rate DV01 shocks one tenor region at a time:

[
DV01_k=PV(C+bump_k)-PV(C)
]

If bucket shocks collectively reproduce a parallel move:

[
DV01_{parallel}\approx\sum_kDV01_k
]

The equality may be approximate because curve rebuilding, interpolation, nonlinear pricing, cross-curve effects, and incomplete bucket grids can create reconciliation differences.

## Worked Scenario

Suppose risk is measured in GBP thousands per positive 1bp move:

| Book | 2Y | 5Y | 10Y | Signed Total |
|---|---:|---:|---:|---:|
| A | -2 | -3 | -5 | -10 |
| B | -8 | +6 | -8 | -10 |

Under a parallel +5bp move, both books have estimated PnL of negative GBP 50,000.

Now consider a shape move:

- 2Y: +10bp;
- 5Y: +4bp;
- 10Y: -3bp.

For Book A:

[
PnL_A\approx(-2\times10)+(-3\times4)+(-5\times-3)
=-GBP\ 17k
]

For Book B:

[
PnL_B\approx(-8\times10)+(6\times4)+(-8\times-3)
=-GBP\ 32k
]

The same total DV01 produces very different PnL because Book B carries substantially more short-end exposure.

Book B also has gross bucket risk of (8+6+8=22), even though its signed total is only 10. Signed total communicates net direction; gross risk exposes internal offsets.

## Zero-Node Risk Versus Market-Quote Risk

A **zero-node bump** changes a node in the curve representation and re-interpolates. It is computationally direct but may not map naturally to a tradable hedge.

A **market-quote bump** changes a calibration quote and rebuilds the curve:

[
QuoteRisk_i=PV(Build(Q+1bp_i))-PV(Build(Q))
]

This maps more closely to observable instruments and trader language, but it requires deterministic curve construction and is more expensive.

The risk contract must identify which approach is used. A column labeled “5Y DV01” is not self-defining.

## Engineering the Risk Contract

```python
@dataclass(frozen=True)
class RiskPoint:
    trade_id: str
    curve_id: str
    curve_version: str
    risk_type: Literal["PARALLEL", "ZERO_BUCKET", "QUOTE_BUCKET"]
    bucket: str
    bump_bp: Decimal
    signed_pv_change: Decimal
    currency: str
    amount_unit: Literal["CCY"]
    scenario_definition_id: str
```

The scenario definition should resolve the bumped instrument or node, bump shape, neighboring-node treatment, rebuild policy, and base and bumped snapshot lineage.

```python
def bucketed_quote_risk(trade, market_quotes, curve_def):
    base_curve = build_curve(curve_def, market_quotes)
    base_pv = price(trade, base_curve)
    results = []

    for instrument_id in curve_def.risk_buckets:
        bumped_quotes = market_quotes.bump(
            instrument_id=instrument_id,
            bp=1,
        )
        bumped_curve = build_curve(curve_def, bumped_quotes)
        bumped_pv = price(trade, bumped_curve)

        results.append(RiskPoint(
            trade_id=trade.id,
            curve_id=base_curve.id,
            curve_version=base_curve.version,
            risk_type="QUOTE_BUCKET",
            bucket=instrument_id,
            bump_bp=Decimal("1"),
            signed_pv_change=bumped_pv-base_pv,
            currency=trade.currency,
            amount_unit="CCY",
            scenario_definition_id=curve_def.risk_scenario_id,
        ))

    return results
```

Before aggregation, validate currency, units, curve identity, scenario definition, and calculation status.

## Controls and Tests

High-value controls include:

- identical base PV across all bucket calculations;
- successful bumped-curve construction and acceptable calibration residuals;
- exactly one result for every expected bucket;
- consistent currency, unit, curve, and sign;
- parallel-versus-bucket reconciliation within tolerance or with a reason;
- trade-level aggregation reconciling to book totals;
- separate representations for zero, missing, and failed.

```python
def test_bucket_sum_reconciles_to_parallel():
    bucketed = sum(calc_bucketed_risk(trade))
    parallel = calc_parallel_risk(trade)
    assert abs(bucketed - parallel) < tolerance

def test_failed_bucket_is_not_reported_as_zero():
    result = calculate_bucket_with_missing_quote()
    assert result.status == "FAILED"
    assert result.value is None
```

## Production Failure Modes

1. A failed bucket is rendered as zero risk.
2. Services use different bump shapes under the same metric name.
3. Base and bumped calculations use different market snapshots.
4. A bumped quote makes curve construction fail.
5. Aggregation duplicates trade-level points.
6. A transformation removes signs by taking absolute values.
7. Risks in different currencies are summed without conversion.
8. Tenor labels from different curves collide.
9. Partial completion is reported as overall success.

These failures often produce plausible totals, making completeness and semantics as important as numerical accuracy.

## Dashboard Design

A useful risk dashboard should expose:

- signed total DV01;
- gross bucket DV01;
- a curve-by-tenor heatmap;
- largest positive and negative buckets;
- base curve version and market-data cut;
- completed versus expected bucket coverage;
- stale, failed, and degraded status;
- drill-down from book to trade;
- units and scenario-definition details.

A single green total card hides both internal offsets and missing calculations.

## Requirement Discovery

For “show me curve risk,” clarify:

- parallel or bucketed;
- zero-node or market-quote risk;
- discount curves, projection curves, or both;
- tenor grid;
- additive or relative bump;
- whether curves are rebuilt;
- signed or absolute, local or reporting currency;
- net, gross, or both;
- missing-bucket behavior;
- freshness, latency, and drill-down requirements.

```yaml
measure: bucketed_quote_dv01
bump:
  size_bp: 1
  method: additive
  rebuild_curve: true
dimensions: [curve, tenor, book, trade]
outputs:
  signed_total: true
  gross_total: true
  bucket_values: true
status_policy:
  failed_bucket_as_zero: false
reconciliation:
  compare_with_parallel_dv01: true
```

## Interview Prompts

- Why can equal total DV01 produce different daily PnL?
- How do zero-node and market-quote risks differ?
- Why might bucket sum not exactly equal parallel DV01?
- How would you represent a failed bucket in an API?
- Which fields prevent semantically incompatible risks from being aggregated?

Strong answers connect curve shape, scenario construction, lineage, completeness, units, signs, and business-aware failure handling.

## Key Takeaways

- Total DV01 summarizes a parallel move but does not describe curve shape.
- Bucketed DV01 preserves tenor-level exposure and internal offsets.
- Signed and gross risk answer different questions.
- Zero-node and quote risk are different contracts.
- Base/bump snapshot consistency and successful curve rebuilding are essential.
- Missing and failed risk must never be silently converted into zero.
- A front-office dashboard should expose semantics and coverage, not only totals.

*All examples are simplified, generic, and for educational purposes only. They do not constitute investment advice.*
