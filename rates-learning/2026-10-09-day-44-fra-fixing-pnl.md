# FRA Fixing Transition: Explaining the Move from Forecast Risk to Known Cash

## Abstract

A forward rate agreement changes character at fixing. Before fixing, its value depends on a projected forward rate and carries projection-curve risk. Once the official fixing is published, that uncertainty disappears and the trade becomes a known settlement amount. This article shows how to explain the fixing transition without inventing PnL, mixing market snapshots, or leaving stale forward PV01 in a risk report. It also translates the desk requirement into a compact, testable Python design.

## Desk Context

Consider a GBP 100 million receive-floating/pay-fixed 3x6 FRA with:

- contractual rate $K=4.00\%$;
- accrual fraction $\alpha=0.25$;
- last projected forward $F=4.35\%$;
- official fixing $L=4.50\%$;
- settlement at the start of the underlying period.

Immediately before publication, the desk sees a forecast-based mark. Immediately after publication, it sees a contractual settlement based on the official rate. A trader asks:

> “The fixing printed 15 basis points above the last forward. How much PnL is the fixing event, and why has my forward PV01 disappeared?”

This is not simply an end-of-day rate move. It is a state transition from a forecast observation to a known observation.

## Two Valuation States

Before fixing, a convenient start-date-equivalent value is:

$$
S(F)=\frac{N\alpha(F-K)}{1+F\alpha}
$$

After fixing, the contractual settlement is:

$$
S(L)=\frac{N\alpha(L-K)}{1+L\alpha}
$$

The fixing-transition PnL, measured on the same settlement-date basis, is therefore:

$$
FixingPnL=S(L)-S(F)
$$

Using the same value date is essential. Comparing a today-discounted pre-fixing PV directly with a settlement-date cash amount would mix market change with discount carry and time passage.

The economic interpretation is straightforward:

- Before fixing, the trade is sensitive to the projection curve.
- At fixing, the official observation replaces the projected rate.
- After fixing, projection risk for that observation is zero.
- The known cash may still carry discount or settlement risk until it is paid, depending on the reporting basis.

The official fixing is not a manual override to the forward curve. It is a lifecycle event with a source, publication timestamp, status, and version.

## Worked Numerical Example

The projected start-date-equivalent amount immediately before fixing is:

$$
S(F)=
\frac{100{,}000{,}000\times0.25\times(0.0435-0.0400)}{1+0.0435\times0.25}
=GBP\ 86{,}558.67
$$

The official settlement is:

$$
S(L)=
\frac{100{,}000{,}000\times0.25\times(0.0450-0.0400)}{1+0.0450\times0.25}
=GBP\ 123{,}609.39
$$

Therefore:

$$
FixingPnL=123{,}609.39-86{,}558.67=+GBP\ 37{,}050.72
$$

The positive sign is intuitive: the position receives floating, and the official fixing is higher than the last projected forward.

A linear estimate can be built from the local fixing sensitivity. Differentiating the settlement function gives:

$$
\frac{dS}{dR}=\frac{N\alpha(1+\alpha K)}{(1+\alpha R)^2}
$$

Near the last forward, the sensitivity is approximately GBP 2,463 per basis point. A 15bp surprise therefore predicts roughly GBP 36.9k. The small difference from GBP 37,050.72 comes from the nonlinear denominator. For the official explain, full repricing should be authoritative; the sensitivity estimate is a useful reasonableness check.

This component should not be added to both old and new valuations. It is the bridge between them.

## Engineering Design

A robust implementation treats fixing as a versioned event and requires both valuations to share the same economic scope.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FraFixingTransition:
    trade_id: str
    notional: Decimal
    fixed_rate: Decimal
    accrual_fraction: Decimal
    projected_rate: Decimal
    official_fixing: Decimal
    receive_floating: bool
    fixing_source: str
    fixing_version: str
    publication_time: str


def explain_fixing(x: FraFixingTransition) -> dict:
    direction = Decimal("1") if x.receive_floating else Decimal("-1")

    def settlement(rate: Decimal) -> Decimal:
        return (
            direction
            * x.notional
            * x.accrual_fraction
            * (rate - x.fixed_rate)
            / (Decimal("1") + rate * x.accrual_fraction)
        )

    projected = settlement(x.projected_rate)
    official = settlement(x.official_fixing)

    return {
        "trade_id": x.trade_id,
        "state_before": "PROJECTED",
        "state_after": "OFFICIAL",
        "projected_settlement": projected,
        "official_settlement": official,
        "fixing_pnl": official - projected,
        "projection_pv01_after": Decimal("0"),
        "fixing_source": x.fixing_source,
        "fixing_version": x.fixing_version,
        "publication_time": x.publication_time,
    }
```

The output deliberately retains both sides of the bridge. A dashboard that shows only the final settlement cannot explain what changed.

## Data Quality and Production Controls

The most relevant controls are selective but strict:

1. **Authoritative fixing status.** Only an official observation from the configured source may move the trade to `OFFICIAL`. A provisional value must remain visibly provisional.
2. **Atomic state and risk update.** The valuation state, settlement amount, and projection PV01 must change together. A known cash amount alongside non-zero forward risk is inconsistent.
3. **Comparable valuation basis.** Pre- and post-fixing values must use the same settlement-date basis, trade version, notional, dates, and conventions.
4. **Idempotent event handling.** Replaying the same fixing version must not book the fixing PnL twice.
5. **Correction lineage.** If the administrator republishes a fixing, the system must create a correction bridge rather than overwrite history silently.

A dangerous production failure occurs when the pricing cache accepts the official fixing but the risk cache remains on the prior projected state. PnL may look correct while the trader receives a hedge recommendation for an exposure that no longer exists.

Useful observability measures include the count of officially fixed trades with non-zero projection PV01, fixing events processed more than once, and corrections lacking a prior fixing version.

## Requirement Discovery and Interview Questions

When a trader says “explain the FRA fixing,” a developer should clarify:

- Which projected snapshot is the baseline: the last pre-publication snapshot or the previous official close?
- Should the bridge be measured on today-PV basis or settlement-date basis?
- Which source and status qualify as official?
- How are provisional, delayed, or corrected fixings handled?
- Does the component include discount carry, or is that reported separately?
- What should happen if pricing receives the fixing before risk and PnL services?
- Is a same-day intraday bridge required, or only end-of-day attribution?

A strong interview answer emphasizes that fixing is both a market-data event and a lifecycle transition. The implementation must update valuation, risk, and explain consistently, preserve event lineage, and remain replay-safe.

## Key Takeaways

- The fixing bridge replaces a projected observation with the official observation on a comparable valuation basis.
- Full repricing gives the authoritative fixing PnL; PV01 times the surprise is a diagnostic approximation.
- Projection PV01 for the fixed observation must become zero atomically with the state change.
- Publication timestamps, source, status, and version are part of the pricing contract.
- Corrections and retries require explicit lineage and idempotent processing, not silent overwrite.
