# Hedge Lot Sizes: Why Nearest Rounding Can Fail Risk Acceptance

## Abstract

An exact continuous hedge is not automatically a valid tradable proposal. When quantities must be multiples of specified lot sizes, independent rounding can breach risk tolerances even when a nearby permitted combination passes. This article evaluates a small, fully bounded candidate set, separates quantity distance from economic acceptance, and shows how to report an honest result without claiming global optimization.

## Desk context

A Rates calculator returns quantities of minus 2.4 units of A and plus 3.2 units of B. Each instrument trades only in whole units. The developer rounds to minus two and plus three, then discovers that level risk exceeds the agreed tolerance.

The trader asks why a seemingly minor rounding step changed the answer. The reason is that risk depends on the combined instrument quantities, not their individual distance from the continuous solution. A slightly more distant pair can have better offsetting effects.

The previous lesson dealt with quantity caps and target feasibility. Today we retain caps but add a discrete grid. We do not introduce a general mixed-integer optimizer, execution costs, or partial fills.

## State the discrete contract

Let $q^*$ be the continuous solution. Tradable quantities must lie on each instrument's allowed grid:

$$
q_i=n_i\ell_i,\qquad n_i\in\mathbb{Z}
$$

Here $\ell_i$ is the lot size expressed in the calculator's documented quantity units. A lot is not necessarily one contract or one million notional; the metadata must say what it means.

For this exercise, both lot sizes are one unit. Caps allow absolute quantities up to four units for A and five for B. Negative quantities mean the opposite of the defined positive instrument direction.

Risk acceptance is based on the error between achieved and requested risk change:

$$
e=Hq-b
$$

We require absolute level error no greater than GBP 20 per level basis point and absolute slope error no greater than GBP 120 per spread basis point. These are economic acceptance bands, not tolerances for floating-point arithmetic.

## Worked example: nearest is not acceptable

Use synthetic signed unit risks:

| Instrument | Level risk | Slope risk |
| --- | ---: | ---: |
| A | 100 | -20 |
| B | 80 | 40 |

The requested hedge contribution is level plus GBP 16 and slope plus GBP 176. The continuous pair minus 2.4/plus 3.2 meets it exactly: level is minus 240 plus 256, and slope is plus 48 plus 128.

Independent nearest rounding produces minus two A and plus three B. The achieved level contribution is GBP 40, so level error is positive GBP 24. Achieved slope is GBP 160, so slope error is minus GBP 16.

Nearest rounding therefore fails level acceptance even though its slope error is small. The policy must be fixed before candidate selection, not changed afterward to favor an answer.

Now consider minus three A and plus four B. Achieved level is GBP 20, giving error positive GBP 4. Achieved slope is GBP 220, giving error positive GBP 44. Both errors fall within the final bands.

The accepted pair is farther from the continuous quantities in ordinary Euclidean distance. That is not a contradiction: quantity distance is not the same objective as keeping economic risk errors within policy.

## Make the example's acceptance policy unambiguous

For every calculation below, use the final bands: GBP 20 for level and GBP 120 for slope. These bands are fixed inputs, not parameters adjusted after observing the candidate results.

The nearby candidate set consists only of floor and ceiling choices around each continuous quantity: A in minus three/minus two and B in three/four. There are four combinations:

| A | B | Level error | Slope error | Accepted |
| ---: | ---: | ---: | ---: | --- |
| -3 | 3 | -76 | +4 | No |
| -3 | 4 | +4 | +44 | Yes |
| -2 | 3 | +24 | -16 | No |
| -2 | 4 | +104 | +24 | No |

Only one candidate passes. This proves acceptance within the explicitly evaluated neighborhood. It does not prove that the pair is globally optimal over all permitted quantities.

If no candidate passes, report “no acceptable candidate in this search set.” Do not claim global infeasibility unless the full allowed set has been exhaustively checked or infeasibility has otherwise been established.

## Compact engineering design

The main calculation should validate lot and cap compliance, recompute risk, and apply factor-specific acceptance bands. Search scope is part of the output's meaning.

```python
from itertools import product

def evaluate_nearby_candidates():
    candidates = []
    for a, b in product((-3, -2), (3, 4)):
        if abs(a) > 4 or abs(b) > 5:
            continue
        achieved = (100*a + 80*b, -20*a + 40*b)
        error = (achieved[0] - 16, achieved[1] - 176)
        accepted = abs(error[0]) <= 20 and abs(error[1]) <= 120
        candidates.append({
            "quantities": (a, b),
            "achieved_change": achieved,
            "risk_error": error,
            "accepted": accepted,
        })
    return {
        "search_scope": "four_floor_ceiling_combinations",
        "candidates": candidates,
        "accepted": [x for x in candidates if x["accepted"]],
    }
```

This deliberately small integer example avoids floating-point boundary ambiguity. Production systems should represent lot counts as integers and convert to notional using exact unit metadata. Numeric comparison tolerances must remain separate from approved risk bands.

## Four selective production controls

1. Validate quantities on each instrument's own grid and within caps; do not assume a common lot size across instruments.
2. Recompute achieved risk from actual rounded quantities, never from the original continuous proposal.
3. Version factor-specific risk bands and define whether boundary equality passes.
4. Report search scope and multiple accepted candidates honestly. Ranking requires an agreed objective and tie-break rule.

A dashboard should show continuous quantities, proposed discrete quantities, signed factor errors, and acceptance reasons. “Rounded successfully” is a technical event, not proof of risk acceptance.

## Requirements and interview practice

When a trader asks for the “closest” hedge, clarify closest in quantity, normalized risk error, transaction cost, or another agreed criterion. These objectives need not select the same pair. Hard bands should be enforced before applying any optional ranking.

An interview-ready response is: “I would recompute post-rounding risk and test the discrete proposal against explicit bands. A nearby search can find a valid proposal, but failure in that neighborhood does not prove global infeasibility.”

The lesson is narrow but important: discrete quantities require economic revalidation. A continuous solution is a starting point, not an executable approval. All examples are synthetic and public-safe, with no confidential information or investment advice.
