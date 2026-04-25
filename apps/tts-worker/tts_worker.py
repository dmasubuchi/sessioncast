"""TTS Worker — FastAPI service (Cloud Run) + shared episode processing logic.

Pipeline:
  Phase 1: Agent generates script.json → Firestore status="script_ready"
  Phase 2: TTS worker (this) claims episode, synthesizes audio, uploads audio.wav
  Phase 3: Video worker picks up audio_ready episodes

Trigger modes:
  Cloud Run: POST /pubsub-push  (Pub/Sub push subscription)
  Local:     local_worker.py polls Firestore directly

Engine routing (per character in script.json):
  "voicevox"   → VOICEVOX HTTP API (Cloud Run service or local)
  "elevenlabs" → ElevenLabs IVC (eleven_multilingual_v2 by default)
  "chirp3"     → Google TTS Chirp 3 (future)

Environment variables:
    GCP_PROJECT         — GCP project ID (required)
    VOICEVOX_URL        — VOICEVOX service URL, default http://localhost:50021
    ELEVENLABS_API_KEY  — ElevenLabs API key (optional; falls back to Secret Manager)
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

import httpx
from elevenlabs.client import ElevenLabs
from fastapi import FastAPI, HTTPException, Request
from google.cloud import firestore, pubsub_v1, secretmanager, storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

GCP_PROJECT = os.environ["GCP_PROJECT"]
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://localhost:50021")
MEDIA_BUCKET = f"{GCP_PROJECT}-media"
PIPELINE_TOPIC = f"projects/{GCP_PROJECT}/topics/sessioncast-pipeline-events"
ELEVENLABS_VOICE_SECRET = f"projects/{GCP_PROJECT}/secrets/sessioncast-matthew-elevenlabs-voice-id/versions/latest"
ELEVENLABS_MODEL_DEFAULT = "eleven_multilingual_v2"

# Identifies this worker instance in Firestore
WORKER_ID = os.environ.get("WORKER_ID", f"local-{socket.gethostname()}")

# Allowlist for episode_id values (prevents path traversal)
_EPISODE_ID_RE = re.compile(r"^[a-z0-9\-]{1,80}$")

app = FastAPI()
_executor = ThreadPoolExecutor(max_workers=8)

# Module-level caches
_elevenlabs_client_cache: Optional[ElevenLabs] = None
_elevenlabs_voice_id_cache: Optional[str] = None


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ScriptLine:
    index: int
    speaker: str
    text: str
    pause_after_ms: int = 300


@dataclass
class CharacterConfig:
    engine: str  # "voicevox" | "elevenlabs"
    params: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Secret / client helpers
# ---------------------------------------------------------------------------

def _get_secret(secret_id: str) -> str:
    sm = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT}/secrets/{secret_id}/versions/latest"
    return sm.access_secret_version(request={"name": name}).payload.data.decode()


def _get_elevenlabs_client() -> ElevenLabs:
    global _elevenlabs_client_cache
    if _elevenlabs_client_cache is None:
        api_key = os.environ.get("ELEVENLABS_API_KEY") or _get_secret("sessioncast-elevenlabs-api-key")
        _elevenlabs_client_cache = ElevenLabs(api_key=api_key)
    return _elevenlabs_client_cache


def _get_elevenlabs_voice_id() -> str:
    global _elevenlabs_voice_id_cache
    if _elevenlabs_voice_id_cache is None:
        sm = secretmanager.SecretManagerServiceClient()
        resp = sm.access_secret_version(request={"name": ELEVENLABS_VOICE_SECRET})
        _elevenlabs_voice_id_cache = resp.payload.data.decode()
    return _elevenlabs_voice_id_cache


# ---------------------------------------------------------------------------
# Synthesis engines
# ---------------------------------------------------------------------------

def _synthesize_voicevox(text: str, speaker_id: int) -> bytes:
    with httpx.Client(base_url=VOICEVOX_URL, timeout=30) as client:
        query = client.post("/audio_query", params={"text": text, "speaker": speaker_id})
        query.raise_for_status()
        synth = client.post(
            "/synthesis",
            params={"speaker": speaker_id},
            content=query.content,
            headers={"Content-Type": "application/json"},
        )
        synth.raise_for_status()
        return synth.content


def _synthesize_elevenlabs(text: str, voice_id: Optional[str], model: Optional[str]) -> bytes:
    client = _get_elevenlabs_client()
    vid = voice_id or _get_elevenlabs_voice_id()
    mid = model or ELEVENLABS_MODEL_DEFAULT
    chunks = client.text_to_speech.convert(
        voice_id=vid,
        text=text,
        model_id=mid,
        output_format="pcm_24000",
    )
    raw_pcm = b"".join(chunks)
    segment = AudioSegment(raw_pcm, sample_width=2, frame_rate=24000, channels=1)
    buf = io.BytesIO()
    segment.export(buf, format="wav")
    return buf.getvalue()


def _synthesize_line(line: ScriptLine, char_configs: dict[str, CharacterConfig]) -> bytes:
    config = char_configs.get(line.speaker)
    if config is None:
        log.warning("No character config for speaker '%s', skipping line %d", line.speaker, line.index)
        return b""

    if config.engine == "voicevox":
        speaker_id = int(config.params.get("speaker_id", 1))
        wav_bytes = _synthesize_voicevox(line.text, speaker_id)
    elif config.engine == "elevenlabs":
        wav_bytes = _synthesize_elevenlabs(
            line.text,
            config.params.get("voice_id"),
            config.params.get("model"),
        )
    else:
        log.warning("Unknown engine '%s' for speaker '%s'", config.engine, line.speaker)
        return b""

    segment = AudioSegment.from_wav(io.BytesIO(wav_bytes))
    if line.pause_after_ms > 0:
        segment = segment + AudioSegment.silent(duration=line.pause_after_ms)
    buf = io.BytesIO()
    segment.export(buf, format="wav")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# GCS / Firestore / Pub/Sub
# ---------------------------------------------------------------------------

def _download_script(episode_id: str) -> tuple[list[ScriptLine], dict[str, CharacterConfig]]:
    gcs = storage.Client()
    blob = gcs.bucket(MEDIA_BUCKET).blob(f"episodes/{episode_id}/script.json")
    data = json.loads(blob.download_as_text())

    char_configs = {
        name: CharacterConfig(
            engine=cfg["engine"],
            params=cfg.get("params", {}),
        )
        for name, cfg in data.get("characters", {}).items()
    }
    lines = [ScriptLine(**ln) for ln in data["lines"]]
    return lines, char_configs


def _upload_audio(episode_id: str, wav_bytes: bytes) -> None:
    gcs = storage.Client()
    blob = gcs.bucket(MEDIA_BUCKET).blob(f"episodes/{episode_id}/audio.wav")
    blob.upload_from_string(wav_bytes, content_type="audio/wav")
    log.info("Uploaded audio.wav for %s (%d bytes)", episode_id, len(wav_bytes))


def _merge_wav_files(wav_list: list[bytes]) -> bytes:
    combined = AudioSegment.empty()
    for wav_bytes in wav_list:
        if wav_bytes:
            combined += AudioSegment.from_wav(io.BytesIO(wav_bytes))
    buf = io.BytesIO()
    combined.export(buf, format="wav")
    return buf.getvalue()


def _publish_audio_ready(episode_id: str) -> None:
    publisher = pubsub_v1.PublisherClient()
    msg = json.dumps({"episode_id": episode_id, "status": "audio_ready"}).encode()
    publisher.publish(PIPELINE_TOPIC, msg)


# ---------------------------------------------------------------------------
# Firestore task claiming (atomic, prevents double-processing)
# ---------------------------------------------------------------------------

def _claim_episode(episode_id: str) -> bool:
    """Atomically move episode status script_ready → tts_processing.
    Returns True if this worker successfully claimed the task."""
    db = firestore.Client(project=GCP_PROJECT)
    ep_ref = db.collection("episodes").document(episode_id)

    @firestore.transactional
    def _try_claim(transaction):
        snap = ep_ref.get(transaction=transaction)
        if not snap.exists or snap.get("status") != "script_ready":
            return False
        transaction.update(ep_ref, {
            "status": "tts_processing",
            "tts_worker": WORKER_ID,
            "tts_claimed_at": SERVER_TIMESTAMP,
        })
        return True

    return _try_claim(db.transaction())


def _mark_episode_done(episode_id: str) -> None:
    db = firestore.Client(project=GCP_PROJECT)
    db.collection("episodes").document(episode_id).update({
        "status": "audio_ready",
        "tts_completed_at": SERVER_TIMESTAMP,
    })


def _mark_episode_failed(episode_id: str, error: str) -> None:
    db = firestore.Client(project=GCP_PROJECT)
    db.collection("episodes").document(episode_id).update({
        "status": "tts_failed",
        "tts_error": error[:500],
    })


# ---------------------------------------------------------------------------
# Core episode processing
# ---------------------------------------------------------------------------

def _process_episode(episode_id: str) -> None:
    log.info("Processing TTS for episode %s (worker=%s)", episode_id, WORKER_ID)
    try:
        lines, char_configs = _download_script(episode_id)

        loop = asyncio.new_event_loop()
        futures = [
            loop.run_in_executor(_executor, _synthesize_line, line, char_configs)
            for line in lines
        ]
        wav_list = loop.run_until_complete(asyncio.gather(*futures))
        loop.close()

        audio_wav = _merge_wav_files(list(wav_list))
        _upload_audio(episode_id, audio_wav)
        _mark_episode_done(episode_id)
        _publish_audio_ready(episode_id)
        log.info("TTS complete for episode %s", episode_id)
    except Exception as exc:
        log.exception("TTS failed for episode %s", episode_id)
        _mark_episode_failed(episode_id, str(exc))
        raise


# ---------------------------------------------------------------------------
# FastAPI endpoints (Cloud Run / Pub/Sub push mode)
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "worker_id": WORKER_ID}


@app.post("/pubsub-push")
async def pubsub_push(request: Request):
    envelope = await request.json()
    try:
        raw = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        msg = json.loads(raw)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Bad Pub/Sub envelope: {exc}")

    if msg.get("status") != "script_ready":
        return {"skipped": True}

    episode_id = msg.get("episode_id", "")
    if not _EPISODE_ID_RE.match(episode_id):
        raise HTTPException(status_code=400, detail="Invalid episode_id")

    if not _claim_episode(episode_id):
        log.info("Episode %s already claimed, skipping", episode_id)
        return {"skipped": True, "reason": "already_claimed"}

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _process_episode, episode_id)
    return {"ok": True, "episode_id": episode_id}
