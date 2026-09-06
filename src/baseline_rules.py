"""
Identity-agnostic baseline detector: fixed thresholds tuned on human-normal
vs. human-compromised behavior only, then applied blindly to agent sessions
too. This represents "what current SIEM/IAM workflows already catch" when
agents are treated as generic service accounts.
"""

import pandas as pd


def fit_thresholds(train_df: pd.DataFrame) -> dict:
    """Tune thresholds using ONLY human sessions, mimicking a SIEM rule set
    that was never validated against agent behavior."""
    human = train_df[train_df["identity_type"] == "human"]
    normal = human[~human["is_compromised"]]
    compromised = human[human["is_compromised"]]

    return {
        "actions_per_session": (normal["actions_per_session"].mean()
                                 + compromised["actions_per_session"].mean()) / 2,
        "batch_size_mean": (normal["batch_size_mean"].mean()
                             + compromised["batch_size_mean"].mean()) / 2,
        "idle_ratio": (normal["idle_ratio"].mean()
                        + compromised["idle_ratio"].mean()) / 2,
    }


def predict(df: pd.DataFrame, thresholds: dict) -> pd.Series:
    """Flag as 'compromised' if 2 of 3 threshold rules trip -- a typical
    simple correlation-rule pattern."""
    votes = (
        (df["actions_per_session"] > thresholds["actions_per_session"]).astype(int)
        + (df["batch_size_mean"] > thresholds["batch_size_mean"]).astype(int)
        + (df["idle_ratio"] < thresholds["idle_ratio"]).astype(int)
    )
    return votes >= 2
