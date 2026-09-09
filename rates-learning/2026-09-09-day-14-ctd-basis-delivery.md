# Cheapest-to-Deliver, Conversion Factors and Basis Risk in Bond Futures

## Abstract

A bond-futures hedge is not tied to one permanent underlying bond. The short chooses from a deliverable basket, and the cheapest-to-deliver bond can change as cash prices, curves and financing conditions move. This article explains invoice pricing, conversion factors, basis ranking and CTD-adjusted futures DV01, then turns those concepts into reproducible data contracts, controls and production diagnostics for a front-office analytics platform.

## Desk Context

A trader has used 200 bond-futures contracts to hedge a cash-bond portfolio. The hedge is close to DV01-neutral in the morning. Later, the curve moves and a different deliverable becomes cheapest to deliver. The position quantities have not changed, yet the dashboard shows a material residual DV01.

The right question is not simply whether the risk engine is wrong. The contract's effective risk proxy may have changed.

This is **CTD switch risk**: the futures contract remains the same legal instrument, but the bond driving its delivery economics—and therefore its approximate DV01—changes.

## The Delivery Option

Physically delivered government-bond futures generally specify a **deliverable basket** rather than one bond. The short chooses which eligible bond to deliver.

For each candidate, the short considers:

- the cost of acquiring the cash bond;
- financing it to the delivery date;
- coupons received before delivery;
- the futures invoice proceeds;
- the exchange conversion factor;
- timing and other delivery options.

The candidate with the lowest delivery economics is commonly called the **cheapest-to-deliver**, or CTD.

CTD should therefore be modelled as a market-dependent result, not a static security-master attribute. It can change when the cash curve, repo assumptions, bond prices or futures price changes.

## Conversion Factor and Invoice Price

Deliverable bonds have different coupons and maturities. The exchange-provided **conversion factor** standardizes their delivery economics against the futures contract.

For a simplified price per 100 of face value:

$$
\text{Invoice Price}
=
\text{Futures Price}\times\text{Conversion Factor}
+
\text{Accrued Interest}
$$

The conversion factor is not duration and is not itself a hedge ratio. It is a contractual adjustment, but it also enters a widely used approximation for futures DV01.

Production calculations must make the contract multiplier, currency, price unit, delivery date and exchange rounding rules explicit.

## Worked Example: From Basis to CTD

Suppose a futures contract is quoted at 116.00. Candidate bond A has:

- cash clean price: 105.50;
- accrued interest at delivery: 1.20;
- conversion factor: 0.9125;
- net carry benefit to delivery: 0.18 points.

The converted futures price is:

$$
116.00\times0.9125=105.85
$$

The invoice price is therefore:

$$
105.85+1.20=107.05
$$

The cash dirty price is:

$$
105.50+1.20=106.70
$$

Using the signed convention

$$
\text{Gross Basis}
=
\text{Cash Clean Price}
-
\text{Futures Price}\times\text{Conversion Factor},
$$

candidate A has:

$$
\text{Gross Basis}_A=105.50-105.85=-0.35
$$

If net basis subtracts the carry benefit:

$$
\text{Net Basis}_A=-0.35-0.18=-0.53
$$

Suppose candidate B has a net basis of -0.21 under the same methodology. Under a lowest-net-basis rule, A is CTD.

This example also illustrates a requirement trap: firms and vendors may use different signs or carry conventions. A field called `basis` is not a sufficient contract. The result must carry its formula, unit and methodology version.

## CTD-Adjusted Futures DV01

A common approximation is:

$$
\text{Futures DV01}
\approx
\frac{\text{CTD DV01}}{\text{Conversion Factor}}
$$

If candidate A has DV01 of GBP 72 per basis point per deliverable unit:

$$
\text{Futures DV01}_A
\approx
\frac{72}{0.9125}
=
\text{GBP }78.90/\text{bp}
$$

For a portfolio with signed DV01 of -GBP 15,780 per basis point, about 200 short futures contracts are required if a short contract contributes positive sensitivity to a one-basis-point yield rise:

$$
\frac{15{,}780}{78.90}=200
$$

Now suppose bond B becomes CTD and its adjusted futures DV01 is:

$$
\frac{85}{0.95}=\text{GBP }89.47/\text{bp}
$$

The same 200 short contracts now contribute approximately:

$$
200\times89.47=\text{GBP }17{,}894/\text{bp}
$$

The hedge overshoots the portfolio risk by roughly GBP 2,114 per basis point. No trade changed; the CTD assumption did.

## Why DV01 Neutrality Does Not Remove Basis Risk

Even a perfectly sized local DV01 hedge retains material risks:

- the cash-futures basis can widen or tighten;
- repo and funding assumptions can move;
- curve twists affect basket candidates differently;
- the CTD can switch;
- conversion factors are static while market risk is dynamic;
- delivery-option value changes near expiry;
- the portfolio bond and CTD differ in maturity, coupon, liquidity and sometimes issuer exposure.

A futures hedge is therefore a controlled approximation, not the elimination of all risk.

## Engineering Design

### Canonical data contracts

```python
@dataclass(frozen=True)
class DeliverableBond:
    instrument_id: str
    contract_id: str
    conversion_factor: Decimal
    eligibility_version: str

    clean_price: Decimal
    accrued_interest: Decimal
    cash_price_timestamp: datetime

    dv01: Decimal
    repo_rate: Decimal
    coupon_cash_before_delivery: Decimal
```

```python
@dataclass(frozen=True)
class DeliveryAnalytics:
    contract_id: str
    instrument_id: str
    delivery_date: date

    invoice_price: Decimal
    gross_basis: Decimal
    net_basis: Decimal
    implied_futures_dv01: Decimal

    is_ctd: bool
    rank: int
    calculation_version: str
    market_snapshot_id: str
    status: Literal["SUCCESS", "FAILED"]
```

### Ranking candidates

```python
def rank_deliverables(contract, basket, market, policy):
    rows = []

    for bond in basket:
        policy.require_eligible(bond, contract)

        invoice = (
            market.futures_price * bond.conversion_factor
            + accrued_interest(bond, contract.delivery_date)
        )

        gross_basis = (
            market.clean_price(bond.instrument_id)
            - market.futures_price * bond.conversion_factor
        )

        carry = carry_to_delivery(
            bond=bond,
            delivery_date=contract.delivery_date,
            repo_curve=market.repo_curve,
        )

        rows.append(
            DeliveryAnalytics(
                contract_id=contract.contract_id,
                instrument_id=bond.instrument_id,
                delivery_date=contract.delivery_date,
                invoice_price=invoice,
                gross_basis=gross_basis,
                net_basis=gross_basis - carry,
                implied_futures_dv01=(
                    market.dv01(bond.instrument_id)
                    / bond.conversion_factor
                ),
                is_ctd=False,
                rank=0,
                calculation_version=policy.version,
                market_snapshot_id=market.snapshot_id,
                status="SUCCESS",
            )
        )

    return rank(rows, key="net_basis", ascending=True)
```

The ranking function should not silently drop a candidate with missing data and still claim complete coverage. A failed candidate may be the true CTD.

### Event-driven refresh

CTD analytics should be invalidated when any material dependency changes:

```text
cash bond prices
futures price
repo assumptions
curve snapshot
deliverable basket or conversion factors
delivery-date policy
```

A change in the top-ranked candidate should emit a `CTD_SWITCH` event and recompute futures DV01, hedge ratio and PnL attribution.

## Data Quality, Controls and Observability

Core controls should include:

- basket and conversion-factor versions match the contract month;
- every eligible candidate has required market and reference data;
- cash, futures, curve and repo inputs use a compatible market cut;
- accrued interest uses the actual delivery date;
- coupons are neither omitted nor double-counted;
- basis, carry and implied-repo signs and units are explicit;
- ranking coverage equals the expected eligible basket;
- a CTD switch invalidates cached futures risk;
- the dashboard exposes the runner-up and basis gap, not only the winner;
- failed candidates remain failed, never zero.

Useful metrics include:

```text
deliverable_basket_coverage_ratio
ctd_candidate_count
ctd_switch_total{contract}
ctd_runner_up_gap_points
conversion_factor_missing_total
mixed_market_cut_rejection_total
futures_dv01_age_seconds
hedge_residual_dv01
```

The runner-up gap is operationally important. A tiny gap means the CTD is unstable, and a deterministic dashboard may otherwise appear to jump unpredictably between candidates.

## Production Failure Modes

1. **Stale CTD cache** — market ranking changes while the risk service retains the old CTD.
2. **Incomplete basket** — a missing price silently removes the true cheapest candidate.
3. **Wrong contract month** — one expiry's basket is paired with another expiry's futures quote.
4. **Conversion-factor scaling** — 0.9125 is interpreted as 91.25.
5. **Clean/dirty collision** — clean cash price is compared with an invoice amount inconsistently.
6. **Coupon double count** — the same coupon appears in carry and settlement cash.
7. **Mixed timestamps** — live futures are ranked against yesterday's cash closes.
8. **Hidden repo fallback** — special repo is unavailable and generic funding is substituted without a status flag.
9. **Ranking-direction error** — lowest cost and highest implied repo conventions are confused.
10. **Switch noise** — an immaterial basis gap causes repeated CTD flips and dashboard churn.
11. **Rounding drift** — internal Decimal policy differs from exchange invoice rounding.
12. **False certainty** — only one CTD is shown, with no runner-up gap or switch proximity.

## Requirement Discovery and Interview Questions

When a trader asks for “the CTD and basis,” clarify:

- Which contract month and delivery date are in scope?
- Is the assumed date first delivery, last delivery or an optimized date?
- Is the ranking measure net basis or implied repo?
- Does the cash side use bid, ask, mid or an executable side?
- Does financing use general collateral, special repo or a desk funding curve?
- How are coupons, accrued interest and financing treated?
- What are the basis sign and unit?
- Should the screen show the runner-up and basis gap?
- Does futures DV01 use the current CTD, scenario CTDs or weighted candidates?
- Does a switch trigger an alert, automatic risk refresh or hedge recommendation?
- Can partial basket coverage be published?
- Which exchange-rule, basket and conversion-factor versions must be retained?

An interview-ready answer is:

> I model CTD as a versioned calculation over the complete deliverable basket, not as static reference data. Each result retains the cash and futures market cut, repo assumptions, delivery-date policy, conversion factor and ranking methodology. A CTD switch invalidates futures risk and triggers a recomputation of the hedge residual.

## Key Takeaways

- A physically delivered bond future references a basket, while the short owns the delivery choice.
- Conversion factors normalize invoice economics but do not eliminate differences between candidates.
- CTD selection depends on cash price, futures price, carry, repo and delivery assumptions.
- CTD-adjusted futures DV01 can change materially when the CTD switches.
- DV01-neutral futures hedges retain basis, curve-shape, repo and delivery-option risk.
- Production systems need complete-basket coverage, versioned lineage, switch events and explicit failure states.

*All examples are generic and illustrative. This article contains no confidential employer data, proprietary architecture, client information or investment advice.*
