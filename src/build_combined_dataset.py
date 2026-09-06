"""
Builds a hybrid dataset: KEEP the synthetic human_normal/human_compromised
sessions (no harness equivalent exists for those), but REPLACE the
synthetic agent_normal/agent_compromised sessions with real output from
agent_harness/run_harness.py.

This answers a direct question: do the detector comparisons in
src/evaluate.py hold up when the agent side of the data comes from an
actual running agent instead of a hand-specified distribution? Run this
after both src/simulator.py and agent_harness/run_harness.py (any backend).

Output: data/combined_sessions.csv, same schema, ready to point
src/evaluate.py or src/error_analysis.py at (edit their data_path, or copy
this over data/sessions.csv if you want to compare side by side first).
"""

from pathlib import Path

import pandas as pd


def main():
    root = Path(__file__).resolve().parent.parent
    synthetic_path = root / "data" / "sessions.csv"
    harness_path = root / "data" / "real_agent_sessions.csv"

    if not synthetic_path.exists():
        raise SystemExit("Run src/simulator.py first.")
    if not harness_path.exists():
        raise SystemExit("Run agent_harness/run_harness.py first (mock, groq, or real).")

    synthetic = pd.read_csv(synthetic_path)
    harness = pd.read_csv(harness_path)

    human_only = synthetic[synthetic["identity_type"] == "human"].copy()
    human_only["source"] = "synthetic"
    human_only["backend"] = "simulator"

    combined = pd.concat([human_only, harness], ignore_index=True)
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

    out_path = root / "data" / "combined_sessions.csv"
    combined.to_csv(out_path, index=False)

    print(f"Wrote {len(combined)} sessions to {out_path}")
    print(combined.groupby(["identity_type", "is_compromised", "source"]).size())
    print(f"\nBackend used for agent data: {harness['backend'].iloc[0]}")
    print("Point src/evaluate.py's data_path at combined_sessions.csv to "
          "compare against the fully-synthetic results.")


if __name__ == "__main__":
    main()
