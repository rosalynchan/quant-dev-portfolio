# Bid/Ask-Aware Curve Validation: Measuring Fit Against the Executable Market

## Abstract

A curve calibration check should not assume that every market instrument has one uniquely correct quote. Dealers and venues expose a bid/ask range, especially in less liquid tenors. A curve-implied quote may differ materially from the mid while remaining inside the executable market. This article develops a practical validation model that separates mid residual, distance outside the spread, and PV materiality. It then translates that model into production-ready data, API, control, and requirement-discovery decisions.

## Desk Context

Suppose a 10-year swap is quoted at 3.240% bid and 3.260% ask. The mid is 3.250%, while a newly calibrated curve implies a 3.257% par rate.

A validation rule inherited from a liquid market might require every model quote to be within 0.05 basis points of mid. Under that rule, the curve fails: its mid residual is +0.7bp. Yet 3.257% is still below the executable ask of 3.260%. The model is not exactly at mid, but it is not outside the market either.

This distinction matters operationally. Forcing every illiquid calibration instrument to an uncertain mid can destabilize neighbouring curve nodes, while accepting any residual under a wide absolute tolerance can hide a genuinely off-market build.

The useful question is therefore not merely “How far is the model from mid?” It is “Where is the model relative to a fresh, comparable, executable bid/ask envelope?”

## Three Residual Measures

Let the bid be $b$, the ask be $a$, and the model-implied quote be $q$. Define the mid and half-spread as

$$
m=\frac{b+a}{2}, \qquad h=\frac{a-b}{2}.
$$

The familiar mid residual is

$$
r_{mid}=q-m.
$$

It shows where the model lies relative to the centre of the market. However, the distance outside the executable envelope is

$$
r_{outside}=\max(b-q,\ 0,\ q-a).
$$

If $q$ lies between bid and ask, $r_{outside}$ is zero. The result can be classified as `WITHIN_MARKET`, even though $r_{mid}$ is non-zero. A normalized location such as $r_{mid}/h$ is also useful: it distinguishes a model near mid from one sitting close to a boundary without changing the validity result.

These measures answer different questions:

- Mid residual describes location inside or outside the spread.
- Outside-spread residual measures the minimum move required to return to an executable boundary.
- PV materiality converts the outside residual into an approximate monetary scale for escalation.

## Worked Numerical Example

For the 10-year swap:

- Bid: 3.240%
- Ask: 3.260%
- Model: 3.257%

The mid is 3.250%, so

$$
r_{mid}=3.257\%-3.250\%=0.007\%=0.7\text{bp}.
$$

The total spread is 2bp and the half-spread is 1bp. The model is 0.7 half-spreads above mid, but remains inside the quoted range. Therefore

$$
r_{outside}=0.
$$

Now suppose the model quote becomes 3.264%. It exceeds the ask by

$$
3.264\%-3.260\%=0.004\%=0.4\text{bp}.
$$

If the calibration instrument has a PV01 magnitude of GBP 2,200 per basis point, the approximate materiality is

$$
0.4\times2{,}200=\text{GBP }880.
$$

GBP 880 is not a realized trading PnL. It is a quality measure: an approximation of the value change associated with bringing the model quote back to the nearest executable boundary.

## Why a Wider Absolute Tolerance Is Not Enough

A universal 1bp tolerance behaves poorly across liquidity regimes. A 1bp miss is severe when a liquid five-year swap has a 0.2bp spread. The same distance from mid may be unremarkable when a long-dated instrument has a 4bp spread.

A sound policy combines two layers:

1. A market-relative rule asks whether the model lies within a valid executable envelope.
2. A hard safety cap limits the allowed outside residual or PV materiality, even when the observed spread becomes unusually wide.

Bid/ask-aware validation must not turn a bad market into a loose tolerance. A spread can widen because one side is stale, a source is degraded, or markets are stressed. Quote quality must be validated before the envelope is used.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MarketEnvelope:
    bid: Decimal
    ask: Decimal
    model: Decimal
    pv01: Decimal
    quote_quality: str


def validate_envelope(x: MarketEnvelope) -> dict:
    if x.quote_quality != "EXECUTABLE":
        return {"status": "NOT_EXECUTABLE"}
    if x.bid > x.ask:
        raise ValueError("crossed market")

    mid = (x.bid + x.ask) / Decimal("2")
    mid_residual_bp = (x.model - mid) * Decimal("10000")
    outside_bp = max(
        x.bid - x.model,
        Decimal("0"),
        x.model - x.ask,
    ) * Decimal("10000")

    return {
        "status": "WITHIN_MARKET" if outside_bp == 0 else "OUTSIDE_MARKET",
        "mid_residual_bp": mid_residual_bp,
        "outside_spread_bp": outside_bp,
        "pv_materiality": outside_bp * abs(x.pv01),
    }
```

The result should be attached to an exact curve version and input manifest. A useful response includes the bid and ask quote identifiers, source, event times, quote quality, model quote, policy version, and all three residual measures. Storing only `passed=true` makes later investigation almost impossible.

An API should also represent `ONE_SIDED` and `NOT_EXECUTABLE` explicitly. A bid without an ask does not define an infinite acceptable range. It may support a one-sided inequality under a documented degraded policy, but it cannot prove that a model is within a two-sided executable market.

## Data Quality and Production Considerations

The most important controls are selective but strict:

- **Comparable units and conventions:** bid, ask, and model must all represent the same quote type, instrument definition, and economic timestamp.
- **Fresh synchronized sides:** an old bid combined with a new ask can create a wide envelope that never existed.
- **Executable lineage:** indicative dealer runs and composites must not silently qualify as executable inputs for an official curve.
- **Hard caps:** a wide or stressed spread must not expand validation tolerance without limit.
- **Boundary tests:** automated tests should cover inside, exactly at bid or ask, outside, crossed, stale, and one-sided markets.

A common failure mode is mixing a 09:59 bid with a 10:04 ask after the market has moved. Another is treating an indicative ask as firm, allowing an incorrect curve to pass. Dashboards should show both mid residual and outside-spread residual so that `WITHIN_MARKET` is not misread as “exactly calibrated.”

## Requirement Discovery and Interview Questions

When a trader says “the curve is off market,” a developer should clarify:

- Is the comparison in par rate, price, spread, or PV?
- Are the bid and ask executable, indicative, or composite?
- What are the maximum age and cross-side time skew?
- Is being within the envelope sufficient, or must the model remain within a fraction of the half-spread?
- What hard cap applies when spreads widen?
- How should one-sided markets be classified?
- Does one failed instrument reject the curve or retain the last valid version?
- Should escalation use basis points, spread fraction, PV materiality, or a combination?

A strong interview answer separates numerical fit from market validity: “I would validate quote quality first, measure location relative to mid, calculate distance outside the executable boundary, and then apply a versioned hard cap and PV materiality threshold.”

## Key Takeaways

- Mid is a useful reference, not the only executable market truth.
- A non-zero mid residual can still be market-consistent.
- Outside-spread residual is the relevant validity measure once quote quality is established.
- PV materiality supports escalation but is not realized PnL.
- One-sided, indicative, stale, or time-inconsistent quotes require explicit states rather than silently wider tolerances.
- Every result should preserve curve, quote, timestamp, source, and policy lineage.

