# Compensation Interest: A Separate Cashflow, Not a Plug for Settlement PnL

## Abstract

A delayed receivable can lose present value because its expected payment date moves. Compensation interest may offset part of that effect, but it is a separate economic claim with its own amount, accrual convention, approval state, and settlement date. Setting compensation equal to an unexplained loss creates a convenient reconciliation without a valid entitlement. This article develops a controlled compensation bridge for a fixed-rate simple-interest example and shows how to avoid recognizing both a cumulative interest amount and the same accrual again.

## The Desk Scenario

A rates settlement adjustment of GBP 2,500,000 is collected later than originally expected. On a frozen valuation curve, the principal’s discount factor changes from 0.9990 to 0.9986. The date-only principal PV change is GBP -1,000.

Operations then reports an accepted compensation amount calculated at an illustrative 4.50% simple annual rate for four calendar days on an ACT/365 basis. The trader asks whether the settlement loss has now disappeared.

Not exactly. Compensation is not defined by the principal’s valuation loss. It follows the applicable accepted terms, while principal timing PnL follows the discounting policy. Different rates, day counts, periods, and payment dates mean the two numbers need not cancel.

## Separate Principal from Compensation

The principal claim remains GBP 2,500,000. Compensation is a linked but distinct cashflow. For a constant principal A, fixed annual rate r, and accepted accrual fraction a, simple compensation is

$$
I=Ara
$$

This is a stipulated example, not a statement about any benchmark or agreement’s mandatory treatment. Actual terms may use a floating rate, compounding, grace periods, different day counts, or no compensation entitlement at all.

The start and end boundaries must be defined. “Four days late” is not enough if one system includes both dates while another uses a start-inclusive, end-exclusive interval. Business-day settlement calendars and calendar-day interest accrual also answer different questions.

The signed compensation value is the signed amount multiplied by the discount factor to its own payment date. If compensation settles separately from principal, it must not inherit the principal’s discount factor without checking the date.

## Worked Numerical Example

Use these generic illustrative inputs:

| Input | Value |
|---|---:|
| Receivable principal | GBP 2,500,000 |
| Accepted fixed compensation rate | 4.50% |
| Accepted calendar-day accrual | 4 days |
| Day-count basis | ACT/365 |
| Compensation payment discount factor | 0.9986 |

The accrued compensation amount is

$$
I=2{,}500{,}000\times0.045\times\frac{4}{365}
$$

Rounded for display, this equals GBP 1,232.88. Its discounted value is approximately GBP 1,231.15, using full precision before rounding.

The controlled bridge is:

| Component | GBP |
|---|---:|
| Principal settlement-date change | -1,000.00 |
| Newly recognized compensation PV | +1,231.15 |
| Combined selected value change | +231.15 |

The positive net result does not establish that delay is desirable. The example excludes funding, fees, credit effects, disputes, and other operational consequences. It only reconciles two specified components.

Nor is GBP +1,231.15 always today’s PnL. It is the recognition effect only if the opening valuation contained no compensation value and the accepted claim is now recognized under the approved policy.

## Cumulative Accrual Is Not Daily PnL

Suppose yesterday’s accepted compensation amount already represented three days at the same rate. At a common frozen discount factor, the fourth day adds one day of interest, not the entire four-day cumulative total.

One day’s nominal increment is approximately GBP 308.22. Its PV at 0.9986 is approximately GBP 307.79. Adding the full four-day GBP 1,231.15 again would double count the first three days.

This is the same level-versus-delta distinction used for fixing revisions. The latest cumulative claim is a state. PnL is the change from the previously recognized value, adjusted for cash and separately classified valuation effects.

If time or discount factors also change between runs, the PV difference contains more than new interest accrual. Use intermediate states to isolate accrual, market revaluation, and any recognition-policy change.

## Recognition and Settlement Are Different Events

A proposed calculation, an accepted entitlement, a recognized asset, and settled cash are not interchangeable states. A pending claim may require an approved valuation treatment; its nominal requested amount is not automatically official PnL.

Once recognized compensation settles, cash increases and the receivable disappears. That transfer should not create the interest gain again. Any difference between the settled amount and the previously carried value needs an explicit explain.

A waiver or revised accepted rate likewise changes the existing claim. It does not justify deleting audit history or appending an unrelated negative cashflow without lineage.

## Engineering Connection

Keep the calculation narrow and make recognition context explicit:

```python
def compensation_bridge(
    principal,
    accepted_rate,
    accepted_year_fraction,
    compensation_df,
    prior_compensation_pv,
    principal_date_pnl,
):
    amount = principal * accepted_rate * accepted_year_fraction
    current_pv = amount * compensation_df
    compensation_delta = current_pv - prior_compensation_pv

    return {
        "cumulative_compensation_amount": amount,
        "compensation_pv": current_pv,
        "compensation_valuation_delta": compensation_delta,
        "principal_date_pnl": principal_date_pnl,
        "combined_delta": principal_date_pnl + compensation_delta,
    }
```

The caller verifies accepted terms, currency, direction, amount coverage, and a common comparison context. This example assumes a positive receivable and no compensation settlement inside the comparison interval. A general implementation needs signed claims and a cash-inclusive bridge.

Use precision appropriate to the approved cashflow policy. Do not round each daily accrual and then assume the sum equals a final calculation rounded once; the contractual rounding rule decides which result is authoritative.

## Selective Production Controls

Four controls matter especially:

1. Version accepted terms. Store principal coverage, rate, period boundaries, day count, rounding rule, and approval evidence.
2. Keep valuation components separate. Principal timing PnL and compensation PV must remain independently visible and must never be forced to cancel.
3. Recognize increments once. Compare against prior recognized value and account for any intervening settlement rather than repeatedly adding cumulative interest.
4. Preserve payment-date linkage. Compensation has its own expected payment date, settlement status, and discounting lineage.

Tests should cover zero days, interval boundaries, a rate revision, partial principal repayment, duplicate acceptance messages, and the difference between daily and final rounding. A partial repayment requires segmented principal balances; applying the original amount across the whole period overstates interest.

## Requirement Discovery and Takeaways

Ask whether compensation is contractually applicable and accepted, which balance accrues, which days count, whether the rate is fixed or floating, and when payment is expected. Confirm whether accrued value was already recognized and whether a dispute or waiver changes that treatment.

A strong desk response is: “I value compensation as a separate accepted cashflow under its own accrual and settlement terms. I reconcile its incremental recognized value alongside principal timing PnL, rather than using it as an offsetting plug.”

The main lesson is that compensation can offset timing loss without being defined by that loss. Reconciliation should explain economic components, not manufacture equality between unrelated calculations.

All numbers are generic educational examples. Contractual applicability and accounting recognition follow approved policy; this article is not legal or investment advice.
