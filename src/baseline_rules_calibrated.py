"""
Tests the headline finding directly: baseline_rules.py fits ONE set of
thresholds on human data only, then applies it blindly to agents too --
which is why it structurally misses agent compromise (agents sit on a
different absolute scale). This module fits SEPARATE thresholds per
identity type instead, to see how much of the gap that alone closes.

Also includes `tool_diversity` in the vote, which baseline_rules.py's
original 3-feature design omits. error_analysis.py identified
tool_diversity as the classifier's single strongest signal (standardized
coefficient +2.03) -- a first calibration-only pass (see git history)
showed almost no improvement over the identity-agnostic baseline, and
diagnosing why showed idle_ratio is now a flat 0.0 for ALL agent sessions
(a side effect of the Week 4 fix -- see README), contributing zero
discriminative power within the agent class regardless of calibration.
Swapping it for tool_diversity, which does vary meaningfully between
agent_normal and agent_compromised, is the fix tested here.

Important assumption to be upfront about: this requires knowing a
session's identity type (human vs. agent) at detection time. That's often
available in practice (IAM systems generally know which accounts are
service/agent identities), but it's a different assumption than
baseline_rules.py's fully identity-agnostic design -- so this isn't a
strictly fair swap-in, it's a test of "how much does identity-aware
calibration plus a better feature choice help, if you have that metadata
available."
"""

import pandas as pd


def fit_thresholds_per_identity(train_df: pd.DataFrame) -> dict:
    thresholds = {}
    for identity in train_df["identity_type"].unique():
        subset = train_df[train_df["identity_type"] == identity]
        normal = subset[~subset["is_compromised"]]
        compromised = subset[subset["is_compromised"]]
        if len(normal) == 0 or len(compromised) == 0:
            continue
        thresholds[identity] = {
            "actions_per_session": (normal["actions_per_session"].mean()
                                     + compromised["actions_per_session"].mean()) / 2,
            "batch_size_mean": (normal["batch_size_mean"].mean()
                                 + compromised["batch_size_mean"].mean()) / 2,
            "tool_diversity": (normal["tool_diversity"].mean()
                                + compromised["tool_diversity"].mean()) / 2,
        }
    return thresholds


def predict(df: pd.DataFrame, thresholds: dict) -> pd.Series:
    def _predict_row(row):
        th = thresholds.get(row["identity_type"])
        if th is None:
            return False  # no calibration data for this identity type -- fail safe, don't guess
        votes = (
            int(row["actions_per_session"] > th["actions_per_session"])
            + int(row["batch_size_mean"] > th["batch_size_mean"])
            + int(row["tool_diversity"] > th["tool_diversity"])
        )
        return votes >= 2

    return df.apply(_predict_row, axis=1)
