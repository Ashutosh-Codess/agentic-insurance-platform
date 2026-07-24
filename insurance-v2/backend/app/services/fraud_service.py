"""
Fraud detection: a weighted sum over concrete, named signals computed
with pandas/numpy over the customer's claim history -- never a bare
guess. Every signal is explainable in one sentence, which matters far
more for a fraud flag than for most other outputs in this project.
"""
from datetime import date

import numpy as np
import pandas as pd

SIGNAL_WEIGHTS = {
    "duplicate_amount_recent": 0.35,
    "near_waiting_period_edge": 0.2,
    "high_claim_frequency": 0.25,
    "amount_is_statistical_outlier": 0.2,
}


def _to_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def assess_fraud(claim: dict, claim_history: list[dict], policy_start_date) -> dict:
    """
    claim: the current claim {"claimed_amount", "submitted_at"}
    claim_history: this customer's OTHER claims (any policy)
    policy_start_date: date the policy this claim is filed against began
    """
    submitted_at = _to_date(claim.get("submitted_at")) or date.today()
    claimed_amount = float(claim.get("claimed_amount", 0))
    signals: dict[str, bool] = {}

    if not claim_history:
        history_df = pd.DataFrame(columns=["claimed_amount", "submitted_at"])
    else:
        history_df = pd.DataFrame(claim_history)
        history_df["submitted_at"] = pd.to_datetime(history_df["submitted_at"]).dt.date

    if not history_df.empty:
        # Signal 1: a near-identical amount filed within the last 30 days.
        recent_window = history_df[
            history_df["submitted_at"].apply(lambda d: 0 <= (submitted_at - d).days <= 30)
        ]
        if (recent_window["claimed_amount"].sub(claimed_amount).abs() < 500).any():
            signals["duplicate_amount_recent"] = True

        # Signal 3: more than 2 claims in the trailing 90 days.
        trailing_90 = history_df[
            history_df["submitted_at"].apply(lambda d: 0 <= (submitted_at - d).days <= 90)
        ]
        if len(trailing_90) > 2:
            signals["high_claim_frequency"] = True

        # Signal 4: amount is a statistical outlier vs. this customer's own
        # history, using a simple z-score (numpy) rather than a fixed multiplier.
        amounts = history_df["claimed_amount"].to_numpy(dtype=float)
        if len(amounts) >= 2 and amounts.std() > 0:
            z_score = (claimed_amount - amounts.mean()) / amounts.std()
            if z_score > 2.5:
                signals["amount_is_statistical_outlier"] = True
        elif len(amounts) == 1 and amounts[0] > 0 and claimed_amount > amounts[0] * 3:
            signals["amount_is_statistical_outlier"] = True

    # Signal 2: claim filed within 7 days of the policy's start (a common
    # fraud pattern -- buying a policy specifically to file a claim on it).
    if policy_start_date:
        policy_start = _to_date(policy_start_date)
        if policy_start and 0 <= (submitted_at - policy_start).days <= 7:
            signals["near_waiting_period_edge"] = True

    fraud_score = round(min(sum(SIGNAL_WEIGHTS[s] for s in signals), 1.0), 2)
    reasoning = f"Fraud score {fraud_score} based on signals: {list(signals.keys()) or ['none triggered']}."

    return {"fraud_score": fraud_score, "signals": signals, "reasoning": reasoning}
