"""Gemini Vision analysis logic — handles slide, atmosphere, and general photos."""

import json
import logging
import os
from typing import Literal

import vertexai
from vertexai.generative_models import GenerativeModel, Part

log = logging.getLogger(__name__)

GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_REGION = os.environ.get("GCP_REGION", "asia-northeast1")

AnalysisType = Literal["slide", "atmosphere", "general"]

_PROMPTS: dict[AnalysisType, str] = {
    "slide": """
You are analyzing a conference presentation slide.
Return ONLY valid JSON (no markdown fences):
{
  "title": "main topic or slide headline",
  "key_points": ["point 1", "point 2", "point 3"],
  "speaker_context": "what a presenter would likely say about this slide (1-2 sentences)",
  "data_or_charts": "description of any charts, graphs, numbers shown — null if none",
  "confidence": 0.95
}
""",
    "atmosphere": """
You are describing a conference atmosphere photo for a radio episode script.
Return ONLY valid JSON (no markdown fences):
{
  "scene": "one-sentence description of what's happening",
  "energy": "low | medium | high",
  "crowd_size": "small (<20) | medium (20-100) | large (100+) | unknown",
  "context_clues": ["clue 1 about the event", "clue 2"],
  "radio_description": "a vivid 1-2 sentence description suitable for reading on air in Japanese",
  "confidence": 0.90
}
""",
    "general": """
You are analyzing a conference photo for use in an audio/video episode.
Return ONLY valid JSON (no markdown fences):
{
  "description": "concise description of what's in the photo",
  "notable_elements": ["element 1", "element 2"],
  "radio_description": "a vivid 1-2 sentence description suitable for reading on air in Japanese",
  "suggested_use": "how this image context could be used in the episode",
  "confidence": 0.85
}
""",
}

_model_cache: dict[str, GenerativeModel] = {}


def _get_model() -> GenerativeModel:
    if "default" not in _model_cache:
        vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
        _model_cache["default"] = GenerativeModel("gemini-2.5-pro")
    return _model_cache["default"]


def analyze_image(gcs_uri: str, analysis_type: AnalysisType) -> dict:
    """Analyze a single GCS image and return structured JSON.

    Gemini reads GCS URIs natively — no download needed.
    """
    ext = gcs_uri.rsplit(".", 1)[-1].lower() if "." in gcs_uri else "jpg"
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    model = _get_model()
    image_part = Part.from_uri(gcs_uri, mime_type=mime_type)
    prompt = _PROMPTS.get(analysis_type, _PROMPTS["general"])

    response = model.generate_content([image_part, prompt])
    text = response.text.strip()

    # Strip optional markdown fences if model adds them
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        log.warning("Non-JSON response for %s, returning raw text", gcs_uri)
        result = {"raw": text, "confidence": 0.0}

    result["gcs_uri"] = gcs_uri
    result["analysis_type"] = analysis_type
    return result


def analyze_images(items: list[dict]) -> list[dict]:
    """Analyze multiple images. Each item: {"gcs_uri": str, "type": AnalysisType}."""
    results = []
    for idx, item in enumerate(items):
        gcs_uri = item["gcs_uri"]
        atype: AnalysisType = item.get("type", "general")
        try:
            result = analyze_image(gcs_uri, atype)
            result["index"] = idx
            results.append(result)
        except Exception as exc:
            log.exception("Failed to analyze %s", gcs_uri)
            results.append({
                "index": idx,
                "gcs_uri": gcs_uri,
                "analysis_type": atype,
                "error": str(exc)[:300],
                "confidence": 0.0,
            })
    return results
