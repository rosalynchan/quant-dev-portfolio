# Diagnosing Futures Position Breaks Between Front Office and Clearing

## Abstract

An internally consistent execution ledger is not sufficient evidence that a futures position is correct. Front-office positions must be reconciled against an authoritative clearing or broker view at a precise contract and account grain. This article shows why portfolio-level netting can hide roll mismatches, calculates the risk impact of a contract-level break, defines practical break categories, and designs an exception workflow that distinguishes timing noise from missing or misclassified economic events.

## Desk Context

At end of day, a front-office ledger reports:

- FRONT: 0 contracts;
- NEXT: +60 contracts.

The clearing statement reports:

- FRONT: -40 contracts;
- NEXT: +100 contracts.

Both sources have a net total of +60 contracts. A reconciliation that compares only the portfolio total therefore passes. Yet the portfolios are not economically equivalent: the two expiries have different prices, DV01s, settlement cash flows, and expiry risks. The break suggests that part of a roll was recorded differently across the two sources.

The central principle is:

> A portfolio can be net-flat at the wrong contracts.

## Define the Reconciliation Grain

For a common key, the signed position break is:

$$
BreakQuantity
=FrontOfficeQuantity-ClearingQuantity
$$

The formula is useful only when both quantities are aggregated on the same dimensions. A futures position key normally includes at least:

- legal account or clearing account;
- front-office book or strategy allocation;
- exchange;
- explicit contract identifier and expiry;
- business date;
- position basis, such as trade-date or settlement-date;
- a documented signed-quantity convention.

A changing generic alias such as `FRONT` is not a valid reconciliation key. Nor is a portfolio total that permits opposite breaks in different expiries to cancel.

## Worked Numerical Example

The contract-level comparison is:

| Contract | Front office | Clearing | FO minus clearing |
|---|---:|---:|---:|
| FRONT | 0 | -40 | +40 |
| NEXT | +60 | +100 | -40 |

At portfolio level:

$$
FO_{total}=0+60=60
$$

$$
Clearing_{total}=-40+100=60
$$

The total difference is zero, but both contract-level breaks are non-zero.

Assume FRONT carries GBP 22/bp of DV01 per contract and NEXT carries GBP 25/bp. The clearing risk is:

$$
DV01_{clear}=(-40)(22)+(100)(25)=GBP\ 1{,}620/bp
$$

The front-office risk is:

$$
DV01_{FO}=60(25)=GBP\ 1{,}500/bp
$$

The risk break is therefore:

$$
DV01Break=1{,}500-1{,}620=-GBP\ 120/bp
$$

For an adverse five-basis-point move, the approximate unexplained impact is:

$$
PnLImpact\approx(-120)\times5=-GBP\ 600
$$

Quantity identifies the mismatch. Risk impact helps the desk decide which exceptions require immediate attention.

## Classify Before Repairing

Not every difference means a trade was lost. Useful categories include:

- **Timing break:** one snapshot contains a valid event that is outside the other source's cutoff.
- **Missing-event break:** a fill, bust, or correction is absent from one side at comparable cutoffs.
- **Mapping break:** contract, account, book, or exchange codes resolve differently.
- **Scope break:** one source includes an allocation, give-up, EFP, or account excluded by the other.
- **Sign or unit break:** long/short convention, lot units, or multipliers differ.

The platform can suggest a classification from evidence. It can check whether the same execution ID exists on both sides, whether quantity is exactly sign-reversed, whether a contract mapping is missing, and whether the difference disappears in the next clearing feed. An operator should confirm the reason rather than writing an unstructured free-text explanation with no supporting records.

## Align the Cutoffs

Two correct snapshots can disagree because they describe different information sets. Suppose the front-office cutoff is 17:00, the clearing file covers events only through 16:45, and a fill occurs at 16:50. The expected result is a temporary difference.

Every reconciliation run should therefore retain:

- both snapshot identifiers;
- effective cutoffs and time zones;
- business date;
- source file or message versions;
- reference-data and mapping version.

The 16:50 fill should be labelled `EXPECTED_TIMING`, with an ageing rule that promotes it to an actionable break if it remains unmatched after the agreed feed window. Without cutoff lineage, support teams repeatedly investigate normal latency as though it were a missing trade.

## Engineering Design

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionKey:
    account_id: str
    book_id: str
    exchange: str
    contract_id: str
    business_date: str


def reconcile_positions(
    front_office: dict[PositionKey, int],
    clearing: dict[PositionKey, int],
) -> list[dict]:
    breaks = []
    for key in sorted(
        set(front_office) | set(clearing),
        key=lambda x: (
            x.account_id,
            x.book_id,
            x.exchange,
            x.contract_id,
        ),
    ):
        fo_qty = front_office.get(key, 0)
        clear_qty = clearing.get(key, 0)
        delta = fo_qty - clear_qty
        if delta:
            breaks.append({
                "key": key,
                "front_office_qty": fo_qty,
                "clearing_qty": clear_qty,
                "break_qty": delta,
                "status": "OPEN",
            })
    return breaks
```

The calculation is intentionally simple. Production quality comes from normalization, lineage, classification, and workflow around it.

## Controls and Exception Workflow

The highest-value controls are:

- **Stable keys:** reconcile explicit contracts and canonical account identifiers.
- **Unit normalization:** align sign conventions, lot units, currencies, and position basis before comparison.
- **Cutoff coverage:** expose timing mismatches instead of presenting them as unexplained economic breaks.
- **Owned exceptions:** every open break has an owner, age, reason, evidence, and remediation action.
- **Verified closure:** a break is resolved only after an independent rerun proves that the source positions agree.

The exception state might progress from `OPEN` to `CLASSIFIED`, `FIX_PENDING`, and `VERIFIED_RESOLVED`. A manual status change must not alter the economic position or substitute for repairing the source event or mapping.

A dangerous failure occurs when the key omits contract ID. The +40 FRONT break and -40 NEXT break net to zero, so monitoring appears green while curve exposure remains wrong.

## Requirement Discovery and Interview Questions

Before building a position reconciliation, clarify:

- Is clearing on a trade-date or settlement-date basis?
- Which source owns canonical account, book, exchange, and contract mappings?
- What cutoffs apply to intraday and end-of-day runs?
- How are give-ups, allocations, EFPs, and block trades scoped?
- Is materiality based on quantity, DV01, potential PnL, margin impact, or a combination?
- When does an expected timing difference become actionable?
- Which team owns each break category?
- Should remediation append an execution correction or fix reference-data mapping?
- Must the dashboard retain reopen history and resolution evidence?

A strong interview summary is:

> I reconcile at a canonical account-and-explicit-contract grain, normalize units and position basis, and retain both source cutoffs. I classify timing, missing-event, mapping, scope, and sign breaks before repair. Exceptions are ranked by risk impact, linked to evidence and ownership, and closed only when an independent rerun confirms that the authoritative positions agree.

## Key Takeaways

- Portfolio totals can hide equal and opposite breaks across expiries.
- Explicit contract and canonical account keys are essential.
- Snapshot cutoff alignment separates normal latency from true missing events.
- Quantity breaks should be enriched with DV01, potential PnL, age, and expiry proximity.
- Workflow status does not repair economics; verified reruns prove resolution.
