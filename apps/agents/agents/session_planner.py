"""
Pre-event session planner agent.
Uses Gemini + google_search grounding to research sessions and speakers,
then outputs a prioritized schedule with pre-session notes.

Upgrade path: when Google Deep Research API is available, swap the
google_search tool for the Deep Research tool — rest of the code stays the same.
"""

import json
import os
import re
from typing import Optional

from google import genai
from google.genai import types

GCP_PROJECT = os.environ.get("GCP_PROJECT", "almeisan-adk-sandbox")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")

_PLANNER_PROMPT = """\
You are a conference session planning assistant for a tech professional.
Your job is to research sessions and speakers, then recommend a prioritized schedule.

Given the event data and the user's interests, for each session:
1. Identify what the speaker is known for (search if needed)
2. Assess how relevant this session is to the user's stated goals
3. Flag any schedule conflicts

Return a JSON object with this structure:
{
  "event_name": "...",
  "recommended_sessions": [
    {
      "rank": 1,
      "title": "...",
      "speaker": "...",
      "time": "...",
      "relevance_score": 0.0-1.0,
      "why": "one sentence reason",
      "pre_notes": "what to know before attending, questions to ask"
    }
  ],
  "conflicts": [
    {"time": "...", "option_a": "...", "option_b": "...", "recommendation": "..."}
  ],
  "skip_list": ["sessions that are not relevant, with brief reason"]
}

Be opinionated. The user cannot attend everything — help them choose.
"""


def plan_sessions(
    event_name: str,
    sessions_text: str,
    interests: list[str],
    goals: str,
    max_sessions: Optional[int] = None,
) -> dict:
    """
    Research sessions and return a prioritized schedule.

    Args:
        event_name:    Name of the conference (e.g. "Google Cloud Next '27")
        sessions_text: Raw session list — free text, CSV paste, or URL content
        interests:     List of topic tags (e.g. ["AI agents", "Gemini", "Cloud Run"])
        goals:         What the user wants to get out of this conference
        max_sessions:  Optional cap on how many sessions to recommend

    Returns:
        Structured dict with recommended_sessions, conflicts, skip_list
    """
    client = genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_REGION)

    cap_note = f"\nLimit recommendations to the top {max_sessions} sessions." if max_sessions else ""

    prompt = f"""{_PLANNER_PROMPT}

Event: {event_name}

Sessions:
{sessions_text}

My interests: {", ".join(interests)}
My goals for this event: {goals}
{cap_note}
"""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            # swap this tool for Deep Research API when available
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_mime_type="application/json",
        ),
    )

    raw = response.text or "{}"
    # Strip markdown code fences if model wraps the JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)
