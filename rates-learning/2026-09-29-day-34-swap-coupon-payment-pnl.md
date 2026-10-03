# Reconciling Swap Coupon Payments: PV Drops, Cash Settlement and Daily PnL

## Abstract

A swap coupon payment can make reported PV fall sharply even when no economic loss has occurred. The reason is simple but operationally important: before payment, the receivable or payable is embedded in dirty PV; after payment, that value moves into the cash ledger. This article develops a payment-date PnL bridge, explains why ex-cash valuation time differs from actual settlement time, and presents an auditable engineering design that separates market PnL from cash and settlement breaks.

## Desk Context

Consider a GBP receive-fixed, pay-floating swap settling one coupon period today. The fixed leg pays the desk GBP 250,000, while the floating leg requires GBP 230,000, so the expected net receipt is GBP 20,000.

Immediately before the payment event, dirty PV is GBP 118,000. Immediately after removing the due cashflow, using the same market snapshot and model, dirty PV is GBP 98,000. Elsewhere in the day, market movement and carry contribute +GBP 1,500.

A trader sees the GBP 20,000 PV drop and asks why the swap lost money. A cash dashboard may simultaneously show a GBP 20,000 receipt. Adding the receipt as profit would be as wrong as treating the PV drop as a loss: both views describe the same value moving between ledgers.

## The Payment-Date Identity

Before settlement, a known coupon receivable belongs to the value of the trade. Once paid, it is removed from the trade and appears as cash. With cash received defined as positive, the payment component is:

$$
PaymentPnL=PV_{after}-PV_{before}+CashReceived
$$

When the expected amount settles correctly and both PVs use the same market state, payment PnL should be approximately zero. This is not a claim that the swap has no daily PnL. Rates moves, carry, curve rebuilding, and other effects may still change economic value. The identity isolates the mechanical cashflow transition.

The distinction also prevents double counting. Cash settlement is not added on top of full economic PnL when the starting PV already contains the receivable.

## Worked Numerical Example

The expected net cash is:

$$
NetCash=250{,}000-230{,}000=+GBP\ 20{,}000
$$

The same-snapshot PV change around the payment event is:

$$
PaymentPVChange=98{,}000-118{,}000=-GBP\ 20{,}000
$$

Therefore:

$$
PaymentPnL=-20{,}000+20{,}000=0
$$

Adding the separate market-and-carry component gives full-day economic PnL of +GBP 1,500.

Now suppose the cash ledger reports only GBP 19,700. The settlement break is:

$$
SettlementBreak=19{,}700-20{,}000=-GBP\ 300
$$

That GBP 300 should not be forced into rates market PnL. It may represent a fee, withholding, netting difference, incorrect coupon amount, partial settlement, or a delayed cash record. Its operational status and lineage matter as much as the number.

## Three Times That Must Not Be Collapsed

Payment processing often contains three different timestamps.

- **Contractual payment time:** when the contract says the coupon is due.
- **Valuation ex-cash time:** when the pricing engine removes the cashflow from PV.
- **Actual settlement time:** when cash is confirmed in the account or clearing ledger.

These times need not coincide. A valuation service may mark the trade ex-cash at the start of the business day, while the settlement message arrives hours later. During that gap, a dashboard that compares ex-cash PV with confirmed cash alone will show an apparent loss.

The correct response is a state such as `EXPECTED` or `PENDING_CASH`, not a confirmed PnL loss. A liquidity view should show that cash is not yet available, while an economic PnL view may include the expected contractual transfer under an explicitly labelled policy.

Clean-versus-dirty conventions create another trap. Dirty PV includes accrued value and due cashflows according to the valuation policy; clean PV removes specified accrued components. Joining an opening dirty PV to a closing clean PV can produce a perfectly deterministic but economically meaningless break. An API field named only `pv` is insufficient.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class SettlementStatus(Enum):
    EXPECTED = "EXPECTED"
    SETTLED = "SETTLED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CouponSettlement:
    pv_before_payment: Decimal
    pv_after_payment: Decimal
    expected_net_cash: Decimal
    actual_net_cash: Decimal | None
    other_economic_pnl: Decimal
    status: SettlementStatus
    currency: str
    valuation_snapshot_id: str
    cashflow_id: str


def reconcile_coupon_payment(x: CouponSettlement) -> dict:
    payment_pv_change = (
        x.pv_after_payment - x.pv_before_payment
    )
    payment_pnl = (
        payment_pv_change + x.expected_net_cash
    )

    settlement_break = None
    if x.actual_net_cash is not None:
        settlement_break = (
            x.actual_net_cash - x.expected_net_cash
        )

    return {
        "payment_pv_change": payment_pv_change,
        "expected_net_cash": x.expected_net_cash,
        "payment_pnl": payment_pnl,
        "total_economic_pnl": (
            payment_pnl + x.other_economic_pnl
        ),
        "actual_net_cash": x.actual_net_cash,
        "settlement_break": settlement_break,
        "settlement_status": x.status.value,
        "cashflow_id": x.cashflow_id,
        "snapshot_id": x.valuation_snapshot_id,
    }
```

The function deliberately distinguishes expected cash from actual cash. Expected cash supports the economic bridge; actual cash supports settlement reconciliation. Production policy must define whether an economic report may use expected cash before settlement confirmation, and the output must make that state visible.

## Data Quality and Production Controls

The highest-value controls are selective.

First, pre- and post-payment PVs must use the same market snapshot, model, currency, and clean/dirty convention. Second, cash sign, value date, and netting scope must be explicit. Third, a stable cashflow ID must prevent duplicate cash inclusion during replay. Fourth, missing actual cash must remain missing rather than being replaced by expected cash. Fifth, payment PnL, market-and-carry PnL, and settlement break must reconcile independently.

Useful observability includes payments expected but not settled, partial settlements, duplicate cashflow IDs, ex-cash-to-settlement latency, and breaks by currency or clearing venue.

## Requirement Discovery and Interview Questions

When a trader says, “The swap lost money when the coupon paid,” clarify:

- Is the dashboard showing clean PV, dirty PV, or economic value including cash?
- Are the fixed and floating legs settled gross or net?
- What sign convention applies to cash received?
- At what cutoff does the pricing engine mark the coupon ex-cash?
- Has actual cash settled, and on which value date?
- Are fees, withholding, clearing netting, or FX included?
- Should pending cash create a warning, a provisional component, or block publication?
- Do the PnL and liquidity views require different states?

An interview-quality answer should state the invariant first: same-snapshot PV drop plus signed cash should neutralise the payment event. Then discuss timing, conventions, and failed settlement.

## Trader–Developer Translation

**Trader:** “The swap PV dropped 20k after the coupon paid. Why is that a loss?”

**Developer:** “The pre-payment dirty PV included the 20k net receivable. Did the cash ledger receive the same amount?”

**Trader:** “Yes, the full 20k settled.”

**Developer:** “Then payment PnL is zero: PV fell 20k and cash rose 20k. I will show the 1.5k market-and-carry PnL separately and reconcile the payment by cashflow ID.”

## Key Takeaways

- A coupon payment transfers value from trade PV to cash; it is not automatically new profit.
- Same-snapshot dirty PV change plus signed cash isolates payment PnL.
- Contractual due time, valuation ex-cash time, and actual settlement time are distinct.
- Expected cash supports valuation explain; actual cash supports settlement confirmation.
- Clean/dirty convention and cash sign must be explicit API metadata.
- Pending or broken settlement must remain visible rather than being hidden in rates PnL.
