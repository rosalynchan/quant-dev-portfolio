# Normalizing Futures Prices, Tick Sizes and Contract Multipliers

## Abstract

A futures position can reconcile perfectly while its PnL is wrong by a factor of ten, one hundred, or one thousand. The cause is often not finance but representation: a vendor integer, displayed decimal, tick count, and cash value are treated as interchangeable. This article defines a safe normalization boundary, derives futures PnL through both point-based and tick-based paths, and shows how versioned contract specifications, semantic validation, and lineage prevent scale errors from reaching a Rates desk.

## Desk Context

A desk is long 80 short-rate futures contracts. Yesterday's settlement was 95.240 and today's is 95.255. With a GBP 2,500 value per full price point, the correct PnL is GBP 3,000.

A new market-data feed, however, transmits the settlements as integers `95240` and `95255`. A downstream engine subtracts the raw values, obtains a move of 15, and multiplies by the contract multiplier. It reports GBP 3,000,000.

The contract, direction, and quantity are all correct. Static type checks also pass because both representations are numeric. The missing information is price scale.

The governing principle is:

> A number is not a price until its scale, unit and contract specification are known.

## Four Different Concepts

### Raw source value

This is the payload exactly as supplied, such as integer `95255`. It is an encoding, not a complete economic price.

### Normalized price

This is the canonical economic representation used inside pricing and PnL services:

$$
P_{normalized}=95.255
$$

### Tick size

The tick size is the minimum permitted quoted increment. Assume:

$$
TickSize=0.005
$$

### Contract multiplier

The multiplier converts one full price point into cash. Assume GBP 2,500 per point. The value of one tick is therefore:

$$
TickValue=0.005\times2{,}500=GBP\ 12.50
$$

Some sources publish tick value directly; others publish a multiplier or enough economics to derive it. The data model must state which quantity it contains.

## Worked Numerical Example

The position and specification are:

- signed quantity: +80;
- previous settlement: 95.240;
- current settlement: 95.255;
- tick size: 0.005;
- multiplier: GBP 2,500 per point.

The normalized price move is:

$$
\Delta P=95.255-95.240=0.015
$$

The number of ticks is:

$$
NumberOfTicks=\frac{0.015}{0.005}=3
$$

Each contract earns three ticks, or GBP 37.50. Total PnL is:

$$
PnL=80\times3\times12.50=GBP\ 3{,}000
$$

The point-based path gives the same result:

$$
PnL=80(95.255-95.240)(2{,}500)=GBP\ 3{,}000
$$

These two independent paths form a useful invariant:

$$
Quantity\times PriceMove\times Multiplier
=Quantity\times TickCount\times TickValue
$$

Now consider the raw integer calculation:

$$
WrongPnL=80(95255-95240)(2{,}500)
=GBP\ 3{,}000{,}000
$$

The result is exactly one thousand times too large because the implied-decimal scale of 0.001 was omitted.

## Establish a Normalization Boundary

Normalization should occur once, at the market-data ingress boundary:

$$
NormalizedPrice=RawPrice\times PriceScale
$$

For this feed, `price_scale = 0.001`. Raw values remain available for audit and vendor investigation, but pricing, risk, and PnL APIs accept only canonical, unit-labelled prices.

Allowing each consumer to infer decimals independently produces inconsistent economics. One service may divide by 1,000, another may assume the source is already normalized, and a third may apply an outdated rule copied from another product family.

A versioned contract specification should include:

- explicit contract and exchange identifiers;
- source-specific price scale;
- tick size or minimum price increment;
- point multiplier and PnL currency;
- effective-from and effective-to timestamps;
- source and specification version.

Specifications can change across products, contracts, or effective dates. Historical replay therefore requires the specification that was valid for the observation, not today's latest reference row.

## Semantic Validation

Checking that a value is numeric is inadequate. Useful validations include:

- normalized settlement falls within a product-appropriate range;
- a price move is an integer number of ticks within tolerance;
- calculated `tick_size × multiplier` matches the authoritative tick value;
- both observations use compatible specification versions;
- PnL currency is known before aggregation or FX conversion.

For the example:

$$
\frac{95.255-95.240}{0.005}=3
$$

An off-grid result such as 3.2 ticks should be investigated. It may indicate incorrect scale, rounding, mixed price types, or a vendor correction. Silently rounding it could hide the source problem and manufacture PnL.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ContractSpec:
    contract_id: str
    price_scale: Decimal
    tick_size: Decimal
    multiplier: Decimal
    pnl_currency: str
    version: str


def normalize_and_pnl(
    raw_previous: int,
    raw_current: int,
    quantity: int,
    spec: ContractSpec,
) -> dict:
    previous = Decimal(raw_previous) * spec.price_scale
    current = Decimal(raw_current) * spec.price_scale
    move = current - previous
    ticks = move / spec.tick_size

    if ticks != ticks.to_integral_value():
        raise ValueError("price move is off tick grid")

    tick_value = spec.tick_size * spec.multiplier
    pnl = Decimal(quantity) * ticks * tick_value

    return {
        "normalized_previous": previous,
        "normalized_current": current,
        "move_ticks": ticks,
        "tick_value": tick_value,
        "pnl": pnl,
        "currency": spec.pnl_currency,
        "spec_version": spec.version,
    }
```

The function uses `Decimal` to keep monetary and tick-grid calculations deterministic. In practice, validation tolerances may be necessary for decimal source conversions, but they should be product-specific rather than global.

## Production Controls and Failure Modes

The most valuable controls are:

- use different schema fields for raw and normalized values; avoid an unqualified field named `price`;
- retain the contract-specification version on every valuation result;
- stop publication when calculated and reference tick values disagree;
- include raw move, normalized move, and applied scale in PnL-jump diagnostics;
- use exchange examples as golden tests before onboarding a new feed.

A classic failure has one consumer interpreting the vendor integer with three implied decimals while another assumes it is already an economic decimal. Position reconciliation remains green because quantities agree, but PnL differs by a factor of one thousand.

## Requirement Discovery and Interview Questions

Before supporting a futures feed, clarify:

- Is the source a decimal, an integer with implied decimals, or fractional notation?
- Do settlement, last, bid, ask, and mid use the same scale?
- Is the published cash value per point or per tick?
- Is tick size identical to the venue's minimum price increment in every regime?
- Which currency does the multiplier produce, and when is FX applied?
- Does the specification apply to a product family or an individual contract?
- Are historical specifications immutable and queryable by effective date?
- Should an off-grid observation be rejected, quarantined, or explicitly rounded?

A concise interview answer is:

> I normalize source prices once at ingestion using a versioned contract specification. Downstream services receive explicit normalized price, tick size, point multiplier, and currency rather than guessing from a numeric field. I reconcile point-based and tick-based PnL as an invariant, preserve raw values for lineage, and quarantine off-grid or specification-inconsistent observations.

## Key Takeaways

- Numeric type does not establish economic meaning.
- Raw price, normalized price, tick size, tick value, and multiplier are distinct fields.
- Point-based and tick-based PnL should reconcile exactly within defined tolerance.
- Contract specifications require effective dating and version lineage.
- Normalize once at ingress; do not distribute scale inference across consumers.
