# Preventing False PnL Jumps When a Futures Series Rolls

## Abstract

When a generic futures ticker rolls from the front contract to the next expiry, its displayed price can jump even if neither tradable contract moved. That jump is the calendar spread between two different instruments, not automatically market PnL. This article explains how to separate contract-switch effects from genuine price changes, construct a versioned continuous analytical series, and keep official PnL tied to explicit contracts and unadjusted settlement prices. The distinction is essential for trustworthy dashboards, backtests, hedge explains, and variation-margin reconciliation.

## The Desk Problem

Assume Monday’s closing settlements are 95.100 for the front contract and 95.350 for the next contract. A liquidity policy switches the desk’s generic `FRONT` alias to the next contract before Tuesday.

If Tuesday’s first generic observation is 95.350, a naive time series reports a rise of 0.250. Yet the front may still be 95.100 and the next may still be 95.350. Nothing moved. Only the identity behind the alias changed.

This matters because a generic ticker often feeds charts, signals, risk summaries, and PnL reports. If downstream systems do not know that a roll occurred, a calendar spread can appear as a market shock. The correct design therefore separates three objects:

- an explicit contract series, representing a real tradable expiry;
- a raw generic series, which follows a roll policy and may contain jumps;
- an adjusted continuous series, created for analytics and not itself tradable.

## Measuring the Roll Gap

Let the final front-contract price at the roll boundary be $P_F$ and the synchronized next-contract price be $P_N$. Define the additive roll gap as:

$$
G=P_N-P_F
$$

In the example:

$$
G=95.350-95.100=0.250
$$

The gap can reflect carry, curve shape, convexity, delivery economics, or other expiry-specific effects. It is not a price change in a single instrument.

For an additively adjusted post-roll series:

$$
P_{continuous,t}=P_{next,t}-G
$$

If the next contract remains at 95.350, the adjusted price is 95.100 and the continuous return is zero. If the next contract falls to 95.330, the adjusted price becomes:

$$
95.330-0.250=95.080
$$

The continuous move is therefore -0.020. The adjustment removes the mechanical 0.250 contract switch while retaining the next contract’s genuine -0.020 move.

Additive adjustment is intuitive for futures quoted on a stable price scale. Some applications use ratio adjustment, particularly when proportional returns are more meaningful. The choice must be policy-driven and visible to consumers.

## A Worked PnL Example

Suppose the desk closes Monday with 400 short front-contract futures. The price multiplier is GBP 2,500 per full price point.

A broken generic-to-generic calculation produces:

$$
WrongPnL=(-400)(95.350-95.100)(2{,}500)
=-GBP\ 250{,}000
$$

The reported loss is fictional: it compares prices of different expiries as though they were the same asset.

If the front position has not yet been closed, Tuesday’s PnL must continue to use the front contract. Assume its price falls from 95.100 to 95.080:

$$
ActualPnL=(-400)(95.080-95.100)(2{,}500)
=+GBP\ 20{,}000
$$

If the roll completed on Monday, the PnL boundary should instead follow the actual old- and new-leg fills and the desk’s accounting convention. It still cannot be obtained by subtracting two generic alias values.

The 0.250 roll adjustment is analytical metadata. It is not cash, execution slippage, variation margin, or a valuation adjustment. Execution quality remains a separate calculation based on actual spread fills relative to a named benchmark.

## Choosing the Roll Boundary

The old and new prices used to compute the gap must be synchronized. Valid examples include:

- the same exchange settlement session;
- mids captured at the same timestamp;
- a defined roll-window benchmark.

Using yesterday’s front settlement and today’s next-contract intraday price contaminates the gap with overnight and intraday market movement. The resulting adjusted series may look continuous, but it will have removed real returns.

The adjustment direction also matters. A backward-adjusted series modifies historical observations so that the latest contract retains its real price level. This is common for research because current prices remain recognizable. A forward-adjusted series preserves old history and modifies observations after each roll. Both can produce continuous changes, but their absolute levels differ.

An API should therefore expose the methodology, roll event, explicit contract, gap, cumulative adjustment, source snapshot, and series version. A consumer should never have to infer whether a returned price is raw or adjusted.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RollObservation:
    roll_session: str
    old_contract_id: str
    new_contract_id: str
    old_price: Decimal
    new_price: Decimal
    price_type: str
    snapshot_id: str


def build_roll_adjustment(x: RollObservation) -> dict:
    if x.old_contract_id == x.new_contract_id:
        raise ValueError("roll requires distinct contracts")
    if x.price_type not in {"SETTLEMENT", "SYNCHRONIZED_MID"}:
        raise ValueError("unsupported roll benchmark")

    gap = x.new_price - x.old_price

    return {
        "roll_session": x.roll_session,
        "old_contract_id": x.old_contract_id,
        "new_contract_id": x.new_contract_id,
        "additive_roll_gap": gap,
        "post_roll_adjustment": -gap,
        "price_type": x.price_type,
        "snapshot_id": x.snapshot_id,
        "usage": "ANALYTICAL_SERIES_ONLY",
    }
```

In a full implementation, each roll event is immutable and uniquely identified. Building the series twice from the same events must be idempotent; otherwise the cumulative adjustment may be applied more than once.

## Production Controls and Failure Modes

The most valuable controls are narrow and explicit:

1. **Synchronized inputs.** Old and new prices must share benchmark type, session, timestamp, currency, scale, and source.
2. **Explicit identities.** Store immutable contract IDs in every roll event. A mutable alias such as `FRONT` is not sufficient lineage.
3. **One adjustment per event.** Deduplicate by roll-event ID and verify cumulative adjustments during reprocessing.
4. **Usage separation.** Adjusted prices are allowed for charts, features, and research, but prohibited as settlement or official valuation inputs.
5. **Versioned rebuilds.** Vendor corrections or policy changes create a new series version with reproducible adjustment lineage.

A dangerous failure occurs when a chart service correctly uses a back-adjusted series, but a PnL service consumes the same dataset without recognizing the adjustment. The chart looks smooth, while variation margin no longer reconciles to the exchange. This is an interface-contract failure: the numeric values are valid for one purpose and invalid for another.

## Requirement Discovery

When a trader or quant asks for a “continuous futures chart,” clarify:

- Is the series intended for visualization, signals, backtesting, or official PnL?
- Is the roll gap measured from settlement, synchronized mid, or execution prices?
- Should the series be backward- or forward-adjusted?
- Is adjustment additive or ratio-based?
- Do historical data corrections rebuild prior series versions?
- Does the API return raw price, adjusted price, contract ID, and cumulative adjustment together?
- Is position PnL guaranteed to use actual filled contracts rather than generic aliases?

These questions turn a cosmetic chart request into a well-defined data product.

## Interview Perspective and Key Takeaways

A strong quant developer answer starts with instrument identity. The front and next contracts are different assets, so a generic ticker’s roll-day jump cannot automatically be treated as a return. Compute the roll gap from synchronized explicit-contract observations, publish the adjustment with complete lineage, and label the resulting series as analytical.

Most importantly, do not let continuous-series logic leak into accounting. Official PnL, settlement, variation margin, and position valuation must remain based on the contracts actually held and their unadjusted market prices. Smooth analytics and correct accounting are both achievable, but only when they are modeled as separate outputs with separate usage contracts.
