# Cost-Aware Hedge Ranking: Feasibility Before Price

## Abstract

Once several discrete hedge proposals satisfy risk tolerances, a desk may prefer the one with the lowest estimated execution cost. That ranking must not allow a cheap but unacceptable proposal to win. This article introduces a deliberately simple per-unit cost model, evaluates three candidate hedges, and separates risk acceptance, cost-data validity, and execution approval. The result is a transparent ranking contract rather than a general trading optimizer.

## Desk context

Yesterday's lesson showed why nearest rounding can fail post-rounding risk acceptance. Today assume the candidate search has produced several permitted quantity pairs. The trader asks, “Which acceptable hedge is cheapest?”

The word acceptable comes first. Quantity grids, caps, and risk bands define which proposals may enter the ranking. Estimated cost selects among those proposals; it does not buy permission to violate a hard constraint.

This lesson uses synthetic GBP amounts and signed linear sensitivities. It does not recommend an actual trade, assume a live quote, or authorize execution.

## Define a narrow cost model

Suppose A costs an estimated GBP 3 per absolute quantity unit and B costs GBP 8. Define each coefficient as an already-monetized one-way execution cost relative to an agreed mid-value benchmark, including only the spread component used in this exercise.

The estimate is:

$$
C(q)=c_A|q_A|+c_B|q_B|
$$

Absolute quantities matter because executing in either direction incurs a cost under this symmetric model. A short quantity is not a negative transaction cost.

This simple formula assumes constant per-unit cost over the candidate size, no package netting, and identical buy/sell coefficients. Real execution may depend on direction, size, venue, fees, or market impact. Those extensions require a richer model; do not pretend this small formula already covers them.

If the source provides a bid/ask spread in rate basis points, it is not yet a GBP-per-unit coefficient. It must be converted using an appropriate instrument-specific valuation relationship. Also clarify whether the input is a full spread or a one-way half-spread. Today's coefficients are explicitly supplied as monetary one-way costs to avoid mixing that separate calculation into the lesson.

## Keep feasibility outside the score

Let the requested risk change be $b$ and the instrument risk matrix be $H$. Risk error remains:

$$
e=Hq-b
$$

A candidate passes only if each absolute error is within its factor's agreed band, and its quantities meet lot and cap rules. Among passing candidates with valid cost estimates, select the smallest $C(q)$ using a declared tie-break rule.

Do not compute “risk error plus cost” without a specified economic objective. Risk sensitivity and monetary execution cost have different units. Even normalized error weights would introduce a new policy choice, not a neutral implementation detail.

## Worked example

Use the same synthetic per-unit risks as the rounding lesson:

| Instrument | Level sensitivity | Slope sensitivity | Estimated cost, GBP/unit |
| --- | ---: | ---: | ---: |
| A | 100 | -20 | 3 |
| B | 80 | 40 | 8 |

The requested change is level plus 16 and slope plus 176. Both quantities must be integers, with absolute caps four for A and five for B. For this new request, the risk bands are fixed at level 25 and slope 120. The level band is intentionally different from yesterday's 20 and is versioned as a new policy input, not silently retrofitted to an old result.

Evaluate three explicitly supplied candidates:

| Candidate | A | B | Level error | Slope error | Cost, GBP | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| P | -2 | 3 | +24 | -16 | 30 | Yes |
| Q | -3 | 4 | +4 | +44 | 41 | Yes |
| R | -1 | 1 | -36 | -116 | 11 | No |

P achieves level 40 and slope 160. Its cost is six plus twenty-four, or GBP 30. Q achieves level 20 and slope 220, at cost nine plus thirty-two, or GBP 41.

Q is closer to the level target, but both candidates satisfy the agreed bands. Under a cost-first ranking of acceptable proposals, P wins. This does not mean that P has less risk under every scenario; it means that the trader's stated acceptance policy permits its residual.

R costs only GBP 11, but its level error breaches the band. It is excluded before ranking, not allowed to win because its cost saving looks attractive.

The result is cheapest among these three supplied candidates, not globally cheapest over every allowable quantity pair. Search scope remains part of the claim.

## Compact engineering connection

The following evaluator uses integer quantities and integer GBP cost coefficients. It recomputes risk rather than trusting a pre-existing accepted flag.

```python
def rank_candidates(candidates):
    eligible = []
    for name, a, b in candidates:
        quantity_ok = (
            isinstance(a, int) and isinstance(b, int)
            and abs(a) <= 4 and abs(b) <= 5
        )
        error = (100*a + 80*b - 16, -20*a + 40*b - 176)
        risk_ok = abs(error[0]) <= 25 and abs(error[1]) <= 120
        if quantity_ok and risk_ok:
            eligible.append({
                "id": name,
                "quantities": (a, b),
                "risk_error": error,
                "estimated_cost_gbp": 3*abs(a) + 8*abs(b),
            })
    return sorted(
        eligible, key=lambda x: (x["estimated_cost_gbp"], x["id"])
    )

ranked = rank_candidates([("P", -2, 3), ("Q", -3, 4), ("R", -1, 1)])
```

The snippet assumes cost data has already passed provenance, currency, size-coverage, and freshness checks. Production code should return rejection reasons as well as ranked entries. The stable identifier tie-break makes equal-cost output reproducible; it is not an economic preference unless explicitly adopted as such.

## Four selective production checks

1. Apply risk and quantity acceptance before cost ranking. Never make a failed hard constraint compensable through a cheap score.
2. Validate cost meaning and units: one-way monetary cost, trade direction, and quantity unit must agree.
3. Treat missing or stale estimates as unrankable under the current policy, not zero cost. Show risk-accepted but cost-unavailable separately.
4. Recompute ranking when relevant quotes, risk snapshots, or policy versions change. A displayed winner is not a timeless approval.

A dashboard should show signed risk errors and estimated cost side by side. Display quote timestamps and estimate assumptions, rather than presenting a bare “best hedge” badge.

## Requirement dialogue and takeaways

Ask whether “cheapest” means spread cost only or includes fees and impact, whether buy/sell asymmetry matters, and whether the available quote covers the proposed size. Confirm the risk bands, search scope, tie-break rule, and requirement for human review.

Estimated execution cost is not a realized PnL guarantee. Keep it separate from hypothetical residual-risk scenario PnL, and do not deduct it twice if an execution-based valuation already incorporates the same spread effect.

The desk-ready answer is: “P is lowest estimated cost among the supplied risk-acceptable candidates. Q has a smaller level error but costs more. R fails risk acceptance and is not eligible.”

All examples are synthetic and public-safe, with no confidential employer or client information, proprietary architecture, or investment advice.
