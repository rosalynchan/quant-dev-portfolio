# Futures PnL and Variation Margin: Building a Settlement Reconciliation

## Abstract

Exchange-traded futures convert daily mark-to-market gains and losses into cash through variation margin. This creates a subtle data-model problem: daily futures PnL and variation-margin cash may be numerically equal, but they are not interchangeable fields and must never be added as separate profits. This article explains the distinction between initial margin, variation margin, PnL, and clearing cash, then shows how to build an auditable settlement reconciliation.

## Desk Context

A rates desk holds 188 short bond-futures contracts after completing a hedge roll. The official settlement price falls from 112.42 to 111.95. The PnL dashboard reports a GBP 88,360 gain, while the clearing cash ledger reports a GBP 88,360 variation-margin receipt.

The trader asks whether the profit has been counted twice.

The answer depends on the report. Seeing the amount once in a valuation ledger and once in a cash ledger is correct: the first measures performance, while the second records settlement. Adding the two amounts into total profit would be double counting.

## Daily Mark-to-Market

Using signed quantity, with long positive and short negative, daily futures PnL is:

$$
DailyFuturesPnL
=
Quantity\times Multiplier
\times(Settle_t-Settle_{t-1})
$$

A long position gains when the settlement price rises. A short position gains when it falls.

For a stable position with aligned cutoffs, currency, and settlement sources:

$$
VariationMarginCash_t
=
DailyFuturesPnL_t
$$

The equality is economic, not semantic. PnL belongs to valuation and performance reporting. Variation margin belongs to cash and clearing. The two ledgers should reconcile through a shared settlement identifier, rather than collapsing into one ambiguous measure.

## Initial Margin Is Different

Initial margin is collateral posted to protect the clearing system against potential future exposure. It is not the purchase price of a futures contract and is not itself a trading expense.

If the initial-margin requirement is GBP 6,000 per contract:

$$
InitialMargin
=
188\times6{,}000
=
GBP\ 1{,}128{,}000
$$

The desk needs GBP 1.128 million of collateral capacity. That amount may be restricted and may create a funding cost, but posting the collateral does not create a GBP 1.128 million loss.

A clear model separates:

- Initial margin: restricted collateral.
- Variation margin: daily settlement cash.
- Futures PnL: daily price performance.
- Fees: exchange, clearing, and brokerage expense.
- Notional: economic exposure, not cash paid.

## Worked Numerical Example

The signed quantity is -188, the multiplier is GBP 1,000 per price point, and the settlement-price move is:

$$
\Delta Price
=
111.95-112.42
=
-0.47
$$

Daily futures PnL is:

$$
DailyFuturesPnL
=
(-188)\times1{,}000\times(-0.47)
=
+GBP\ 88{,}360
$$

The short position profits because the futures price fell.

Assuming no intraday trades, currency differences, or timing adjustments, the expected variation-margin receipt is also GBP 88,360.

If clearing fees are GBP 235:

$$
NetClearingCash
=
88{,}360-235
=
GBP\ 88{,}125
$$

A useful report therefore shows:

- Market PnL: GBP +88,360.
- Variation margin received: GBP +88,360.
- Fees: GBP -235.
- Net clearing cash: GBP +88,125.

It must not calculate total profit as PnL plus variation margin. The variation-margin receipt settles the PnL; it is not a second gain.

## Why PnL and Variation Margin Can Differ

The simplified equality breaks when scope or timing differs. Common causes include:

- PnL uses a live price while clearing uses official settlement.
- The position changes through new trades, closes, or a roll.
- First-day PnL runs from trade price to settlement.
- Clearing cash has a different value date.
- Cash includes fees, FX conversion, or clearing adjustments.
- The position snapshot and clearing statement use different cutoffs.

A production control should not assert equality without context. It should reconcile expected settlement PnL with actual clearing cash under explicit position, price-source, date, currency, and activity policies.

## Engineering the Reconciliation

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FuturesSettlement:
    contract_id: str
    signed_quantity: int
    previous_settle: Decimal
    current_settle: Decimal
    multiplier: Decimal
    reported_vm_cash: Decimal
    fees: Decimal
    currency: str
    position_snapshot_id: str
    settlement_run_id: str


def reconcile_settlement(
    x: FuturesSettlement,
    tolerance: Decimal,
) -> dict:
    expected_pnl = (
        Decimal(x.signed_quantity)
        * x.multiplier
        * (x.current_settle - x.previous_settle)
    )

    vm_break = x.reported_vm_cash - expected_pnl
    net_cash = x.reported_vm_cash - x.fees

    return {
        "daily_futures_pnl": expected_pnl,
        "variation_margin_cash": x.reported_vm_cash,
        "vm_reconciliation_break": vm_break,
        "net_clearing_cash": net_cash,
        "status": (
            "RECONCILED"
            if abs(vm_break) <= tolerance
            else "BREAK"
        ),
        "position_snapshot_id": x.position_snapshot_id,
        "settlement_run_id": x.settlement_run_id,
    }
```

Trade activity requires additional segmentation. If a position begins the day at -188 contracts, closes 20 contracts intraday, and ends at -168, applying the closing quantity to the full settlement move is wrong. The calculation needs opening-position PnL plus trade-to-settlement PnL for activity.

## Data Quality and Production Controls

The highest-value controls are:

- Use the official settlement for the correct contract and business date.
- Align the position snapshot with the clearing cutoff.
- Preserve multiplier, currency, and price scale.
- Segment new and closed trades according to the activity policy.
- Expose every reconciliation break with reason and lineage; never turn failure into zero.

The dashboard should show expected settlement PnL, actual variation margin, fees, net clearing cash, and the reconciliation break. A single margin total hides whether a difference came from valuation, activity, timing, or cash processing.

## Requirement Discovery

When a trader asks to “show futures margin,” clarify:

- Does margin mean initial margin, variation margin, or both?
- Does PnL use live price, close, or official settlement?
- Is the position opening, closing, or clearing-cutoff inventory?
- How is first-day PnL for new trades handled?
- Is variation margin expected or taken from the actual clearing statement?
- Are fees and FX included?
- Is reporting in local or reporting currency?
- What tolerance and escalation owner apply to breaks?

A useful dialogue is:

**Trader:** “Futures made 88k, and cash also increased by 88k. Are we counting the profit twice?”

**Developer:** “No. PnL measures price performance; variation margin is the cash settlement of that PnL. Should the dashboard link the two through reconciliation?”

**Trader:** “Yes, and keep initial margin separate.”

**Developer:** “I’ll show PnL, VM receipt, fees, net cash, and any break. Initial margin will remain collateral rather than expense.”

## Interview Questions

1. Why may futures PnL and variation-margin cash be equal without representing two profits?
2. How does initial margin differ economically from variation margin?
3. Which price source should drive an official settlement reconciliation?
4. How should intraday trade activity affect the calculation?
5. What identifiers are required to reproduce a clearing break?

## Key Takeaways

Variation margin is the cash settlement of futures mark-to-market PnL, not an additional source of profit. Initial margin is collateral, not transaction expense. A reliable platform keeps valuation and cash semantics separate, then reconciles them using aligned official settlements, position cutoffs, activity rules, currency, and lineage. Breaks should remain visible and actionable rather than being absorbed into PnL or converted into false zeros.