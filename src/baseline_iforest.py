"""
Week 3: second baseline. Unlike the threshold rules (baseline_rules.py) and
the supervised classifier (classifier.py), Isolation Forest is trained
WITHOUT compromise labels -- only on sessions assumed normal at deploy time.
This represents a realistic SOC scenario where labeled compromise examples
are scarce but "this is what normal traffic looks like" is available.
"""

from sklearn.ensemble import IsolationForest

FEATURES = [
    "session_duration",
    "inter_action_variance",
    "actions_per_session",
    "batch_size_mean",
    "idle_ratio",
    "tool_diversity",
]


def fit(train_df, contamination=0.1, random_state=42):
    """Fit on assumed-normal sessions only -- mirrors how you'd deploy this
    in practice, before you have confirmed compromise examples to learn
    from."""
    normal_only = train_df[~train_df["is_compromised"]]
    model = IsolationForest(contamination=contamination, random_state=random_state)
    model.fit(normal_only[FEATURES])
    return model


def predict(model, df):
    """IsolationForest.predict returns -1 for anomalies, 1 for inliers --
    convert to the same True=compromised convention used elsewhere."""
    raw = model.predict(df[FEATURES])
    return raw == -1
