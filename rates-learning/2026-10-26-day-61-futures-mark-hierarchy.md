# Designing a Futures Mark Hierarchy: Settlement, Last and Mid Are Not Interchangeable

## Abstract

A futures price can be numerically valid and still be the wrong mark for the business question. Official settlement, last trade and bid-ask midpoint have different meanings, timestamps and downstream uses. This article develops a purpose-driven mark hierarchy, quantifies the PnL differences between legitimate price types, and shows how a Python service can preserve source, publication status and policy lineage. The objective is not to invent one universal “best price,” but to make intraday risk, official PnL, execution analysis and clearing reconciliation internally consistent and auditable.

## Desk Context

Suppose a desk is long 120 short-rate futures contracts. The previous official settlement is 95.200. Near the current close, several plausible prices exist:

- last trade: 95.214 at 16:24:10;
- bid and ask: 95.210 and 95.212;
- preliminary exchange settlement: 95.208;
- final exchange settlement: 95.209, published at 17:05.

An intraday dashboard may reasonably value the position from a fresh midpoint. The official end-of-day ledger should use the final settlement because that is the basis for daily settlement economics. An execution report may instead compare a fill with an arrival-price benchmark.

The production error begins when all three systems call their input `close_price`. The values are valid, but their economic definitions have been erased.

## Price Type Is Part of the Value

An official settlement is determined by the exchange under a defined methodology. It commonly drives variation margin, official books and records, and clearing reconciliation. It need not equal the last observed trade or the closing midpoint.

The last trade is the most recent executed price. It answers where a transaction occurred, but it may be stale, unusually small, or outside the market that exists at the valuation cutoff.

The midpoint is an indicative valuation derived from synchronized bid and ask quotes:

$$
P_{mid}=\frac{P_{bid}+P_{ask}}{2}
$$

It can be useful for live risk, but it is neither an executable price nor automatically the official cash-settlement basis.

The governing principle is simple: a valid price can still be the wrong mark for the business question.

## Worked Numerical Example

Assume:

- position: long 120 contracts;
- previous official settlement: 95.200;
- current bid and ask: 95.210 and 95.212;
- current final settlement: 95.209;
- last trade: 95.214;
- contract multiplier: GBP 2,500 per price point.

The current midpoint is:

$$
P_{mid}=\frac{95.210+95.212}{2}=95.211
$$

An indicative intraday PnL marked to mid is:

$$
PnL_{mid}=120(95.211-95.200)(2{,}500)=GBP\ 3{,}300
$$

The official settlement-to-settlement PnL is:

$$
PnL_{settlement}=120(95.209-95.200)(2{,}500)=GBP\ 2{,}700
$$

The GBP 600 difference is mark basis:

$$
MarkBasis=PnL_{mid}-PnL_{settlement}=GBP\ 600
$$

It is not unexplained market PnL. The two marks answer different questions at different cutoffs.

Using the last trade would produce:

$$
PnL_{last}=120(95.214-95.200)(2{,}500)=GBP\ 4{,}200
$$

That is GBP 1,500 above official PnL. A recent timestamp does not make last trade an acceptable replacement for settlement.

## A Purpose-Driven Mark Hierarchy

A robust design avoids one system-wide “best price.” It selects a mark according to valuation purpose.

For `INTRADAY_RISK`, a synchronized, sufficiently fresh midpoint may be the first choice. The policy should impose quote-age and maximum-spread limits. If the quote fails, the service should either reject the request or use an explicitly labelled fallback.

For `OFFICIAL_EOD_PNL`, the final official settlement is authoritative. A preliminary settlement has a different publication status and should not silently become final. Last or mid must not enter the official ledger merely because the settlement feed is delayed.

For `EXECUTION_SLIPPAGE`, the relevant mark may be an arrival mid or another benchmark frozen when the order decision was made. Settlement is usually answering a different question.

For `CLEARING_RECON`, the mark must agree with the clearing or exchange settlement for the same contract, business date and position scope.

The selected result therefore needs more than a decimal. It should carry:

- price type;
- as-of timestamp and timezone;
- source;
- publication status, such as preliminary or final;
- selection-policy version;
- fallback reason, when applicable.

## Preliminary and Final Settlement Are States

An exchange may publish a preliminary settlement and later replace it with a final value. Treating the final value as a silent database overwrite destroys the explanation for a PnL change.

Suppose preliminary settlement is 95.208 at 16:45 and final settlement is 95.209 at 17:05. The corresponding PnLs are GBP 2,400 and GBP 2,700. The GBP 300 update should be labelled `SETTLEMENT_REVISION`, with both publication events retained.

This also exposes an important requirement question: if a finance cutoff occurs before the final publication, should the platform wait, publish a provisional number, or approve a fallback? That is a desk and control policy, not a decision a developer should infer from “latest price wins.”

## Engineering Design

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Mark:
    value: Decimal
    price_type: str
    as_of: datetime
    source: str
    publication_status: str


def select_mark(
    purpose: str,
    marks: list[Mark],
    cutoff: datetime,
) -> Mark:
    eligible = [m for m in marks if m.as_of <= cutoff]

    if purpose == "OFFICIAL_EOD_PNL":
        candidates = [
            m for m in eligible
            if m.price_type == "SETTLEMENT"
            and m.publication_status == "FINAL"
        ]
    elif purpose == "INTRADAY_RISK":
        candidates = [
            m for m in eligible
            if m.price_type == "MID"
            and (cutoff - m.as_of).total_seconds() <= 60
        ]
    else:
        raise ValueError(f"unsupported purpose: {purpose}")

    if not candidates:
        raise ValueError("no eligible mark under policy")

    return max(candidates, key=lambda m: m.as_of)
```

The deliberate feature is failure. If no final settlement exists, the official request does not quietly return a midpoint. A separate, approved fallback policy can exist, but it must change the result status and retain its reason.

## Data Quality and Production Considerations

Four controls matter most.

First, value, price type, timestamp and publication status must be published atomically. Updating the number before its metadata creates a transient but economically ambiguous state.

Second, midpoint validation must test bid-ask synchronization, freshness and spread. A mathematically correct midpoint from mismatched timestamps is not a reliable mark.

Third, preliminary-to-final changes must create an auditable PnL delta rather than overwrite history. Consumers need to distinguish market movement from settlement revision.

Fourth, dashboards must label `INDICATIVE` and `OFFICIAL` explicitly. Calling both outputs “close PnL” guarantees confusion during reconciliation.

A common production failure occurs when the settlement feed is delayed and a generic price service silently returns last trade. The desk receives a timely number, but variation-margin reconciliation remains broken and no result field reveals the fallback.

## Requirement-Discovery and Interview Questions

When a trader asks to “use the close,” a quant developer should ask:

- Does close mean final settlement, preliminary settlement, closing midpoint or last trade?
- Is the result for live risk, official PnL, valuation control or execution analysis?
- What happens before final settlement is published?
- Can a fallback enter the official ledger, and who approves it?
- What freshness and spread limits apply to midpoint marks?
- Should a settlement revision replace a snapshot or publish a delta?
- How is business date assigned for contracts in another timezone?
- Should the dashboard bridge indicative PnL to official PnL?

A strong interview answer emphasizes that mark selection is a versioned business policy. The engineer preserves both the market observation and the reason it was eligible for a particular calculation.

## Key Takeaways

- Settlement, last and mid are different data products, not interchangeable columns.
- Mark selection must be driven by valuation purpose.
- Mid-to-settlement PnL difference is mark basis, not automatically unexplained PnL.
- Preliminary and final settlements are publication states with explicit revision lineage.
- Official workflows should fail visibly when the authoritative mark is missing.
- A production result must carry value, type, source, timestamp, status and policy version.
