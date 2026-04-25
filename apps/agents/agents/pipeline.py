"""
SessionCast Content Pipeline Agents (Vertex AI ADK)

Episode pipeline: notes → script → TTS → video → publish
1 episode = 1 root trace span (Cloud Trace)
"""

from google.adk.agents import Agent, SequentialAgent
from google.cloud import firestore, pubsub_v1
from opentelemetry import trace

from monitoring.context_monitor import ContextRotMonitor
from monitoring.accuracy_tracker import PipelineAccuracyTracker
from tools.internal_reasoning import InternalReasoningTool

tracer = trace.get_tracer("sessioncast")
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

RESEARCH_AGENT_PROMPT = """
<role>
  Research agent for SessionCast. Extract key facts and insights from session notes.
  Focus on: technical announcements, speaker quotes, actionable takeaways.
</role>
<taskflow>
  <step id="1">Identify 3-5 key points from the notes</step>
  <step id="2">Verify facts using Google Search if needed</step>
  <step id="3">Return structured JSON: {key_points, quotes, context}</step>
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

        pipeline = build_episode_pipeline(series_id, episode_id)

        # TODO: replace with actual ADK session runner when API stabilizes
        result = await pipeline.run_async(notes)

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
