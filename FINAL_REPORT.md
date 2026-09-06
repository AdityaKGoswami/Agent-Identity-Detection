# Final Project Report: Agent Identity Detection

**Research question:** When an AI agent's credentials are compromised,
does it produce a behaviorally distinguishable signature from a
compromised human account — and can a lightweight detector catch what
today's identity-agnostic SIEM rules miss?

**Status:** Core research question answered with a positive, specific,
well-supported finding. One planned phase (real-model validation) remains
open pending API access outside this environment.

---

## 1. Method summary

- **Six behavioral features** per session: session duration, inter-action
  timing variance, actions per session, batch clustering, idle ratio, tool
  diversity.
- **Four session types**: human normal, human compromised, agent normal,
  agent compromised.
- **Four detectors compared**: identity-agnostic threshold rules
  (SIEM-style), identity-*aware* calibrated threshold rules, a supervised
  logistic regression classifier, and an unsupervised Isolation Forest.
- **Two data sources**: a synthetic simulator (hand-specified distributions
  encoding the original hypothesis) and a real tool-calling agent harness
  running genuine indirect prompt injection against a support-ticket
  handling task, with sensitive tool calls (data export, privilege
  escalation, audit-log deletion, exfiltration email) as ground-truth
  compromise signal — independent of the behavioral features being tested.

## 2. Timeline and what happened at each stage

| Phase | What was built | Key outcome |
|---|---|---|
| Week 1 | Synthetic simulator, threshold-rule baseline, supervised classifier | Established the pipeline and the identity-agnostic rule's apparent 100% agent recall (later shown to be a synthetic-data artifact) |
| Week 2 | Real-agent injection harness: genuine indirect prompt injection, pluggable backends (mock / free Groq / paid Claude) | Real control-flow structure and ground-truth labeling in place; timing still placeholder |
| Week 3 | Isolation Forest baseline, `evaluate.py --data` flag for multi-dataset comparison | Three-detector comparison pipeline complete |
| Week 4, round 1 | Fixed harness latency (real timing for real/Groq backends) and added scope-creep injection scenarios | Harness data moved substantially closer to realistic scale, but revealed the threshold rules' agent recall collapsing to 0% on real data |
| Week 4, round 2 | Added a 5-ticket batch (longer-horizon) scenario | Action density converged toward human levels; idle ratio got worse, not better — a real anomaly worth investigating rather than ignoring |
| Week 4, round 3 | Found and fixed the `idle_ratio` bug: it was counting LLM "thinking time" as idleness | Agent `idle_ratio` corrected to ~0.0 vs. humans' 0.30 — confirms the original hypothesis once the measurement itself was fixed |
| Week 4, round 4 | Caught a follow-on risk: a flat-constant feature is not free signal | Classifier's agent recall dropped from an inflated 98.6% to an honest 55.8% once retrained — reported the corrected number |
| Phase 2 (final) | Tested identity-aware calibration of the threshold rules; diagnosed why a first attempt barely helped; swapped in `tool_diversity` | Calibrated rules reached 33.7% agent recall (from 0%), closing roughly a third of the gap to the full classifier, using no ML — at a real cost to human recall (89.3% → 76.7%) |

## 3. Final results table

All figures from `MockVulnerableBackend` harness data (scripted compliance,
not a real model's judgment — see Section 5).

| Detector | Agent recall | Human recall | Notes |
|---|---|---|---|
| Identity-agnostic threshold rules | 0% | 89.3% | Cutoff fit on human data (18.8 actions/session) sits above every agent session's max (18.0) |
| Calibrated threshold rules (identity-aware + tool_diversity) | 33.7% | 76.7% | No ML — just per-identity calibration and the right feature |
| Lightweight supervised classifier | 55.8% | 86.0% | Best overall balance |
| Isolation Forest (unsupervised) | 10.6% | 92.0% | Trained on assumed-normal data only |

## 4. The headline finding

**Agent identities do show a distinguishable behavioral signature under
compromise. Identity-agnostic detection misses it anyway — not because the
signal is weak or absent, but because the detection is calibrated to human
absolute behavior, and agents operate on a categorically different scale.**

This was tested, not assumed: fixing a real measurement bug in `idle_ratio`
confirmed the underlying hypothesis, and a targeted calibration experiment
showed that identity-aware detection substantially closes the gap using
nothing more sophisticated than threshold rules — as long as the detector
both knows the identity type and uses features that actually carry
information for that identity type.

## 5. Known limitations (read before citing any number above)

- **All results are from `MockVulnerableBackend`**, a scripted-compliance
  stand-in, not a real model's judgment. This was a deliberate choice to
  make the harness runnable at zero cost, but it means "does the agent
  fall for the injection" was scripted, not observed. Real Groq or Claude
  API results are the necessary next step before treating any compromise
  *rate* as real — the compromise *detection* findings (recall/precision
  comparisons) are less dependent on this, but should still be re-checked.
- **Single task shape.** Every scenario is a support-ticket-handling agent.
  Generalization to other agent tasks (code review, internal tooling,
  longer-running autonomous workflows) is untested.
- **`idle_ratio` is now a near-constant for agents.** Confirmed useful for
  telling "agent vs. human" but not "compromised vs. normal" within the
  agent class. This may change with real API jitter — worth re-testing.
- **The calibrated-rules improvement assumes identity-type metadata is
  available at detection time.** That's realistic for most IAM setups but
  is a different assumption than the fully identity-agnostic original
  design — the comparison is honest about this trade, not a strictly fair
  swap-in.

## 6. What's next

1. **Run `--backend groq`** (free, no card required) to replace scripted
   compliance with genuine model decisions, and re-run every comparison in
   this report against that data.
2. **Extend scenarios beyond support tickets** to test whether the
   scale-mismatch finding and the calibration fix generalize to other
   agent task shapes.
3. **Write up and present**: this report is the raw material for an
   article, a conference/meetup talk, and continued LinkedIn build-in-public
   content — the honest bug-and-fix narrative throughout is stronger
   material than a clean result would have been.
4. **Longer-term**: use this body of work as a foundation for either a PhD
   application or a small applied tool (e.g. the compliance-evidence-mapping
   idea raised earlier in this project), and begin expanding research
   attention into adjacent AI-security domains.
