# Explaining Futures Hedge Execution Slippage

## Abstract

A futures hedge can be sized correctly and still generate an immediate loss because the execution price differs from the price observed when the hedge decision was made. That amount is execution slippage, not post-trade market PnL and not residual DV01. This article builds a fill-level slippage explain, shows how to handle multiple partial fills, and translates the desk requirement into a reproducible Python calculation with timestamp, price-source, contract, and cost lineage.

## Desk Context

After calculating a hedge, a desk decides to short 455 futures contracts. The displayed futures price at the decision timestamp is 95.420. The order fills in two clips:

- 300 contracts at 95.415;
- 155 contracts at 95.407.

For a short, selling below the decision price is adverse. The hedge quantity may ultimately be correct, but the execution has incurred a cost before any post-fill market move is explained.

The primary concept is **execution slippage PnL**. The closely related distinction is between slippage measured against a decision benchmark and market PnL earned after each fill.

## The Benchmark Defines the Question

Execution slippage compares each fill price with a benchmark price. Common benchmarks include:

- the market price when the hedge recommendation was accepted;
- the arrival price when the order reached the execution system;
- the mid-price at the start of an execution window;
- a time-weighted or volume-weighted benchmark.

These answer different questions. Decision-price slippage measures the economic cost from decision to fill. Arrival-price slippage removes latency before the order reached execution. A desk must choose one explicitly; a field named merely `reference_price` is not enough.

Let signed quantity $q_i$ be positive for a long fill and negative for a short fill, price multiplier $M$ be currency per price point, benchmark price $P_b$, and fill price $P_i$. A consistent slippage convention is:

$$
Slippage_i=q_i(P_b-P_i)M
$$

Under this convention, positive slippage is favourable and negative slippage is adverse.

For a short fill, $q_i<0$. If the fill price is below the benchmark, $P_b-P_i>0$, giving negative slippage as expected.

The formula must not be replaced by an unsigned absolute difference. Direction is economic information.

## Worked Numerical Example

Assume:

- decision benchmark: 95.420;
- price multiplier: GBP 2,500 per full price point;
- first fill: short 300 at 95.415;
- second fill: short 155 at 95.407.

Represent short quantities as negative.

First-fill slippage is:

$$
(-300)(95.420-95.415)(2{,}500)
=-GBP\ 3{,}750
$$

Second-fill slippage is:

$$
(-155)(95.420-95.407)(2{,}500)
=-GBP\ 5{,}037.50
$$

Total execution slippage is therefore:

$$
-3{,}750-5{,}037.50=-GBP\ 8{,}787.50
$$

The quantity-weighted average fill price is:

$$
P_{avg}=
\frac{300(95.415)+155(95.407)}{455}
=95.4122747
$$

The same total can be recovered from the average price:

$$
(-455)(95.420-95.4122747)(2{,}500)
=-GBP\ 8{,}787.50
$$

This equality is a useful reconciliation invariant for a linear contract multiplier.

### Separating Post-Fill Market PnL

Suppose the end-of-day settlement price is 95.390. Each fill earns market PnL only from its own execution price to settlement:

$$
MarketPnL_i=q_i(P_i-P_{close})M
$$

For the two short fills:

$$
(-300)(95.415-95.390)(2{,}500)
=-GBP\ 18{,}750
$$

This sign reveals that the generic signed-quantity convention above treats positive quantity as long and computes long value change as $q(P_{close}-P_i)M$. The correct unified post-fill formula is therefore:

$$
MarketPnL_i=q_i(P_{close}-P_i)M
$$

which gives the short a gain:

$$
(-300)(95.390-95.415)(2{,}500)
=+GBP\ 18{,}750
$$

The second fill contributes:

$$
(-155)(95.390-95.407)(2{,}500)
=+GBP\ 6{,}587.50
$$

Total post-fill market PnL is GBP 25,337.50. It must be reported separately from the GBP -8,787.50 execution slippage. Combining them without labels would hide whether value came from execution quality or subsequent market direction.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime


@dataclass(frozen=True)
class FuturesFill:
    execution_id: str
    signed_quantity: int  # long +, short -
    fill_price: Decimal
    execution_time: datetime


def explain_execution(
    fills: list[FuturesFill],
    benchmark_price: Decimal,
    close_price: Decimal,
    price_multiplier: Decimal,
) -> dict:
    seen: set[str] = set()
    slippage = Decimal("0")
    post_fill_market = Decimal("0")
    net_quantity = 0

    for fill in fills:
        if fill.execution_id in seen:
            continue
        seen.add(fill.execution_id)

        q = Decimal(fill.signed_quantity)
        net_quantity += fill.signed_quantity

        slippage += (
            q
            * (benchmark_price - fill.fill_price)
            * price_multiplier
        )
        post_fill_market += (
            q
            * (close_price - fill.fill_price)
            * price_multiplier
        )

    return {
        "net_filled_quantity": net_quantity,
        "execution_slippage_pnl": slippage,
        "post_fill_market_pnl": post_fill_market,
        "benchmark_type": "DECISION_MID",
        "processed_execution_ids": sorted(seen),
    }
```

This compact calculation deliberately excludes commissions, exchange fees, and bid-offer attribution. Those may be added as separate components, but should not be silently embedded in slippage.

## Data Quality and Production Controls

The most relevant controls are:

- **Timestamp alignment:** the benchmark price must come from the approved market snapshot at the defined decision or arrival time, with timezone and venue.
- **Contract identity:** fill and benchmark must share contract code, expiry, currency, multiplier, and price scale.
- **Fill idempotency:** duplicate execution messages cannot contribute twice; busts and corrections require linked lifecycle events.
- **Price provenance:** distinguish executable bid or offer, mid, last trade, and settlement. Each creates a different benchmark.
- **Component reconciliation:** execution slippage, fees, and post-fill market PnL should reconcile to the chosen total hedge PnL without double counting.

A dangerous failure is using 95.420 as one service's price but 0.95420 as another's decimal representation. The calculation runs successfully while the reported cost is wrong by orders of magnitude.

Useful observability includes missing benchmark coverage, benchmark-to-fill latency, duplicate execution count, average slippage per contract, and reconciliation breaks between execution and PnL ledgers.

## Requirement Discovery

When a trader asks, “How much did the hedge cost us?”, clarify:

- Cost relative to decision price, arrival price, mid, bid/offer, or another benchmark?
- Is positive output favourable or adverse?
- Should the benchmark be frozen once or refreshed for each child order?
- Are fees and commissions separate components?
- How should partial fills across venues be aggregated?
- What price and timestamp are used when the benchmark quote is missing or stale?
- Should post-fill PnL start at each fill timestamp or from the average fill time?
- How are busts, corrections, and late fills applied to a previously published explain?

A concise desk answer is:

> I measure execution slippage against a named, timestamped benchmark using signed fill quantities and the contract multiplier. Each fill starts earning market PnL only after execution. I keep slippage, fees, and post-fill market PnL separate, deduplicate execution events, and reconcile the components to the hedge ledger.

## Key Takeaways

- A correctly sized hedge can still incur adverse execution slippage.
- The benchmark definition is a business requirement, not a display preference.
- Signed quantity and price scale must be explicit.
- Each partial fill has its own price and market-PnL start time.
- Execution slippage, fees, and post-fill market PnL are different explain components.
- Fill-level calculations should reconcile to the quantity-weighted average result and the authoritative ledger.

