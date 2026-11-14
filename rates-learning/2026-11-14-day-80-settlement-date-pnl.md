# Settlement-Date PnL: Why an Unchanged Claim Can Change Value

## Abstract

A settlement adjustment can retain the same contractual amount while its present value changes because the expected receipt or payment date moves. Treating that change as another fixing correction obscures the real driver. This article isolates a settlement-date update under frozen market inputs, demonstrates the signed discounting effect for receivables and payables, and shows how to distinguish a valuation assumption from a contractual due date. The scope is a deterministic single-currency claim, without credit impairment, compensation interest, fees, or a broader funding model.

## Desk Context

Yesterday’s workflow created an adjustment receivable linked to a settled coupon. Today, operations expects collection later than previously assumed. The claim amount has not changed, the original settled cash is unchanged, and no additional fixing revision has arrived.

Nevertheless, the valuation moves. With positive discount rates, a later receipt generally has a lower present value. The desk asks whether the movement belongs to fixing PnL, market PnL, or an operational adjustment.

The answer requires a controlled comparison. Hold valuation time, amount, currency, and curve snapshot fixed; change only the approved expected settlement date. The resulting difference is settlement-date assumption PnL. It should not be confused with ordinary time passage or a fresh market-curve move.

## Three Dates, Three Meanings

The contractual due date states when an obligation is due under the applicable agreement. The expected settlement date is the date used in an approved valuation assumption. The actual value date records when cash really transfers.

An operations message revising expected timing does not automatically amend the contractual obligation. The original due date must remain available for aging, escalation, and any applicable compensation process.

A deterministic expected date is also a simplification. If receipt timing is materially uncertain, valuation may require scenarios or another approved method. That uncertainty should not be hidden behind a precise but unsupported date.

## The Controlled Calculation

Let A be the signed outstanding claim: positive for a receivable and negative for a payable. Let D(t,T) be the approved discount factor at valuation time t for settlement date T.

Claim value is

$$
V=A D(t,T)
$$

At the same valuation time and market snapshot, changing the date from T0 to T1 gives

$$
P_{date}=A[D(t,T_1)-D(t,T_0)]
$$

The formula is exact for the stipulated fixed-amount deterministic claim. It excludes changes in entitlement, actual cash settlement, compensation interest, and credit valuation. Those effects need separate inputs and classification.

The direction is conditional on the discount curve. Under ordinary positive-rate discounting, later discount factors are smaller. Negative rates or a non-monotonic curve can reverse that intuition; calculate the factors rather than hard-code the PnL sign.

## Worked Numerical Example

Suppose an accepted receivable has the following generic illustrative values:

| Input | Value |
|---|---:|
| Signed outstanding amount | GBP +2,500,000 |
| Discount factor to old expected date | 0.9990 |
| Discount factor to revised expected date | 0.9986 |

The old value is GBP 2,497,500. The revised value is GBP 2,496,500.

The date-only effect is

$$
2{,}500{,}000\times(0.9986-0.9990)=-1{,}000
$$

No cash moved and no amount was written off. The GBP 1,000 decline comes entirely from the revised timing assumption under the frozen curve.

For a payable of GBP -2,500,000, the same factors produce GBP +1,000 of model value change. That arithmetic does not imply that deliberately delaying payment is appropriate or economically beneficial after compensation, funding, credit, and legal consequences. Those are excluded from this narrow comparison.

## Separate the Date Update from the Curve Move

Suppose the current market curve then values the revised settlement date at a discount factor of 0.9985. Closing claim PV becomes GBP 2,496,250.

Using a date-first convention, the bridge is:

| Component | GBP |
|---|---:|
| Date update on the frozen curve | -1,000 |
| Curve update at the revised date | -250 |
| Total selected PV change | -1,250 |

The two components sum to the opening-to-closing value difference. As with other sequential attribution ladders, the chosen order can allocate interaction differently. Save the convention rather than presenting it as a uniquely determined economic decomposition.

If the valuation timestamp also advances, introduce an explicit time-roll state. Comparing yesterday’s old-date PV directly with today’s revised-date PV mixes at least three dimensions: time, market, and timing assumption.

## Engineering Connection

The calculation should receive discount factors already obtained from a versioned valuation context:

```python
def settlement_date_bridge(
    signed_amount,
    old_date_df_frozen,
    new_date_df_frozen,
    new_date_df_current,
):
    old_pv = signed_amount * old_date_df_frozen
    date_updated_pv = signed_amount * new_date_df_frozen
    closing_pv = signed_amount * new_date_df_current

    return {
        "date_change_pnl": date_updated_pv - old_pv,
        "market_pnl": closing_pv - date_updated_pv,
        "total_pnl": closing_pv - old_pv,
        "closing_pv": closing_pv,
    }
```

The wrapper verifies that the amount and valuation timestamp are unchanged for the date leg, and that all factors belong to the intended currency and curve policy. Dates, market snapshot identifiers, assumption version, and approval reason should accompany the numerical result.

This function does not authorize settlement and does not rewrite the contractual due date. It merely exposes how the approved valuation assumption changes value.

## Selective Production Controls

Four controls are especially useful:

1. Preserve date semantics. Keep contractual due date, expected date, and actual value date as separate fields.
2. Version timing assumptions. Record the old and new dates, evidence, approval, effective time, and known-at time.
3. Validate calendar and cutoff treatment. Apply the approved business-day rules and reject ambiguous or unsupported timing updates.
4. Reconcile attribution boundaries. A date-only comparison must freeze amount, valuation time, and market state; compensation and credit adjustments remain separate.

Tests should cover receivables, payables, identical dates, negative-rate factors, calendar boundaries, and a claim that has already settled. A settled claim should not retain an outstanding timing valuation merely because a late operations update arrives.

A dashboard should show outstanding amount, original due date, current expected date, assumption-change PnL, and an aging exception. A date update must not reset aging and make an overdue claim appear newly originated.

## Requirement Discovery and Interview Questions

Ask who approves the revised expected date, what evidence supports it, and whether the change is an operational forecast or a contractual amendment. Confirm the discounting policy, compensation-interest scope, valuation cutoff, and treatment of uncertain timing.

Also clarify the reporting label. Calling every decline “market loss” is misleading if the curve did not move. Calling it “credit loss” is equally unsupported without a credit assessment.

A concise interview answer is: “I isolate settlement-date PnL by changing only the approved expected date under frozen valuation time, amount, and curve. I preserve the contractual due date for aging and separate timing assumptions from credit, compensation, and cash settlement.”

## Key Takeaways

- A fixed claim amount does not imply fixed PV.
- Date-only attribution requires a common valuation time and frozen curve.
- Expected settlement is not the same as contractual due date.
- Sign intuition depends on both claim direction and discount factors.
- Timing updates must not hide overdue status or duplicate a correction component.

All figures are generic educational examples and do not constitute investment or legal advice.
