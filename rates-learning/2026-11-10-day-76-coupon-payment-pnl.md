# Coupon Payment PnL: Reconcile Value and Cash Before Explaining Rates

## Abstract

A coupon payment can make a rates trade’s remaining present value fall sharply without creating an economic loss. The value has moved from the derivative into cash or a settlement receivable. A PnL engine that compares only opening and closing trade PV will misclassify this lifecycle transition as market loss. This article develops a cash-inclusive payment-day bridge, illustrates its numerical reconciliation, and explains the engineering boundary between contractual cashflow entitlement and operational settlement. The objective is reliable desk explain, not a comprehensive accounting policy.

## A Payment-Day Desk Incident

A receive-fixed swap book opens with GBP 1,200,000 of value. During the day it receives a net coupon of GBP 250,000. Its closing remaining-trade PV is GBP 953,000.

The trader sees a GBP 247,000 PV decline and asks whether the curve moved against the book. The answer cannot come from the PV difference alone. GBP 250,000 has left the trade’s future cashflow set and become an asset outside that remaining-trade valuation. Once that amount is included, economic PnL is positive GBP 3,000.

This is a useful boundary for market-risk explain. Before asking DV01, gamma, or a full-revaluation ladder to explain a loss, reconcile lifecycle value transfers. A numerical attribution engine cannot repair a missing economic component.

## Define the Value Boundary First

For this lesson, opening value includes the payment entitlement, while closing trade PV excludes the detached coupon. Cashflow amounts are signed: receipts are positive and payments are negative. All amounts are in one currency, and external capital flows, fees, funding, taxes, and FX translation are excluded.

With that boundary, cash-inclusive PnL is

$$
P = V_1 - V_0 + C
$$

Here $C$ is the net entitlement that leaves the trade valuation during the interval and is recognized exactly once outside it. For a settled coupon it is cash. If settlement is delayed, it may instead be a separately valued receivable or payable.

This is an economic bridge, not a rule that every accounting system should book the same journal entry. If a valuation already retains the receivable, adding it again double counts. The implementation must identify exactly where the entitlement lives at both endpoints.

Do not combine clean PV at one endpoint with dirty PV at the other. Accrued interest and coupon detachment conventions must be consistent. For a swap with two legs paying on the same day, use the signed amounts from both legs or the approved net settlement, not only the receive-fixed coupon.

## Worked Numerical Example

Assume:

| Component | GBP |
|---|---:|
| Opening value, including coupon entitlement | 1,200,000 |
| Closing remaining-trade PV | 953,000 |
| Net coupon received | +250,000 |

The trade-PV change is GBP -247,000. Cash-inclusive economic PnL is

$$
P = -247{,}000 + 250{,}000 = 3{,}000
$$

Now introduce a controlled no-market-move roll. Advance valuation time to the closing point using a documented frozen-market roll policy, apply the same coupon lifecycle transition, and obtain GBP 952,000 of remaining-trade PV.

The cash-inclusive rolled baseline is GBP 952,000 plus GBP 250,000, or GBP 1,202,000. Relative to the opening value, time and lifecycle contribute GBP +2,000. Closing market value then adds GBP 1,000 relative to the rolled remaining-trade PV.

| Bridge component | GBP |
|---|---:|
| Time/lifecycle, including coupon transfer | +2,000 |
| Market move after the controlled roll | +1,000 |
| Total economic PnL | +3,000 |

The GBP 250,000 payment is not an additional profit component after this decomposition: it is already included in the time/lifecycle bridge. Adding it once more would double count.

The frozen-market roll is itself a policy choice. Holding curve quotes fixed and rebuilding at a later valuation date is not identical to holding every discount factor fixed. Store the roll policy and do not describe the result as a universally unique definition of carry.

## Entitlement Is Not Settlement Status

An operational settlement feed can arrive after the pricing engine has removed the coupon from future cashflows. If the PnL engine recognizes value only when a cash confirmation arrives, it temporarily creates an artificial loss.

Conversely, recognizing both the payment entitlement and a later settlement message as new PnL creates an artificial gain. The settlement confirmation changes the asset’s state from receivable to cash; absent valuation or fee changes, it does not create the coupon’s value again.

A delayed payment should not be relabeled as settled. Preserve the outstanding receivable and operational exception. Material credit, discounting, or funding consequences require their own policy; they are outside this simple example.

## Engineering Connection

The main calculation can remain small when inputs have already passed lifecycle and currency checks:

```python
def payment_day_bridge(
    opening_value,
    rolled_remaining_pv,
    closing_remaining_pv,
    detached_entitlement,
):
    time_lifecycle = (
        rolled_remaining_pv
        + detached_entitlement
        - opening_value
    )
    market = closing_remaining_pv - rolled_remaining_pv
    total = (
        closing_remaining_pv
        + detached_entitlement
        - opening_value
    )

    return {
        "time_lifecycle_pnl": time_lifecycle,
        "market_pnl": market,
        "economic_pnl": total,
        "reconciliation_error": time_lifecycle + market - total,
    }
```

The entitlement input must be assembled from stable cashflow identities, not a sum of every message received. A cashflow key should distinguish trade, leg, accrual period, currency, and payment date. Corrections should revise the same entitlement rather than append duplicate economic cashflows.

## Selective Production Controls

Four controls are especially relevant:

1. Align endpoint inclusion. Confirm that opening PV contains the coupon and closing remaining-trade PV excludes it.
2. Reconcile entitlement to settlement. Distinguish due, receivable, and settled states without recognizing the same value twice.
3. Validate payment economics. Include signed cashflows from both legs, business-day-adjusted dates, and the applicable valuation cutoff.
4. Version the roll policy. The rolled baseline must use the same trades and lifecycle treatment as the actual closing run.

Tests should cover receipts, payments, two-leg netting, delayed settlement, duplicate confirmations, and a coupon still included in closing PV. A dashboard should show remaining PV change, detached entitlement, economic PnL, and settlement exception separately.

## Questions to Ask the Trader and Quant

Does “daily PnL” mean trade-PV change or cash-inclusive economics? Is the opening number clean or dirty? Which cutoff detaches a coupon? Are both legs netted? Where does an unsettled receivable appear? Which frozen-market roll defines the time component?

A strong interview answer is: “I reconcile remaining trade value with detached cashflow entitlement before attributing market PnL. Settlement changes the location of value, not necessarily economic profit. I make endpoint inclusion and duplicate-recognition controls explicit.”

## Key Takeaways

- A payment-day PV decline is not automatically a market loss.
- Economic reconciliation must include value transferred into cash or receivables exactly once.
- Contractual entitlement and settlement confirmation are different states.
- Carry and market attribution require an explicit rolled baseline.
- Lifecycle reconciliation comes before a Greek-based or full-revaluation market explain.

All figures are generic educational examples and do not constitute investment advice.
