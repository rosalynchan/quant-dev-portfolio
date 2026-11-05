# Log-Linear Discount-Factor Interpolation for Rates Curves

## Abstract

A bootstrapped rates curve is a discrete set of calibrated nodes, while a pricer needs values on arbitrary cash-flow dates. The rule connecting those nodes is therefore part of the pricing methodology, not a display preference. This article develops log-linear interpolation of discount factors, works through a numerical example, and shows how to make interpolation conventions explicit across pricing, risk, and PnL explain services.

## Desk Context

Suppose yesterday's bootstrap produced two discount factors:

- $P(1.25)=0.9599208313$
- $P(1.50)=0.9495939966$

A swap coupon falls at 1.375 years. One valuation path uses linear interpolation of discount factors; another uses log-linear interpolation. Both consume identical market quotes and calibrated nodes, yet the swap PVs differ.

This is a common class of front-office break. Calibration determines curve values at selected maturities. Interpolation determines the curve between them, where most portfolio cash flows actually occur. If pricing, risk, scenarios, and PnL explain do not share that convention, every component can look individually plausible while the overall workflow fails to reconcile.

## The Interpolation Rule

For $t_1<t<t_2$, define the interpolation weight

$$
w=\frac{t-t_1}{t_2-t_1}.
$$

Log-linear discount-factor interpolation is

$$
\log P(t)=(1-w)\log P(t_1)+w\log P(t_2),
$$

or equivalently,

$$
P(t)=P(t_1)^{1-w}P(t_2)^w.
$$

The method draws a straight line through log discount factors rather than discount factors themselves. Since a discount factor can be written as $P(t)=e^{-z(t)t}$ under continuous compounding, a linear segment in $log P$ implies a constant instantaneous forward rate over that segment.

That is a useful and interpretable local assumption, but it is not universally superior. Curve libraries may interpolate zero rates, discount factors, or forwards and may use monotone-convex or spline methods. The engineering requirement is to name the state variable and method precisely and apply them consistently.

## Worked Numerical Example

The target at 1.375 years is halfway between the two nodes:

$$
w=\frac{1.375-1.25}{1.50-1.25}=0.5.
$$

Therefore,

$$
\begin{aligned}
P(1.375)
&=\sqrt{P(1.25)P(1.50)}\\
&=\sqrt{0.9599208313\times0.9495939966}\\
&=0.9547434517.
\end{aligned}
$$

The simple forward for the first 0.125-year subperiod is

$$
F_{1.25,1.375}
=\frac{P(1.25)/P(1.375)-1}{0.125}
=4.338237\%.
$$

The second subperiod gives exactly the same result:

$$
F_{1.375,1.50}
=\frac{P(1.375)/P(1.50)-1}{0.125}
=4.338237\%.
$$

That equality is the economic signature of the log-linear segment.

Linear interpolation of discount factors instead gives

$$
P_{\text{linear}}(1.375)
=\frac{0.9599208313+0.9495939966}{2}
=0.9547574140.
$$

The discount-factor difference is only 0.0000139622. Applied to a GBP 100 million cash flow, however, it creates roughly GBP 1,396 of PV difference. Linear discount-factor interpolation also produces unequal forwards of approximately 4.326475% and 4.350000% across the two half-periods.

Neither calculation changes the endpoint nodes. The entire difference comes from the off-node curve shape.

## Why Risk Changes Too

An off-node value depends on both surrounding nodes. At the midpoint,

$$
P(t)=\sqrt{P_1P_2}.
$$

A bump to either node therefore changes the cash-flow PV. The interpolation Jacobian determines how risk is distributed between curve buckets. A pricing service using log-linear interpolation and a risk service using linear discount factors will disagree not only on PV but also on bucketed DV01.

Finite-difference risk must rebuild or reevaluate the curve with the same interpolation after every bump. Replacing the official evaluator with a convenient library default is not a harmless optimisation. It changes the methodology.

## Engineering Design

```python
from dataclasses import dataclass
from math import exp, log


@dataclass(frozen=True)
class CurveNode:
    time: float
    discount_factor: float


def log_linear_df(left: CurveNode, right: CurveNode, t: float) -> float:
    if not left.time < t < right.time:
        raise ValueError("target must be bracketed by distinct nodes")
    if left.discount_factor <= 0 or right.discount_factor <= 0:
        raise ValueError("discount factors must be positive")

    w = (t - left.time) / (right.time - left.time)
    return exp(
        (1.0 - w) * log(left.discount_factor)
        + w * log(right.discount_factor)
    )
```

In production, the curve snapshot should carry more than arrays of dates and values. It should identify the interpolation state variable, interpolation method, time measure, node-hit behaviour, extrapolation policy, and methodology version. Consumers should reference the immutable snapshot rather than recreate the curve from loosely related inputs.

The implementation should distinguish three cases explicitly:

1. A target exactly on a node returns the calibrated node value.
2. A target inside the node range uses the configured interpolation method.
3. A target outside the range invokes a separate extrapolation policy or fails.

Letting an interpolation function silently extend beyond the last node hides a coverage problem behind a reasonable-looking number.

## Data Quality and Production Controls

The highest-value controls are selective:

- Require strictly increasing, non-duplicate node times and positive discount factors.
- Derive node and target times using the same valuation date, calendar, and day-count mapping.
- Persist interpolation and methodology versions in curve-snapshot lineage.
- Reject pricing, risk, or explain runs whose curve methodology differs from the official snapshot.
- Regression-test node hits, midpoints, near-node continuity, and PV-versus-risk consistency under small bumps.

A particularly dangerous failure mode occurs when pricing uses `LOG_LINEAR_DF` while PnL explain uses `LINEAR_DF`. Both services return smooth, credible outputs. Market quotes and calibrated nodes match, so superficial controls pass. The break appears only on off-node cash flows and becomes a persistent unexplained PnL component.

Useful observability includes the count of evaluations by interpolation method, extrapolation attempts, curve-version mismatches, and maximum PV difference against a controlled reference evaluator.

## Requirement Discovery and Interview Questions

When a trader or quant says “use the same curve,” a developer should clarify:

- Does “same” mean identical market quotes, calibrated nodes, or an immutable curve snapshot?
- Is the interpolated state variable a discount factor, zero rate, or forward rate?
- Which day-count convention maps dates to curve time?
- What happens on an exact node date?
- What is the extrapolation policy beyond the first and last nodes?
- Must pricing, Greeks, scenarios, and PnL explain share one methodology version?
- How will an interpolation-method change be impact-tested and rolled out?

A strong interview answer separates calibration from evaluation: calibration fits market instruments at nodes, while interpolation defines off-node values and their sensitivities. It also recognises that a method change affects both PV and risk allocation and therefore needs versioning, regression evidence, and coordinated deployment.

## Key Takeaways

- A curve is not fully specified by its calibrated nodes; interpolation is part of the model.
- Log-linear discount-factor interpolation is a geometric interpolation that implies a constant instantaneous forward within each segment.
- Small off-node differences can become material across large cash flows or portfolios.
- Interpolation changes the Jacobian from nodes to cash flows, so it changes bucketed risk as well as PV.
- Pricing, risk, scenarios, and PnL explain should consume the same versioned curve evaluator, with extrapolation handled explicitly.
