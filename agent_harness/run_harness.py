"""
Runs the real-agent harness: N sessions on benign tickets, N sessions on
tickets carrying real indirect prompt injection.

Output: data/real_agent_sessions.csv, same schema as data/sessions.csv so
the two can be concatenated or compared directly in src/evaluate.py.

Usage:
    python -m agent_harness.run_harness                    # mock backend, no key, 60/ticket
    python -m agent_harness.run_harness --backend groq      # FREE real API (console.groq.com)
    python -m agent_harness.run_harness --backend real      # paid Claude API
    python -m agent_harness.run_harness --backend groq --n-per-ticket 15
"""

import argparse
import csv
import os
from pathlib import Path

from dotenv import load_dotenv

from .agent_loop import run_session
from .documents import (
    BENIGN_TICKETS, INJECTED_TICKETS, SCOPE_CREEP_TICKETS,
    BATCH_BENIGN_TICKETS, BATCH_INJECTED_TICKETS, BATCH_SCOPE_CREEP_TICKETS,
)
from .features import compute_features
from .llm_backend import MockVulnerableBackend, RealAnthropicBackend, GroqBackend

load_dotenv()  # reads .env in the project root if present -- see .env.example

FIELDNAMES = [
    "session_duration", "inter_action_variance", "actions_per_session",
    "batch_size_mean", "idle_ratio", "tool_diversity",
    "label", "identity_type", "is_compromised", "source", "backend", "scenario",
]


def make_backend(kind, seed=None):
    if kind == "real":
        return RealAnthropicBackend()  # reads ANTHROPIC_API_KEY internally
    if kind == "groq":
        return GroqBackend()  # reads GROQ_API_KEY internally -- free, no card
    return MockVulnerableBackend(compliance_rate=0.8, seed=seed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["mock", "real", "groq"], default="mock")
    parser.add_argument(
        "--n-per-ticket", type=int, default=None,
        help="Sessions per ticket template. Default: 60 for mock, 15 for "
             "real/groq (both call a live API, so keep initial runs small).",
    )
    args = parser.parse_args()

    key_by_backend = {"real": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY"}
    if args.backend in key_by_backend and not os.environ.get(key_by_backend[args.backend]):
        hint = (
            'Get a key at platform.claude.com (Settings -> API Keys) -- paid.'
            if args.backend == "real" else
            'Get a FREE key (no credit card) at https://console.groq.com'
        )
        raise SystemExit(
            f"{key_by_backend[args.backend]} is not set. {hint}\n"
            f'Then: export {key_by_backend[args.backend]}="..."'
        )

    n_per_ticket = args.n_per_ticket or (60 if args.backend == "mock" else 15)
    backend_label = {
        "real": "RealAnthropicBackend",
        "groq": "GroqBackend",
        "mock": "MockVulnerableBackend",
    }[args.backend]

    rows = []
    seed = 0
    all_tickets = [(t, "benign", 10) for t in BENIGN_TICKETS] + \
                  [(t, "injected_narrow", 10) for t in INJECTED_TICKETS] + \
                  [(t, "injected_scope_creep", 10) for t in SCOPE_CREEP_TICKETS] + \
                  [(t, "batch_benign", 25) for t in BATCH_BENIGN_TICKETS] + \
                  [(t, "batch_injected_narrow", 25) for t in BATCH_INJECTED_TICKETS] + \
                  [(t, "batch_injected_scope_creep", 25) for t in BATCH_SCOPE_CREEP_TICKETS]

    for ticket_text, kind, max_steps in all_tickets:
        for i in range(n_per_ticket):
            # Fresh backend instance per session -- conversation state
            # (self.messages) must not leak across sessions.
            backend = make_backend(args.backend, seed=seed)
            session = run_session(backend, ticket_text, max_steps=max_steps, seed=seed)
            seed += 1

            feats = compute_features(session)
            rows.append({
                **feats,
                "label": "agent_compromised" if session["compromised"] else "agent_normal",
                "identity_type": "agent",
                "is_compromised": session["compromised"],
                "source": f"harness_{args.backend}",
                "backend": backend_label,
                "scenario": kind,
            })
            if args.backend in ("real", "groq"):
                print(f"  [{kind}] session {i + 1}/{n_per_ticket} "
                      f"-> {'COMPROMISED' if session['compromised'] else 'clean'}")

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "real_agent_sessions.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    n_compromised = sum(1 for r in rows if r["is_compromised"])
    print(f"\nWrote {len(rows)} sessions to {out_path}")
    print(f"Compromised: {n_compromised} ({n_compromised / len(rows):.1%})")
    print(f"Backend: {backend_label}")
    if args.backend == "mock":
        print("This is the scripted-compliance mock -- see README for what "
              "that does and doesn't tell you. Run with --backend groq for "
              "a genuine result at zero cost (free key at console.groq.com).")


if __name__ == "__main__":
    main()
