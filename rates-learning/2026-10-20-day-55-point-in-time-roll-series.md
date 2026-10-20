# Building Point-in-Time Futures Roll Series Without Look-Ahead Bias

## Abstract

A continuous futures series can be mathematically adjusted yet still be unsuitable for backtesting. Historical open interest may be corrected after publication, roll rules may change, and exchange calendars may be revised. If a research pipeline rebuilds the past using today’s latest values and policies, it can move historical roll dates to times that were not knowable in production. This article shows how point-in-time data, bitemporal versioning, and decision lineage prevent look-ahead bias while supporting both tradable replay and latest-corrected analysis.

## Desk and Research Context

Suppose a short-rate futures roll policy requires the next contract’s liquidity score to remain at or above 0.60 for two consecutive sessions. In production, the system observed 0.58 on 10 June and 0.63 on 11 June. Confirmation was incomplete, so the generic contract did not roll.

A week later, the vendor corrected the 10 June open-interest figure. The recalculated score became 0.62. A research platform that keeps only the latest value now sees two consecutive qualifying sessions and moves the historical roll date earlier.

The rebuilt series may look cleaner and the strategy may perform better, but the corrected value did not exist at the original decision time. The backtest has used future information.

The fundamental question is not simply, “What is the best value for 10 June today?” It is:

> What information was actually available to the decision process at the historical cutoff?

## Three Times for One Observation

A market-data record should distinguish at least three timestamps:

- **Event time:** the session or instant described by the value.
- **Publication time:** when the exchange or vendor released it.
- **Ingestion time:** when the consuming system actually received and could use it.

Open interest describing the 10 June session might be published at 07:00 on 11 June and ingested at 07:03. A correction might arrive on 18 June. A decision made at the 10 June close cannot use either version; a decision on 12 June can use the original but not the correction.

For decision time $t$, the available information set is:

$$
AvailableData(t)=\{x\mid ingestion\_time_x\le t\}
$$

Publication time helps explain source latency, but ingestion time is normally the decisive system boundary. A vendor may publish data while an internal feed is delayed or unavailable.

## As-Observed and Latest-Corrected Views

A robust platform supports two explicit historical views.

The **as-observed view** returns the record version available at the requested cutoff. It is required for tradable backtests, model validation, incident replay, and reproducing a production decision.

The **latest-corrected view** returns the best value known now. It is useful for data-quality investigations, revised reporting, and analyses that deliberately study corrected history.

Neither view is inherently wrong. The failure occurs when an API silently returns the latest version and a consumer assumes it represents the historical information set.

Data versioning alone is also insufficient. A roll decision depends on policy and reference data:

$$
Decision=f(DataAsOf,PolicyVersion,CalendarVersion)
$$

Applying today’s 0.60 threshold to a period when production used 0.65 rewrites history even if every market-data record is perfectly versioned.

## Worked Example: A Two-Day Roll Shift

Assume the policy requires two consecutive scores at or above 0.60. The values observed in production were:

- 9 June: 0.61;
- 10 June: 0.58;
- 11 June: 0.63;
- 12 June: 0.66.

The 10 June failure resets the confirmation count. The first valid production roll date is therefore 12 June, following qualifying observations on 11 and 12 June.

The corrected history later changes 10 June from 0.58 to 0.62. A latest-value rebuild now sees qualifying observations on 9 and 10 June and rolls on 10 June—two sessions earlier than the decision that was actually possible.

Suppose the synchronized front/next roll gap was 0.18 on 10 June and 0.25 on 12 June. The altered date changes the continuous-series adjustment chain. It may also change signal returns, execution assumptions, transaction costs, and the price at which a simulated position enters the next contract.

If those differences improve the backtest by GBP 40,000, that amount is not demonstrated alpha. It is information-leakage PnL unless the corrected value was available at the original cutoff.

The platform should publish two labelled results:

- a production replay that uses the original ingestion cutoff and rolls on 12 June;
- a latest-corrected analysis that may roll on 10 June but is not described as a tradable backtest.

## Bitemporal Engineering Design

A table keyed only by `(contract_id, market_session)` can store only one value. When a correction overwrites the row, evidence of the original information state disappears.

A point-in-time store needs two temporal dimensions:

- **valid time**, identifying the market session described by the record;
- **system time**, identifying when that version was considered active by the platform.

For the 10 June observation, the original version may be system-valid from 11 to 18 June. The corrected version becomes system-valid from 18 June onward. A query with an as-of cutoff on 12 June returns the original; a cutoff on 20 June returns the correction.

```python
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal


@dataclass(frozen=True)
class LiquidityVersion:
    contract_id: str
    market_session: date
    score: Decimal
    ingested_at: datetime
    superseded_at: datetime | None
    vendor_version: str


def value_as_of(
    versions: list[LiquidityVersion],
    contract_id: str,
    session: date,
    cutoff: datetime,
) -> LiquidityVersion:
    eligible = [
        x for x in versions
        if x.contract_id == contract_id
        and x.market_session == session
        and x.ingested_at <= cutoff
        and (x.superseded_at is None or cutoff < x.superseded_at)
    ]
    if len(eligible) != 1:
        raise ValueError("non-unique point-in-time value")
    return eligible[0]
```

Corrections should append a new version and close the prior system-time interval. They should not update the old row in place.

## Production Controls

The essential controls are focused:

1. **Immutable revisions.** Preserve every vendor version and its record-level ingestion timestamp.
2. **Explicit cutoff.** Every backtest or replay request supplies a timezone-aware decision cutoff.
3. **Complete decision lineage.** A roll event records data versions, policy version, calendar version, decision time, and output reason.
4. **Shared decision code.** Research replay should call the production roll engine rather than reimplementing similar logic in a notebook.
5. **Visible vintage labels.** APIs and dashboards distinguish `AS_OBSERVED` from `LATEST_CORRECTED`.

A common failure is retaining only a data-file date. The platform knows which daily file contained a record but not when an individual correction arrived. That is insufficient to prove what the strategy could have known at a specific cutoff.

## Requirement Discovery

When asked to rebuild a historical continuous future, clarify:

- Is the objective a tradable historical replay or today’s best corrected history?
- Is the decision cutoff the close, next open, or an intraday time?
- Are publication lag and internal ingestion latency modeled?
- Do corrections reopen previously published roll decisions?
- Are roll policy and exchange calendar read from their historical versions?
- How are data vintage and replay mode exposed in research output?
- Can every historical decision be traced to its exact input records?

## Key Takeaways

Corrected historical data is not necessarily historically observable data. A credible futures backtest must reproduce the information set available at each decision cutoff, including the market-data versions, roll policy, and calendar in force at that time.

Maintain as-observed and latest-corrected histories as separate, labelled products. Preserve revisions instead of overwriting them, use record-level ingestion timestamps, and reuse production decision logic for replay. These controls do more than satisfy audit requirements: they prevent a strategy from earning fictional PnL by knowing the future.
