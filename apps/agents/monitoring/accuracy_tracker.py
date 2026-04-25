"""Pipeline Accuracy Tracker — implements 95%^3 = 85.7% compound tracking."""

import math
from datetime import datetime, timezone
from google.cloud import bigquery

_bq = bigquery.Client()
_TABLE = "sessioncast_observability.pipeline_accuracy"


class PipelineAccuracyTracker:
    def __init__(self, episode_id: str):
        self.episode_id = episode_id
        self.step_scores: list[float] = []

    def record_step(self, step_name: str, score: float) -> None:
        self.step_scores.append(score)
        _bq.insert_rows_json(_TABLE, [{
            "episode_id": self.episode_id,
            "step_name": step_name,
            "score": score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }])

    def record_callback(self, callback_context) -> None:
        """ADK after_agent_callback: record accuracy after each agent step."""
        agent_name = getattr(callback_context, "agent_name", "unknown")
        # Derive a score from the agent's output quality signals
        # Placeholder: replace with actual quality scoring logic
        score = getattr(callback_context, "quality_score", 0.95)
        self.record_step(agent_name, score)

    @property
    def compound_accuracy(self) -> float:
        """95% × 95% × 95% = 85.7% — compounded across all pipeline steps."""
        if not self.step_scores:
            return 1.0
        return math.prod(self.step_scores)

    def required_per_step(self, target: float) -> float:
        """Back-calculate per-step accuracy needed to reach target compound."""
        if not self.step_scores:
            return target
        return target ** (1 / len(self.step_scores))
