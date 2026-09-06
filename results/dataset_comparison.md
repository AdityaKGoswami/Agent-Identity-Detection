# Synthetic vs. Real-Harness Data: What Changed After Fixing Latency and Scenarios

**Update (post-fix):** the two fixes from the first version of this doc
(real wall-clock timing for real/groq backends, chained multi-tool
scope-creep injections) closed much of the original gap -- but also
surfaced something more interesting than a calibration bug: **the core
research hypothesis doesn't hold in this harness's data.**

## The recalibration worked, directionally

| | Before fix | After fix | Synthetic assumption |
|---|---|---|---|
| Mean session duration (agent-compromised) | 4.7s | 11.3-15.6s | 175.5s |
| Mean tool diversity (scope-creep injection) | 5.0 | 7.0 | 9.04 |

Both moved substantially closer to the synthetic model's assumptions, and
the fully-supervised classifier's performance improved sharply as a result:

| Detector | Agent recall (synthetic) | Agent recall (combined, before fix) | Agent recall (combined, after fix) |
|---|---|---|---|
| Threshold rules | 100% | 0% | **0%** (unchanged -- see below) |
| Classifier | 98.7% | 81.8% | **98.6%** |
| Isolation Forest | 95.3% | 13.6% | **33.8%** |

## But the threshold-rules failure isn't a calibration bug -- it's the finding

The original hypothesis (see README) was: *agent identities show tighter
timing, near-zero idle time, and higher action density than humans, even
under compromise.* In this harness's actual data, the opposite is true:

| | Agent (harness) | Human (synthetic) |
|---|---|---|
| Mean actions/session | 4.9 | 18.6 |
| Mean idle ratio | 0.57 | 0.30 |

Real agents in this scenario take **fewer** actions and are **more** idle
than humans, not fewer and busier. The threshold rules (tuned to flag
"high action count + low idle" as compromised) structurally cannot catch
agent compromise here, because agent behavior sits on the opposite side of
every threshold from what the rule expects -- regardless of how well the
timing scale is calibrated.

## Why, and what it means

Two candidate explanations, both worth testing separately rather than
picking one:

1. **Task-shape artifact**: a single support-ticket resolution is a short,
   bounded task (4-7 tool calls). A longer-running or more open-ended
   agent task might show the higher-density pattern the hypothesis
   predicted. Worth testing with a second, longer-horizon scenario before
   concluding the hypothesis is simply wrong.
2. **`idle_ratio`'s definition may be capturing the wrong thing**: it
   currently counts LLM "thinking time" between tool calls as idle. For a
   human, idle time plausibly reflects genuine inactivity; for an agent,
   that same gap is the model actively generating a response. Whether that
   should count as "idle" is a modeling choice worth revisiting in
   `agent_harness/features.py`, not a settled fact.

## Why this is still a good result

A hypothesis that survives contact with real data by accident is weaker
evidence than one that's tested honestly and found to need revision. This
is a legitimate, citable finding either way: *"identity-agnostic threshold
rules fail to detect agent compromise, but not for the reason we
originally hypothesized -- the failure mode is structurally different
than assumed."* That's arguably a stronger paper/post than the original
hypothesis being simply confirmed.

## Update: testing the longer-horizon explanation directly

Added a batch scenario (`BATCH_*_TICKETS` in `documents.py`) where the agent
handles 5 tickets in one session instead of 1, to test explanation #1
above directly rather than leaving it as speculation.

| | Single-ticket task | Batch (5-ticket) task | Human baseline |
|---|---|---|---|
| Actions/session | 4.4 | **16.6** | 18.6 |
| Idle ratio | 0.55 | **0.76** | 0.30 |

**Mixed result, and it's more informative than a clean confirmation would
have been:**

- **Action density**: the longer-horizon task closes almost the entire gap
  with human behavior (16.6 vs. 18.6) -- explanation #1 (task-shape
  artifact) is largely correct for this feature. A single bounded ticket
  really was an unrepresentative task to draw conclusions from.
- **Idle ratio**: got *worse*, not better -- moving further from the
  "near-zero idle" hypothesis, not closer. This points at explanation #2:
  `idle_ratio` sums up "thinking time" between tool calls, so simply
  adding more LLM turns (more tickets to reason about) inflates it further
  regardless of how busy the agent actually is. The metric is measuring
  turn count, not idleness, once an agent makes many sequential decisions.

**Detector impact**: re-evaluating on the combined dataset with both
scenarios mixed in, the classifier's agent-compromise recall actually
*dropped* from 98.6% (single-scenario data) to 65.4% -- the earlier strong
number was partly an artifact of a narrower, easier data distribution.
Threshold rules remain at 0% agent recall regardless of task length,
confirming that failure is about *direction* (agents don't fit the "high
action + low idle = compromised" rule shape at all, at any horizon), not
about scale or task duration.

## Update: fixing `idle_ratio`'s definition

The original `idle_ratio` used a fixed 0.3s threshold -- any gap between
tool calls longer than that counted as "idle," which meant ordinary LLM
thinking time got counted as idleness, and the metric mostly just tracked
how many decision steps a session had.

**Fix** (`agent_harness/features.py`): a gap now only counts as idle if
it's markedly longer than *that session's own* typical cadence (3x its
median gap), not longer than a fixed constant. This works the same way
regardless of backend or timing regime, since it self-calibrates to
whatever latency the session actually produced.

**Result**: with the mock backend's data, `idle_ratio` now comes out to
**exactly 0.0 for all 660 harness sessions, with zero variance.** This is
the honest answer given the data -- the mock's modeled latency is drawn
from a bounded range with no rare long pauses built in, so under a
rhythm-relative definition, nothing ever looks anomalously idle. Taken at
face value, this actually now *supports* the original hypothesis's
"near-zero idle time" claim for agents, resolving the earlier contradiction
-- but see the caveat below before treating that as settled.

## Caveat: a fixed feature becomes an identity shortcut, not a compromise signal

Because `idle_ratio` is now a literal constant per identity type in this
dataset (0.0 for every agent row, variable 0.2-0.6 for human rows, since
`src/simulator.py`'s synthetic human data wasn't touched by this fix), the
classifier still assigns it a non-trivial coefficient (-1.15, second
strongest feature) when retrained on the combined dataset. That's not
evidence the feature is meaningfully separating compromised from normal
sessions -- it's evidence the model found a cheap way to distinguish
identity type from compromise status. A feature that's ~0 for every agent
regardless of compromise state can't discriminate compromise *within* the
agent class; it can only help distinguish "this is an agent" as a side effect.

**Why this matters going forward**: this exact shortcut will likely break
once real Groq/Claude timing data is used, since real API calls have natural
jitter (rate limiting, variable model load, network conditions) that will
introduce genuine non-zero variance into agent `idle_ratio`.
When that happens, re-check whether the classifier's reliance on
`idle_ratio` holds up, or whether it was quietly leaning on the mock
data's artificial cleanliness. **Recommended**: report classifier
performance both with and without `idle_ratio` once real backend data
exists, to separate genuine signal from an identity-type shortcut.

## Detector performance, final (post idle_ratio fix)

| Detector | Agent recall | Human recall |
|---|---|---|
| Threshold rules | 0% | 89.3% |
| Classifier | 55.8% | 86.0% |
| Isolation Forest | 10.6% | 92.0% |

Classifier agent recall dropped again (65.4% -> 55.8%) after this fix --
consistent with the caveat above: some of the earlier "performance" was
the model exploiting `idle_ratio`'s old scenario-correlated noise, not
genuine compromise signal. This is the right tradeoff: a less impressive
number that's more honestly earned from the remaining features
(`tool_diversity`, `actions_per_session`, `batch_size_mean`) is worth more
than an inflated one riding on a metric artifact.
