# Cash-Inclusive Swap PnL: A Coupon Payment Is Not a Loss

## Abstract

A swap can lose present value when a coupon leaves its future cashflow schedule without suffering an equivalent economic loss. The missing value has moved into cash. A reliable desk PnL bridge therefore reconciles remaining trade value and signed cash over the same interval. This article develops that bridge, explains the payment boundary, and shows how a Python developer can prevent a settlement transition from becoming a false trading loss.

## The desk problem

A trader sees a position valued at EUR 101,100 immediately before a coupon payment. Immediately after payment, its remaining value is EUR 1,100. The dashboard flashes a EUR 100,000 loss. Meanwhile, a cash record shows EUR 100,000 received.

Neither source necessarily contains an incorrect number. The error is combining a change in remaining value with a definition of PnL that ignores cash. The developer's first job is to establish what each number includes, not to suppress the apparent loss with an unexplained adjustment.

The previous lesson separated inception execution attribution from subsequent valuation change. Today we extend the valuation boundary to include a paid coupon. The central concept is cash-inclusive PnL; the closely related implementation issue is consistent payment cutoffs.

## Define the boundary before calculating

Consider an existing vanilla swap in one local currency. There are no new trades, amendments, termination payments, fees, collateral movements, or reporting-currency conversions. Opening and closing valuations cover the remaining contractual cashflows under an agreed inclusion policy.

Let $V_0$ and $V_1$ be opening and closing trade values. Let $C$ be contractual cash received during the interval, with payments represented as negative amounts. All values use the desk's perspective.

$$
P=V_1-V_0+C
$$

This is a cash-inclusive desk valuation bridge, not a prescription for financial-accounting recognition. It assumes the cash interval and the valuation inclusion boundary agree. Cash must not already be embedded in the closing value as a separate cash asset and then be added again.

For an instantaneous transition with other inputs held fixed, a coupon of amount $C$ moving from remaining trade value into cash produces a value change of minus $C$. Adding the received cash restores the economic total.

Across a real overnight interval, discounting, market changes, fixings, and financing may also matter. The formula captures the chosen total; it does not prove that every remaining contribution is market PnL.

## Worked example

Use synthetic values immediately around a payment boundary. The due receivable is worth its cash amount at that boundary, and the other swap cashflows are worth EUR 1,100.

| Component | Before payment | After payment |
| --- | ---: | ---: |
| Due coupon included in trade value | 100,000 | 0 |
| Remaining swap cashflows | 1,100 | 1,100 |
| Total trade PV | 101,100 | 1,100 |
| Cash received during interval | — | 100,000 |

The trade PV change is minus EUR 100,000. Cash-inclusive PnL is EUR 1,100 minus EUR 101,100 plus EUR 100,000, which equals zero.

Now suppose the remaining cashflows instead close at EUR 1,350. The same bridge gives positive EUR 250. That is the residual economic change under the stated boundary. Calling it a pure curve-market contribution requires a separate controlled attribution.

The sign convention also works for a payment. If the opening trade includes a payable worth minus EUR 100,000, removing it raises trade PV by EUR 100,000. The signed cash payment is minus EUR 100,000, so the transition alone still produces zero PnL.

Do not treat receipt as profit simply because cash is positive. It settles a receivable already included in opening wealth.

## The payment-date trap

“Exclude today's payments” is not a complete requirement. A pricer may remove a coupon according to a contractual-date cutoff before the cash feed reports actual settlement. If the payment is still unpaid, dropping it from trade value without retaining a receivable creates an artificial loss.

A consistent alternative boundary includes the unpaid receivable as an explicit asset until settlement. When cash arrives, the receivable disappears and cash replaces it. This article does not implement that lifecycle; it requires the simple bridge to reject an unmatched boundary rather than invent cash.

The same warning applies in reverse: keeping a paid coupon in closing trade PV and adding the cash receipt double counts its value. Payment dates, actual settlement timestamps, and valuation cashflow-inclusion policies must be distinguishable.

## A compact calculation contract

The arithmetic should be small. The input contract should be precise.

```python
from decimal import Decimal

def cash_pnl(opening_pv, closing_pv, signed_cash, *, boundary_matched):
    if not boundary_matched:
        raise ValueError("Reconcile coupon inclusion and settlement first")
    pv_change = closing_pv - opening_pv
    return {
        "pv_change": pv_change,
        "contractual_cash": signed_cash,
        "total_pnl": pv_change + signed_cash,
    }

result = cash_pnl(
    Decimal("101100"), Decimal("1100"), Decimal("100000"),
    boundary_matched=True,
)
```

The flag represents an upstream reconciliation result, not a user-controlled bypass. Inputs require matching currency, trade identity, valuation scope, and finite amounts. A decimal representation avoids incidental binary rounding in the illustration but does not replace agreed valuation tolerances.

Retain the opening and closing valuation identifiers, cash event identities, and interval definition alongside the output. A dashboard should display PV change, contractual cash, total PnL, and reconciliation status. Users can then distinguish an economic result from a missing feed.

## Four production controls

1. Align the cutoff. For example, use an agreed opening-exclusive, closing-inclusive cash interval and compatible valuation snapshots. Specify timestamp timezone explicitly.
2. Reconcile inclusion. A coupon removed from closing trade PV must be represented by settled cash or an explicitly retained receivable under the chosen boundary.
3. Deduplicate cash events. Feed replay must not add the same receipt twice. Apply corrections and reversals through their documented event semantics.
4. Separate contractual cash from collateral and transfers. A collateral movement is not automatically swap coupon income.

Test a pure receipt transition, a pure payment transition, a EUR 250 residual, and an unmatched settlement state. A replayed event should leave the result unchanged. The reconciliation error should remain visible rather than becoming an unexplained balancing item.

## Requirement discovery and interview practice

When asked to fix a payment-day PnL jump, ask: Does closing PV include today's coupon? Does the cash feed represent scheduled or settled amounts? What happens to an unpaid receivable? Are the valuation and cash intervals aligned?

A useful desk response is: “The PV fell because the coupon left the remaining schedule. I will reconcile that removal with signed contractual cash before classifying any residual as trading PnL.”

## Key takeaways

PnL follows value across the trade-to-cash boundary. A coupon receipt is not automatically new profit, and a falling trade PV is not automatically a loss. A good developer makes inclusion rules explicit, preserves event identity, and refuses to hide unmatched settlement states.

All examples are synthetic and educational. They contain no confidential employer or client information, proprietary architecture, or investment advice.
