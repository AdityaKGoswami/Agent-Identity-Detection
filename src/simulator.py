"""
Simulates behavioral telemetry for four session types:
human-normal, human-compromised, agent-normal, agent-compromised.

This is a PROOF-OF-CONCEPT data generator. The agent-compromised class is
currently drawn from a hand-specified behavioral model (see TODO below) —
replace it with logs from a real prompt-injected tool-calling agent before
treating any downstream result as a genuine finding.

Output: data/sessions.csv with one row per session and a `label` column.
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(seed=42)
N_PER_CLASS = 500  # sessions per class -> 2000 total


def _sample(mean, std, n, low=0.0):
    """Truncated-normal sampler so features don't go negative."""
    return np.clip(RNG.normal(mean, std, n), low, None)


def simulate_human_normal(n=N_PER_CLASS):
    return pd.DataFrame({
        "session_duration": _sample(900, 400, n),          # ~15 min avg, high variance
        "inter_action_variance": _sample(45, 20, n),         # irregular pacing
        "actions_per_session": _sample(12, 6, n, low=1),
        "batch_size_mean": _sample(1.2, 0.4, n, low=1),      # rarely batches actions
        "idle_ratio": _sample(0.45, 0.15, n, low=0, ),
        "tool_diversity": _sample(3, 1.5, n, low=1),
        "label": "human_normal",
    })


def simulate_human_compromised(n=N_PER_CLASS):
    # Compromised human accounts (e.g. stolen creds used by a human operator or
    # simple script) look faster and more repetitive than normal, but still
    # noisier than an agent because there's a human (or crude script) driving it.
    return pd.DataFrame({
        "session_duration": _sample(300, 150, n, low=10),
        "inter_action_variance": _sample(20, 12, n),
        "actions_per_session": _sample(25, 10, n, low=1),
        "batch_size_mean": _sample(2.0, 0.8, n, low=1),
        "idle_ratio": _sample(0.15, 0.1, n),
        "tool_diversity": _sample(5, 2, n, low=1),
        "label": "human_compromised",
    })


def simulate_agent_normal(n=N_PER_CLASS):
    # Agents are already regular/dense even when doing legitimate work —
    # this is the key confound the research question is testing.
    return pd.DataFrame({
        "session_duration": _sample(120, 40, n, low=5),
        "inter_action_variance": _sample(4, 2, n),
        "actions_per_session": _sample(30, 8, n, low=1),
        "batch_size_mean": _sample(4.0, 1.0, n, low=1),
        "idle_ratio": _sample(0.03, 0.02, n),
        "tool_diversity": _sample(4, 1.5, n, low=1),
        "label": "agent_normal",
    })


def simulate_agent_compromised(n=N_PER_CLASS):
    # TODO(week 4+): replace this synthetic model with telemetry captured from
    # a real tool-calling agent (e.g. a LangChain/MCP agent) under an actual
    # prompt-injection attack, logged with the same 6 features. Until then,
    # this class encodes the hypothesis (higher tool_diversity + larger
    # batches from scope creep / delegation) rather than an observed fact.
    return pd.DataFrame({
        "session_duration": _sample(180, 60, n, low=5),
        "inter_action_variance": _sample(3, 1.5, n),
        "actions_per_session": _sample(55, 15, n, low=1),
        "batch_size_mean": _sample(6.5, 1.5, n, low=1),      # scope creep -> larger batches
        "idle_ratio": _sample(0.02, 0.015, n),
        "tool_diversity": _sample(9, 2.5, n, low=1),          # touches tools outside normal scope
        "label": "agent_compromised",
    })


def build_dataset() -> pd.DataFrame:
    df = pd.concat([
        simulate_human_normal(),
        simulate_human_compromised(),
        simulate_agent_normal(),
        simulate_agent_compromised(),
    ], ignore_index=True)
    df["identity_type"] = df["label"].apply(lambda x: "agent" if "agent" in x else "human")
    df["is_compromised"] = df["label"].apply(lambda x: "compromised" in x)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    dataset = build_dataset()
    out_path = out_dir / "sessions.csv"
    dataset.to_csv(out_path, index=False)
    print(f"Wrote {len(dataset)} sessions to {out_path}")
    print(dataset["label"].value_counts())
