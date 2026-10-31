# Atomic Curve Snapshots: Preventing Mixed-Time Rates PnL

## Abstract

A Rates curve can bootstrap successfully even when its inputs describe different moments in the market. If a new 2Y quote is combined with an old 5Y quote, the resulting curve may never have existed economically, yet it can still generate prices, risk, and plausible PnL. This article explains atomic curve snapshots: versioned, immutable input sets governed by an explicit cutoff and published as a single object. It shows how mixed-time nodes create ghost PnL, how watermarks and manifests support reproducibility, and how a front-office system should behave while a snapshot is incomplete.

## Desk Context

Suppose a Rates portfolio has signed market-quote sensitivities of GBP −1,200 per basis point to the 2Y node and GBP +800 per basis point to the 5Y node. A positive signed sensitivity means the portfolio gains when that quote rises; a negative sensitivity means it loses.

Around 10:00, the economic market move is +4bp at 2Y and +3bp at 5Y. The 2Y update arrives first. A curve builder immediately combines the new 2Y quote with the old 5Y quote and publishes a valuation. One second later, the 5Y update arrives and the curve is rebuilt.

The dashboard first shows a GBP 4,800 loss and then a GBP 2,400 recovery. That pattern looks like market volatility, but it is an artefact of publishing a half-new, half-old curve.

## A Curve Is a Versioned Object

A valuation curve should not be understood as a live dictionary of the latest available node values. It is an indivisible object with economic and technical identity:

$$
C^{(v)}=
\left(
\text{inputs},
\text{cutoff},
\text{builder version},
\text{quality state}
\right)
$$

Inputs may have different event timestamps, but a snapshot policy determines which observations are eligible for version $v$. Mandatory instruments must be present, each quote must be fresh enough, cross-source timing skew must remain within policy, and any carried-forward node must be explicit.

The core principle is that successful bootstrapping proves numerical solvability, not temporal consistency. A curve can converge and still represent a market state that never existed.

## Worked Numerical Example

Define signed sensitivity as approximate PnL for a 1bp rise in the corresponding market quote:

- 2Y sensitivity: GBP −1,200/bp;
- 5Y sensitivity: GBP +800/bp.

The complete economic move is:

$$
\Delta q_{2Y}=+4\text{bp},\qquad
\Delta q_{5Y}=+3\text{bp}
$$

The mixed-time snapshot includes the new 2Y quote but the old 5Y quote:

$$
\begin{aligned}
\text{PnL}_{mixed}
&=(-1{,}200)(4)+(800)(0)\\
&=-\text{GBP }4{,}800
\end{aligned}
$$

The atomic snapshot includes both updates:

$$
\begin{aligned}
\text{PnL}_{atomic}
&=(-1{,}200)(4)+(800)(3)\\
&=-4{,}800+2{,}400\\
&=-\text{GBP }2{,}400
\end{aligned}
$$

The temporary ghost difference is:

$$
\text{GhostPnL}
=\text{PnL}_{mixed}-\text{PnL}_{atomic}
=-\text{GBP }2{,}400
$$

When the 5Y update arrives, the dashboard appears to gain GBP 2,400. No new market event is required to explain that recovery; the input set merely becomes complete.

This linear calculation provides intuition. Full revaluation may include interpolation, nonlinear pricing, and cross-gamma, but atomicity remains necessary regardless of the valuation model.

## Event Time, Cutoff, and Publish Time

Three timestamps should remain distinct.

Quote event time identifies the economic moment represented by an input. Snapshot cutoff, often implemented through a watermark, states that the builder has assembled an eligible set for a defined market time. Publish time records when the complete curve version became available to consumers.

For example, the snapshot cutoff may be 10:00:05. A 5Y quote with event time 10:00:04 may not reach the platform until 10:00:06. The builder can publish the complete 10:00:05 snapshot at 10:00:06 while recording one second of completion latency.

It would be wrong to rewrite every input event time to 10:00:06. It would also be wrong for an as-observed replay to pretend the late input was available before its ingestion time.

## The Snapshot Manifest

Each curve version needs a manifest containing the curve identifier and version, cutoff and publish time, every input instrument, quote value, event time, source and revision, the builder configuration version, carried-forward or excluded inputs, and the resulting quality state.

Quality might be `COMPLETE`, `DEGRADED`, or `REJECTED`. A degraded snapshot is not automatically wrong, but consumers must opt into its economic meaning. It must never be labelled complete merely because the bootstrap solver returned a result.

A downstream valuation result should reference the exact curve version, not only a curve name. Otherwise the trade cannot be replayed after quotes, corrections, or builder configuration change.

## Engineering Design

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class CurveQuote:
    instrument_id: str
    value: Decimal
    event_time: datetime
    source: str
    revision: int


def build_snapshot(
    required_ids: set[str],
    quotes: list[CurveQuote],
    cutoff: datetime,
    max_age: timedelta,
) -> dict:
    eligible = {
        q.instrument_id: q
        for q in quotes
        if q.instrument_id in required_ids
        and q.event_time <= cutoff
        and cutoff - q.event_time <= max_age
    }

    missing = required_ids - eligible.keys()
    if missing:
        raise ValueError(f"incomplete curve snapshot: {sorted(missing)}")

    manifest = tuple(
        sorted(
            (q.instrument_id, q.event_time, q.source, q.revision)
            for q in eligible.values()
        )
    )
    return {
        "cutoff": cutoff,
        "quality": "COMPLETE",
        "quotes": eligible,
        "manifest": manifest,
    }
```

The example deliberately rejects incomplete sets. A production system may support an approved degraded mode, but that policy should create a different quality state and record every carried-forward node.

## Production Controls and Failure Modes

Five controls are especially useful. Publish a curve version atomically only after mandatory inputs meet cutoff, freshness, and skew rules. Persist the manifest and builder configuration version. Record missing and carried-forward nodes rather than hiding them. Generate a stable content hash so rebuilding the same manifest is idempotent and cacheable. Monitor snapshot completion latency, stale-node count, and rejected-build rate.

A common concurrency failure occurs when node values are updated in place in a shared dictionary while a risk engine reads halfway through the update. The consumer obtains a mixed-time curve without any explicit degraded state.

Another failure appears after a vendor correction. If the manifest stores a quote source but not its revision, the platform cannot determine whether the historical curve used revision 1 or revision 2. The revision lineage from the previous lesson therefore belongs inside the curve manifest.

## Requirement Discovery and Interview Questions

When a trader or quant asks to “keep the curve live,” clarify:

- What is the maximum acceptable publication latency?
- Which instruments are mandatory and which may be absent?
- Are freshness and timing-skew limits global or tenor-specific?
- While incomplete, should the system retain the last complete curve, publish a degraded version, or fail valuation?
- Can carried-forward nodes enter official PnL?
- Does a late quote create a new revision for the same cutoff?
- Should a corrected curve trigger portfolio restatement?
- Which quality and node-level exceptions must appear on the dashboard?

A strong interview answer makes the trade-off explicit: “I would not let consumers read mutable node caches. I would assemble a versioned input manifest behind a watermark, publish the curve atomically, and expose age and quality while waiting for completeness.”

## Key Takeaways

- Individually fresh quotes do not guarantee a time-consistent curve.
- Numerical convergence does not prove that the market state existed.
- Event time, snapshot cutoff, and publish time serve different purposes.
- Every valuation should reference an immutable curve version and input manifest.
- Incomplete or carried-forward inputs require an explicit quality state.
- Atomic publication prevents mixed-time nodes from masquerading as market PnL.

Suggested repository filename: `2026-10-31-day-66-atomic-curve-snapshots.md`.
