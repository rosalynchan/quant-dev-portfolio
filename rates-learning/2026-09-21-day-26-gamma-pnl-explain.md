# Adding Gamma to a Key-Rate PnL Explain

## Abstract

A first-order key-rate PnL explain assumes DV01 remains constant throughout the market move. On volatile days, sensitivity changes as rates move and the approximation can leave a meaningful residual. This article adds diagonal curve gamma to a swap-hedge PnL bridge, explains the unit conventions that cause production errors, and shows why second-order attribution must reconcile to full-revaluation PnL.

## Desk Context

The previous explain produced +GBP 9,800 linear curve PnL, +GBP 600 carry, +GBP 10,650 actual clean PnL, and +GBP 250 residual.

Opening diagonal gamma is GBP 60/bp² at 5Y, GBP 40/bp² at 7Y, and GBP 20/bp² at 10Y. Node moves are +2bp, -1bp, and +3bp. The trader asks whether the residual is noise or curvature.

## From DV01 to Second Order

The linear approximation is:

$$
\Delta PV_{linear}\approx\sum_i DV01_i\Delta r_i
$$

It assumes risk remains constant. A diagonal second-order approximation is:

$$
\Delta PV
\approx
\sum_i DV01_i\Delta r_i
+
\frac{1}{2}\sum_i\Gamma_i(\Delta r_i)^2
$$

Here, $\Gamma_i$ is PV curvature for node $i$ in currency per bp squared. DV01 PnL changes direction with the rate move. Diagonal gamma contains a squared move, so its direction is determined by gamma’s sign. Doubling a move roughly quadruples the second-order term.

This lesson excludes cross-gamma between nodes. Diagonal gamma must not be presented as a complete nonlinear surface.

## Worked Numerical Example

$$
GammaPnL_{5Y}
=
\frac{1}{2}\times60\times2^2
=
GBP\ 120
$$

$$
GammaPnL_{7Y}
=
\frac{1}{2}\times40\times(-1)^2
=
GBP\ 20
$$

$$
GammaPnL_{10Y}
=
\frac{1}{2}\times20\times3^2
=
GBP\ 90
$$

Therefore:

$$
GammaPnL=120+20+90=GBP\ 230
$$

$$
ExplainedPnL=9{,}800+600+230=GBP\ 10{,}630
$$

$$
Residual=10{,}650-10{,}630=GBP\ 20
$$

Gamma reduces residual from GBP 250 to GBP 20. Curvature was useful, but the remainder may contain cross-gamma, activity, rounding, or valuation differences.

## Unit Convention: The Main Risk

Systems publish several quantities under “gamma”: a derivative against decimal rate, curvature per bp, a coefficient already containing one-half, or an amount inferred from up/down scenarios.

Because $1bp=10^{-4}$, confusing decimal gamma with per-bp-squared gamma can create a scale error of $10^8$.

A production field must state shock unit, half-factor policy, currency, bucket, method, and snapshot. A clear contract publishes gamma amount per bp squared and lets the explain service apply $\frac12\Gamma(\Delta r)^2$ explicitly.

## When Is Gamma Material?

Gamma is most useful when node moves exceed a threshold, the portfolio contains nonlinear products, the linear residual breaches tolerance, or the desk reviews an event day.

For a mostly linear swap or bond portfolio on a quiet day, gamma may be below rounding noise. The engine can calculate it consistently while the dashboard applies materiality.

Actual PnL still comes from full revaluation. Linear and gamma explain that result; adding them again to actual PnL would double count.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BucketSecondOrder:
    bucket: str
    opening_dv01: Decimal
    gamma_per_bp2: Decimal
    move_bp: Decimal


def second_order_curve_explain(
    rows: list[BucketSecondOrder],
    carry_pnl: Decimal,
    actual_pnl: Decimal,
    tolerance: Decimal,
) -> dict:
    linear, gamma = {}, {}

    for row in rows:
        linear[row.bucket] = row.opening_dv01 * row.move_bp
        gamma[row.bucket] = (
            Decimal("0.5")
            * row.gamma_per_bp2
            * row.move_bp
            * row.move_bp
        )

    linear_total = sum(linear.values(), Decimal("0"))
    gamma_total = sum(gamma.values(), Decimal("0"))
    explained = linear_total + gamma_total + carry_pnl
    residual = actual_pnl - explained

    return {
        "linear_by_bucket": linear,
        "gamma_by_bucket": gamma,
        "gamma_total": gamma_total,
        "residual": residual,
        "status": "RECONCILED" if abs(residual) <= tolerance else "BREAK",
    }
```

## Data Quality and Production Considerations

The essential controls are:

- Align DV01, gamma, and moves to the same buckets, curve, opening snapshot, and shock convention.
- Store bp-squared scale and half-factor policy as metadata.
- Never replace missing gamma with zero while claiming a complete second-order explain.
- Reconcile linear, gamma, and carry to actual full-revaluation PnL.
- Monitor gamma materiality and residual improvement.

A classic failure occurs when upstream already publishes half-gamma and downstream applies another factor of one-half. Gamma PnL is understated by 50%.

## Requirement Discovery and Interview Questions

When a trader asks to “add convexity,” clarify:

- Is this bond-yield convexity or curve-node gamma?
- Is the scope diagonal gamma only, or cross-gamma too?
- Should risk come from opening, closing, or average snapshot?
- What shock size produced gamma?
- Has the one-half factor already been applied?
- What materiality threshold controls display?
- Does missing gamma block publication or trigger a labelled linear-only fallback?
- Should gamma appear by bucket or only as a total?

A strong answer states that sensitivity attribution is approximate while actual PnL is generated by full revaluation.

## Key Takeaways

- DV01 is first-order; gamma captures sensitivity change and grows with squared move.
- Gamma sign determines diagonal gamma PnL direction.
- Unit and half-factor conventions are essential API data.
- Diagonal gamma is not complete cross-node nonlinear risk.
- Second-order components explain actual PnL; they are not extra profit.
- A concise desk statement is: “I add gamma under an explicit bp-squared convention, test whether it materially reduces residual, and preserve full-revaluation reconciliation.”