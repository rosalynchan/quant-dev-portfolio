# Late-Booked Rates Trades: PnL Restatement Across Business Dates

## Abstract

A trade does not begin taking risk when a booking platform first records it. When a Rates trade is executed before a reporting close but booked afterwards, PnL must be replayed from the economic execution time and allocated across the affected business dates. This article explains the difference between economic and recorded time, shows how prior-period restatement differs from a current-day adjustment, and proposes an idempotent engineering design for reproducible PnL.

## Desk Context

Consider a pay-fixed swap executed yesterday at 14:00 but entered into the booking system today at 09:30. Its signed DV01 is +GBP 2,000 per basis point. The market rate is 3.50% at execution, 3.54% at yesterday's close, and 3.51% at today's close. To isolate the timing problem, assume zero carry, gamma, fees, and cashflows.

If the PnL engine starts the trade at booking time, it discards exposure that existed before the system learned about the trade. If it reports the entire execution-to-today amount as today's market PnL, it moves yesterday's economics into the wrong period and may even reverse the apparent direction of today's performance.

## Two Clocks, One Trade

A late booking requires at least two timestamps:

- **Economic or valid time:** when the trade became real and started bearing risk.
- **Recorded or transaction time:** when the system received and stored the fact.

Between yesterday at 14:00 and today at 09:30, the platform was unaware of the swap, but the desk was economically exposed. The missing object was the record, not the risk.

The correct cumulative decomposition is:

$$
PnL_{total}=PnL_{execution\rightarrow prior\ close}+PnL_{prior\ close\rightarrow current\ close}
$$

It is not a booking-time-to-close calculation.

## Worked Numerical Example

From execution to yesterday's close, the rate rises from 3.50% to 3.54%, a 4bp move:

$$
PnL_{prior\ day}=(+2{,}000)\times(+4)=+GBP\ 8{,}000
$$

Under the signed convention used here, the pay-fixed swap has positive DV01, so a rate rise creates positive PnL.

From yesterday's close to today's close, the rate falls from 3.54% to 3.51%, a -3bp move:

$$
PnL_{current\ day}=(+2{,}000)\times(-3)=-GBP\ 6{,}000
$$

Cumulative PnL since execution is:

$$
CumulativePnL=8{,}000-6{,}000=+GBP\ 2{,}000
$$

Reporting +GBP 2,000 as today's market PnL is wrong in two ways. It omits yesterday's +GBP 8,000 and replaces today's genuine -GBP 6,000 loss with a positive number. Net cumulative PnL can reconcile while daily attribution is economically false.

## Restating an Open Period versus Adjusting a Closed Period

Economic attribution is unambiguous: yesterday earned +GBP 8,000 and today lost GBP 6,000. Publication policy determines how the late discovery is reported.

If yesterday can be reopened, the prior result is restated to include +GBP 8,000, while today's market PnL remains -GBP 6,000. The system should publish a new run that explicitly supersedes the previous prior-day result.

If yesterday is locked, today's operational ledger may contain a +GBP 8,000 prior-period adjustment and -GBP 6,000 current-day market PnL, producing a +GBP 2,000 reported change today. The dashboard must not call the net amount today's market PnL. It should expose both economic date and posting date.

A closed-period policy can change when an amount is posted. It cannot change the business date to which the economics belong.

## Bitemporal Data as a Practical Model

A single `created_at` field cannot represent this lifecycle. A practical event should retain economic execution time, recorded time, business date, source event ID, trade version, replay-from date, and the run ID it supersedes.

This is a useful application of bitemporal thinking: the system records both when a fact was valid in the business world and when it became known to the system.

When the late event arrives, the PnL service should replay from the earliest affected business date using reproducible historical market snapshots. The process must also be idempotent. Receiving the same source event twice must not create a second position or adjustment.

## Engineering Design

```python
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal


@dataclass(frozen=True)
class LateBookedTrade:
    event_id: str
    trade_id: str
    economic_execution_time: datetime
    recorded_at: datetime
    signed_dv01: Decimal
    execution_rate_bp: Decimal
    prior_close_rate_bp: Decimal
    current_close_rate_bp: Decimal
    prior_business_date: date
    current_business_date: date


def attribute_late_trade(
    x: LateBookedTrade,
    prior_period_open: bool,
) -> dict:
    prior_pnl = x.signed_dv01 * (
        x.prior_close_rate_bp - x.execution_rate_bp
    )
    current_pnl = x.signed_dv01 * (
        x.current_close_rate_bp - x.prior_close_rate_bp
    )

    return {
        "event_id": x.event_id,
        "trade_id": x.trade_id,
        "economic_execution_time": x.economic_execution_time,
        "recorded_at": x.recorded_at,
        "replay_from": x.prior_business_date,
        "prior_period_pnl": prior_pnl,
        "current_market_pnl": current_pnl,
        "posting_policy": (
            "RESTATE_PRIOR"
            if prior_period_open
            else "POST_PRIOR_ADJUSTMENT_TODAY"
        ),
        "today_reported_change": (
            current_pnl
            if prior_period_open
            else prior_pnl + current_pnl
        ),
    }
```

The calculation separates economic allocation from posting policy. A production implementation would also replay full valuation, carry, cashflows, and related hedge activity where material.

## Data Quality and Production Controls

Five controls provide most of the protection.

First, economic execution time must come from an authoritative execution source and include timezone. Second, replay must cover every affected business date and use historically reproducible market snapshots. Third, the source event ID must be an idempotency key. Fourth, a restated run must preserve `supersedes_run_id` rather than silently overwriting the previous published result. Fifth, prior-period adjustment and current-day market PnL must remain separate dashboard components.

Useful observability includes late trades by age, replay duration, events missing historical market snapshots, duplicate event attempts, and restatement amounts by business date.

## Requirement Discovery and Interview Questions

When a trader says, “This was booked late,” ask:

- What is the original execution timestamp and authoritative source?
- Did the delay cross minutes, a desk close, or an accounting period?
- May the prior PnL period be reopened?
- Can trade-time and prior-close market snapshots be reproduced?
- Must carry, fees, cashflows, and hedge activity also be replayed?
- Which books, limits, reports, and downstream consumers are affected?
- Who approves a material prior-period change?
- Should the dashboard display economic date, posting date, or both?

An interview-quality answer should say that calculation and publication are separate decisions: first allocate economics correctly, then apply the approved period policy.

## Trader–Developer Translation

**Trader:** “The swap was executed yesterday, but the dashboard shows a 2k gain today.”

**Developer:** “The 2k is cumulative since execution. Economically, yesterday made 8k and today lost 6k. Can yesterday's PnL be reopened?”

**Trader:** “The official period is locked, so post the 8k as a prior-period adjustment today.”

**Developer:** “I will keep today's market PnL at -6k, show the +8k adjustment separately, and retain both economic and posting dates with a replay run ID.”

## Key Takeaways

- Risk begins at economic execution, not ingestion.
- Late booking requires PnL replay across every affected business date.
- Cumulative reconciliation does not prove daily attribution is correct.
- A locked prior period requires a labelled adjustment, not relabelled market PnL.
- Bitemporal fields preserve what was valid and when the system knew it.
- Idempotent events and versioned runs make restatement safe and auditable.
