# When a Rates Book Gains in EUR but Loses in GBP

## Abstract

A positive local-currency valuation move does not guarantee a positive reporting-currency PnL. For a foreign-currency Rates position, the reporting value depends on both its local PV and the exchange rate used to translate that PV. This article builds an exact two-step bridge, explains the importance of quote direction, and turns the calculation into a small, testable engineering contract. The example deliberately excludes cashflows and position changes so that currency translation remains the only new concept.

## Desk context: two correct numbers that appear to disagree

A trader sees a EUR Rates book increase in value by EUR 10,000. A GBP dashboard shows a loss of GBP 1,500. Before escalating a pricing incident, the developer should ask whether the two screens measure the same thing.

Local PV is the value expressed in the position's valuation currency. Reporting PV is that value translated into the reporting currency. Neither is inherently more correct: they answer different questions. The local move describes what happened to the EUR valuation. The reporting move also captures the changing GBP value of that EUR exposure.

This follows naturally from valuing a separate compensation claim: first establish its value in its own currency, then translate it. Translation must not manufacture a second local cashflow or change the underlying contractual entitlement.

Our scope is a fixed, unpaid EUR position set between two snapshots. There are no new trades, settlements, fees, or transfers. We are not pricing a cross-currency swap or designing an FX hedge.

## Define the rate before writing the formula

Let $V_t$ be signed local PV in EUR and $x_t$ be GBP per EUR. One EUR therefore converts into $x_t$ GBP. Reporting PV, denoted $R_t$, is:

$$
R_t = V_t x_t
$$

The units are a practical validation tool: EUR multiplied by GBP per EUR gives GBP. A reciprocal quote would require division instead. A field named only “EURGBP” is weaker than an explicit base currency, quote currency, value, and timestamp.

Keep PV signed. A positive EUR asset loses GBP value when EUR weakens against GBP; a negative EUR liability becomes less negative under the same translation move. Taking absolute values destroys that distinction.

Also separate translation from an actual FX conversion trade. Re-expressing PV in GBP does not mean that EUR cash has been sold. An economic hedge, if present, has its own valuation and PnL and must be included explicitly.

## An exact bridge with a declared ordering

Use a local-first convention: move local PV while holding the opening exchange rate fixed, then translate the closing local PV at the closing rate.

$$
L = (V_1 - V_0)x_0
$$

$$
F = V_1(x_1 - x_0)
$$

Here $L$ is the local-PV contribution in GBP and $F$ is the FX-translation contribution in GBP. They reconcile exactly:

$$
R_1 - R_0 = L + F
$$

This is an attribution convention, not a claim that markets moved in that sequence. An FX-first bridge would assign the interaction differently while preserving the total. The earlier lesson on ordering applies here; today the important requirement is to declare one convention and use it consistently.

Calling $L$ “Rates PnL” would overstate what this bridge establishes. Local PV might also change because of time passage, fixings, or model changes. This calculation translates the observed local change; it does not explain its internal causes.

## Worked example: the apparent contradiction disappears

Assume the following synthetic snapshots:

| Input | Opening | Closing |
| --- | ---: | ---: |
| Signed local PV, EUR | 1,000,000 | 1,010,000 |
| GBP per EUR | 0.8600 | 0.8500 |
| Reporting PV, GBP | 860,000 | 858,500 |

The local PV gain is EUR 10,000. Translated at the opening rate, it contributes GBP 8,600. The closing EUR exposure then experiences a translation move of minus GBP 10,100. Together these produce the observed GBP 1,500 loss.

A useful intermediate valuation is GBP 868,600: closing local PV translated at the opening rate. The bridge is therefore 860,000 to 868,600 to 858,500.

Why not multiply the opening EUR exposure by the FX move? That gives minus GBP 10,000. Combined with GBP 8,600, it leaves minus GBP 100 unexplained. This is the interaction between the EUR 10,000 local increase and the minus 0.01 exchange-rate move. Our local-first convention includes it in the FX contribution by using closing PV.

The residual is not automatically a pricing error. First test whether the attribution used the exposure required by its stated convention.

## A compact engineering contract

Store the calculation alongside both snapshot identifiers, local and reporting currency, quote direction, signed values, and attribution convention. Return components in reporting-currency units. Do not let a generic presentation layer silently apply a second currency conversion.

```python
from decimal import Decimal

def translation_bridge(v0, v1, x0, x1):
    # v: signed EUR PV; x: GBP per EUR
    if x0 <= 0 or x1 <= 0:
        raise ValueError("FX quotes must be positive")
    opening = v0 * x0
    closing = v1 * x1
    local = (v1 - v0) * x0
    fx = v1 * (x1 - x0)
    total = closing - opening
    assert total == local + fx
    return {
        "currency": "GBP",
        "convention": "local_first",
        "opening_pv": opening,
        "closing_pv": closing,
        "local_pv_pnl": local,
        "fx_translation_pnl": fx,
        "total_pnl": total,
    }

result = translation_bridge(
    Decimal("1000000"), Decimal("1010000"),
    Decimal("0.86"), Decimal("0.85"),
)
```

This snippet assumes validated currency metadata and aligned snapshots upstream. Decimal arithmetic makes the toy reconciliation exact; a production floating-point implementation needs a documented tolerance. Round displayed components only after calculating the bridge, rather than rounding every intermediate value.

Test unchanged FX, unchanged local PV, a negative PV, and a reciprocal quote normalized to the same economic rate. An unchanged local PV must produce zero local contribution, not zero total PnL.

## Four selective production checks

1. **Quote direction:** normalize reciprocal quotes once and retain source metadata. A plausible positive number is not sufficient validation.
2. **Snapshot alignment:** record the local valuation cut and FX cut. A closing valuation translated with a live intraday rate answers a different question from an end-of-day report.
3. **Position and cash scope:** reject this simplified bridge when trades or settlements change the population. A paid coupon requires a cash-inclusive bridge, not disappearance of value.
4. **Single conversion:** label output currency and ensure aggregation does not translate a GBP result again.

A reconciliation dashboard should show opening reporting PV, the two contributions, closing reporting PV, and residual. Snapshot mismatches should be visible as status, not hidden by a balancing plug.

## Questions that turn a request into a specification

When a trader asks, “Show my PnL without FX,” clarify whether they want EUR PnL or a GBP constant-currency measure. If GBP, which fixed FX rate should apply? Is the report local-first or FX-first? Are FX hedges included, and does “without FX” remove their PnL too?

An interview-ready answer is: “I would separate valuation currency from reporting currency, state the quote units, and reconcile an explicit translation bridge before investigating the pricer.”

## Key takeaways

A local gain and a reporting loss can coexist. Exact attribution requires signed exposure, explicit quote direction, aligned snapshots, and a declared ordering. Reconciliation establishes arithmetic consistency; it does not prove market-data correctness or explain every driver of local PV.

All numbers and workflows here are synthetic educational examples, not employer information or investment advice.
