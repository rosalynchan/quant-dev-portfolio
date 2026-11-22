# Hedge Quantity Limits: Proving a Risk Target Is Unreachable

## Abstract

A quantity cap is not a cosmetic adjustment to an unconstrained hedge. It changes the set of risk changes the available instruments can deliver. This article derives a simple capacity bound while preserving level exposure, shows why a solver can succeed while the economic target remains unmet, and turns that distinction into an explicit proposal status. The example avoids a general optimization framework so the feasibility argument remains hand-checkable.

## Desk context

A Rates hedge calculator needs to add positive GBP 500 of slope sensitivity without changing level sensitivity. Its two available instruments have nearly identical risk vectors. The exact hedge requires minus one hundred units of A and plus one hundred units of B, but policy permits at most sixty units in absolute value for either instrument.

A developer might clip the quantities to the limits and retain the original “hedged” label. That would conceal a changed outcome. The right first question is whether any permitted quantities can meet the target at all.

Yesterday's lesson covered instability under small sensitivity revisions. Today the inputs are fixed. We study feasibility under hard limits, not numerical conditioning, market uncertainty, or execution.

## Define the request and the allowed set

Each instrument unit has a documented positive trade direction and notional size. All risk values are signed, in GBP per normalized level or spread basis point. FX and the risk snapshot are frozen.

The unit risk vectors are:

| Instrument | Level risk | Slope risk |
| --- | ---: | ---: |
| A | 1,000 | 400 |
| B | 1,000 | 405 |

The required risk change is zero level and positive GBP 500 slope. It is a change supplied by the hedge, not the final book exposure.

Preserving level imposes:

$$
q_A+q_B=0
$$

The hard quantity limits are:

$$
|q_A|\leq60,\qquad |q_B|\leq60
$$

These are continuous signed quantities for the exercise. Lot sizes, asymmetric buy/sell limits, costs, and partial fills would introduce additional constraints and are intentionally outside today's model.

## Derive capacity before running a solver

The level constraint makes $q_A=-q_B$. Substitute it into the slope contribution. The large common sensitivity cancels, leaving only the five-unit difference between the instruments:

$$
\Delta S=400q_A+405q_B=5q_B
$$

Because B cannot exceed sixty positive units, the largest positive slope change compatible with exact level preservation is GBP 300 per spread basis point. The requested GBP 500 is outside the achievable interval.

This proves infeasibility for the specified constraints. It is stronger than observing that one numerical algorithm failed. Another solver cannot overcome the same mathematical limit.

The general lesson is that capacity must be assessed jointly with the risk-preservation constraint. Ignoring level would allow other combinations to produce more slope change, but those combinations would solve a different request.

## Worked example: the best directional endpoint still misses

Set A to minus sixty and B to plus sixty. Their level contributions are minus GBP 60,000 and plus GBP 60,000, so level change remains zero.

Their slope contributions are minus GBP 24,000 and plus GBP 24,300, giving positive GBP 300. The error relative to the requested positive GBP 500 is minus GBP 200.

If the initial book had slope sensitivity minus GBP 500 and target zero, the final book would retain minus GBP 200 of slope sensitivity. Under a pure positive one-basis-point spread shock, that remaining exposure gives approximately minus GBP 200 of first-order PnL. It is not an execution cost or a realized loss.

A partial proposal may still be useful, but it must be described as adding GBP 300 and leaving GBP 200 unmet. In this special one-dimensional feasible set, the positive endpoint is closest to the positive target while preserving level. We are not claiming it minimizes trading cost, gross exposure, or a broader weighted risk objective.

## Why clipping is not a general constrained solver

Here, clipping the unconstrained pair from minus one hundred/plus one hundred to minus sixty/plus sixty happens to preserve level because the limits and level coefficients are symmetric.

Change A's cap to fifty while B's remains sixty. Independent clipping gives minus fifty/plus sixty and creates positive GBP 10,000 of level sensitivity. To preserve level, both magnitudes must instead be limited to fifty; positive slope capacity falls to GBP 250.

This short variation explains the failure mode without adding another optimization method. Component-wise clipping enforces individual bounds, not coupled risk constraints. Always recompute achieved risk from the actual proposed quantities.

## Engineering a transparent response

For this particular equal-level, two-instrument model, a compact diagnostic can calculate the capacity directly. It should report requested and achieved changes separately and never use numerical completion as an economic success flag.

```python
def capped_slope_proposal(requested_slope, cap_a, cap_b):
    if cap_a < 0 or cap_b < 0:
        raise ValueError("Caps must be non-negative")
    # Fixed model: A=(1000, 400), B=(1000, 405).
    max_abs_pair = min(cap_a, cap_b)
    wanted_b = requested_slope / 5.0
    q_b = max(-max_abs_pair, min(wanted_b, max_abs_pair))
    q_a = -q_b
    achieved = 400.0 * q_a + 405.0 * q_b
    error = achieved - requested_slope
    return {
        "quantities": {"A": q_a, "B": q_b},
        "level_change": 1000.0 * (q_a + q_b),
        "requested_slope_change": requested_slope,
        "achieved_slope_change": achieved,
        "target_error": error,
        "target_feasible": abs(wanted_b) <= max_abs_pair,
    }

proposal = capped_slope_proposal(500.0, 60.0, 60.0)
```

The function is not a general hedge optimizer. Production validation must also reject non-finite inputs and use documented tolerances for floating-point comparisons. Keep factor normalization and instrument-unit metadata outside this compact snippet but inside the proposal contract.

## Four selective controls

1. Separate hard constraints from optional objectives. “Preserve level exactly” must not become a soft preference without authorization.
2. Recompute risk after applying all limits; a quantity-valid proposal may still violate a coupled constraint.
3. Distinguish computational completion, target feasibility, and permission to execute. They are three different states.
4. Version limits with the risk snapshot and request. Otherwise the same proposal can appear feasible under an unrelated policy configuration.

Tests should include the symmetric sixty-unit example, asymmetric fifty/sixty caps, a reachable request of GBP 250, and a negative request with reversed directions.

## Requirement dialogue and takeaways

When the trader says, “Do what you can,” clarify whether a partial proposal is allowed and which constraint must remain hard. Report the remaining signed risk and the binding quantity limits. Do not silently enlarge caps, add instruments, or change the target.

A useful response is: “With exact level preservation and these limits, positive slope capacity is GBP 300. The GBP 500 target is infeasible. A partial proposal would leave GBP 200 unmet and requires review.”

Feasibility is a property of the request and allowed set, not a solver success message. All examples are synthetic educational illustrations, with no confidential information, proprietary architecture, or investment advice.
