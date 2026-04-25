"""
Review agent — reads accumulated session notes and proposes episode structure.
Streams the response as SSE for the PWA chat UI.
"""

import json
import os
from typing import AsyncIterator

from google import genai
from google.genai import types

GCP_PROJECT = os.environ.get("GCP_PROJECT", "almeisan-adk-sandbox")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")

_SYSTEM_PROMPT = """\
You are a podcast producer reviewing a person's conference notes.
Your job is to:
1. Summarize the key themes from all the notes
2. Propose how many episodes to create and what each episode should cover
3. If there are too many topics for one episode, suggest splitting into parts

Be direct and concise. Write in Japanese. Aim for 2-4 short paragraphs.

At the END of your response, output a JSON block like this (no markdown fences):
PROPOSED_EPISODES:
[{"title": "エピソードタイトル", "sessions": ["session1", "session2"], "notes": "combined notes text here"}]

This JSON will be parsed by the UI to show the confirmation card.
"""


async def stream_review(
    event_name: str,
    series_id: str,
    notes: str,
    message: str | None = None,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """
    Yield SSE-formatted lines.
    Each line: "data: <json>\n\n"
    Final line: "data: [DONE]\n\n"
    """
    client = genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_REGION)

    if message and history:
        # Follow-up message in existing conversation
        contents = []
        for msg in (history or []):
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["text"])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    else:
        # Initial review request
        user_prompt = f"イベント: {event_name}\nシリーズ: {series_id}\n\n---\n\n{notes}"
        contents = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]

    accumulated = ""

    async for chunk in await client.aio.models.generate_content_stream(
        model="gemini-2.5-pro",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.7,
        ),
    ):
        text = chunk.text or ""
        accumulated += text

        # Check if we've hit the PROPOSED_EPISODES marker
        if "PROPOSED_EPISODES:" in accumulated:
            # Split: narrative part and JSON part
            parts = accumulated.split("PROPOSED_EPISODES:", 1)
            narrative = parts[0]
            json_str = parts[1].strip()

            # Stream the narrative portion only
            yield f"data: {json.dumps({'text': text})}\n\n"

            # Try to parse the proposed episodes
            try:
                proposed = json.loads(json_str)
                yield f"data: {json.dumps({'proposed': proposed})}\n\n"
            except json.JSONDecodeError:
                pass  # JSON not complete yet, keep accumulating
        else:
            yield f"data: {json.dumps({'text': text})}\n\n"

    yield "data: [DONE]\n\n"
