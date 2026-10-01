# Delivery Timing Option: Engineering the Optimal Bond-Futures Delivery Date

## Abstract

A physical bond-futures contract can give the short more than a choice of deliverable bond. When contract rules permit delivery across a window, the short may also choose when to deliver. That timing option has economic value because funding cost, coupon entitlement, accrued interest and invoice proceeds change with the date. This article explains the intuition, works through a numerical example, and designs a production calculation that ranks every eligible date without hiding missing inputs or coupon discontinuities.

## Desk Context

Assume the cheapest-to-deliver bond has already been identified. A trader now sees two outputs:

- delivery on the first eligible day produces an estimated gain of 0.060 price points;
- delivery on day 20 produces an estimated gain of 0.125 points.

The trader asks why the preferred date moved even though the bond and futures position did not change.

The answer is that “CTD” identifies a bond under a delivery methodology, while “optimal delivery date” compares the economics of holding and delivering that bond on different eligible dates. A change in term repo, coupon entitlement or expected invoice proceeds can change the timing winner without changing the position.

## The Delivery Timing Option

For a simplified short-futures delivery strategy, define the net cost of a candidate delivery date as:

$$
\text{Net delivery cost}(d)
=
\text{purchase dirty price}
+
\text{funding cost}(d)
-
\text{coupon cash}(d)
-
\text{invoice price}(d)
$$

The invoice amount per 100 face is:

$$
\text{Invoice price}(d)
=
\text{futures price}(d)\times\text{conversion factor}
+
\text{accrued interest}(d)
$$

Using a lower-is-better cost convention, the preferred date is:

$$
d^*
=
\arg\min_d
\text{Net delivery cost}(d)
$$

This is not necessarily a forecast of future markets. It is a ranking under stated assumptions. A production implementation may use frozen prices for a diagnostic view, forward cash and futures assumptions for a planning view, or scenario curves for stress analysis. Those outputs need different methodology labels.

The main date-dependent components are:

- **Funding:** holding the cash bond longer normally increases financing cost.
- **Accrued interest:** the invoice includes accrued interest on the delivery date.
- **Coupon entitlement:** crossing an ex-coupon, record or payment date can create a discrete cash-flow change.
- **Repo specialness:** cheap bond-specific financing may make waiting more attractive.
- **Futures carry:** the assumed futures settlement price can change through the window.

## Worked Example

Consider one CTD bond with the following simplified inputs:

- purchase dirty price: 102.40;
- futures price: 111.00;
- conversion factor: 0.9200;
- repo rate: 3.60%;
- day-count basis: 360;
- no coupon payment inside the window;
- all other prices held constant.

For delivery on day 1:

$$
\text{Funding}_1
=
102.40\times3.60\%\times\frac{1}{360}
=
0.01024
$$

If delivery accrued interest is 0.35:

$$
\text{Invoice}_1
=
111.00\times0.9200+0.35
=
102.47
$$

Therefore:

$$
\text{Net cost}_1
=
102.40+0.01024-102.47
=
-0.05976
$$

The negative cost represents a simplified gain of approximately 0.060 points.

For delivery on day 20:

$$
\text{Funding}_{20}
=
102.40\times3.60\%\times\frac{20}{360}
=
0.20480
$$

If accrued interest has increased to 0.61:

$$
\text{Invoice}_{20}
=
111.00\times0.9200+0.61
=
102.73
$$

Then:

$$
\text{Net cost}_{20}
=
102.40+0.20480-102.73
=
-0.12520
$$

Under these frozen assumptions, day 20 is better by about 0.065 points. That result is conditional, not investment advice. A higher repo rate, a change in specialness, a coupon event or a different futures-price assumption could reverse the ranking.

## Why Coupon Dates Break Linear Intuition

Accrued interest often looks smooth between coupon dates, which can tempt developers to model timing economics as a simple daily line. Coupon boundaries invalidate that shortcut.

Around a coupon event:

- accrued interest resets;
- a cash coupon may be received;
- ex-coupon or record-date rules determine entitlement;
- settlement calendars can separate economic entitlement from payment timing.

The coupon and accrued-interest calculations must therefore come from the same versioned cash-flow engine. Otherwise one service may add coupon cash while another fails to reset accrued interest, double-counting the same economic event. The opposite error—omitting both effects—can also move the apparent optimum to the wrong side of the coupon date.

## Engineering Design

The robust approach is to enumerate every eligible business date and persist the component breakdown.

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class DeliveryDateResult:
    delivery_date: date
    funding_cost: Decimal
    coupon_cash: Decimal
    invoice_price: Decimal
    net_delivery_cost: Decimal
    status: str


def rank_delivery_dates(contract, bond, market, policy):
    results = []

    for delivery_date in policy.eligible_dates(contract):
        funding = funding_to_date(
            dirty_price=market.purchase_dirty(bond),
            repo_curve=market.repo_curve(bond),
            end_date=delivery_date,
        )
        coupon = coupon_entitlement(
            bond=bond,
            settlement_date=delivery_date,
        )
        invoice = (
            market.futures_price(delivery_date)
            * contract.conversion_factor(bond)
            + accrued_interest(bond, delivery_date)
        )

        results.append(DeliveryDateResult(
            delivery_date=delivery_date,
            funding_cost=funding,
            coupon_cash=coupon,
            invoice_price=invoice,
            net_delivery_cost=(
                market.purchase_dirty(bond)
                + funding
                - coupon
                - invoice
            ),
            status="SUCCESS",
        ))

    require_all_dates_successful(results)
    return sorted(results, key=lambda x: x.net_delivery_cost)
```

The result should retain contract-rules version, eligible-date calendar, market snapshot, repo-curve version, price-side assumptions and cash-flow version. A winner without this lineage cannot be reproduced.

## Data Quality and Production Controls

Five controls provide most of the value:

1. Eligible dates must come from the correct contract month, notice rules and business calendar.
2. Coupon entitlement and accrued-interest reset must use one consistent cash-flow engine.
3. Repo, cash and futures assumptions must cover the entire delivery window.
4. A failed date must not be silently excluded while the remaining set is labelled complete.
5. The dashboard should show the winner, runner-up, cost gap and component-level change.

The runner-up gap is operationally important. A tiny gap means the recommendation can switch after a small market move. Showing only one “optimal” date creates false certainty.

## Requirement Discovery and Interview Questions

When a trader asks for the best delivery date, clarify:

- Are all eligible dates required, or only the first and last?
- Should the calculation freeze today’s prices or use forward assumptions?
- Is funding based on GC or bond-specific repo?
- Which coupon and ex-coupon rules apply?
- How is the future futures settlement price determined?
- Should the output be net cost, profit, IRR or difference versus first delivery?
- What runner-up gap should trigger an alert?
- Does one failed date invalidate the entire ranking?

A strong interview explanation connects the economics to system design: the timing option is a date-indexed calculation with discontinuities, not a single scalar attached permanently to the contract.

## Key Takeaways

- CTD selection and delivery-date selection are related but separate calculations.
- The short compares funding, coupon cash and invoice proceeds for every eligible date.
- Coupon entitlement creates discontinuities that a linear accrued-interest model can miss.
- Optimal delivery date changes with repo, market assumptions, calendars and contract rules.
- Production systems should require complete date coverage and expose the runner-up gap.
- Every result needs sufficient lineage to reproduce both the winning date and why it won.