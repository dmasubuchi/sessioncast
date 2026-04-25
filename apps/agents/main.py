"""
SessionCast Agent Service — FastAPI entrypoint for Vertex AI Agent Engine
Triggered via Cloud Run (HTTP) or Pub/Sub push subscription
"""

import os
import json
import asyncio
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

from agents.pipeline import run_episode

app = FastAPI(title="SessionCast Agent Service", version="0.1.0")

GCP_PROJECT = os.environ.get("GCP_PROJECT", "almeisan-adk-sandbox")
PUBSUB_TOPIC = f"projects/{GCP_PROJECT}/topics/sessioncast-pipeline-events"


class RunEpisodeRequest(BaseModel):
    notes: str
    series_id: str
    episode_id: str


@app.get("/healthz")
async def health():
    return {"status": "ok"}


@app.post("/run-episode")
async def run_episode_endpoint(req: RunEpisodeRequest):
    """Kick off the full episode pipeline for given notes."""
    try:
        result = await run_episode(
            notes=req.notes,
            series_id=req.series_id,
            episode_id=req.episode_id,
        )
        return {"status": "started", "episode_id": req.episode_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pubsub-push")
async def pubsub_push(request: Request):
    """Pub/Sub push endpoint — receives pipeline events from Firestore triggers."""
    envelope = await request.json()
    if not envelope or "message" not in envelope:
        raise HTTPException(status_code=400, detail="Invalid Pub/Sub message")

    message = envelope["message"]
    data = json.loads(
        __import__("base64").b64decode(message.get("data", "e30=")).decode()
    )

    episode_id = data.get("episode_id")
    status     = data.get("status")

    if status == "notes_ready" and episode_id:
        asyncio.create_task(
            run_episode(
                notes=data.get("notes", ""),
                series_id=data.get("series_id", "google-radio"),
                episode_id=episode_id,
            )
        )

    return {"status": "accepted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
