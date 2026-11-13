# After the Coupon Has Settled: Fixing Corrections Become Adjustment Claims

## Abstract

A fixing correction received before payment changes an unpaid coupon. The same correction received after payment cannot change cash that already moved. It instead creates a contractual adjustment claim or obligation, subject to validation and the applicable agreement. This article explains a signed entitlement-versus-settlement reconciliation, shows how correction recognition differs from later cash settlement, and presents a compact engineering calculation that prevents duplicate PnL and duplicate payments. The scope is one linear term-rate coupon in one currency, not legal advice or a universal accounting policy.

## Desk Context

A receive-floating coupon of GBP 1,060,000 has settled. The reference observation is then corrected downward, making the validated contractual amount GBP 1,057,500.

The pricing developer has two tempting but incorrect shortcuts: reopen the original coupon and send the corrected full amount again, or rewrite historical cash to the smaller amount. Neither represents what happened. The original cash remains a fact; the difference is a separate adjustment payable.

This extends an incremental fixing bridge across the payment boundary. Before settlement, the revised amount remains in unpaid trade value. After settlement, the adjustment may live outside remaining derivative PV. An explain report that ignores that location can show no correction loss, followed by an unexplained cash loss when the refund eventually occurs.

## Entitlement and Cash Are Different Quantities

Use signed amounts throughout: receipts are positive and payments negative. Let E be the latest validated signed entitlement for the coupon and C the cumulative signed cash already settled against it, including any completed adjustments.

The outstanding adjustment is

$$
A=E-C
$$

A positive result is a receivable; a negative result is a payable. This identity reconciles contractual economics to actual settlement. It is not itself an authorization to pay, and it does not imply that every published data revision is automatically enforceable under every contract.

The calculation should run only after the observation revision, coupon linkage, and contractual applicability have been accepted. A proposed or disputed claim needs an explicit state and valuation policy rather than being silently treated as confirmed cash.

## Worked Numerical Example

Assume an uncapped, uncompounded receive-floating coupon:

| Input | Value |
|---|---:|
| Notional | GBP 100,000,000 |
| Accrual fraction | 0.25 |
| Original rate | 4.24% |
| Corrected rate | 4.23% |
| Original cash received | GBP 1,060,000 |

The original cashflow equals notional times accrual fraction times 0.0424. The corrected contractual cashflow is GBP 1,057,500.

The outstanding amount is

$$
A=1{,}057{,}500-1{,}060{,}000=-2{,}500
$$

The position therefore has a GBP 2,500 payable, not another GBP 1,057,500 receipt.

Suppose the approved discount factor to the expected adjustment settlement date is 0.999. At correction recognition, its signed value is GBP -2,497.50. This is the current economic correction impact if no related adjustment was previously recognized and other inputs are held fixed.

| Moment | Cash movement | Outstanding adjustment value |
|---|---:|---:|
| Immediately before correction | 0 | 0 |
| Accepted correction | 0 | -2,497.50 |
| Refund settlement, immediately before transfer | 0 | -2,500 |
| Immediately after refund | -2,500 | 0 |

At settlement, the payable disappears while cash decreases by the same amount. The transfer itself creates no new loss. The GBP 2.50 change from initial recognition to the payment-date value is a separate time/valuation effect under the simplified assumptions, not a second GBP 2,500 correction.

This also explains why a historical frozen-discount restatement can differ from today’s adjustment value. They refer to different comparison times and potentially different payment dates.

## Do Not Reopen Settled History Blindly

Keep the original settled cashflow immutable. Link the adjustment to the original coupon, accepted fixing revision, and settlement history.

If another validated correction arrives, recompute the outstanding amount against cumulative actual settlements. Do not emit the entire newly calculated balance as a fresh additive payment instruction on every run. The outstanding balance is a level; a payment instruction is an authorized action with its own identity and lifecycle.

For example, once the GBP 2,500 refund settles, cumulative signed cash becomes GBP 1,057,500. The outstanding adjustment becomes zero. Replaying the same accepted correction must not create another refund.

Partial adjustment settlements use the same identity. A GBP 1,000 refund reduces the remaining payable to GBP 1,500. Cash confirmations update settlement state, not the contractual entitlement.

## Engineering Connection

A compact reconciliation function can expose the economics without hiding authorization inside arithmetic:

```python
def reconcile_adjustment(
    accepted_entitlement,
    settled_cash,
    adjustment_discount_factor,
    previously_recognized_pv,
):
    outstanding = accepted_entitlement - settled_cash
    current_pv = outstanding * adjustment_discount_factor

    return {
        "outstanding_signed_amount": outstanding,
        "adjustment_pv": current_pv,
        "valuation_delta": current_pv - previously_recognized_pv,
        "direction": (
            "RECEIVABLE" if outstanding > 0
            else "PAYABLE" if outstanding < 0
            else "FLAT"
        ),
    }
```

The function does not send a payment. Its valuation delta also needs classification: if discounting or time changed, it is not purely fixing-correction PnL. Isolate a correction using old and new accepted entitlements under the same settlement ledger and valuation context.

The settlement ledger should be reconciled to confirmed cash movements rather than inferred from payment instructions. An instruction can fail, be cancelled, or settle partially.

## Selective Production Controls

Four controls are especially relevant:

1. Preserve original cash history. Never replace a completed cash record with a corrected hypothetical amount.
2. Link claims precisely. Record original coupon identity, accepted observation revision, claim currency, signed amount, and contractual approval state.
3. Separate valuation from authorization. A payable balance must not automatically generate a payment without the approved settlement workflow.
4. Prevent duplicate adjustment settlement. Use stable instruction identities, revision-aware processing, and reconciliation against cumulative confirmed cash.

Tests should cover downward and upward corrections, pay-floating direction, duplicate messages, partial refunds, failed instructions, and a second revision after an adjustment has settled. Monitor aged receivables/payables and valuation-to-ledger mismatches, rather than only checking that the derivative risk run is green.

## Requirement Discovery and Interview Questions

Ask whether the contractual correction has been accepted, which entity owns the claim, and whether settlement is gross or netted with another payment. Confirm the expected adjustment date, discounting policy, reporting cutoff, and owner of disputed claims.

Also ask whether an adjustment value is already included in trade PV, a separate receivable ledger, or both. Economic value must appear exactly once in the consolidated PnL boundary.

A strong interview answer is: “After settlement, I preserve actual cash and reconcile the latest accepted entitlement against cumulative settled cash. I value the resulting adjustment claim separately and treat its later settlement as a value transfer, not a second correction loss.”

## Key Takeaways

- A correction cannot rewrite cash that has already settled.
- Latest accepted entitlement minus cumulative settled cash gives the outstanding adjustment.
- Correction recognition and adjustment settlement are different events.
- An outstanding balance is not a new payment instruction on every replay.
- Consolidated PnL must include the claim once, wherever its value is recorded.

All figures are generic educational examples. Contractual enforceability and accounting treatment require the applicable approved policy; this article provides neither legal nor investment advice.
