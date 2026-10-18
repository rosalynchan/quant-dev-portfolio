# Designing an Auditable Liquidity Trigger for Futures Rolls

## Abstract

A futures hedge cannot remain in the front contract indefinitely, but “roll when liquidity moves” is not an implementable requirement. Volume is responsive but noisy; open interest is stable but delayed; expiry creates a deadline even when the liquidity signal is inconclusive. This article develops a transparent roll trigger that combines volume and open interest, requires multi-session confirmation, applies a separate days-to-expiry hard stop, and prevents the selected contract from flipping back and forth. The result is not an execution strategy. It is a deterministic, explainable policy for risk displays, hedge recommendations, and PnL attribution.

## Desk Context

Suppose yesterday’s hedge recommendation used the front futures contract. The next contract now trades more volume, but it has not yet accumulated most of the open interest. Should today’s recommendation switch?

This decision matters beyond a ticker label. A contract change alters the hedge instrument, its DV01, the market data used for valuation, and the interpretation of daily PnL. If two services use different roll dates, the desk can see inconsistent risk even when both calculations are individually correct.

The requirement is often stated informally: “Move to the next contract when liquidity has rolled.” A production system needs to define what liquidity means, which observation window is comparable, how long the signal must persist, and what happens as expiry approaches.

## Volume and Open Interest Measure Different Things

Daily volume is a flow: it measures how much trading occurred during a session. It reacts quickly when market participants begin using the next contract, but it can be distorted by a news event, a block trade, a holiday, or a partial session.

Open interest is a stock: it measures outstanding positions. It is usually more stable and provides evidence that positions have migrated, but it often arrives with a delay and may be corrected by the exchange or data vendor.

For a front/next pair, normalize both measures into shares:

$$
VolumeShare_{next}=\frac{V_{next}}{V_{front}+V_{next}}
$$

$$
OIShare_{next}=\frac{OI_{next}}{OI_{front}+OI_{next}}
$$

A simple composite score is then:

$$
L_{next}=0.6\times VolumeShare_{next}+0.4\times OIShare_{next}
$$

The weights are policy, not market law. A higher volume weight responds faster; a higher open-interest weight is more conservative. The system should retain both component shares so that users can explain the score rather than treating it as an opaque signal.

## A Worked Three-Session Example

Assume the policy requires a score of at least 0.60 for two consecutive complete business sessions. It also forces a roll when the front contract reaches five business days to expiry.

On Day A, front and next volumes are 80,000 and 120,000, giving the next contract a 0.60 volume share. Open interest is 300,000 and 200,000, giving it a 0.40 OI share:

$$
L_A=0.6(0.60)+0.4(0.40)=0.52
$$

The next contract leads in trading activity, but the combined evidence is insufficient.

On Day B, volume is 60,000 versus 140,000, while open interest is 220,000 versus 280,000:

$$
L_B=0.6(0.70)+0.4(0.56)=0.644
$$

The threshold is met, but this is only the first confirming session. The state becomes confirming; the effective hedge contract remains the front.

On Day C, the volume shares are 0.25 and 0.75, and the open-interest shares are 0.36 and 0.64:

$$
L_C=0.6(0.75)+0.4(0.64)=0.706
$$

The second consecutive confirmation moves the cycle to rolled, making the next contract effective. If the score falls to 0.55 on Day D, the policy does not automatically switch back. This one-way behavior within a roll cycle is a form of hysteresis: it prevents small fluctuations from causing contract churn.

If the score remains only 0.48 but the front reaches five business days to expiry, the hard stop triggers the roll. The recorded reason must be `EXPIRY_DEADLINE`, not `LIQUIDITY_CONFIRMED`. Distinguishing the causes makes policy performance measurable.

## Engineering the Trigger as a State Transition

The calculation should return more than a Boolean. A useful result includes the effective contract, state, trigger reason, component shares, score, observation session, policy version, data version, and any manual override.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LiquiditySnapshot:
    session: str
    front_volume: int
    next_volume: int
    front_oi: int
    next_oi: int
    front_dte: int
    complete: bool


def evaluate_roll(history: list[LiquiditySnapshot]) -> dict:
    threshold = Decimal("0.60")
    confirm_days, hard_dte = 2, 5
    observations = []

    for x in history:
        if not x.complete:
            continue
        totals = (x.front_volume + x.next_volume, x.front_oi + x.next_oi)
        if min(x.front_volume, x.next_volume, x.front_oi, x.next_oi) < 0:
            raise ValueError("negative liquidity input")
        if 0 in totals:
            raise ValueError("undefined liquidity share")

        volume_share = Decimal(x.next_volume) / totals[0]
        oi_share = Decimal(x.next_oi) / totals[1]
        score = Decimal("0.6") * volume_share + Decimal("0.4") * oi_share
        observations.append((x, score, volume_share, oi_share))

    latest = observations[-1]
    if latest[0].front_dte <= hard_dte:
        triggered, reason = True, "EXPIRY_DEADLINE"
    else:
        recent = observations[-confirm_days:]
        triggered = len(recent) == confirm_days and all(x[1] >= threshold for x in recent)
        reason = "LIQUIDITY_CONFIRMED" if triggered else "AWAITING_CONFIRMATION"

    return {
        "effective_contract": "NEXT" if triggered else "FRONT",
        "reason": reason,
        "score": latest[1],
        "volume_share": latest[2],
        "oi_share": latest[3],
        "as_of_session": latest[0].session,
    }
```

In production, the already-rolled state must be persisted by contract cycle. Re-running the same session should be idempotent, and a later score decline should not reverse the cycle unless the policy explicitly permits it.

## Data Quality and Production Controls

The most important controls are selective but strict:

1. **Comparable sessions.** Do not compare partial-session volume for one contract with a full-session figure for another. Both observations need the same exchange session and cutoff.
2. **Missing is not zero.** A missing feed can manufacture a 100% share for the other contract. Reject or visibly degrade the decision instead.
3. **Versioned open interest.** Retain the vendor timestamp and correction version. A historical rerun should declare whether it uses originally observed or corrected data.
4. **Monotonic cycle state.** Once rolled, the cycle should not silently revert. Manual overrides need actor, reason, and effective time.
5. **Separate hard-stop reason.** A deadline-triggered roll must remain distinguishable from a liquidity-triggered roll on dashboards and in downstream lineage.

A classic failure occurs when a service evaluates the trigger at 10:00 using the next contract’s morning volume against a stale full-day front volume. The data types look valid, but the windows are not comparable. This is a semantic data-quality failure, not a numerical one.

## Requirement Discovery

Before implementing “roll when the next contract is liquid,” ask:

- Is volume measured over a complete day, at a synchronized intraday cutoff, or as a rolling average?
- Which open-interest publication and correction policy is authoritative?
- How many confirming sessions are required, and how are holidays or half-days treated?
- Is the expiry limit in calendar days or business days?
- Can the state reverse automatically, and who may apply an override?
- Does the trigger change only analytics and recommendations, or can it initiate execution?

The last question is a critical boundary. Selecting an instrument for a risk display is not authorization to submit an order.

## Interview Perspective and Key Takeaways

A strong quant developer answer should frame the problem as controlled state management, not merely a formula. Explain that volume and open interest provide complementary evidence; confirmation filters one-day noise; hysteresis prevents flapping; and an expiry deadline provides operational safety. Then discuss session alignment, missing-data semantics, policy versioning, and audit lineage.

The core lesson is simple: a robust roll trigger is a deterministic decision process with an explainable state transition. It should tell the desk not only which contract is effective, but also when the decision occurred, which evidence supported it, and whether liquidity, expiry, or a human override caused the change.
