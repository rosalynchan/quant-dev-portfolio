# Why Full-Revaluation PnL Attribution Depends on Factor Order

## Abstract

Full revaluation avoids the local approximation error of a Greek-based PnL explain, but it does not make factor attribution unique. When two curve factors interact, changing one first assigns the interaction differently from changing the other first. This article distinguishes total PnL from its allocation, demonstrates a two-factor exact reconciliation, and presents an order-averaged attribution suitable for a small, explicitly defined factor set. The goal is reproducible desk communication, not a claim that one decomposition reveals the unique economic cause of every gain or loss.

## The Desk Problem

A trader asks why yesterday’s report attributed GBP 10,000 of losses to 5Y rates while a rerun attributes GBP 8,000 to the same factor. Both reports reconcile perfectly to the same GBP 14,000 total loss. There has been no trade amendment, quote correction, or pricing-model release.

The difference is the order of the full-revaluation ladder. One process updated 5Y before 10Y; the other did the reverse. Because portfolio value contains interactions, the second factor in either sequence inherits the joint effect.

This follows naturally from cross-gamma. Cross-gamma describes a local interaction; an order-dependent full-revaluation ladder exposes that interaction without truncating the pricing function to second order. The ladder is exact for its selected endpoints, but its allocation is still a convention.

## Four Valuation States

Freeze valuation time, trades, fixings, model version, and every market factor outside the selected pair. Construct four valid market states:

- V00: both factors at their opening values.
- V10: 5Y at closing, 10Y at opening.
- V01: 5Y at opening, 10Y at closing.
- V11: both factors at closing.

The hybrid states must be rebuilt through the approved curve construction. Replacing cached discount factors independently is not equivalent to changing market quotes and recalibrating the dependent curves.

Total selected-factor PnL is simply the difference between V11 and V00. It is invariant to the ladder order. Intermediate allocations need not be.

## Worked Numerical Example

All values below are generic illustrative GBP portfolio PVs:

| State | 5Y quote state | 10Y quote state | PV |
|---|---|---|---:|
| V00 | Opening | Opening | 1,000,000 |
| V10 | Closing | Opening | 990,000 |
| V01 | Opening | Closing | 994,000 |
| V11 | Closing | Closing | 986,000 |

Total PnL is GBP -14,000.

If 5Y moves first, its contribution is 990,000 minus 1,000,000, or GBP -10,000. The subsequent 10Y contribution is 986,000 minus 990,000, or GBP -4,000.

If 10Y moves first, its contribution is GBP -6,000. Updating 5Y next contributes GBP -8,000. Both ladders reconcile to GBP -14,000, yet their bucket allocations differ.

The exact finite-move interaction is:

$$
I = V_{11}-V_{10}-V_{01}+V_{00}
$$

For this example, the interaction is GBP +2,000. The standalone contributions sum to GBP -16,000; the positive interaction brings the joint result to GBP -14,000.

This finite-move interaction is not itself a cross-gamma Greek. For sufficiently small moves, it can be approximated by cross-gamma multiplied by the two factor moves. For larger moves, it also contains higher-order joint effects.

## Averaging the Two Orders

For exactly two factors, averaging each factor’s marginal contribution across both orders splits the interaction equally:

$$
A_5 = \frac{(V_{10}-V_{00})+(V_{11}-V_{01})}{2}
$$

$$
A_{10} = \frac{(V_{01}-V_{00})+(V_{11}-V_{10})}{2}
$$

The resulting allocations are GBP -9,000 to 5Y and GBP -5,000 to 10Y. Their sum remains GBP -14,000.

This is the two-player Shapley allocation. It is symmetric between the chosen factors and independent of choosing one of the two orders as official. It is not independent of factor definition or grouping. Treating an entire projection curve as one factor can produce different allocations from treating its individual quotes as separate factors.

For a larger factor set, exact permutation averaging becomes expensive. A two-factor result must not be advertised as an exact full-portfolio Shapley attribution.

## Engineering Connection

The attribution function should consume four validated valuation results rather than initiate loosely coordinated live market reads.

```python
def attribute_two_factors(v00, v10, v01, v11):
    total = v11 - v00
    interaction = v11 - v10 - v01 + v00

    factor_5y = ((v10 - v00) + (v11 - v01)) / 2
    factor_10y = ((v01 - v00) + (v11 - v10)) / 2

    return {
        "method": "TWO_FACTOR_ORDER_AVERAGE",
        "factor_5y_pnl": factor_5y,
        "factor_10y_pnl": factor_10y,
        "interaction_pnl": interaction,
        "total_pnl": total,
        "reconciliation_error": factor_5y + factor_10y - total,
    }
```

The interaction field is diagnostic. It has already been allocated between the two factor contributions and must not be added again to total PnL.

## Selective Production Controls

Four controls matter especially for this workflow:

1. Validate hybrid-state construction. Each state must use an approved quote-replacement and curve-rebuild policy; a failed calibration makes attribution incomplete.
2. Version factor grouping and allocation method. A switch from sequential to order-averaged attribution changes report semantics even if total PnL is unchanged.
3. Enforce reconciliation within currency precision. Require both sequences and the averaged result to match the same endpoint difference.
4. Prevent interaction double counting. Publish allocated contributions and an explicitly non-additive interaction diagnostic.

Tests should include a separable pricing function with zero interaction, a known joint term, exchanged factor labels, and a failed hybrid valuation. Swapping factor names and their corresponding states should swap allocations without changing total PnL.

## Requirement Discovery

Before implementing “show PnL by tenor,” ask which market inputs define each factor, whether curve dependencies are rebuilt, and which nonselected inputs remain frozen. Confirm whether the desk wants a fixed sequential ladder, explicit standalone-plus-interaction reporting, or order-averaged allocation.

Also establish how methodology changes are handled. A change in allocation policy can require a comparative report, but it is not a change in market PnL. Labels should make that distinction visible.

A useful interview answer is: “Full revaluation makes the endpoint comparison exact, not the factor allocation unique. I version the hybrid-state construction and attribution convention, quantify interaction, and reconcile every decomposition to the same total.”

## Key Takeaways

- Exact total PnL does not imply unique factor attribution.
- Sequential ladders assign interaction differently depending on order.
- Two-factor order averaging splits the finite interaction equally.
- Factor grouping remains a business and modeling choice.
- Interaction diagnostics are not an extra additive PnL component.

All figures are illustrative and public-safe. This article is educational and does not provide investment advice.
