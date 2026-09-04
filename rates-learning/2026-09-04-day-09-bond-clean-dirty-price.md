# Clean Price, Dirty Price and Yield: Engineering Bond Valuation Data

## Abstract

A bond can legitimately appear as 101.65 on one screen and 103.15 in a valuation service. The difference may be accrued interest rather than a pricing error. This article explains clean price, dirty price, yield and settlement amount, then shows how to build a traceable multi-source bond-price pipeline with explicit semantics, reference-data lineage, controls and production-safe failure handling.

## Desk Context

A trader sees an internal bond value of 103.15 while an external screen shows 101.65:

> “Why are we 1.5 points away from the market?”

The first investigation should align meaning before comparing numbers. One source may show clean mid price while another shows dirty valuation price. Settlement date, quote side, units, observation time and accrued-interest convention can all create valid differences.

## Bond Price as Present Value

The dirty price of a fixed-rate bond is the present value of coupons and principal:

[
DirtyPrice
=
sum_{i=1}^{n}
rac{Coupon_i}{(1+y/m)^{m t_i}}
+
rac{Principal}{(1+y/m)^{mT}}
]

Bond prices are commonly quoted per 100 of face value. A displayed price of 101.65 therefore does not mean GBP 101.65 for the whole position.

## Clean, Dirty and Accrued

The central reconciliation is:

[
DirtyPrice=CleanPrice+AccruedInterest
]

Clean price excludes interest accumulated since the last coupon date. This convention prevents the quoted market series from rising mechanically every day and dropping on coupon dates.

Accrued interest can be approximated by:

[
AI
=
CouponPayment
	imes
rac{DaysSinceLastCoupon}
{DaysInCouponPeriod}
]

The exact result depends on schedule, settlement date, day-count convention and ex-coupon rules.

Dirty price, also called full price, includes accrued interest and forms the basis of settlement consideration:

[
SettlementAmount
approx
FaceAmount	imesrac{DirtyPrice}{100}
]

## Worked Example

Consider a simplified GBP bond:

- Face amount: GBP 10 million
- Coupon rate: 6% annually
- Semi-annual coupon: 3 per 100 face
- Settlement halfway through the coupon period
- Market clean price: 101.65
- No ex-coupon adjustment or fees

Accrued interest is:

[
AI=3	imes0.5=1.50
]

Therefore:

[
DirtyPrice=101.65+1.50=103.15
]

The two displayed prices are consistent.

Settlement amount is:

[
GBP 10{,}000{,}000	imes103.15/100
=
GBP 10{,}315{,}000
]

The accrued-interest cash amount is GBP 150,000.

Now assume modified duration is 1.8 and yield rises by 10bp. The duration approximation gives:

[
rac{Delta P}{P}approx-D_{mod}Delta y
]

[
Delta P
approx
-1.8	imes0.001	imes103.15
=
-0.18567
]

For GBP 10 million face, approximate PnL is:

[
10{,}000{,}000	imes(-0.18567)/100
=
-GBP 18{,}567
]

This is a first-order estimate. Full revaluation captures convexity and exact cash-flow timing.

## Coupon, Yield and Curve Price

The coupon rate defines contractual payments. Yield to maturity is the single discount rate that reproduces the current dirty price:

[
DirtyPrice=PV(Cashflows,YTM)
]

Price and yield usually move in opposite directions. A longer-duration bond generally reacts more strongly to the same yield move.

YTM is a summary measure, not a statement that every cash flow is economically discounted at one identical rate. Curve-based valuation uses maturity-specific discount factors.

## Why Sources Disagree

Before declaring a broken price, compare:

- clean versus dirty;
- bid, ask, mid, last or evaluated;
- price, yield or spread;
- per-100, decimal or currency units;
- trade date versus settlement date;
- settlement convention;
- observation timestamp and freshness;
- currency and face amount;
- accrued-interest convention;
- source hierarchy;
- workout or yield definition for callable bonds.

For an illiquid instrument, an evaluated price and a stale last trade can both look plausible while representing very different information.

## Canonical Data Model

```python
@dataclass(frozen=True)
class BondQuote:
    instrument_id: str
    source: str

    measure: Literal["PRICE", "YIELD", "SPREAD"]
    price_type: Literal["CLEAN", "DIRTY"] | None
    side: Literal[
        "BID", "ASK", "MID", "LAST", "EVALUATED"
    ]

    value: Decimal
    unit: str
    observed_at: datetime
    received_at: datetime
    settlement_date: date | None
    quality_status: str
```

Reference data must also be versioned:

```python
@dataclass(frozen=True)
class BondTerms:
    instrument_id: str
    currency: str
    face_value: Decimal
    coupon_rate: Decimal
    coupon_frequency: str
    issue_date: date
    maturity_date: date
    day_count: str
    calendar: str
    business_day_rule: str
    settlement_lag_days: int
    ex_coupon_days: int | None
    terms_version: str
```

A generic value column without measure, price type and unit is not a safe market-data contract.

## Normalization Pipeline

```python
def normalize_to_clean_price(
    quote,
    bond,
    valuation_date,
):
    settlement_date = resolve_settlement_date(
        valuation_date=valuation_date,
        lag=bond.settlement_lag_days,
        calendar=bond.calendar,
    )

    if quote.measure == "YIELD":
        dirty = price_from_yield(
            bond=bond,
            yield_value=quote.value,
            settlement_date=settlement_date,
        )
    elif quote.price_type == "DIRTY":
        dirty = quote.value
    elif quote.price_type == "CLEAN":
        return quote.value
    else:
        raise AmbiguousQuoteError(quote)

    accrued = accrued_interest(
        bond=bond,
        settlement_date=settlement_date,
    )
    return dirty - accrued
```

The normalized record should retain the raw value, transformation steps, resolved settlement date, accrued interest, reference-data version, observation timestamp and fallback status. Keeping only the final clean price destroys the evidence needed for investigation.

## Controls and Business-Invariant Tests

Essential controls include:

- explicit price type and measure;
- measure-specific validation ranges;
- correct settlement calendar and lag;
- complete coupon schedule;
- correct accrued-interest day count;
- dirty equals clean plus accrued within tolerance;
- correct conversion from price-per-100 to currency amount;
- prevention of stale-over-fresh overwrite;
- versioned source priority;
- visible missing or invalid status;
- explicit handling of matured or defaulted instruments.

```python
def test_dirty_equals_clean_plus_accrued():
    result = normalize(bond_quote)
    assert_close(
        result.dirty_price,
        result.clean_price + result.accrued_interest,
    )

def test_price_falls_when_yield_rises():
    assert (
        price_from_yield(bond, 0.05)
        < price_from_yield(bond, 0.04)
    )

def test_coupon_date_resets_accrued_interest():
    assert_close(
        accrued_interest(bond, coupon_date),
        Decimal("0"),
    )
```

Useful metrics include quote age by source, cross-source price spreads, normalization failures, price-type distribution, accrued reconciliation error, fallback usage, reference-data versions and outlier counts.

## Production Failure Modes

1. Clean and dirty prices compared directly.
2. Yield percentage interpreted as a price.
3. A price of 101.65 divided by 100 twice.
4. T+1 and T+2 settlement dates mixed.
5. Wrong accrued-interest day-count convention.
6. A late stale message overwrites a fresher quote.
7. Internal mid compared with external ask.
8. Coupon or maturity reference data differs by version.
9. Ex-coupon rules are omitted.
10. Normalization lineage is discarded.
11. Missing price is represented as zero.
12. Vendor and internal identifiers map to different instruments.

## Requirement Discovery

When a trader asks for a bond price, clarify:

- clean or dirty;
- bid, ask, mid, last or evaluated;
- price, yield or spread;
- source and hierarchy;
- observation time and freshness tolerance;
- settlement date and lag;
- price per 100 or position amount;
- whether accrued interest must be displayed;
- source-comparison tolerance;
- outlier and override policy;
- audit fields for overrides;
- yield-to-maturity or yield-to-worst for callable instruments.

A precise requirement might be:

```yaml
display:
  clean_price: true
  accrued_interest: true
  dirty_price: true
  settlement_amount: true

quote:
  side: mid
  unit: price_per_100
  include_source_timestamp: true

settlement:
  use_instrument_standard_lag: true
  include_resolved_date: true

lineage:
  retain_raw_quote: true
  retain_transformation_steps: true
  include_reference_data_version: true

failure_policy:
  missing_price_as_zero: false
  ambiguous_price_type: hard_error
```

## Interview Questions

1. How do clean and dirty bond prices differ?
2. Why do fixed-rate bond prices normally fall when yields rise?
3. Which metadata is needed before comparing vendor prices?
4. How would you prevent stale data from overwriting a fresh quote?
5. Why should a normalization service retain the raw input?

Strong answers should mention accrued interest, settlement conventions, duration, quote semantics, event ordering, provenance and explicit missing-data states.

## Key Takeaways

- Dirty price equals clean price plus accrued interest.
- Bond prices are commonly quoted per 100 face value.
- Coupon defines cash flows; yield is the rate that reproduces price.
- Price and yield generally move in opposite directions.
- Multi-source comparisons require aligned price type, measure, side, unit, settlement and timestamps.
- A production bond pipeline should preserve raw inputs, transformations and reference-data lineage.
- Missing or ambiguous data must never masquerade as a valid zero.
