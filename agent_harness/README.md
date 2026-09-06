# Real-Agent Injection Harness

Replaces the synthetic `agent_compromised` generator in `src/simulator.py`
with telemetry from an actual tool-calling agent loop running against real
indirect prompt injection payloads.

## Three backends

| Backend | Cost | What you get |
|---|---|---|
| `mock` (default) | Free, no key, no network | Real control-flow structure, scripted compliance decision. Good for testing the harness itself. |
| `groq` | **Free**, no credit card | Real open-weight model (Llama 3.3 70B by default) making genuine decisions. Recommended for real results at zero cost. |
| `real` | Paid | Real Claude API. |

## What's real vs. still modeled, by backend

| Aspect | mock | groq / real |
|---|---|---|
| Tool-calling control flow | Real | Real |
| Injection payloads | Real | Real |
| Ground-truth compromise label | Real | Real |
| Whether the model falls for the injection | **Scripted** (tunable `compliance_rate`) | **Genuinely decided by the model** |
| Timing / latency between actions | Modeled (see `LATENCY_MODEL_SECONDS` in `agent_loop.py`) | Modeled (same placeholder -- swap for real round-trip timing as a next step) |

**The honest headline finding from `mock` data is about the harness's control-flow structure, not real LLM safety behavior.** Use `groq` or `real` for anything you'd actually publish or cite.

## Run it

```bash
python -m agent_harness.run_harness                       # mock: free, no key
python -m agent_harness.run_harness --backend groq         # FREE real results -- get a key at console.groq.com
python -m agent_harness.run_harness --backend real         # paid -- get a key at platform.claude.com
```

Get a Groq key with no credit card at **console.groq.com**, then:
```bash
export GROQ_API_KEY="your-key-here"
python -m agent_harness.run_harness --backend groq
```

Writes `data/real_agent_sessions.csv`, tagged with `source=harness_<backend>`
and `backend=<ClassName>` so mock, Groq, and Claude runs are never silently
conflated with each other or with the fully synthetic data.

## Why Groq is a good fit here, not just a free workaround

Open-weight models (Llama, Mixtral, etc.) typically carry lighter
instruction-hierarchy/safety tuning than frontier closed models like
Claude. That means they're more likely to actually comply with an injected
instruction -- which is exactly what you need to get genuine, non-trivial
compromised examples. If you later add `--backend real` results and find
Claude refuses almost everything while Llama complies noticeably more
often, that's not a bug in the comparison -- that's a legitimate,
publishable finding about model-tier vulnerability differences, and a
natural extension of the original research question.

## Next steps

- Run `--backend groq` and compare its compromise rate and behavioral
  features against the `mock` data above -- report the gap, don't hide it.
- Add more ticket templates and injection phrasings -- 3 templates validates
  the harness end-to-end, not enough to publish from.
- If budget allows later, add `--backend real` results to compare a
  frontier model's resistance against Groq's open-weight models directly.
- Once real-backend data exists, compare it against `data/sessions.csv`'s
  synthetic `agent_compromised` class: if the behavioral features diverge a
  lot, that's evidence the synthetic model in `src/simulator.py` needs
  recalibrating before it's used beyond a proof-of-concept.
