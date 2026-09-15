# Explaining Daily PnL on a Bond-Futures Hedge

## Abstract

A bond-futures hedge can be close to DV01-neutral and still produce a non-zero daily PnL. That is not automatically a hedge failure. DV01 measures local sensitivity to a defined rate shock, while the cash bond and futures also respond to spread, curve shape, carry, basis, cheapest-to-deliver changes and trading activity. This article builds a practical PnL bridge for a long cash-bond position hedged with short government-bond futures and translates the economics into a controlled Python workflow.

## Desk Context

A desk holds cash bonds and shorts government-bond futures as a rate hedge. At the close:

- cash-bond PnL is -GBP 95,000;
- futures PnL is +GBP 72,000;
- combined PnL is -GBP 23,000.

The trader asks: “The hedge was DV01-neutral. Why did we still lose money?”

The first requirement question is what “worked” means. Opening DV01 neutrality, successful offset of the rates component, low combined PnL volatility and small basis PnL are related but different acceptance criteria. A system should report them separately rather than compressing them into one hedge-success flag.

## Start with Actual PnL

For a frozen opening population, the simplified combined market PnL is:

$$
\text{Combined PnL}
=
\text{Cash-bond PnL}
+
\text{Futures PnL}
$$

In the example:

$$
\text{Combined PnL}
=
-95{,}000+72{,}000
=
-\text{GBP }23{,}000
$$

For futures, use a signed position convention: long quantity is positive and short quantity is negative.

$$
\text{Futures PnL}
=
\text{quantity}
\times
\text{contract multiplier}
\times
\Delta\text{futures price}
$$

A short futures position gains when the futures price falls because both quantity and price change are negative.

A first-order cash-bond diagnostic can be written as:

$$
\text{Cash PnL}
\approx
\text{curve DV01}\times\text{rate move}
+
\text{CS01}\times\text{spread move}
+
\text{carry}
+
\text{residual}
$$

The residual is a disclosed reconciliation item. It may contain convexity, curve-shape effects, basis, price-source changes or data problems. It should not automatically be renamed “basis PnL.”

## Worked Numerical Example

Assume the following opening risk and market changes:

- cash curve DV01: -GBP 15,800 per basis point;
- cash CS01: -GBP 4,000 per basis point;
- government curve move: +8 basis points;
- credit spread move: -5 basis points, meaning tightening;
- carry and accrual: +GBP 6,000;
- futures position: short 200 contracts;
- contract multiplier: GBP 1,000 per price point;
- futures price moves from 112.40 to 112.04;
- actual cash-bond PnL: -GBP 95,000.

The rates component is:

$$
\text{Rates PnL}
=
(-15{,}800)\times8
=
-\text{GBP }126{,}400
$$

The spread component is:

$$
\text{Spread PnL}
=
(-4{,}000)\times(-5)
=
+\text{GBP }20{,}000
$$

Including carry, the cash explain before residual is:

$$
-126.4k+20k+6k
=
-\text{GBP }100.4k
$$

The actual cash PnL is -GBP 95k, so:

$$
\text{Cash residual}
=
-95k-(-100.4k)
=
+\text{GBP }5.4k
$$

For the short futures position:

$$
\text{Futures PnL}
=
(-200)\times1{,}000\times(112.04-112.40)
=
+\text{GBP }72{,}000
$$

The complete bridge is:

$$
-126.4k+20k+6k+5.4k+72k
=
-\text{GBP }23k
$$

The futures hedge materially reduced the rates loss. It did not hedge the cash bond’s spread exposure, and the GBP 5.4k residual still requires investigation.

## Why DV01 Neutral Does Not Mean PnL Neutral

A cash bond and a futures contract are not the same instrument. Even if their opening parallel-rate DV01 values offset, their prices can diverge because of:

- the cash bond’s credit and liquidity spread;
- different maturity and coupon profiles;
- a curve twist rather than a parallel move;
- convexity and other nonlinear effects;
- a change in the CTD bond or CTD-adjusted futures DV01;
- repo specialness and delivery-option value;
- trade activity, fees or inconsistent market cuts.

Cash–futures basis is one useful lens for this divergence, but basis must be defined. It may mean a quoted gross basis, net basis, modelled relative-value measure or a full-revaluation component. A generic field called basis_pnl is not sufficient without methodology and lineage.

## Engineering Design

The explain should preserve one position population, aligned market cuts and explicit sign conventions.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class HedgePnLInput:
    cash_actual_pnl: Decimal
    cash_curve_dv01: Decimal
    cash_cs01: Decimal
    rate_move_bp: Decimal
    spread_move_bp: Decimal
    carry_pnl: Decimal
    futures_quantity: int
    futures_multiplier: Decimal
    futures_open_price: Decimal
    futures_close_price: Decimal
    position_snapshot_id: str
    market_cut_id: str


def explain_hedge_pnl(x: HedgePnLInput) -> dict:
    rates = x.cash_curve_dv01 * x.rate_move_bp
    spread = x.cash_cs01 * x.spread_move_bp

    futures = (
        Decimal(x.futures_quantity)
        * x.futures_multiplier
        * (x.futures_close_price - x.futures_open_price)
    )

    cash_before_residual = rates + spread + x.carry_pnl
    cash_residual = x.cash_actual_pnl - cash_before_residual

    return {
        "cash_rates_pnl": rates,
        "cash_spread_pnl": spread,
        "cash_carry_pnl": x.carry_pnl,
        "cash_residual": cash_residual,
        "futures_price_pnl": futures,
        "combined_pnl": x.cash_actual_pnl + futures,
        "position_snapshot_id": x.position_snapshot_id,
        "market_cut_id": x.market_cut_id,
    }
```

The approximation is diagnostic. Official actual PnL should still come from the desk’s approved valuation and settlement sources. If a full-revaluation basis component is required, it should be calculated as an explicit counterfactual state transition rather than inferred as whatever remains.

## Data Quality and Production Controls

Five controls provide most of the value:

1. Cash and futures must use the same close window and frozen position scope.
2. Futures quantity, quote unit and contract multiplier must have explicit sign and scale.
3. Opening futures risk must retain CTD, conversion factor and scenario versions.
4. Failed components must remain failed or null, never zero.
5. Component totals must reconcile to combined actual PnL.

A useful dashboard shows a waterfall for cash rates, cash spread, carry, futures price PnL and residual, with drill-down to bond position and futures contract. It should also show opening residual DV01 and whether the CTD changed during the window.

## Requirement Discovery and Interview Questions

When a trader asks whether the hedge worked, clarify:

- Is success defined by DV01 neutrality or actual PnL offset?
- Should risk be opening, closing or intraday?
- Is cash rates PnL based on a parallel move or key-rate moves?
- Does futures PnL use exchange settlement or a live price?
- Are spread, carry, fees and variation margin separate components?
- Is a CTD switch shown separately?
- Is the residual tolerance absolute, relative, or both?
- Can a partial explain be labelled successful?

A strong interview answer should emphasize that hedge performance is multi-dimensional. Risk neutrality is a local model statement; PnL effectiveness is an observed outcome under realized market moves.

## Key Takeaways

- DV01 neutrality does not guarantee zero daily PnL.
- Separate actual cash PnL, futures PnL and combined package PnL.
- Use DV01 and CS01 as diagnostic explain components, not substitutes for official valuation.
- Preserve futures sign, multiplier, CTD and market-cut lineage.
- Do not label every residual as basis without a defined counterfactual calculation.
- Define hedge effectiveness explicitly: risk neutrality, rates offset, basis stability or PnL-volatility reduction.