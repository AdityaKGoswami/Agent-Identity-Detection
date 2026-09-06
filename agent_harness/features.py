"""
Turns a raw session (from agent_loop.run_session) into the same 6 features
used throughout the project, so this data is directly comparable to
src/simulator.py's synthetic output.
"""

import statistics


def compute_features(session):
    events = session["events"]
    duration = (session["end"] - session["start"]).total_seconds()

    if len(events) < 2:
        inter_action_variance = 0.0
    else:
        gaps = [
            (events[i]["t"] - events[i - 1]["t"]).total_seconds()
            for i in range(1, len(events))
        ]
        inter_action_variance = statistics.pvariance(gaps) if len(gaps) > 1 else 0.0

    actions_per_session = len(events)

    # batch_size_mean: for each event, how many events (incl. itself) fall
    # within a 2-second window centered on it.
    if events:
        batch_sizes = []
        for e in events:
            window = [
                other for other in events
                if abs((other["t"] - e["t"]).total_seconds()) <= 1.0
            ]
            batch_sizes.append(len(window))
        batch_size_mean = statistics.mean(batch_sizes)
    else:
        batch_size_mean = 0.0

    # idle_ratio (redefined -- see README "Hypothesis check" and
    # results/dataset_comparison.md): the original fixed 0.3s threshold
    # counted ordinary LLM "thinking time" between tool calls as idle,
    # which inflated the metric proportionally to how many decision steps
    # a session had -- measuring turn count, not actual inactivity.
    #
    # Fix: a gap only counts as idle if it's markedly longer than THIS
    # session's own typical action cadence (3x its median gap), not simply
    # longer than a fixed constant. Normal per-step latency -- whether
    # mocked, or real Groq/Claude round-trip time -- is then correctly
    # treated as active processing, not idleness, regardless of which
    # backend or timing regime produced it. Only gaps that stand out as
    # unusual relative to the session's own rhythm count as genuine idle
    # time.
    if len(events) >= 2 and duration > 0:
        median_gap = statistics.median(gaps)
        idle_threshold = max(0.05, median_gap * 3)
        idle_time = sum(max(0.0, g - idle_threshold) for g in gaps)
        idle_ratio = min(1.0, idle_time / duration)
    else:
        idle_ratio = 0.0

    tool_diversity = len({e["tool"] for e in events})

    return {
        "session_duration": round(duration, 3),
        "inter_action_variance": round(inter_action_variance, 4),
        "actions_per_session": actions_per_session,
        "batch_size_mean": round(batch_size_mean, 3),
        "idle_ratio": round(idle_ratio, 4),
        "tool_diversity": tool_diversity,
    }
