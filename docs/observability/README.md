# Observability: Traces, Accuracy, and Dashboards

![Observability dashboard illustration](../images/observability-dashboard.png)
<!-- 🍌 Nanobanana prompt: a Looker Studio dashboard on a large monitor showing compound accuracy trend, pipeline latency waterfall, and a glowing 91.2% accuracy badge. Dark theme. 16:9 -->

## The Core Insight: Bad Outputs Compound

From Google Cloud Next '26:

```
95% × 95% × 95% = 85.7%
```

A three-step pipeline where each step is 95% accurate delivers only 85.7% quality at the output. Chain five steps and you're at 77%.

SessionCast makes this **measurable and visible** so you can actually improve it.

## What We Track

### Per-Episode Compound Accuracy

Every agent step records a confidence score (0.0–1.0). `PipelineAccuracyTracker` computes:

```python
@property
def compound_accuracy(self) -> float:
    return math.prod(self.step_scores)

def required_per_step(self, target: float) -> float:
    return target ** (1 / len(self.step_scores))
```

To hit **90% compound accuracy** across 3 steps, each step needs ~96.5% accuracy individually.

### Cloud Trace: One Episode = One Root Span

Every episode generates a single root trace with child spans per agent:

```
[Episode: google-radio-ep42]          total: 4m 12s
  ├─ [ResearchAgent]                    1m 08s
  ├─ [ScriptWriterAgent]                2m 33s
  ├─ [TTSWorker: kukuri]                  18s
  ├─ [TTSWorker: matthew]                 22s
  └─ [VideoRenderer]                    1m 51s
```

Latency outliers are immediately visible in Cloud Trace Explorer.

### Context Rot Monitoring

Cloud Monitoring receives a custom metric whenever the context monitor fires:

- `sessioncast/context_rot_warning` — token count crossed 50k
- `sessioncast/context_rot_reset` — forced reset at 100k

Alert policies notify if a reset happens more than once per episode.

## BigQuery Schema

Every episode result is written to `sessioncast.episode_metrics`:

| Column | Type | Description |
|---|---|---|
| `episode_id` | STRING | Unique episode identifier |
| `series` | STRING | Radio series name |
| `compound_accuracy` | FLOAT | Final accuracy (0.0–1.0) |
| `step_scores` | ARRAY\<FLOAT\> | Per-step scores |
| `context_resets` | INTEGER | Times context was forced-reset |
| `total_duration_s` | INTEGER | Wall-clock pipeline time |
| `created_at` | TIMESTAMP | Episode completion time |

## Looker Studio Dashboard

Connected to the BigQuery table above. Tracks:

- **Compound accuracy trend** across all episodes (goal: stay above 90%)
- **Per-agent latency breakdown** — which step is the bottleneck?
- **Context rot frequency** — are prompts getting too long?
- **Series comparison** — which radio format produces better quality?

The plan is to walk into **Google Cloud Next '27** with 50+ episodes on this dashboard and say: *"Here's what the data shows."*
