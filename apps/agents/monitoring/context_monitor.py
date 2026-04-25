"""Context Rot Monitor — tracks token bloat and triggers compression."""

import math
from google.cloud import monitoring_v3

CONTEXT_ROT_THRESHOLD = 50_000   # warning
CONTEXT_ROT_CRITICAL  = 100_000  # forced reset

_monitoring_client = monitoring_v3.MetricServiceClient()


class ContextRotMonitor:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def check(self, context_tokens: int) -> str | None:
        """Check token count and return alert level if threshold exceeded."""
        self._write_metric(context_tokens)
        if context_tokens > CONTEXT_ROT_CRITICAL:
            return "CRITICAL"
        if context_tokens > CONTEXT_ROT_THRESHOLD:
            return "WARNING"
        return None

    def check_callback(self, callback_context) -> None:
        """ADK before_model_callback: check context before each LLM call."""
        tokens = getattr(callback_context, "token_count", 0)
        level = self.check(tokens)
        if level == "CRITICAL":
            # Signal ADK to compress context (raises to trigger ADK reset)
            raise RuntimeError(
                f"Context rot CRITICAL: {tokens} tokens in {self.agent_id}"
            )

    def _write_metric(self, context_tokens: int) -> None:
        # Cloud Monitoring custom metric
        # Metric path: custom.googleapis.com/sessioncast/context/token_count
        pass  # TODO: implement Cloud Monitoring write
