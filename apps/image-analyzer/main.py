"""SessionCast Image Analyzer — A2A-compatible Cloud Run service.

Exposes Gemini Vision analysis via the A2A (Agent-to-Agent) protocol.

A2A endpoints:
  GET  /.well-known/agent.json  — Agent Card (agent discovery)
  POST /a2a                     — A2A JSON-RPC task handler
  GET  /healthz                 — Health check

A2A request format (tasks/send):
  {
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "id": "req-001",
    "params": {
      "id": "task-001",
      "message": {
        "role": "user",
        "parts": [
          {"type": "text", "text": "slide"},
          {"type": "file", "file": {"uri": "gs://bucket/img.jpg", "mimeType": "image/jpeg"}}
        ]
      }
    }
  }

Analysis types (first text part): "slide" | "atmosphere" | "general"
"""

import logging
import os
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from analyzer import analyze_images

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SERVICE_URL = os.environ.get("SERVICE_URL", "https://sessioncast-image-analyzer.example.run.app")

app = FastAPI(title="SessionCast Image Analyzer", version="0.1.0")

AGENT_CARD = {
    "name": "SessionCast Image Analyzer",
    "description": (
        "Analyzes conference photos using Gemini Vision. "
        "Handles slide content extraction, atmosphere descriptions, "
        "and general conference scene analysis for radio episode scripts."
    ),
    "url": SERVICE_URL,
    "version": "0.1.0",
    "defaultInputModes": ["text/plain", "image/jpeg", "image/png", "image/webp"],
    "defaultOutputModes": ["application/json"],
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False,
    },
    "skills": [
        {
            "id": "analyze_slide",
            "name": "Analyze Presentation Slide",
            "description": "Extract title, key points, and speaker context from a slide photo",
            "inputModes": ["image/jpeg", "image/png"],
            "outputModes": ["application/json"],
        },
        {
            "id": "analyze_atmosphere",
            "name": "Analyze Conference Atmosphere",
            "description": (
                "Describe venue energy, crowd size, and generate a radio-ready "
                "scene description from atmosphere/reception/lunch photos"
            ),
            "inputModes": ["image/jpeg", "image/png"],
            "outputModes": ["application/json"],
        },
        {
            "id": "analyze_general",
            "name": "General Photo Analysis",
            "description": "Flexible analysis for any conference photo",
            "inputModes": ["image/jpeg", "image/png", "image/webp"],
            "outputModes": ["application/json"],
        },
    ],
}


@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "image-analyzer"}


@app.post("/a2a")
async def a2a_handler(request: Request):
    """A2A JSON-RPC 2.0 task handler."""
    body = await request.json()

    jsonrpc_id = body.get("id")
    method = body.get("method", "")

    if method not in ("tasks/send", "tasks/get"):
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": jsonrpc_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }, status_code=400)

    params = body.get("params", {})
    task_id = params.get("id") or str(uuid.uuid4())

    # tasks/get: status-only (we process synchronously, so always completed)
    if method == "tasks/get":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": jsonrpc_id,
            "result": {
                "id": task_id,
                "status": {"state": "unknown"},
            },
        })

    # tasks/send: extract images and analysis type from message parts
    message = params.get("message", {})
    parts = message.get("parts", [])

    analysis_type = "general"
    image_items = []

    for part in parts:
        ptype = part.get("type", "")
        if ptype == "text":
            text_val = part.get("text", "").strip().lower()
            if text_val in ("slide", "atmosphere", "general"):
                analysis_type = text_val
        elif ptype == "file":
            file_info = part.get("file", {})
            gcs_uri = file_info.get("uri", "")
            if gcs_uri.startswith("gs://"):
                image_items.append({"gcs_uri": gcs_uri, "type": analysis_type})

    if not image_items:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": jsonrpc_id,
            "error": {"code": -32602, "message": "No valid GCS image URIs found in request"},
        }, status_code=400)

    log.info("Analyzing %d image(s) as '%s' (task=%s)", len(image_items), analysis_type, task_id)

    try:
        results = analyze_images(image_items)
    except Exception as exc:
        log.exception("Analysis failed for task %s", task_id)
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": jsonrpc_id,
            "error": {"code": -32000, "message": str(exc)[:500]},
        }, status_code=500)

    import json
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": jsonrpc_id,
        "result": {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [
                {
                    "name": "image_analysis",
                    "parts": [{"type": "text", "text": json.dumps(results, ensure_ascii=False)}],
                }
            ],
        },
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
