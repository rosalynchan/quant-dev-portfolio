# Hedging Bond DV01 with Futures: CTD, Conversion Factors and Production Controls

## Abstract

A bond-futures hedge should be sized by risk, not notional. The practical calculation links a cash book’s DV01 to the futures contract through the deliverable basket, cheapest-to-deliver bond, conversion factor and, where appropriate, a hedge beta. This article explains the economics, works through a contract-count example, and shows how to engineer a reproducible hedge recommendation without hiding basis, curve or CTD-switch risk.

## Desk Context

A government-bond book has signed curve DV01 of -GBP 125,000 per basis point. The trader wants to short bond futures. One screen recommends 1,389 contracts; a spreadsheet recommends 1,462.

Both can be internally consistent. The first may use a pure CTD-adjusted DV01 ratio. The second may also apply a 0.95 beta because the cash book does not move one-for-one with the futures hedge.

The developer must expose the assumptions rather than return an unexplained integer.

## Futures and the Deliverable Basket

A bond-futures short can normally choose an eligible government bond from a deliverable basket during the delivery period. Basket members have different coupons, maturities, prices and durations. A conversion factor standardises their delivery economics.

A simplified invoice relationship is:

\[
InvoicePrice=FuturesPrice\times ConversionFactor+AccruedInterest
\]

Actual implementation also requires the contract multiplier, quotation convention, rounding and exchange delivery rules.

The cheapest-to-deliver bond, or CTD, is the deliverable that minimises the short’s economic delivery cost under the current cash, futures and financing assumptions. Implied repo analysis is commonly used, but CTD is not permanent. It can change with the curve, cash prices, repo, futures price and time to delivery.

## From CTD DV01 to Futures DV01

A common approximation is:

\[
FuturesDV01\approx\frac{CTD\ CashDV01}{ConversionFactor}
\]

If CTD cash DV01 is GBP 72/bp and the conversion factor is 0.80:

\[
FuturesDV01\approx72/0.80=GBP\ 90/bp
\]

This is a practical local sensitivity, not a complete option-adjusted futures model. It does not fully capture CTD switching, delivery optionality, basis, convexity or financing.

## Worked Hedge-Ratio Example

Assume:

- Cash-book signed DV01: -GBP 125,000/bp
- CTD cash DV01: -GBP 72/bp per contract-equivalent
- Conversion factor: 0.80
- One long futures contract has negative rate DV01
- A short contract therefore contributes positive DV01

The long futures DV01 is:

\[
-72/0.80=-GBP\ 90/bp
\]

The signed contract quantity required for a DV01-neutral hedge is:

\[
N=-\frac{BookDV01}{LongFuturesDV01}
\]

\[
N=-\frac{-125,000}{-90}=-1,388.89
\]

The negative sign means short. Rounding gives 1,389 short contracts.

Residual DV01 is:

\[
-125,000+1,389\times90=+GBP\ 10/bp
\]

### Beta-Adjusted Hedge

If the estimated relationship between the book and futures hedge is 0.95:

\[
EffectiveFuturesDV01=90\times0.95=GBP\ 85.5/bp
\]

\[
Contracts=125,000/85.5=1,461.99
\]

The beta-adjusted recommendation is 1,462 short contracts.

The correct choice depends on the objective:

- Pure DV01 matching uses 1,389.
- A beta-adjusted hedge uses 1,462.
- A minimum-variance hedge may use a different statistical optimisation.

## Why DV01-Neutral Is Not PnL-Neutral

A hedge can have near-zero initial DV01 and still produce PnL.

### Curve mismatch

The cash book may concentrate risk at 7Y and 15Y while the futures CTD behaves more like 10Y. A curve twist breaks a parallel-risk hedge.

### Cash–futures basis

A simplified basis is:

\[
Basis=CashPrice-FuturesPrice\times CF
\]

Basis movement creates PnL even when outright duration is hedged.

### CTD switching

A different deliverable may become cheapest. Futures duration and effective DV01 can change discontinuously.

### Convexity mismatch

Cash bonds and the futures/CTD package may have different convexity, so hedge effectiveness drifts during large moves.

### Carry and financing

Cash bonds have coupons, accrual and repo economics. Futures have margin, roll and delivery effects.

The accurate desk statement is: the position may be DV01-neutral while retaining curve and basis risk.

## PnL Sanity Check

If yields rise 4bp:

\[
UnhedgedPnL=-125,000\times4=-GBP\ 500,000
\]

For 1,389 short contracts:

\[
FuturesPnL=1,389\times90\times4=+GBP\ 500,040
\]

Linear net PnL is GBP 40. If actual hedged PnL is -GBP 18,000, investigate curve shape, basis, CTD, convexity, financing, execution price, timing, fees and stale risk before calling it a pricing error.

## Engineering Design

\`\`\`python
@dataclass(frozen=True)
class BondFutureContract:
    contract_id: str
    exchange: str
    expiry: date
    delivery_month: str
    contract_face: Decimal
    price_multiplier: Decimal
    specification_version: str


@dataclass(frozen=True)
class DeliverableBond:
    instrument_id: str
    conversion_factor: Decimal
    clean_price: Decimal
    accrued_interest: Decimal
    cash_dv01: Decimal
    repo_rate: Decimal
    eligibility_version: str
\`\`\`

\`\`\`python
@dataclass(frozen=True)
class CTDResult:
    contract_id: str
    ctd_instrument_id: str
    conversion_factor: Decimal
    implied_repo_rate: Decimal
    futures_dv01: Decimal

    market_snapshot_id: str
    financing_snapshot_id: str
    methodology_version: str
    status: Literal["SUCCESS", "FAILED"]
\`\`\`

\`\`\`python
@dataclass(frozen=True)
class HedgeRecommendation:
    book_id: str
    contract_id: str
    signed_contract_quantity: int

    book_dv01: Decimal
    futures_dv01: Decimal
    beta: Decimal
    residual_dv01: Decimal

    ctd_instrument_id: str
    scenario_id: str
    calculation_status: str
\`\`\`

\`\`\`python
def recommend_futures_hedge(
    book_risk,
    futures_market,
    deliverables,
    policy,
):
    ctd = select_ctd(
        futures_market=futures_market,
        deliverables=deliverables,
        financing=policy.financing_snapshot,
        method=policy.ctd_method,
    )

    futures_dv01 = (
        ctd.cash_dv01
        / ctd.conversion_factor
    )

    effective_dv01 = (
        futures_dv01
        * policy.hedge_beta
    )

    raw_quantity = (
        -book_risk.signed_dv01
        / effective_dv01
    )

    quantity = round_according_to_policy(
        raw_quantity,
        policy.rounding_method,
    )

    residual = (
        book_risk.signed_dv01
        + quantity * effective_dv01
    )

    return HedgeRecommendation(
        book_id=book_risk.book_id,
        contract_id=futures_market.contract_id,
        signed_contract_quantity=quantity,
        book_dv01=book_risk.signed_dv01,
        futures_dv01=futures_dv01,
        beta=policy.hedge_beta,
        residual_dv01=residual,
        ctd_instrument_id=ctd.instrument_id,
        scenario_id=policy.scenario_id,
        calculation_status="SUCCESS",
    )
\`\`\`

Signed quantity should remain canonical internally. A UI can translate negative quantity into SELL, avoiding duplicated sign logic.

## Data Flow and Controls

\`\`\`text
Cash-book positions
        |
Bucketed curve risk
        |
Target DV01 and hedge horizon
        |
Contract specification
        |
Deliverable basket + prices + repo
        |
CTD + conversion factor
        |
Futures DV01 + optional beta
        |
Integer contract quantity
        |
Residual risk + scenario checks
\`\`\`

Controls should require:

- correct contract and expiry;
- complete, versioned deliverable basket;
- aligned cash, futures and repo cuts;
- positive conversion factor;
- compatible book and futures risk scenarios;
- correct multiplier and units;
- versioned beta window and frequency;
- residual recalculation after integer rounding;
- automatic risk refresh after CTD changes;
- an explicit contract-roll policy;
- failure rather than zero when no valid CTD exists;
- a boundary between recommendation and authorised execution.

## Tests and Observability

\`\`\`python
def test_short_future_offsets_long_bond_dv01():
    result = recommend(long_duration_book)
    assert result.signed_contract_quantity < 0
    assert abs(result.residual_dv01) < tolerance


def test_lower_cf_increases_futures_dv01():
    assert (
        futures_dv01(72, 0.8)
        > futures_dv01(72, 0.9)
    )


def test_missing_ctd_is_not_zero_hedge():
    result = recommend_without_valid_deliverables()
    assert result.status == "FAILED"
    assert result.contract_count is None
\`\`\`

Monitor CTD age and changes, basket coverage, futures-DV01 reconciliation, residual DV01, beta-version usage, days to roll and failures by reason.

A useful dashboard shows book DV01, contract and expiry, CTD and runner-up, conversion factor, futures DV01, beta, raw and rounded quantities, residual DV01, switch warnings and market/financing lineage.

## Common Production Failure Modes

1. Matching notionals instead of risk.
2. Using a stale CTD.
3. Applying the wrong contract-month conversion factor.
4. Confusing per-100, per-contract and currency units.
5. Reversing the hedge direction.
6. Mixing cash, futures and repo cuts.
7. Treating an incomplete basket as successful.
8. Recommending an expiring contract inside the roll window.
9. Estimating beta with future data.
10. Using unversioned beta windows.
11. Ignoring CTD changes.
12. Hedging total DV01 while worsening tenor buckets.
13. Hiding integer-rounding residuals.
14. Treating a recommendation API as execution authority.

## Requirement Discovery

Clarify:

- total DV01 or selected tenor buckets;
- contract and expiry;
- hedge horizon;
- current CTD or scenario-weighted deliverables;
- conversion-factor treatment;
- whether beta is required and how it is estimated;
- curve and risk methodology;
- DV01-neutral, minimum-variance or PnL-protection objective;
- rounding and liquidity limits;
- roll policy;
- refresh behaviour after CTD changes;
- recommendation versus execution;
- approval and audit requirements.

## Key Takeaways

- Size bond-futures hedges by sensitivity, not notional.
- Futures DV01 depends on the current CTD and conversion factor.
- A hedge beta is a separate, versioned assumption.
- Whole-contract rounding leaves residual risk that must be shown.
- DV01 neutrality does not eliminate curve, basis, convexity or CTD-switch risk.
- Contract specifications, basket eligibility, prices and financing require aligned lineage.
- A hedge calculator should support decisions without silently becoming an execution system.