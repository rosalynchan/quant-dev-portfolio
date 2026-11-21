# When an Exact Hedge Is an Unstable Hedge

## Abstract

A hedge solver can return quantities that perfectly match the requested risk change while remaining highly sensitive to small changes in its inputs. The problem is often not the solver but the available instruments: nearly parallel risk vectors provide little independent control. This article builds a hand-checkable example, separates reconciliation from robustness, and shows how a proposal service can test sensitivity without silently changing the trader's objective.

## Desk context

Yesterday's exercise used two instruments to remove slope risk while preserving level exposure. Today the target is unchanged, but the instruments have almost identical risk shapes. The calculator suggests selling fifty units of one and buying fifty units of the other. A small revision to one instrument's sensitivity then doubles both quantities.

A trader reasonably asks whether the system is broken. The first question is whether the pair genuinely offers two useful risk directions. Different instrument identifiers do not guarantee independent hedging capability.

This lesson concerns conditioning of a fixed linear hedge model. It does not claim that a perturbation experiment predicts future market moves, execution quality, or investment outcomes.

## Exactness and stability answer different questions

Write the hedge requirement as:

$$
Hq=b
$$

Here $H$ contains per-unit instrument sensitivities, with risk factors in rows and instruments in columns. The vector $b$ is the required change from current risk to target risk. The quantity vector $q$ is signed relative to documented positive instrument directions.

A small residual means the proposed quantities solve the supplied system accurately:

$$
r=Hq-b
$$

That does not tell us whether similar inputs produce similar quantities. An ill-conditioned system can have a tiny residual and an unstable solution. This is a property of the problem presented to the solver, not necessarily a numerical implementation defect.

The intuitive geometry is simple. If two instruments move level and slope in almost the same proportion, buying one and selling the other cancels most of their risk. Only a small difference remains to achieve the desired independent change. Producing a material effect through that small difference requires large opposing positions.

## Worked example: use the difference between the columns

Assume signed sensitivities in GBP per normalized factor basis point. One unit has a fixed, documented notional and trade direction.

| Instrument, per positive unit | Level | Slope |
| --- | ---: | ---: |
| A | 1,000 | 400 |
| B | 1,000 | 410 |

The book requires zero additional level risk and positive GBP 500 of slope risk. Preserving level gives $q_A=-q_B$. Substituting into the slope equation leaves ten times $q_B=500$.

The exact solution is therefore minus fifty units of A and plus fifty units of B. Level contributions of minus GBP 50,000 and plus GBP 50,000 cancel. Slope contributions of minus GBP 20,000 and plus GBP 20,500 leave the required positive GBP 500.

Now revise B's slope sensitivity from 410 to 405, leaving everything else unchanged. The difference between the columns is only five. The revised exact solution is minus one hundred units of A and plus one hundred units of B.

A change of about 1.22% in that single sensitivity doubles the quantities. Both solutions reconcile to their own input matrices. The reconciliation check cannot distinguish them as robust or fragile.

The relative change in one entry is not the matrix condition number. It is a concrete perturbation example demonstrating sensitivity in a relevant direction.

## Revalue the old proposal under the revised inputs

A second check makes the economic implication easier to see. Keep the original proposal of minus fifty A and plus fifty B, but assess it using B's revised slope sensitivity of 405.

Level contribution remains zero. Slope contribution becomes minus GBP 20,000 plus GBP 20,250, or positive GBP 250. The proposal now supplies only half the requested slope change.

For a one-basis-point pure slope scenario, the shortfall relative to target corresponds to minus GBP 250 of first-order scenario PnL. This is not a realized trading loss. It measures how far the assessed risk misses the requested target under revised assumptions.

Keep these experiments separate: re-solving asks how quantities move; reassessing the old quantities asks how achieved risk moves. A useful diagnostic report shows both.

## A compact robustness diagnostic

The following code deliberately tests an explicit revised input rather than introducing an unexplained random noise distribution.

```python
import numpy as np

def hedge_stability(base_h, revised_h, required_change):
    q0 = np.linalg.solve(base_h, required_change)
    q1 = np.linalg.solve(revised_h, required_change)
    old_proposal_error = revised_h @ q0 - required_change
    return {
        "base_quantities": q0,
        "revised_quantities": q1,
        "quantity_change": q1 - q0,
        "base_residual": base_h @ q0 - required_change,
        "revised_residual": revised_h @ q1 - required_change,
        "old_proposal_error": old_proposal_error,
    }

base_h = np.array([[1000.0, 1000.0], [400.0, 410.0]])
revised_h = np.array([[1000.0, 1000.0], [400.0, 405.0]])
result = hedge_stability(base_h, revised_h, np.array([0.0, 500.0]))
```

Inputs must already share factor order, currency, slope normalization, and instrument-unit definitions. Production code also needs finite-value checks and explicit handling of singular solves. This function diagnoses a proposal; it does not approve or execute one.

Perturbations should reflect justified uncertainty, such as observed risk recalculation differences or a documented scenario set. Do not choose a convenient perturbation merely to make a proposal pass.

## Four selective controls

1. Report large opposing quantities alongside residuals. A zero residual must not be the only green-light criterion.
2. Version the perturbation specification and show both quantity sensitivity and achieved-risk error.
3. Normalize units before comparing condition metrics. Rescaling risk rows or instrument columns can change a numerical condition number without changing the underlying economic request.
4. Block or escalate proposals that breach agreed quantity or stability limits. Never silently relax the target to make the output look reasonable.

A condition number can support diagnosis, but there is no universal threshold independent of scaling and desk policy. A nonzero determinant establishes invertibility, not practical usefulness.

## Requirement discovery

When a trader says, “Just cap each quantity at sixty,” explain that a cap changes feasibility. The revised exact solution needs one hundred units on each side. A capped proposal cannot meet both equalities in this example.

Ask whether to choose a different instrument pair, accept an explicit residual-risk tolerance, or return no feasible proposal under the current constraints. Those are economic decisions. A developer should expose the trade-off rather than smuggle it into a numerical fallback.

## Interview practice and takeaways

Why can an exact hedge be unstable? Because nearly parallel instrument risk vectors require large cancellation, amplifying input changes.

Why not fix this with a pseudoinverse automatically? A different numerical method does not supply missing economic independence. Any approximate or regularized objective must be agreed and its remaining risk reported.

The desk-ready response is: “The solution reconciles, but the instrument pair is fragile. Here is the quantity sensitivity and the remaining risk under revised inputs.”

All examples are synthetic educational illustrations, with no employer data, proprietary architecture, client information, or investment advice.
