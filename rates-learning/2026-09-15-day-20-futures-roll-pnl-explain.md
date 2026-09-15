# Measuring Futures Roll Execution with Implementation Shortfall

## Abstract

A futures roll can be economically well designed and still be poorly executed—or appear poorly executed because the benchmark is wrong. Implementation shortfall provides a disciplined way to compare actual fills with the market available when execution began. For a bond-futures hedge, the calculation must be side-aware, quantity-weighted, fee-inclusive, and driven by actual fills. This article shows how to separate roll execution cost from ordinary market PnL and how to avoid the common mistake of measuring slippage against the previous close.

## Desk Context

The desk has already planned a DV01-preserving roll. It will buy 200 front-month futures to close an existing short and sell 188 next-month futures to establish the replacement hedge.

After completion, a dashboard reports a GBP 74,000 “roll loss.” The trader challenges the number because observed bid-offer spreads were much smaller. Investigation shows that the report compares today’s fills with yesterday’s closing prices. It has therefore mixed overnight market movement with execution quality.

The relevant question is not simply “What changed between yesterday’s close and today’s fills?” It is:

> How much worse were the actual fills than the market observable when the order entered execution?

That is the purpose of implementation shortfall.

## Choosing the Benchmark

Several legitimate benchmarks exist, but each answers a different question:

- **Decision price** measures performance from the moment the trader decided to transact.
- **Arrival mid** uses the mid-market when the order entered the execution workflow.
- **Arrival executable price** compares the fill with the bid or offer that was immediately tradable.
- **VWAP or TWAP** compares execution with the market over a defined time window.

This article uses arrival mid because it is intuitive and symmetric across the two legs. It captures spread, market impact, latency, and adverse price movement after arrival. It deliberately excludes movement before the order began.

Previous close remains useful for close-to-close PnL, but it is not a clean execution benchmark. A system should preserve both measures under different labels rather than force one number to serve both purposes.

## Side-Aware Shortfall

For a buy order, paying above the benchmark is a cost:

$$
BuySlippageCost
=
Quantity\times Multiplier
\times(FillPrice-ArrivalPrice)
$$

For a sell order, receiving less than the benchmark is a cost:

$$
SellSlippageCost
=
Quantity\times Multiplier
\times(ArrivalPrice-FillPrice)
$$

These formulas use a reporting convention in which positive values represent costs. Total implementation shortfall is:

$$
ImplementationShortfall
=
BuyCost+SellCost+Fees
$$

A PnL-oriented API may expose the same result with the opposite sign:

$$
ExecutionPnL=-ImplementationShortfall
$$

The field name and sign convention must be explicit. A generic execution-value field invites downstream sign errors.

## Worked Numerical Example

The front close leg buys 200 contracts. Its arrival mid is 111.96, the quantity-weighted average fill is 111.98, and the multiplier is GBP 1,000 per price point:

$$
FrontBuyCost
=
200\times1{,}000\times(111.98-111.96)
=
GBP\ 4{,}000
$$

The next open leg sells 188 contracts. Its arrival mid is 112.45 and its average fill is 112.42:

$$
NextSellCost
=
188\times1{,}000\times(112.45-112.42)
=
GBP\ 5{,}640
$$

Suppose exchange, clearing, and brokerage fees total GBP 1.25 per traded contract. The two legs contain 388 contracts:

$$
Fees=(200+188)\times1.25=GBP\ 485
$$

The implementation shortfall is therefore:

$$
ImplementationShortfall
=
4{,}000+5{,}640+485
=
GBP\ 10{,}125
$$

Expressed as execution PnL, the result is GBP -10,125.

If the original dashboard reports GBP -74,000, approximately GBP -63,875 remains outside pure execution shortfall. That amount may reflect pre-arrival market movement, carry, or another attribution component. It should not be labelled slippage without evidence.

The calendar-spread price is also not identical to implementation shortfall. The spread expresses the relative price of two contracts with different carry and delivery economics. Execution shortfall evaluates how the desk traded relative to a timestamped benchmark.

## Engineering a Fill-Driven Calculation

A roll is often filled in pieces. The system must calculate cost from actual fills and must not declare completion merely because both orders were submitted.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LegExecution:
    side: str
    target_quantity: int
    filled_quantity: int
    arrival_price: Decimal
    average_fill_price: Decimal | None
    multiplier: Decimal
    fee_per_contract: Decimal


def execution_shortfall(legs: list[LegExecution]) -> dict:
    price_cost = Decimal("0")
    fees = Decimal("0")

    for leg in legs:
        if leg.filled_quantity == 0:
            continue
        if leg.average_fill_price is None:
            raise ValueError("filled leg requires fill price")

        if leg.side == "BUY":
            unit_cost = (
                leg.average_fill_price - leg.arrival_price
            )
        elif leg.side == "SELL":
            unit_cost = (
                leg.arrival_price - leg.average_fill_price
            )
        else:
            raise ValueError("unsupported side")

        price_cost += (
            Decimal(leg.filled_quantity)
            * leg.multiplier
            * unit_cost
        )
        fees += (
            Decimal(leg.filled_quantity)
            * leg.fee_per_contract
        )

    complete = all(
        leg.filled_quantity == leg.target_quantity
        for leg in legs
    )

    return {
        "price_shortfall_cost": price_cost,
        "fees": fees,
        "implementation_shortfall": price_cost + fees,
        "status": "COMPLETE" if complete else "PARTIAL",
    }
```

In production, the average fill should either be derived from immutable fill records or accompanied by sufficient lineage to reproduce it. If the next leg has filled only 120 of 188 contracts, the calculation should use 120 contracts, expose 68 remaining, and recompute the live residual DV01.

## Data Quality and Production Controls

The most relevant controls are:

- The arrival timestamp must precede the first fill, and benchmark prices must use the same unit as fills.
- BUY/SELL logic must not be confused with signed position quantity.
- Average fills must be quantity-weighted.
- Partial, cancelled, and rejected quantities must remain explicit.
- Previous close, arrival mid, and executable-side benchmarks must use distinct methodology labels.

A particularly damaging failure is storing only the final average fill while discarding the arrival snapshot. The trade amount remains known, but execution quality can no longer be reproduced or audited.

Another failure is counting price improvement on one leg as a cost because the service applies the buy formula to both sides. Side-aware invariant tests are more valuable here than broad unit-test counts.

## Requirement Discovery

When a trader asks for “roll cost,” clarify:

- Does the phrase mean calendar-spread price, execution slippage, fees, or total PnL?
- Is the benchmark decision price, arrival mid, executable side, VWAP, or TWAP?
- Do the two legs share one arrival timestamp or have separate timestamps?
- Are exchange, clearing, and brokerage fees included?
- Should partial fills update the metric in real time?
- Must bid-offer and market impact be separated?
- Should cost be positive, or should loss be negative PnL?

A useful requirement translation is:

**Trader:** “The dashboard says the roll cost 74k. That cannot all be slippage.”

**Developer:** “The current report compares fills with yesterday’s close. Should execution quality start from each order’s arrival market?”

**Trader:** “Yes. Show both legs and fees, and separate anything that happened before arrival.”

**Developer:** “I’ll quantity-weight the fills, apply side-aware signs, report GBP 10,125 implementation shortfall, and leave pre-arrival movement in market PnL.”

## Interview Questions

1. Why is previous close a poor benchmark for execution quality?
2. How do slippage signs differ between buy and sell orders?
3. Why must average fill price be quantity-weighted?
4. How should partial fills affect roll status and live hedge risk?
5. What lineage is required to reproduce implementation shortfall?

## Key Takeaways

Implementation shortfall turns a vague complaint about roll cost into a reproducible execution metric. Use a timestamped benchmark aligned with the question, apply side-aware formulas, weight fills by quantity, and include fees explicitly. Keep pre-arrival market movement outside execution slippage. Most importantly, drive completion, shortfall, and residual hedge risk from actual fills rather than intended orders.