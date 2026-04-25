"""
SessionCast Content Pipeline Agents (Vertex AI ADK)

Episode pipeline: notes → script → TTS → video → publish
1 episode = 1 root trace span (Cloud Trace)
"""

import json
import logging
import os

import httpx
import google.auth
import google.auth.transport.requests
from google.adk.agents import Agent, SequentialAgent
from google.cloud import firestore, pubsub_v1
from opentelemetry import trace

from monitoring.context_monitor import ContextRotMonitor
from monitoring.accuracy_tracker import PipelineAccuracyTracker
from tools.internal_reasoning import InternalReasoningTool

log = logging.getLogger(__name__)
tracer = trace.get_tracer("sessioncast")
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

IMAGE_ANALYZER_URL = os.environ.get("IMAGE_ANALYZER_URL", "")


def _get_oidc_token(audience: str) -> str:
    """Get OIDC token for Cloud Run service-to-service auth."""
    credentials, _ = google.auth.default()
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    # For Cloud Run, use identity tokens
    from google.oauth2 import id_token
    return id_token.fetch_id_token(request, audience)


def call_image_analyzer(images: list[dict]) -> list[dict]:
    """Call the Image Analyzer A2A service.

    images: [{"gcs_uri": "gs://...", "type": "slide"|"atmosphere"|"general"}, ...]
    Returns list of analysis results.
    """
    if not IMAGE_ANALYZER_URL or not images:
        return []

    # Build A2A message parts: one text part for type + one file part per image
    parts = []
    # Use type of first image as the overall analysis type (simplification)
    analysis_type = images[0].get("type", "general")
    parts.append({"type": "text", "text": analysis_type})

    for item in images:
        gcs_uri = item["gcs_uri"]
        ext = gcs_uri.rsplit(".", 1)[-1].lower() if "." in gcs_uri else "jpg"
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")
        parts.append({
            "type": "file",
            "file": {"uri": gcs_uri, "mimeType": mime_type},
        })

    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "id": "pipeline-req",
        "params": {
            "id": "pipeline-task",
            "message": {"role": "user", "parts": parts},
        },
    }

    headers = {"Content-Type": "application/json"}
    try:
        token = _get_oidc_token(IMAGE_ANALYZER_URL)
        headers["Authorization"] = f"Bearer {token}"
    except Exception:
        log.debug("No OIDC token available (local dev mode)")

    try:
        response = httpx.post(
            f"{IMAGE_ANALYZER_URL.rstrip('/')}/a2a",
            json=payload,
            headers=headers,
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()
        artifacts = result.get("result", {}).get("artifacts", [])
        if artifacts:
            text = artifacts[0]["parts"][0]["text"]
            return json.loads(text)
    except Exception as exc:
        log.warning("Image Analyzer A2A call failed: %s", exc)

    return []


def _fetch_episode_images(episode_id: str) -> list[dict]:
    """Read image metadata from Firestore episode document."""
    doc = db.collection("episodes").document(episode_id).get()
    if not doc.exists:
        return []
    return doc.get("images") or []


def _build_image_context(analyses: list[dict]) -> str:
    """Format image analysis results into a context block for the Research Agent."""
    if not analyses:
        return ""
    lines = ["\n\n## 📷 セッション写真の解析結果\n"]
    for item in analyses:
        atype = item.get("analysis_type", "general")
        idx = item.get("index", "?")
        if "error" in item:
            lines.append(f"- 写真{idx}: 解析失敗 ({item['error']})")
            continue
        if atype == "slide":
            title = item.get("title", "不明")
            points = item.get("key_points", [])
            context = item.get("speaker_context", "")
            lines.append(f"- スライド{idx}「{title}」: {', '.join(points)}。{context}")
        elif atype == "atmosphere":
            scene = item.get("scene", "")
            radio_desc = item.get("radio_description", "")
            lines.append(f"- 雰囲気写真{idx}: {scene} → ラジオ用: 「{radio_desc}」")
        else:
            desc = item.get("description", item.get("radio_description", ""))
            lines.append(f"- 写真{idx}: {desc}")
    return "\n".join(lines)


RESEARCH_AGENT_PROMPT = """
<role>
  Research agent for SessionCast. Extract key facts and insights from session notes.
  Focus on: technical announcements, speaker quotes, actionable takeaways.
  When image analysis context is provided, incorporate visual observations into the research.
</role>
<taskflow>
  <step id="1">Identify 3-5 key points from the notes and any image analysis</step>
  <step id="2">Verify facts using Google Search if needed</step>
  <step id="3">Return structured JSON: {key_points, quotes, context, atmosphere_notes}</step>
</taskflow>
"""

SCRIPT_WRITER_PROMPT = """
<role>
  Dialogue script writer for SessionCast radio episodes.
  Write natural conversation between two hosts discussing the session content.
</role>
<persona>
  Host A: Enthusiastic, asks clarifying questions. Uses "なるほど！", "そういうことか".
  Host B: Analytical, gives structured explanations. Uses "つまり〜", "ポイントは3つ".
</persona>
<taskflow>
  <step id="1">Call internal_agent_reasoning before structuring the episode</step>
  <step id="2">Write opening (hook), body (3 acts), closing (call-to-action)</step>
  <step id="3">Run Actionability Test: can a new listener understand the value?</step>
</taskflow>
<trigger condition="before_body_writing">
  <action>Call internal_agent_reasoning tool</action>
</trigger>
"""


def build_episode_pipeline(series_id: str, episode_id: str) -> SequentialAgent:
    """Build a full episode pipeline agent for a given series."""
    context_monitor = ContextRotMonitor(agent_id=f"{series_id}/{episode_id}")
    accuracy_tracker = PipelineAccuracyTracker(episode_id=episode_id)

    research_agent = Agent(
        name="research_agent",
        model="gemini-2.5-pro",
        instruction=RESEARCH_AGENT_PROMPT,
        tools=[InternalReasoningTool()],
    )

    script_writer = Agent(
        name="script_writer",
        model="gemini-2.5-pro",
        instruction=SCRIPT_WRITER_PROMPT,
        tools=[InternalReasoningTool()],
        before_model_callback=context_monitor.check_callback,
    )

    return SequentialAgent(
        name=f"episode_pipeline_{episode_id}",
        sub_agents=[research_agent, script_writer],
        after_agent_callback=accuracy_tracker.record_callback,
    )


async def run_episode(notes: str, series_id: str, episode_id: str) -> dict:
    """Entry point: run the full episode pipeline with tracing."""
    with tracer.start_as_current_span("episode_pipeline") as span:
        span.set_attribute("series_id", series_id)
        span.set_attribute("episode_id", episode_id)
        span.set_attribute("notes_length", len(notes))

        # Fetch and analyze any uploaded images via A2A
        episode_images = _fetch_episode_images(episode_id)
        image_context = ""
        if episode_images:
            log.info("Analyzing %d image(s) for episode %s", len(episode_images), episode_id)
            analyses = call_image_analyzer(episode_images)
            image_context = _build_image_context(analyses)
            span.set_attribute("image_count", len(episode_images))

        enriched_notes = notes + image_context

        pipeline = build_episode_pipeline(series_id, episode_id)

        # TODO: replace with actual ADK session runner when API stabilizes
        result = await pipeline.run_async(enriched_notes)

        span.set_attribute("compound_accuracy",
                           PipelineAccuracyTracker(episode_id).compound_accuracy)

        # Notify downstream (TTS worker) via Pub/Sub
        publisher.publish(
            "projects/{project}/topics/sessioncast-pipeline-events".format(
                project="almeisan-adk-sandbox"
            ),
            data=f'{{"episode_id":"{episode_id}","status":"script_ready"}}'.encode(),
        )

        return result
