# Implied Repo Rate: From Delivery Economics to CTD Selection

## Abstract

Implied repo rate converts the cash-and-carry economics of a deliverable bond into an annualized financing return. It connects futures pricing, cheapest-to-deliver selection, and production market-data engineering. This article explains the measure, works through a numerical example, and shows how to implement it without confusing an implied break-even rate with actual funding.

## Desk Context

A government-bond futures trader sees that one deliverable bond has an implied repo rate of 1.31%. Another candidate has a cheaper cash price, yet the first bond is marked cheapest-to-deliver.

The 1.31% is not necessarily the rate at which the desk can finance the bond. It is the annualized return implied by buying the cash bond, carrying it to delivery, and delivering it into the futures contract. An apparently attractive return may disappear after executable price sides, special repo, coupon timing, margin, and transaction costs are included.

## From Delivery Economics to an Annualized Rate

A simplified cash-and-carry strategy is:

1. Buy an eligible deliverable bond.
2. Finance the purchase until delivery.
3. Receive coupons during the holding period.
4. Deliver the bond and receive the futures invoice amount.

Ignoring coupons and costs initially:

$$
HoldingReturn =
\frac{InvoicePrice - PurchaseDirtyPrice}
{PurchaseDirtyPrice}
$$

Annualizing on a money-market basis:

$$
IRR =
HoldingReturn
\times
\frac{DayBasis}{DaysToDelivery}
$$

The invoice price per 100 face is:

$$
InvoicePrice =
FuturesPrice \times ConversionFactor
+ DeliveryAccruedInterest
$$

The day basis may be 360 or 365. A production system should treat it as an explicit policy input. Implied repo is a break-even financing return inferred from delivery economics, not a directly observed repo quote.

## Worked Numerical Example

Assume:

- purchase clean price: 105.50;
- purchase accrued interest: 1.20;
- purchase dirty price: 106.70;
- futures price: 116.00;
- conversion factor: 0.9125;
- delivery accrued interest: 1.20;
- 90 days to delivery;
- 360-day basis;
- no interim coupon.

First calculate the invoice price:

$$
InvoicePrice =
116.00 \times 0.9125 + 1.20
= 107.05
$$

The holding-period return is:

$$
HoldingReturn =
\frac{107.05 - 106.70}{106.70}
= 0.003280
$$

The annualized implied repo rate is:

$$
IRR =
0.003280 \times \frac{360}{90}
= 1.312\%
$$

If actual financing is 1.00%, the simplified annualized advantage is:

$$
1.312\% - 1.00\%
= 31.2bp
$$

That is not guaranteed profit. The calculation still ignores bid–ask spreads, bond-specific repo, coupon reinvestment, margin cash flows, transaction costs, and delivery optionality.

## Why the Highest IRR Often Identifies the CTD

Net basis expresses relative delivery cost in price points. Implied repo expresses closely related economics as an annualized return. Under consistent assumptions, the candidate with the lowest net basis will normally have the highest implied repo.

The equivalence depends on:

- the same delivery date;
- consistent cash and futures price sides;
- identical coupon and accrued-interest treatment;
- the same financing convention;
- complete basket coverage.

If two systems disagree on CTD ranking, “different formula” is not enough. The first investigation should compare economic inputs and conventions.

## Engineering Design

\`\`\`python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class ImpliedRepoInput:
    instrument_id: str
    purchase_dirty_price: Decimal
    futures_price: Decimal
    conversion_factor: Decimal
    delivery_accrued: Decimal
    coupon_proceeds: Decimal
    days_to_delivery: int
    day_basis: int
    market_snapshot_id: str

def implied_repo(x: ImpliedRepoInput) -> Decimal:
    if x.purchase_dirty_price <= 0:
        raise ValueError("purchase dirty price must be positive")
    if x.days_to_delivery <= 0:
        raise ValueError("delivery must be in the future")

    invoice = (
        x.futures_price * x.conversion_factor
        + x.delivery_accrued
    )
    proceeds = invoice + x.coupon_proceeds
    holding_return = (
        proceeds - x.purchase_dirty_price
    ) / x.purchase_dirty_price

    return (
        holding_return
        * Decimal(x.day_basis)
        / Decimal(x.days_to_delivery)
    )
\`\`\`

A production result should also carry calculation status, price sides, settlement and delivery dates, coupon-reinvestment policy, basket version, market snapshot, and methodology version.

## Data Quality and Production Controls

The most valuable controls are economic:

- **Aligned snapshots:** cash, futures, accrued-interest, and repo inputs must belong to a compatible market cut.
- **Correct price direction:** cash-and-carry normally buys the bond and sells the future, so ask and bid may be more appropriate than mids.
- **Consistent price basis:** dirty price must reconcile to clean price plus accrued interest.
- **Complete basket:** missing candidates must not be silently excluded from a result labelled complete.
- **Explicit missing data:** absent coupon or repo information must not become zero.

Typical failures include stale futures paired with live cash, a 360/365 mismatch, double-counted coupons, conversion-factor scaling errors, and ranking a partial basket as complete.

## Requirement Discovery

When a trader asks for implied repo, clarify:

1. Which contract month and delivery-date policy apply?
2. Which cash and futures price sides should be used?
3. Are coupons reinvested, and at what rate?
4. Is financing general collateral or bond-specific special repo?
5. Should the output show implied repo, actual repo, or their spread?
6. Can partial basket results be published?
7. Which day-count and rounding rules define the official number?

## Interview Perspective

> Implied repo is the annualized break-even return from buying a deliverable bond, carrying it to delivery, and delivering it into the futures contract. It is not the observed funding rate. I would use explicit price sides, coupon timing, delivery date, conversion factor, and day-count conventions; preserve snapshot and methodology lineage; and rank only a complete basket.

## Key Takeaways

- Implied repo translates delivery economics into an annualized financing return.
- It must not be confused with the bond’s actual repo funding rate.
- Highest implied repo and lowest net basis normally identify the same CTD under consistent assumptions.
- Executable sides and bond-specific repo can materially change the apparent opportunity.
- A reliable implementation preserves conventions, lineage, basket coverage, and failure status.