# Reporting-Currency DV01 Is Not FX Risk

## Abstract

A Rates risk number has two different currency meanings: the currency of the underlying risk factor and the currency in which its value is displayed. Confusing them can turn a harmless reporting change into an apparent hedge failure. This article shows how to translate a signed EUR rate sensitivity into GBP while holding FX fixed, validates the result against a bumped valuation, and explains why converted EUR and GBP sensitivities should retain separate factor identities.

## The desk question

A trader opens a GBP dashboard and sees EUR curve sensitivity fall from GBP 4,300 per basis point to GBP 4,250 per basis point. No trade has changed, and the local risk remains EUR 5,000 per basis point. Has the hedge improved?

Not necessarily. If GBP per EUR changed from 0.86 to 0.85, the displayed number changed solely because its reporting unit changed. The EUR curve exposure is unchanged. The dashboard must distinguish movement in economic risk from movement in its currency translation.

Yesterday's valuation lesson established that reporting PV equals local PV multiplied by a consistently directed FX quote. Today's question applies that relationship to a controlled rate bump, not to a historical PnL bridge.

## Define the sensitivity before converting it

“DV01” is not a sufficient specification. Some desks report a positive loss magnitude; others report signed PV changes or derivatives. Here we define a signed up-bump measure: local PV after a specified positive one-basis-point rate shock minus base local PV. A negative number therefore means the position loses value under that shock.

Let $V_0$ and $V_+$ be base and bumped EUR valuations. Let $x$ be GBP per EUR, frozen throughout the scenario. The signed one-basis-point PV change is:

$$
D_{EUR} = V_+ - V_0
$$

The corresponding reporting-currency result is:

$$
D_{GBP} = x D_{EUR}
$$

This is exact for the finite scenario when the same FX rate translates both valuations. It does not require a first-order Taylor approximation. Approximating PnL for a different-sized market move using this sensitivity is a separate step.

A production label should state “signed PV change for +1 bp” rather than relying on DV01 alone. Also record whether the scenario bumps market quotes and rebuilds the curve, or directly shifts a curve representation. Currency conversion cannot reconcile different shock definitions.

## Worked example: validate against the pricer

Consider an illustrative EUR Rates position, with FX frozen at 0.86 GBP per EUR:

| Measure | Base | EUR rate shock +1 bp |
| --- | ---: | ---: |
| Local PV, EUR | 1,000,000 | 1,005,000 |
| Reporting PV, GBP | 860,000 | 864,300 |

The local signed sensitivity is positive EUR 5,000 per basis point. The reporting sensitivity is positive GBP 4,300 per basis point. Subtracting the translated valuations gives precisely the same answer as translating the local sensitivity.

Now change only the reporting quote to 0.85. Base reporting PV becomes GBP 850,000 and bumped reporting PV becomes GBP 854,250. Their difference is GBP 4,250. Nothing in this experiment changed the EUR curve risk. The GBP 50 reduction is a translation effect on the risk display.

A dangerous implementation uses 0.86 for base PV and 0.85 for bumped PV. It reports 854,250 minus 860,000, or negative GBP 5,750, as “DV01.” That result combines a rate scenario with an FX scenario and even reverses the sign. It is not the requested pure rate sensitivity.

This is why a scenario must identify everything held fixed, not only the factor it shocks. A live FX lookup inside each valuation call is enough to contaminate an otherwise reproducible risk run.

## FX sensitivity asks a different question

Translated EUR rate risk still measures an EUR rate shock. It does not measure a change in the exchange rate.

For intuition, keep the base EUR PV fixed at one million and move GBP per EUR by 0.001. Reporting value changes by GBP 1,000. That experiment shocks FX while keeping local valuation fixed; the rate experiment does the reverse. The two results have different shock units and must not share a single unqualified “risk” field.

This simple distinction assumes the local EUR valuation itself is independent of the chosen reporting FX quote. Products whose valuation genuinely depends on FX require a product-aware risk calculation; the shortcut is not a universal cross-currency pricing formula.

## Engineering the frozen-input contract

A valuation service should receive an immutable market snapshot. The rate-scenario builder creates a new snapshot with the specified curve shock while leaving the reporting FX input unchanged. Translation then operates on the paired local valuations.

```python
from decimal import Decimal

def report_rate_risk(base_eur, bumped_eur, gbp_per_eur):
    if gbp_per_eur <= 0:
        raise ValueError("Invalid reporting FX")
    local = bumped_eur - base_eur
    reported = local * gbp_per_eur
    check = bumped_eur * gbp_per_eur - base_eur * gbp_per_eur
    assert reported == check
    return {
        "risk_factor": "EUR_CURVE",
        "scenario": "specified_up_1bp",
        "sign_convention": "bumped_minus_base",
        "local_currency": "EUR",
        "reporting_currency": "GBP",
        "local_value": local,
        "reported_value": reported,
    }

risk = report_rate_risk(
    Decimal("1000000"), Decimal("1005000"), Decimal("0.86")
)
```

The compact function assumes snapshot compatibility has already been checked. A real response should additionally retain curve identifier, bucket if relevant, market snapshot, FX snapshot, and scenario version. Decimal makes this example exact; floating-point systems need a documented reconciliation tolerance.

## Four targeted controls

1. Freeze reporting FX across base and rate-bumped valuations. Reject mismatched snapshot provenance rather than silently accepting a mixed scenario.
2. Normalize quote direction and prevent double conversion. The output is already in GBP.
3. Preserve sign and bump semantics. A signed up-bump result must not be compared directly with a positive loss convention.
4. Preserve factor identity after conversion. GBP reporting units do not turn EUR curve risk into GBP curve risk.

Tests should include unchanged local risk with changing FX, zero sensitivity, negative sensitivity, and equivalence between translating the difference and differencing translated valuations. An FX move alone should change the displayed sensitivity proportionately, without triggering a “local risk changed” classification.

## Requirements and aggregation

A trader asks, “Put every DV01 in GBP and show the net.” Ask whether they want a common display unit or a joint shock across all curves. Converted EUR and GBP curve sensitivities may be added for a specifically defined simultaneous scenario, but their cancellation does not establish a hedge against independent curve moves.

For example, positive GBP 4,300 of EUR curve sensitivity and negative GBP 4,300 of GBP curve sensitivity net to zero under the specified same-direction joint shock. An EUR-only shock still produces positive GBP 4,300. Keep the factor breakdown beside any scenario total.

## Key takeaways

Reporting-currency DV01 changes the unit of a rate sensitivity, not its underlying factor. Freeze FX, declare the sign and shock, and validate through paired valuations. A common currency makes numbers comparable; it does not make different risk factors interchangeable.

All examples are synthetic and educational, with no confidential data or investment advice.
