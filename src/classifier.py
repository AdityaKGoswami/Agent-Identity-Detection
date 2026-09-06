"""
Lightweight behavioral classifier. Deliberately simple (logistic regression)
so the point of the research is the FEATURE SET and the human-vs-agent
comparison, not model sophistication.
"""

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

FEATURES = [
    "session_duration",
    "inter_action_variance",
    "actions_per_session",
    "batch_size_mean",
    "idle_ratio",
    "tool_diversity",
]


def build_model() -> "Pipeline":
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced"),
    )


def fit(model, train_df):
    X = train_df[FEATURES]
    y = train_df["is_compromised"]
    model.fit(X, y)
    return model


def predict(model, df):
    return model.predict(df[FEATURES])
