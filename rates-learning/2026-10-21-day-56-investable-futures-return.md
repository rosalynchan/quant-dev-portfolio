# From Continuous Futures Signals to Investable Strategy PnL

## Abstract

A point-in-time, roll-adjusted futures series is valuable for signals and research, but its return is not automatically an investable strategy return. Real portfolios hold explicit contracts, roll through confirmed fills, pay execution costs, and settle daily variation margin. This article shows how to translate an analytical continuous-series move into a contract-level PnL ledger, separate market PnL from roll slippage and fees, define non-overlapping component boundaries, and reconcile the result to clearing cash.

## Desk Context

A research dashboard shows an adjusted continuous short-rate futures price rising from 95.000 to 95.040. A strategy is long 100 contracts with a GBP 2,500 multiplier, so a quick estimate reports:

$$
100\times0.040\times2{,}500=GBP\ 10{,}000
$$

During the period, however, the position rolled from the front contract into the next expiry. The old contract was sold below its benchmark, the new contract was bought above its benchmark, and explicit fees were charged. The clearing ledger increased by only GBP 8,650.

Both numbers can be valid, but they answer different questions. The continuous-series return measures movement in an adjusted analytical coordinate. Investable PnL measures the economics of positions that could actually be held and traded.

## What a Continuous Return Omits

An adjusted continuous series is designed to remove mechanical contract-switch jumps. It is useful for trend signals, volatility estimation, long histories, and research features. It does not describe:

- the exact contract held at each instant;
- confirmed rather than target or ordered quantity;
- old- and new-leg execution times;
- fill prices relative to a benchmark;
- partial-roll exposure;
- commissions, exchange fees, or clearing cash.

The design boundary is therefore simple:

> A signal series can choose a trade, but it cannot replace the execution ledger.

On an ordinary day, contract-level market PnL for signed quantity $q$, prices $P_{t-1}$ and $P_t$, and multiplier $M$ is:

$$
MarketPnL=q(P_t-P_{t-1})M
$$

On a roll day, the strategy waterfall should identify the economics of the contract lifecycle:

$$
StrategyPnL
=OldContractPnL+NewContractPnL+RollSlippage-Fees
$$

The old contract earns market PnL only until its defined exit boundary. The new contract earns market PnL only after entry. Roll slippage compares actual spread execution with a frozen benchmark. The analytical roll adjustment is not included because it is not a cash or valuation event.

## Worked Roll-Day Example

The strategy begins long 100 front contracts. The multiplier is GBP 2,500 per full price point.

The front contract rises from the previous settlement of 95.000 to a roll-time mid of 95.030:

$$
OldMarketPnL
=100(95.030-95.000)(2{,}500)
=GBP\ 7{,}500
$$

At the frozen benchmark, the front mid is 95.030 and the next mid is 95.230. The benchmark calendar spread is therefore 0.200.

The actual roll sells the front at 95.028 and buys the next at 95.234. The executed spread is:

$$
95.234-95.028=0.206
$$

The long strategy paid 0.006 more than the benchmark to migrate into the next contract:

$$
RollSlippage
=-100(0.206-0.200)(2{,}500)
=-GBP\ 1{,}500
$$

After execution, the next contract rises from its 95.234 entry fill to a 95.245 settlement:

$$
NewMarketPnL
=100(95.245-95.234)(2{,}500)
=GBP\ 2{,}750
$$

With GBP 100 of explicit fees:

$$
StrategyPnL
=7{,}500-1{,}500+2{,}750-100
=GBP\ 8{,}650
$$

The adjusted continuous series suggested a GBP 10,000 gross move. It did not model the actual execution boundary or costs, so it cannot serve as official PnL.

## Component Boundaries and Double Counting

PnL decomposition is valid only when components have non-overlapping boundaries. If old-contract market PnL is measured all the way to the actual exit fill, adding the full exit-fill-versus-mid difference again as slippage counts the same price difference twice.

One consistent methodology is to calculate market PnL between benchmark states and assign fill-versus-benchmark differences to execution. Another is to calculate total position PnL directly from settlements and fills, while reporting slippage as an explanatory label that is not added again during reconciliation.

Either approach can work. The system must state which one it uses and test the accounting identity. For the additive waterfall used here:

$$
ExplainedStrategyPnL=ClearingPnL-Fees
$$

A component without a documented start price, end price, timestamp, and contract identity should not be accepted into the ledger.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RollDayLedger:
    quantity: int
    old_previous_settle: Decimal
    old_benchmark: Decimal
    new_benchmark: Decimal
    old_exit_fill: Decimal
    new_entry_fill: Decimal
    new_close_settle: Decimal
    multiplier: Decimal
    fees: Decimal


def explain_roll_day(x: RollDayLedger) -> dict:
    q = Decimal(x.quantity)
    old_market = q * (x.old_benchmark - x.old_previous_settle) * x.multiplier

    benchmark_spread = x.new_benchmark - x.old_benchmark
    actual_spread = x.new_entry_fill - x.old_exit_fill
    roll_slippage = -q * (actual_spread - benchmark_spread) * x.multiplier

    new_market = q * (x.new_close_settle - x.new_entry_fill) * x.multiplier

    return {
        "old_market_pnl": old_market,
        "roll_slippage_pnl": roll_slippage,
        "new_market_pnl": new_market,
        "fees": -x.fees,
        "strategy_pnl": old_market + roll_slippage + new_market - x.fees,
    }
```

The example is deliberately compact. A production service also consumes fill events, position states, benchmark lineage, and clearing records.

## Production Controls

The most relevant controls are:

1. **Explicit identities.** Positions, fills, and settlements use immutable contract IDs rather than generic aliases.
2. **Consistent economics.** Price scale, multiplier, currency, and sign conventions match across every component.
3. **Declared boundaries.** Each component stores its start and end observation, timestamp, and methodology.
4. **Event integrity.** Execution IDs are deduplicated, while busts and corrections remain linked economic events.
5. **Cash reconciliation.** Daily strategy PnL reconciles to clearing variation margin and a separate fee ledger.

A common failure is to use adjusted continuous return for the market component and independently add execution slippage without checking how the adjusted return spans the roll boundary. Depending on the construction, the system can omit economics or count them twice while still producing plausible totals.

## Requirement Discovery

When a trader or quant asks to “show strategy return,” clarify:

- Is the desired measure analytical signal return or investable net PnL?
- Does position quantity come from targets, orders, or confirmed fills?
- Is the roll-day market boundary a settlement, benchmark, or fill?
- Is slippage an additive component or a non-additive explanation of total PnL?
- Which broker, exchange, and clearing fees are included?
- How are partial rolls and temporary old/new positions handled?
- Is the authoritative reconciliation target clearing variation margin, a broker statement, or internal valuation PnL?

## Key Takeaways

Continuous futures series and investable ledgers should coexist, not compete. Use the point-in-time adjusted series to generate stable signals and research features. Use explicit contracts, confirmed fills, and actual fees to calculate realizable strategy economics.

On roll days, define non-overlapping boundaries for old-contract market PnL, roll execution slippage, new-contract market PnL, and fees. Preserve every contract and event identifier, and reconcile the resulting ledger to clearing cash. That separation turns an attractive backtest chart into a strategy result the desk can trust.
