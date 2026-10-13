# Market-Quote DV01 Through Bump-and-Rebootstrap

## Abstract

Rates traders observe and hedge futures, FRAs, swaps, and bonds—not anonymous curve parameters. A risk engine must therefore distinguish sensitivity to internal curve nodes from sensitivity to calibration-market quotes. This article explains market-quote DV01 using a controlled bump-and-rebootstrap workflow, develops a numerical example with central differences, and translates the methodology into a production-ready risk contract.

## Desk Context

Assume a short-end projection curve is calibrated from two futures-adjusted forward quotes. A swap valued on that curve has a base PV of GBP 2.5 million. The trader asks a simple question: if the first futures quote rises by one basis point, how much does the trade lose?

Directly bumping one discount-factor node does not answer that question. A quote move changes the calibrated curve through the bootstrap equations. Depending on instrument ordering, interpolation, and multi-curve dependencies, one quote can affect several downstream nodes. The trade must be repriced on that rebuilt curve.

## Two Risk Coordinate Systems

Let the vector of calibration quotes be $q$, let the curve parameters be $x=C(q)$, and let the trade value be $V(x)$. Quote sensitivity follows the chain rule:

$$
\frac{\partial V}{\partial q_j}
=
\sum_k
\frac{\partial V}{\partial x_k}
\frac{\partial x_k}{\partial q_j}.
$$

The first factor is sensitivity to internal curve parameters. The second is the bootstrap Jacobian: it describes how the calibrated nodes move when a market quote moves.

Node risk and quote risk therefore answer different questions:

- **Node risk:** What happens if an internal curve parameter is changed directly?
- **Quote risk:** What happens if an observable calibration quote changes and the curve is recalibrated?

Node risk is useful for model diagnostics and cross-system comparison. Quote risk is generally closer to a trader's hedging instruments. Labelling node sensitivity as futures DV01 silently discards the bootstrap transformation.

## Controlled Bump-and-Rebootstrap

For each quote bucket, the engine should:

1. Copy a frozen base quote set.
2. Apply a labelled bump to one target quote.
3. Rebuild the complete curve using unchanged conventions, interpolation, solver settings, and non-target quotes.
4. Validate that the bumped curve reprices its calibration instruments.
5. Revalue the same trade population and compare PVs.

A one-sided measure is

$$
DV01_j^{up}=V(q_j+1bp)-V(q_j).
$$

A central measure is

$$
DV01_j
=
\frac{V(q_j+1bp)-V(q_j-1bp)}{2}.
$$

This result is currency per basis point. If an API instead publishes a derivative per unit decimal rate, the denominator would be $2\times10^{-4}$. A field called simply `delta` is unsafe without a declared unit.

Central differences reduce some local curvature error but require two curve builds per bucket. The choice between one-sided and central risk is therefore a methodology decision with both numerical and computational consequences.

## Worked Numerical Example

The base trade PV is

$$
V_0=GBP\ 2{,}500{,}000.
$$

After bumping the first adjusted futures quote by plus and minus one basis point, rebuilding, and repricing, suppose the engine returns:

- $V(q_1+1bp)=GBP\ 2{,}493{,}200$
- $V(q_1-1bp)=GBP\ 2{,}506{,}850$

The signed quote DV01 is

$$
QuoteDV01_1
=
\frac{2{,}493{,}200-2{,}506{,}850}{2}
=-GBP\ 6{,}825/bp.
$$

The negative sign means a one-basis-point rise in the first adjusted quote reduces PV.

For the second quote, suppose:

- $V(q_2+1bp)=GBP\ 2{,}495{,}600$
- $V(q_2-1bp)=GBP\ 2{,}504{,}450$

Then

$$
QuoteDV01_2
=
\frac{2{,}495{,}600-2{,}504{,}450}{2}
=-GBP\ 4{,}425/bp.
$$

If the first quote rises 2bp and the second falls 1bp, first-order quote PnL is

$$
\begin{aligned}
QuotePnL
&\approx(-6{,}825)\times2
+(-4{,}425)\times(-1)\\
&=-GBP\ 9{,}225.
\end{aligned}
$$

If official full revaluation produces -GBP 9,380, the -GBP 155 residual may reflect valuation curvature, cross-effects, or interpolation. It should not be forced back into the quote buckets merely to balance a waterfall.

## Why Direct Node Bumps Are Insufficient

A sequential bootstrap creates a dependency chain. An early quote can move its directly solved node and every downstream node that depends on it. Bumping a single discount factor while freezing all other nodes breaks the calibration equations and represents a different scenario.

A valid quote-risk scenario should satisfy two invariants:

- the targeted quote is changed by exactly the declared bump; and
- the rebuilt curve reprices all bumped and unbumped calibration instruments within tolerance.

This makes calibration validation part of risk generation, not just part of the overnight curve build.

Independent quote bumps produce bucketed quote risk. Moving an entire quote strip together produces a parallel scenario. The parallel full-revaluation result need not equal the sum of single-quote DV01s because bootstrap and valuation mappings can be nonlinear and can contain interactions.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class QuoteRiskRequest:
    quote_ids: tuple[str, ...]
    bump_bp: Decimal
    market_snapshot_id: str
    curve_config_version: str


def central_quote_dv01(request, base_quotes, build_curve, price):
    results = {}
    bump = request.bump_bp * Decimal("0.0001")

    for quote_id in request.quote_ids:
        up = dict(base_quotes)
        down = dict(base_quotes)
        up[quote_id] += bump
        down[quote_id] -= bump

        curve_up = build_curve(up)
        curve_down = build_curve(down)

        if not curve_up.reprices or not curve_down.reprices:
            raise ValueError("bumped curve failed calibration")

        results[quote_id] = (
            price(curve_up) - price(curve_down)
        ) / (Decimal("2") * request.bump_bp)

    return {
        "risk_unit": "currency_per_bp",
        "method": "CENTRAL_BUMP_REBOOTSTRAP",
        "quote_dv01": results,
        "market_snapshot_id": request.market_snapshot_id,
        "curve_config_version": request.curve_config_version,
    }
```

Parallel execution is natural because buckets are independent scenarios, but results still require deterministic ordering and per-bucket status. A failed build is missing risk, not zero risk.

## Data Quality and Production Controls

The most important controls are:

- Base, up, and down runs must share the position population, market snapshot, and curve configuration.
- Quote ID, quote type, unit, bump size, and direction must be explicit.
- Every bumped curve must pass calibration-repricing checks.
- Failed buckets must remain failures rather than being filled with zero.
- Output must preserve quote, curve, and valuation lineage.

A classic production failure is a unit mismatch. The quote service stores 4.20 as percentage points while the risk engine adds 0.0001, believing the field is a decimal rate. The intended 1bp scenario becomes a 0.0001bp scenario, shrinking risk by a factor of 10,000 without causing an exception.

Focused observability should include successful bucket coverage, maximum calibration residual per bump, curve-build latency, and lineage-mismatch counts. These metrics reveal missing or invalid risk more effectively than monitoring only whether the batch completed.

## Requirement Discovery and Interview Questions

When a trader requests “futures DV01,” clarify:

- Is the coordinate the raw futures price or the convexity-adjusted forward rate?
- How does a futures-price rise map to the sign of the implied-rate bump?
- Is the methodology one-sided, central, or a larger stress shock?
- Are quotes bumped independently or as a parallel strip?
- Is the convexity adjustment recalculated or frozen during the bump?
- Which instruments must the bumped curve reprice, and to what tolerance?
- Does one failed bucket invalidate the report or produce an explicitly partial result?
- Is the output required as currency per bp, a futures-contract hedge ratio, or both?

A strong interview answer explains that market-quote DV01 includes the calibration Jacobian. It also treats scenario definition, units, curve validation, and lineage as part of the risk methodology rather than operational metadata.

## Key Takeaways

- Node risk and market-quote risk are sensitivities in different coordinate systems.
- Quote DV01 requires bumping a labelled market input, rebuilding the curve, validating calibration, and repricing the unchanged portfolio.
- Central differences improve local symmetry but double curve-build work.
- Failed risk is unknown risk, never zero risk.
- Quote-risk output needs explicit units, sign convention, methodology, and end-to-end lineage to support hedging and PnL explain.
