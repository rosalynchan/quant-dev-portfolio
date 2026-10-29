# Engineering Market-Data Failover Without Creating False Futures PnL

## Abstract

Market-data failover is often described as an availability problem: when the primary feed stops, use the backup. On a Rates desk, that is incomplete. Two healthy sources can quote the same futures contract differently because of timestamp alignment, venue coverage, rounding, or price construction. A raw switch can therefore create PnL that looks like a market move but is actually a change in measurement basis. This article develops a controlled failover pattern that estimates source basis from a valid overlap window, separates market PnL from source-basis PnL, and preserves lineage for traders, controls, and production support.

## Desk Context

Consider a desk long 100 short-rate futures contracts. The primary market-data source stops updating at 10:00, leaving a last valid mark of 95.200. At 10:05, a secondary source is healthy and shows 95.208.

A simple fallback rule publishes 95.208 and reports a price move of 0.008. With a multiplier of GBP 2,500 per point, that appears to be GBP 2,000 of PnL.

However, during the most recent period when both feeds were healthy and time-aligned, the secondary source was consistently 0.001 above the primary source. If that difference is ignored, feed architecture becomes part of market PnL.

The engineering question is not merely whether the backup value is valid. It is whether the two sources are economically comparable and how a change in source should be represented in the PnL explain.

## A Source Switch Changes the Measurement Basis

Let the two source prices for the same contract and price type be $P_t^A$ and $P_t^B$. During a synchronized overlap window, define the source basis as:

$$
b_t=P_t^B-P_t^A
$$

If downstream valuation is expressed on the primary-source convention, a primary-equivalent secondary mark can be constructed as:

$$
\widetilde{P}_t^B=P_t^B-\widehat{b}
$$

The estimate $\widehat{b}$ is not an alpha signal and should not be an arbitrary smoothing parameter. It is a measurement adjustment obtained from observations that pass explicit comparability tests.

This leads to a useful desk principle: a source switch is a change in measurement basis, not automatically a market move.

## Worked Numerical Example

Assume:

- quantity: +100 contracts;
- multiplier: GBP 2,500 per point;
- last valid primary mark: 95.200;
- secondary mark at the switch: 95.208;
- validated overlap basis, secondary minus primary: +0.001.

The raw switch PnL is:

$$
\text{RawSwitchPnL}
=100(95.208-95.200)(2{,}500)
=\text{GBP }2{,}000
$$

The source-basis component is:

$$
\text{SourceBasisPnL}
=100(0.001)(2{,}500)
=\text{GBP }250
$$

The adjusted secondary mark is:

$$
\widetilde{P}^B=95.208-0.001=95.207
$$

The primary-equivalent market PnL is therefore:

$$
\text{MarketPnL}
=100(95.207-95.200)(2{,}500)
=\text{GBP }1{,}750
$$

The explain reconciles exactly:

$$
\text{RawSwitchPnL}
=\text{MarketPnL}+\text{SourceBasisPnL}
$$

or GBP 2,000 = GBP 1,750 + GBP 250.

The GBP 250 is not additional economic profit. It is the mechanical effect of changing the measurement convention. A desk may choose to publish the raw secondary price rather than an adjusted price, but the explain should still identify the source-basis component. The published-price convention and PnL accounting identity must be designed together to avoid omission or double counting.

## What Makes an Overlap Window Valid?

Not every pair of observations can calibrate source basis. Both records should refer to the same contract and price type, use the same scale and currency, and be close in event time. Each side must independently pass freshness, market-shape, and source-health checks.

It is invalid to compare a primary midpoint with a secondary last trade and call the difference source basis. That number contains both a source effect and a price-type effect. It is equally unsafe to reuse a basis estimated hours earlier across a session boundary or a volatile market regime without an explicit policy.

A practical calibration result should carry the observation count, time window, median or other approved estimator, dispersion, maximum quote skew, and policy version. When no reliable overlap exists, the system should expose an explicit state such as `UNADJUSTED_FALLBACK` or remain unavailable. It should not manufacture continuity.

## Engineering Design

Failover should be modelled as a small state machine rather than a scattered collection of `if source is None` conditions. Useful states include `PRIMARY_ACTIVE`, `PRIMARY_STALE`, `SECONDARY_ACTIVE`, and `RECOVERY_PROBATION`.

The probation state matters because a primary feed may recover briefly and fail again. Immediate automatic fail-back creates source ping-pong, repeated basis events, and a flickering dashboard.

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class FailoverDecision:
    source_from: str
    source_to: str
    raw_price: Decimal
    basis_to_primary: Decimal
    effective_at: datetime
    policy_version: str


def apply_failover(
    last_primary: Decimal,
    decision: FailoverDecision,
    quantity: int,
    multiplier: Decimal,
) -> dict:
    adjusted = decision.raw_price - decision.basis_to_primary
    source_basis_pnl = (
        Decimal(quantity) * decision.basis_to_primary * multiplier
    )
    market_pnl = (
        Decimal(quantity) * (adjusted - last_primary) * multiplier
    )

    return {
        "published_mark": adjusted,
        "market_pnl": market_pnl,
        "source_basis_pnl": source_basis_pnl,
        "raw_switch_pnl": market_pnl + source_basis_pnl,
        "active_source": decision.source_to,
        "policy_version": decision.policy_version,
    }
```

The result is intentionally richer than a price. A consumer must be able to identify the active source, adjustment, effective time, policy version, and explain components.

## Data Quality and Production Controls

Four controls matter most for this workflow.

First, calibration requires fresh synchronized overlap, with minimum sample count and maximum dispersion. Second, a switch event needs an idempotency key, such as contract, outage identifier, and target source, so replay cannot generate PnL twice. Third, recovery needs probation and hysteresis to prevent rapid source switching. Fourth, live-risk fallback and official EOD valuation need separate policies: permission to use a backup for an indicative dashboard does not authorize it for an official ledger.

Observability should show active source, source age, switch reason, basis estimate, calibration quality, and time spent in each state. A useful alert says “secondary active; basis 0.001; calibration 25 observations; primary in probation,” not merely “feed degraded.”

A common production failure is comparing different price types across sources. Another is publishing an adjusted mark and then adding source-basis PnL to the total again. Both arise when data lineage and the accounting identity are implemented in separate systems without a shared policy contract.

## Requirement Discovery and Interview Questions

When a trader asks to “switch to the backup,” a developer should clarify:

- Is failover for live risk, indicative PnL, or official EOD valuation?
- Do both sources provide the same price type and timestamp semantics?
- How long may the primary remain stale before switching?
- How is basis estimated, and what age and dispersion limits apply?
- What happens when no valid overlap exists?
- How many healthy updates are required before failing back?
- Should source-basis PnL require acknowledgement above a threshold?
- Can the official settlement workflow ever use an automatic fallback?

A strong interview answer connects availability to economics: “I would not only select the next healthy feed. I would validate comparability, calibrate a synchronized source basis, version the policy, expose source lineage, and reconcile raw switch PnL into market and source-basis components.”

## Key Takeaways

- A valid backup price can still use a different measurement basis.
- Source basis must be estimated from comparable, fresh, synchronized observations.
- Raw switch PnL should reconcile to market PnL plus source-basis PnL.
- Failover and fail-back are explicit, idempotent state transitions.
- Live and official valuation workflows require separate fallback authority.
- Source, basis, calibration quality, and policy version belong in the valuation result, not only in operational logs.

Suggested repository filename: `2026-10-29-day-64-market-data-failover.md`.
