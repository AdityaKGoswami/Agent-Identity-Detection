"""
Week 4: digs into WHERE each detector goes wrong, not just aggregate
recall/precision. Two outputs:

  results/misclassified_sessions.csv -- every session any detector got
    wrong, tagged with which detector(s) missed it and its identity type.
  results/error_analysis.md -- human-readable summary: which detector
    struggles with which identity type, what the classifier's learned
    feature weights are, and how false negatives differ from true
    positives on the features that matter most.

Run after src/evaluate.py (uses the same train/test split, same seed, so
the two reports describe the same underlying run).
"""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

import baseline_rules
import baseline_iforest
import classifier as clf_module

FEATURES = clf_module.FEATURES


def build_predictions(df):
    train_df, test_df = train_test_split(
        df, test_size=0.3, random_state=42, stratify=df["label"]
    )
    test_df = test_df.copy()

    thresholds = baseline_rules.fit_thresholds(train_df)
    test_df["baseline_pred"] = baseline_rules.predict(test_df, thresholds)

    model = clf_module.build_model()
    clf_module.fit(model, train_df)
    test_df["classifier_pred"] = clf_module.predict(model, test_df)

    iforest_model = baseline_iforest.fit(train_df)
    test_df["iforest_pred"] = baseline_iforest.predict(iforest_model, test_df)

    return train_df, test_df, model


def misclassified_rows(test_df):
    detectors = ["baseline_pred", "classifier_pred", "iforest_pred"]
    rows = []
    for _, row in test_df.iterrows():
        missed_by = [d for d in detectors if row[d] != row["is_compromised"]]
        if missed_by:
            r = row.to_dict()
            r["missed_by"] = ",".join(m.replace("_pred", "") for m in missed_by)
            r["n_detectors_missed"] = len(missed_by)
            rows.append(r)
    return pd.DataFrame(rows)


def feature_importance(model):
    clf = model.named_steps["logisticregression"]
    scaler = model.named_steps["standardscaler"]
    # Coefficients are in standardized-feature space, which is exactly what
    # we want for comparing relative importance across features with very
    # different natural scales (e.g. session_duration in seconds vs.
    # tool_diversity as a small integer count).
    return sorted(
        zip(FEATURES, clf.coef_[0]), key=lambda x: abs(x[1]), reverse=True
    )


def write_report(test_df, missed_df, importances, out_path):
    lines = ["# Week 4 Error Analysis\n"]

    lines.append("## Miss rate by detector and identity type\n")
    lines.append("| Detector | Human miss rate | Agent miss rate |")
    lines.append("|---|---|---|")
    for detector in ["baseline_pred", "classifier_pred", "iforest_pred"]:
        row = []
        for identity in ["human", "agent"]:
            subset = test_df[test_df["identity_type"] == identity]
            miss_rate = (subset[detector] != subset["is_compromised"]).mean()
            row.append(f"{miss_rate:.1%}")
        name = detector.replace("_pred", "")
        lines.append(f"| {name} | {row[0]} | {row[1]} |")
    lines.append("")

    lines.append("## Classifier feature importance (standardized coefficients)\n")
    lines.append("Sign indicates direction: positive pushes toward "
                  "'compromised', negative toward 'normal'.\n")
    lines.append("| Feature | Coefficient |")
    lines.append("|---|---|")
    for feat, coef in importances:
        lines.append(f"| {feat} | {coef:+.3f} |")
    lines.append("")

    lines.append("## Hardest cases (missed by 2+ detectors)\n")
    hardest = missed_df[missed_df["n_detectors_missed"] >= 2]
    if len(hardest):
        lines.append(f"{len(hardest)} sessions missed by 2 or more detectors "
                      f"(out of {len(test_df)} test sessions). Breakdown by "
                      f"identity type:\n")
        lines.append(hardest["identity_type"].value_counts().to_markdown())
    else:
        lines.append("None -- every miss was caught by at least one other detector.")
    lines.append("")

    lines.append("## False negatives vs. true positives, by feature (agent identity)\n")
    lines.append("Where the classifier's false negatives on agent-compromised "
                  "sessions differ most from its true positives -- these features "
                  "are where a missed compromise 'hides'.\n")
    agent_test = test_df[(test_df["identity_type"] == "agent") & (test_df["is_compromised"])]
    fn = agent_test[agent_test["classifier_pred"] == False]
    tp = agent_test[agent_test["classifier_pred"] == True]
    if len(fn) and len(tp):
        lines.append("| Feature | False-negative mean | True-positive mean |")
        lines.append("|---|---|---|")
        for feat in FEATURES:
            lines.append(f"| {feat} | {fn[feat].mean():.3f} | {tp[feat].mean():.3f} |")
    else:
        lines.append(f"Not enough data: {len(fn)} false negatives, {len(tp)} true positives.")
    lines.append("")

    out_path.write_text("\n".join(lines))


def main():
    root = Path(__file__).resolve().parent.parent
    data_path = root / "data" / "sessions.csv"
    if not data_path.exists():
        raise SystemExit("Run src/simulator.py first.")

    df = pd.read_csv(data_path)
    train_df, test_df, model = build_predictions(df)
    missed_df = misclassified_rows(test_df)
    importances = feature_importance(model)

    out_dir = root / "results"
    out_dir.mkdir(exist_ok=True)
    missed_df.to_csv(out_dir / "misclassified_sessions.csv", index=False)
    write_report(test_df, missed_df, importances, out_dir / "error_analysis.md")

    print(f"{len(missed_df)} / {len(test_df)} test sessions missed by at least one detector")
    print(f"Wrote results/misclassified_sessions.csv and results/error_analysis.md")


if __name__ == "__main__":
    main()
