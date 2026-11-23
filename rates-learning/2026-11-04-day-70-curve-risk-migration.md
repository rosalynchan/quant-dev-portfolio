# Curve Risk Migration: Why Stable PV and Total DV01 Do Not Guarantee a Stable Hedge

## Abstract

A curve methodology release may leave portfolio PV and total DV01 almost unchanged while redistributing sensitivity across tenors. That migration matters because traders hedge bucketed curve exposure, not only parallel risk. This article shows how to compare old and new market-quote DV01 vectors on frozen inputs, quantify gross migration, test a twist scenario, and build release controls that prevent cross-bucket netting from hiding a material hedge change.

## Desk Context

Consider a swap book whose old-methodology market-quote DV01 is:

- 5Y: GBP -80,000 per basis point
- 10Y: GBP +20,000 per basis point
- Total: GBP -60,000 per basis point

After a curve interpolation release, the new risk is:

- 5Y: GBP -65,000 per basis point
- 10Y: GBP +5,000 per basis point
- Total: GBP -60,000 per basis point

Total DV01 is identical. A dashboard that shows only the total reports no impact. Yet each bucket changed by GBP 15,000 per basis point, so the hedge's response to a curve twist has changed.

## Risk Is a Vector, Not Only a Scalar

Let the old and new bucketed-DV01 vectors be

$$
\mathbf d^{old}
=(d^{old}_{2Y},d^{old}_{5Y},d^{old}_{10Y},\ldots)
$$

and

$$
\mathbf d^{new}
=(d^{new}_{2Y},d^{new}_{5Y},d^{new}_{10Y},\ldots).
$$

Define the migration vector:

$$
\Delta\mathbf d
=\mathbf d^{new}-\mathbf d^{old}.
$$

Even if the sums of both vectors are equal, the vectors themselves may differ. Total DV01 is a parallel-rate scalar; it nets changes between tenors and therefore cannot describe curve-shape exposure.

## Worked Numerical Example

Using 5Y and 10Y as the bucket order:

$$
\mathbf d^{old}=(-80{,}000,+20{,}000)
$$

$$
\mathbf d^{new}=(-65{,}000,+5{,}000).
$$

The migration is

$$
\Delta\mathbf d=(+15{,}000,-15{,}000).
$$

Its net sum is zero, but both buckets changed materially.

For a one-basis-point parallel rise:

$$
PnL_{old}=(-80{,}000)(1)+(20{,}000)(1)
=-\text{GBP }60{,}000
$$

and

$$
PnL_{new}=(-65{,}000)(1)+(5{,}000)(1)
=-\text{GBP }60{,}000.
$$

The parallel scenario cannot distinguish the methodologies.

Now apply a twist: 5Y rises 3bp while 10Y rises 1bp.

$$
PnL_{old}=(-80{,}000)(3)+(20{,}000)(1)
=-\text{GBP }220{,}000
$$

$$
PnL_{new}=(-65{,}000)(3)+(5{,}000)(1)
=-\text{GBP }190{,}000.
$$

The same market scenario differs by GBP 30,000. Stable total DV01 therefore does not imply a stable hedge.

## Why Methodology Moves Bucket Risk

Market-quote DV01 is commonly calculated by bumping one calibration quote and rebuilding the entire curve:

$$
DV01_i
\approx
V(C(q_i+1bp))-V(C(q_i)).
$$

Changing interpolation, bootstrap ordering, calibration instruments, or failed-bump handling changes how an individual quote bump propagates through discount factors and forwards. The same portfolio cash flows can consequently be attributed to different market-quote buckets.

That migration is not automatically an error. It is nevertheless economically important because it changes trader-visible tenor exposure, hedge selection, hedge ratios, scenario PnL, and risk-limit utilization.

## Compare Under a Common Taxonomy

An old-versus-new comparison is meaningful only when both vectors use the same:

- market-quote bucket labels and tenor boundaries;
- bump size, direction, and finite-difference scheme;
- rebootstrap and failed-bump policy;
- currency, units, and sign convention;
- frozen market, trade, and fixing snapshots.

If one report's “5Y” means a 4Y-6Y quote bucket while another means an exact five-year zero-rate bump, subtracting them creates a number without a stable economic meaning. Both results should first be mapped to an approved reporting taxonomy.

In addition to signed bucket changes, calculate gross migration:

$$
GrossMigration=\sum_i|\Delta d_i|.
$$

For the example:

$$
15{,}000+15{,}000
=\text{GBP }30{,}000/\text{bp}.
$$

Gross migration remains visible when positive and negative bucket changes net to zero.

## Engineering Design

```python
from decimal import Decimal


def compare_bucket_risk(
    old: dict[str, Decimal],
    new: dict[str, Decimal],
) -> dict:
    if old.keys() != new.keys():
        raise ValueError("risk taxonomies differ")

    migration = {
        bucket: new[bucket] - old[bucket]
        for bucket in old
    }
    total_old = sum(old.values(), Decimal("0"))
    total_new = sum(new.values(), Decimal("0"))
    gross = sum(
        (abs(value) for value in migration.values()),
        Decimal("0"),
    )

    return {
        "migration": migration,
        "total_change": total_new - total_old,
        "gross_migration": gross,
        "max_bucket_change": max(
            abs(value) for value in migration.values()
        ),
    }
```

The API should also return market snapshot ID, trade snapshot ID, methodology versions, risk taxonomy version, bump definition, unit, sign convention, and completeness state. A vector without this lineage is difficult to reproduce and unsafe to compare.

## Data Quality and Production Considerations

The most relevant controls are:

- **Frozen comparison inputs:** old and new runs must share market, trade, and fixing snapshots.
- **Versioned semantics:** taxonomy, bump method, unit, and sign convention must be explicit.
- **Multiple release thresholds:** check total change, gross migration, and maximum bucket change.
- **Concentration visibility:** provide a book-tenor heatmap and top migrated trades.
- **Incomplete-risk state:** a failed bump must not silently become zero sensitivity.

A common failure occurs when two APIs both return a “5Y” label but use different risk factors. Another occurs when the release gate checks total DV01 only; large opposite migrations net to zero and pass automatically.

Useful observability includes failed-bump count, missing bucket count, gross migration by book, maximum bucket change, taxonomy mismatch count, and the methodology versions being compared.

## Requirement Discovery and Interview Questions

When a trader asks to ensure that “the new curve does not change risk,” clarify:

- Does risk mean total DV01, market-quote DV01, zero-rate risk, or scenario PnL?
- Which bucket boundaries and canonical labels apply?
- Is the bump forward, central, absolute, or relative?
- Which hedge instruments correspond to each bucket?
- Are thresholds absolute, percentage-based, or tied to limit utilization?
- Should approval use net, gross, or maximum bucket migration?
- Which books and trades need separate sign-off?
- Should the system recommend a hedge rebalance or only alert?
- Does a failed bump block cutover?

A strong interview response is: “I would freeze inputs, align both runs to a versioned market-quote taxonomy, compare the complete risk vectors, and gate on gross and maximum migration rather than total DV01 alone. I would then run desk-relevant twist scenarios and drill material changes down to books and trades.”

## Key Takeaways

- Stable PV and total DV01 do not guarantee stable bucket risk.
- Curve methodology changes can alter how quote bumps propagate.
- Old and new vectors require a common, versioned risk taxonomy.
- Gross migration prevents cross-bucket netting from hiding change.
- Twist scenarios reveal hedge differences that parallel moves miss.
- Failed bumps must create an explicit incomplete state, never a false zero.
- Material migration requires trader-visible drill-down and approval.

