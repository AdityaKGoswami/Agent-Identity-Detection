# Agent vs. Human: Can Your SOC Tell a Compromised AI Agent From a Compromised Human?

**Status:** Week 4 complete — real-agent harness, second baseline, error analysis, longer-horizon batch scenario, and the `idle_ratio` metric bug are all done. **Result: the hypothesis is supported once the measurement bug is fixed — but so is a more interesting caveat about what the classifier is actually learning. See "Hypothesis check" below.**

## Research question

When an AI agent's credentials are compromised, does it produce a behaviorally
distinguishable signature from a compromised human account — and can a
lightweight classifier detect it faster than identity-agnostic SIEM rules do?

## Why this matters

Most SIEM/IAM alerting was tuned on human behavioral baselines (login times,
geolocation, click cadence). AI agents are increasingly given real credentials
and tool access, but are commonly treated as generic service accounts with no
dedicated identity or behavioral model. Nobody has published a clean
before/after comparison of detection performance across the two identity
types.

## Hypothesis

Agent identities produce structurally different telemetry than human
identities, even under compromise: tighter timing regularity, higher
action-call density, near-zero idle time, and batch-style tool invocation.
A detector trained on these features should out-perform generic,
identity-agnostic anomaly rules at flagging agent-specific compromise.

### Hypothesis check (final, Week 4: latency fix → scope-creep → batch scenario → idle_ratio fix)

**Supported, once a measurement bug was fixed — with an important caveat
about what that fix implies for the classifier.**

- **Action density**: converges toward human-like levels on a
  realistically long task (16.6 actions/session on a 5-ticket batch vs.
  humans' 18.6, up from 4.4 on a single bounded ticket). Confirmed.
- **Idle ratio**: the original definition counted ordinary LLM "thinking
  time" as idleness, which inflated the metric with every extra decision
  step -- making agents look *more* idle on longer tasks, the opposite
  of the hypothesis. **Fixed** in `agent_harness/features.py`: a gap now only
  counts as idle if it's an outlier relative to that session's own typical
  cadence, not longer than a fixed constant. After the fix, agent `idle_ratio`
  comes out to **0.0** across all harness sessions vs. humans' 0.30 -- confirming
  this part of the hypothesis too.
- **Caveat**: because `idle_ratio` is now a literal constant (0.0) for
  every single agent session regardless of compromise status, it can only
  help a classifier tell "this is an agent" -- it cannot discriminate
  compromised from normal *within* the agent class. Retraining on the
  fixed data, the classifier's agent-compromise recall actually *dropped*
  again (65.4% → 55.8%), consistent with it having leaned on this
  shortcut before. This is expected to change once real Groq/Claude
  timing data introduces genuine jitter into agent `idle_ratio` --
  recommended to report classifier performance with and without
  `idle_ratio` once that data exists, to separate real signal from an
  identity-type shortcut.
- Identity-agnostic threshold rules remain at **0% agent-compromise
  recall** throughout every fix -- not because the behavioral signature is
  absent (it isn't -- see above), but because the rules' `actions_per_session`
  cutoff (18.8, fit only on human data) sits just above every agent
  session's actual maximum (18.0). Agents operate on a categorically
  different absolute scale than the human data the rules were calibrated
  on, regardless of whether the underlying signal is real.

**This is now a direct, positive, well-supported answer to the original
research question**: agent identities do show a distinguishable
behavioral signature under compromise, but identity-agnostic SIEM rules
miss it anyway because they're scaled to human absolute behavior. Full
numbers and reasoning in `results/dataset_comparison.md`.

## Method

1. **Simulate** four session types: human-normal, human-compromised,
   agent-normal, agent-compromised (`src/simulator.py`).
2. **Baseline**: run simple identity-agnostic SIEM-style threshold rules
   against all sessions (`src/baseline_rules.py`) — this represents "what
   current workflows already catch."
3. **Classifier**: train a lightweight logistic regression on 6 behavioral
   features (`src/classifier.py`).
4. **Evaluate** both approaches, broken out separately by identity type
   (`src/evaluate.py`) — the interesting result is the *gap* between
   human and agent detection rates, not the absolute numbers.

## Features used

| Feature | Description |
|---|---|
| `session_duration` | Total session length (seconds) |
| `inter_action_variance` | Variance in time between consecutive actions |
| `actions_per_session` | Count of discrete actions/tool calls |
| `batch_size_mean` | Average number of actions fired within a 2s window |
| `idle_ratio` | Fraction of session in gaps that are outliers vs. that session's own typical cadence (see `agent_harness/features.py` for the fix history) |
| `tool_diversity` | Number of distinct tools/APIs called |

## Quickstart

```bash
pip install -r requirements.txt
python src/simulator.py          # generates data/sessions.csv
python src/evaluate.py           # trains classifier, compares vs baseline,
                                  # writes results/metrics.json + confusion matrices
```

## Known limitation (read before citing results)

The current dataset is **synthetic** — agent-compromise sessions are generated
from a behavioral model, not from a real prompt-injection attack against a
live tool-calling agent. Treat early results as a proof-of-concept for the
method, not a final finding. Next step: replace the synthetic
agent-compromised generator with logs from an actual injected LangChain/MCP
agent (see `src/simulator.py::TODO`).

## Roadmap

- [x] Synthetic session simulator
- [x] Baseline rule-based detector
- [x] Lightweight classifier + evaluation
- [x] Real-agent injection harness (`agent_harness/`), fully wired to Claude API and free Groq API -- see `agent_harness/README.md`
- [x] Second baseline: Isolation Forest (unsupervised, trained on assumed-normal sessions only)
- [x] Week 4: error analysis (`src/error_analysis.py`) + combined-dataset comparison (`src/build_combined_dataset.py`) -- see `results/error_analysis.md` and `results/dataset_comparison.md`
- [x] Recalibrate `agent_loop.py`'s latency model (real wall-clock timing for groq/real backends) -- see `results/dataset_comparison.md`
- [x] Add multi-tool scope-creep injection scenarios (`SCOPE_CREEP_TICKETS`) alongside narrow single-action ones
- [x] Test a second, longer-horizon agent scenario (5-ticket batch) -- action density converges toward human levels
- [x] Fix `idle_ratio`'s definition (self-calibrating per-session threshold instead of a fixed constant) -- resolves the hypothesis check above, surfaces an identity-shortcut caveat to watch for
- [ ] Run `--backend groq` for genuinely model-driven compromise decisions, re-run all comparisons, and specifically re-check whether `idle_ratio` still discriminates once real API jitter exists
- [ ] Write up findings as an article + local meetup talk

## Week 4: error analysis + dataset comparison

```bash
cd src && python error_analysis.py            # results/error_analysis.md + misclassified_sessions.csv
python build_combined_dataset.py               # data/combined_sessions.csv (real agent data + synthetic humans)
python evaluate.py --data combined_sessions.csv --out metrics_combined.json
```

Final headline findings (from `MockVulnerableBackend` harness data, all
fixes applied -- re-check once using `--backend groq`):

- **Threshold rules: 0% agent recall, 89.3% human recall.** Not a bug -- their `actions_per_session` cutoff (18.8, fit on human data only) sits above every agent session's actual maximum (18.0). Agents operate on a different absolute scale than the human data these rules were calibrated on.
- **Classifier: 55.8% agent recall, 86.0% human recall.** Lower than an earlier interim number (98.6%) that turned out to be partly riding on `idle_ratio` being a near-constant per identity type before the fix below -- see the caveat in `results/dataset_comparison.md` for why the corrected, lower number is the more trustworthy one.
- **Isolation Forest: 10.6% agent recall, 92.0% human recall.**
- **`idle_ratio` bug fixed**: originally counted LLM "thinking time" as idleness, inflating with every extra step. Fixed to a per-session adaptive threshold -- agent `idle_ratio` is now correctly ~0.0 (vs. humans' 0.30), confirming that part of the original hypothesis. But because it's now a near-constant for agents, it risks acting as an identity-type shortcut rather than genuine compromise signal -- worth re-checking once real API jitter exists.

## Week 2: real-agent harness

`agent_harness/` runs an actual tool-calling agent loop against real indirect
prompt injection payloads (not hand-scripted "bad" behavior). Three backends:

```bash
python -m agent_harness.run_harness                       # mock: free, no key needed
python -m agent_harness.run_harness --backend groq         # FREE real results -- no credit card
python -m agent_harness.run_harness --backend real         # paid Claude API
```

**No budget needed**: get a free Groq key (no credit card) at
console.groq.com, then `export GROQ_API_KEY="..."` and run with
`--backend groq`. See `agent_harness/README.md` for why Groq's open-weight
models are actually a good methodological fit here, not just a free
workaround, and for exactly what's real vs. still modeled at each stage.

## Week 3: second baseline (Isolation Forest)

`src/baseline_iforest.py` adds an unsupervised anomaly detector, trained
only on sessions assumed normal at deploy time (no compromise labels used
 during fitting) -- a more realistic SOC scenario than the fully-supervised
classifier. `src/evaluate.py` reports all three detectors
(`baseline_rules`, `lightweight_classifier`, `isolation_forest`)
side by side, broken out by identity type, in `results/metrics.json`.

## License

MIT
