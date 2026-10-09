# Swap Amendments, Booking Corrections and PnL Attribution

## Abstract

A cancel-and-rebook sequence does not prove that a trade was economically closed and replaced. It may merely correct a booking error in terms that were always valid. This distinction is critical for Rates PnL: a genuine amendment changes risk at the event time, while a booking correction requires a restated opening baseline. This article shows how to classify the event, calculate a transparent PnL bridge, and preserve economic trade identity across technical versions.

## Desk Context

Consider a receive-fixed swap recorded with a 3.00% fixed rate. Its confirmed rate has always been 3.02%, but Operations discovers the error and corrects it at 10:30. The booking platform implements the change by cancelling the old record and creating a corrected one.

If a downstream engine interprets database actions literally, it may report a closed trade at 10:30 and a new trade from 10:30 to the close. That result is operationally plausible but economically false. No counterparty renegotiation occurred, no risk was intentionally closed, and no new risk was executed.

The first requirement is therefore not a formula. It is a classification question: did the contract economics change today, or did the system learn today that its earlier representation was wrong?

## Economic Amendment versus Booking Correction

A genuine economic amendment changes a contractual field such as coupon, notional, dates, index, or cashflow schedule by agreement between the parties. The old economics apply until the event; the amended economics apply afterwards. Its PnL timeline normally contains old-version market PnL to the event, new-version market PnL from the event, and any negotiated upfront or value transfer.

A booking correction has different semantics. The corrected terms were economically valid before the record was fixed. The corrected version should not begin earning PnL only at ingestion time. Instead, the opening position and risk should be restated using the correct terms, while the difference from the previously booked opening value is disclosed as correction PnL.

Booking time answers when the system learned something. Economic effective time answers when the risk actually existed. Conflating them creates ghost trades and unexplained PnL.

## Worked Numerical Example

Suppose the incorrect opening record contains:

- Booked opening PV: +GBP 80,000
- Booked DV01: -GBP 4,000/bp
- Incorrect fixed rate: 3.00%

The confirmed 3.02% economics imply:

- Restated opening PV: +GBP 70,000
- Corrected opening DV01: -GBP 3,950/bp

The opening restatement is:

$$
CorrectionPnL=PV_{restated,open}-PV_{booked,open}
$$

$$
CorrectionPnL=70{,}000-80{,}000=-GBP\ 10{,}000
$$

This is not a 10:30 market loss and not amendment execution. It is the effect of replacing an incorrect opening state with the contractual state.

Assume rates rise 2bp before the correction arrives and another 1bp afterwards. The correct trade existed throughout, so its market window is the full 3bp move:

$$
MarketPnL=(-3{,}950)\times3=-GBP\ 11{,}850
$$

With GBP 300 of carry:

$$
EconomicPnL=-11{,}850+300=-GBP\ 11{,}550
$$

Suppose the corrected closing PV is GBP 58,450. Comparing it with the incorrectly booked opening PV produces a raw change of:

$$
RawChange=58{,}450-80{,}000=-GBP\ 21{,}550
$$

The transparent bridge is:

$$
RawChange=CorrectionPnL+EconomicPnL
$$

$$
-21{,}550=-10{,}000-11{,}550
$$

Calling the entire amount market PnL exaggerates the day's rates loss. Calling GBP 10,000 amendment execution invents a negotiation that never happened.

## Why Cancel/Rebook Is Not an Economic Model

Booking platforms often implement corrections through cancellation and rebooking. Those are record-management operations, not reliable economic classifications.

If downstream services use status alone, they may create a false close-out component, a false new-trade component, and a missing morning exposure for the corrected trade. They may also inflate trade count, turnover, notional activity, and execution-cost metrics.

A robust model keeps a stable economic trade ID above version-specific record IDs. The lifecycle event should contain a controlled reason code such as `ECONOMIC_AMENDMENT`, `BOOKING_CORRECTION`, `CANCEL_REBOOK_TECHNICAL`, or `TRUE_CANCEL`. It should also preserve old and new version IDs, original execution references, economic effective time, booking time, and approval lineage.

## Engineering Design

```python
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class AmendmentType(Enum):
    ECONOMIC = "ECONOMIC_AMENDMENT"
    CORRECTION = "BOOKING_CORRECTION"


@dataclass(frozen=True)
class AmendmentPnLInput:
    amendment_type: AmendmentType
    booked_opening_pv: Decimal
    restated_opening_pv: Decimal
    corrected_opening_dv01: Decimal
    open_rate_bp: Decimal
    close_rate_bp: Decimal
    carry_pnl: Decimal
    reported_closing_pv: Decimal
    economic_trade_id: str
    old_version_id: str
    new_version_id: str


def explain_booking_correction(x: AmendmentPnLInput) -> dict:
    if x.amendment_type is not AmendmentType.CORRECTION:
        raise ValueError("use event-time amendment workflow")

    correction_pnl = x.restated_opening_pv - x.booked_opening_pv
    market_pnl = x.corrected_opening_dv01 * (
        x.close_rate_bp - x.open_rate_bp
    )
    economic_pnl = market_pnl + x.carry_pnl
    raw_change = x.reported_closing_pv - x.booked_opening_pv
    residual = raw_change - correction_pnl - economic_pnl

    return {
        "correction_pnl": correction_pnl,
        "market_pnl": market_pnl,
        "carry_pnl": x.carry_pnl,
        "economic_pnl": economic_pnl,
        "raw_valuation_change": raw_change,
        "residual": residual,
        "economic_trade_id": x.economic_trade_id,
        "superseded_version": x.old_version_id,
        "corrected_version": x.new_version_id,
    }
```

The function refuses to process a true economic amendment through the correction path. That boundary prevents a classification mistake from being hidden inside otherwise valid arithmetic.

## Data Quality and Production Controls

Four controls are especially valuable.

First, event type must come from a governed reason code or approved workflow, not an inference from cancel/rebook records.

Second, a correction requires restated opening PV and opening risk. Using closing risk to fill a missing opening snapshot introduces hindsight into the explain.

Third, every technical record must map to a stable economic trade identity with non-overlapping version validity. Without that relationship, aggregation can duplicate or omit risk.

Fourth, correction, market, carry, and residual must reconcile to raw valuation change. Material backdated changes should retain approval, reason, and whether historical accounting periods were reopened.

Useful monitoring includes correction PnL by reason code, records without an economic trade ID, overlapping versions, and corrections that arrived after the PnL close.

## Requirement Discovery and Interview Questions

When someone says, “This trade was amended,” ask:

- Did both parties renegotiate economics, or was a record corrected?
- Which fields changed: rate, notional, dates, index, counterparty, or book?
- What are the economic effective time and booking time?
- Was there an upfront, fee, or compensation payment?
- Must the opening position and risk be restated?
- Should historical PnL be reopened or adjusted today?
- Do cancelled and rebooked records share an economic trade ID?
- Where should correction PnL appear on the dashboard?

A strong interview answer states that lifecycle classification precedes attribution. The same database actions can represent very different economics.

## Trader–Developer Translation

**Trader:** “Why does the dashboard say I lost 10k on an amendment? We did not renegotiate anything.”

**Developer:** “The platform cancelled the 3.00% record and rebooked 3.02% at 10:30. Was 3.02% the original confirmed rate?”

**Trader:** “Yes. The original record was wrong.”

**Developer:** “Then I will classify the 10k as an opening restatement, rebuild today's PnL using the corrected opening trade, and preserve both records under one economic trade ID.”

## Key Takeaways

- Classify an amendment by economic intent, not by the booking-system action.
- A genuine economic amendment changes risk at the event time.
- A booking correction restates the opening baseline when corrected terms were always valid.
- Correction PnL must remain separate from market, carry, and execution.
- Stable economic identity and version lineage prevent ghost trades and double counting.
- A fully reconciled number can still be economically wrong if the lifecycle event was misclassified.
