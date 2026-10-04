# Hedging Bond DV01 with an Interest Rate Swap

## Abstract

A swap hedge should match risk, not face amount. A long fixed-rate bond portfolio usually has negative signed DV01, while a pay-fixed interest-rate swap usually has positive signed DV01 under a parallel upward curve shock. This article explains the direction, calculates the required swap notional, and shows why a portfolio can be neutral in total DV01 while retaining substantial curve-shape risk.

## Desk Context

A cash-bond portfolio has signed curve DV01 of GBP -15,800 per basis point. The trader asks to “hedge the duration with swaps.”

That request leaves several implementation choices open: pay fixed or receive fixed, which curve and tenor to use, whether the target is total or key-rate DV01, how to round notional, and what residual is acceptable.

The first deliverable is deliberately narrow: create a parallel-DV01 hedge using a liquid 10-year vanilla interest-rate swap.

## Direction: Pay Fixed or Receive Fixed?

Define signed DV01 as:

$$
DV01=PV(r+1bp)-PV(r)
$$

A conventional long fixed-rate bond loses value when rates rise, so its signed DV01 is normally negative.

A receive-fixed swap has similar direction: the holder receives a fixed stream whose relative value falls when market rates rise. Its signed DV01 is usually negative.

A pay-fixed swap normally has positive signed DV01. The holder pays fixed and receives floating; when rates rise, the floating side becomes more valuable relative to the fixed payments. Therefore a pay-fixed swap is the natural directional hedge for a long bond portfolio’s negative rate sensitivity.

This conclusion depends on an explicit shock and sign convention. A service returning absolute DV01 cannot safely recommend direction.

## Risk Matching, Not Notional Matching

Suppose a GBP 10 million reference pay-fixed swap has signed DV01 of GBP +8,100/bp. The hedge notional is:

$$
HedgeNotional
=
ReferenceNotional
\times
\frac{-PortfolioDV01}
{ReferenceSwapDV01}
$$

Matching the bond face amount would be unreliable. Bond and swap cashflows may differ in maturity, coupon, amortization, payment frequency, and curve mapping. Notional describes contractual scale; DV01 describes the target rate sensitivity.

A swap hedge also addresses rate risk, not the bond’s credit-spread risk. A DV01-neutral package can still carry CS01 and liquidity risk.

## Worked Numerical Example

Given:

- Portfolio signed curve DV01: GBP -15,800/bp.
- Reference swap notional: GBP 10 million.
- Ten-year pay-fixed swap DV01: GBP +8,100/bp per GBP 10 million.

The theoretical notional is:

$$
HedgeNotional
=
10m\times\frac{15{,}800}{8{,}100}
=
GBP\ 19.506m
$$

If the desk trades in GBP 100,000 increments, round to GBP 19.5 million.

Assuming approximately linear DV01 scaling:

$$
SwapDV01
=
8{,}100\times\frac{19.5m}{10m}
=
+GBP\ 15{,}795/bp
$$

The package residual is:

$$
ResidualDV01
=
-15{,}800+15{,}795
=
-GBP\ 5/bp
$$

For a parallel seven-basis-point rate rise, the first-order residual PnL is approximately:

$$
ResidualPnL=-5\times7=-GBP\ 35
$$

The hedge is therefore very close to neutral under the stated parallel-shift definition.

## Total DV01 Can Hide Curve Risk

Consider a simplified key-rate view:

| Tenor | Bond DV01 | Package after 10Y hedge |
|---|---:|---:|
| 5Y | GBP -5,000/bp | GBP -5,000/bp |
| 10Y | GBP -10,800/bp | GBP +10,795/bp |
| Total | GBP -15,800/bp | GBP -5/bp |

The total is almost zero, but the 5Y and 10Y buckets contain large opposing exposures. A curve twist can therefore generate material PnL.

This is a parallel-DV01 hedge, not a key-rate hedge. If the trader cares about steepening or flattening, the next design step is a multi-tenor swap hedge rather than pretending that one total number captures the curve.

## Engineering the Hedge Calculation

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class SwapHedgeInput:
    portfolio_dv01: Decimal
    reference_notional: Decimal
    pay_fixed_swap_dv01: Decimal
    notional_increment: Decimal
    currency: str
    curve_id: str
    market_snapshot_id: str


def size_pay_fixed_hedge(x: SwapHedgeInput) -> dict:
    if x.portfolio_dv01 >= 0:
        raise ValueError("expected negative portfolio DV01")
    if x.pay_fixed_swap_dv01 <= 0:
        raise ValueError("pay-fixed DV01 must be positive")

    raw_notional = (
        x.reference_notional
        * (-x.portfolio_dv01)
        / x.pay_fixed_swap_dv01
    )

    units = (
        raw_notional / x.notional_increment
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    hedge_notional = units * x.notional_increment
    hedge_dv01 = (
        x.pay_fixed_swap_dv01
        * hedge_notional
        / x.reference_notional
    )

    return {
        "direction": "PAY_FIXED",
        "hedge_notional": hedge_notional,
        "hedge_dv01": hedge_dv01,
        "residual_dv01": x.portfolio_dv01 + hedge_dv01,
        "curve_id": x.curve_id,
        "market_snapshot_id": x.market_snapshot_id,
    }
```

The output must retain the curve, market snapshot, shock definition, swap template, and rounding policy. A number such as “GBP 19.5m” is not reproducible without those assumptions.

## Data Quality and Production Controls

The most relevant controls are:

- Portfolio and swap risk must share currency, curve shock, and market snapshot.
- Pay/receive direction must reconcile with signed DV01.
- Notional increments and rounding policy must be explicit.
- Start date, maturity, floating index, calendars, and clearing conventions must describe a tradable swap.
- Failed or stale swap risk must not become zero or silently fall back to an earlier value.

A severe production failure occurs when an upstream service returns absolute DV01. The hedge engine may choose receive fixed instead of pay fixed, increasing the portfolio’s negative DV01 while displaying a plausible positive risk number.

## Requirement Discovery

When a trader says “hedge the duration with swaps,” clarify:

- Is the target total DV01 or key-rate DV01?
- Which government, OIS, or swap curve defines risk?
- Is direction recommended by the system or supplied by the trader?
- Should the swap be spot-starting or forward-starting?
- Is 10Y fixed, or should maturity match portfolio cashflows?
- What notional increment and residual tolerance apply?
- Are spread, FX, or cross-currency risks in scope?
- What event triggers rehedging?

A useful dialogue is:

**Trader:** “Use a 10-year swap to flatten the bond book’s DV01.”

**Developer:** “The book is GBP -15.8k/bp. Under our +1bp convention, a 10Y pay-fixed swap is GBP +8.1k/bp per GBP 10m. Do you want parallel or key-rate neutrality?”

**Trader:** “Parallel DV01 for now. Round to the nearest GBP 100k.”

**Developer:** “That gives GBP 19.5m pay fixed and approximately GBP -5/bp residual. I’ll expose the remaining 5Y/10Y bucket mismatch.”

## Interview Questions

1. Why does pay fixed usually hedge a long bond’s negative DV01?
2. Why is face-amount matching inferior to DV01 matching?
3. How does notional rounding create residual risk?
4. Why can total-DV01 neutrality coexist with large curve-shape risk?
5. What metadata makes the calculation reproducible?

## Key Takeaways

Size a swap hedge from signed DV01 rather than face amount. Under a parallel +1bp curve shock, a long fixed-rate bond normally has negative DV01 and a pay-fixed swap normally provides positive DV01. Align curve and snapshot definitions, round notional under an explicit policy, and expose the residual. Finally, distinguish total-DV01 neutrality from key-rate neutrality: one swap can flatten the headline number while leaving a significant curve trade underneath.