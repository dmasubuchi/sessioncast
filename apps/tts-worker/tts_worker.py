"""TTS Worker — FastAPI service that synthesizes audio for a SessionCast episode.

Receives Pub/Sub push for `status == "script_ready"`, downloads script.json from
GCS, synthesizes each line (VOICEVOX for くくり, ElevenLabs IVC for Matthew), merges
into audio.wav, and uploads back to GCS.

Environment variables:
    GCP_PROJECT         — GCP project ID (required)
    VOICEVOX_URL        — VOICEVOX service URL, default http://localhost:50021
    VOICEVOX_SPEAKER_ID — VOICEVOX speaker ID for くくり, default 1
    ELEVENLABS_API_KEY  — ElevenLabs API key (optional; falls back to Secret Manager)
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

import httpx
from elevenlabs.client import ElevenLabs
from fastapi import FastAPI, HTTPException, Request
from google.cloud import firestore, pubsub_v1, secretmanager, storage
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

GCP_PROJECT = os.environ["GCP_PROJECT"]
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://localhost:50021")
VOICEVOX_SPEAKER_ID = int(os.environ.get("VOICEVOX_SPEAKER_ID", "1"))
MEDIA_BUCKET = f"{GCP_PROJECT}-media"
ELEVENLABS_VOICE_SECRET = f"projects/{GCP_PROJECT}/secrets/sessioncast-matthew-elevenlabs-voice-id/versions/latest"
PIPELINE_TOPIC = f"projects/{GCP_PROJECT}/topics/sessioncast-pipeline-events"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# Allowlist for episode_id values (prevents path traversal)
_EPISODE_ID_RE = re.compile(r"^[a-z0-9\-]{1,80}$")

app = FastAPI()
_executor = ThreadPoolExecutor(max_workers=8)

# Cached on first use
_elevenlabs_voice_id_cache: Optional[str] = None
_elevenlabs_client_cache: Optional[ElevenLabs] = None


@dataclass
class ScriptLine:
    index: int
    speaker: str  # "kukuri" or "matthew"
    text: str
    pause_after_ms: int = 300


def _get_elevenlabs_voice_id() -> str:
    global _elevenlabs_voice_id_cache
    if _elevenlabs_voice_id_cache is None:
        sm = secretmanager.SecretManagerServiceClient()
        resp = sm.access_secret_version(request={"name": ELEVENLABS_VOICE_SECRET})
        _elevenlabs_voice_id_cache = resp.payload.data.decode("utf-8")
    return _elevenlabs_voice_id_cache


def _get_elevenlabs_client() -> ElevenLabs:
    global _elevenlabs_client_cache
    if _elevenlabs_client_cache is None:
        api_key = os.environ.get("ELEVENLABS_API_KEY") or _get_secret("sessioncast-elevenlabs-api-key")
        _elevenlabs_client_cache = ElevenLabs(api_key=api_key)
    return _elevenlabs_client_cache


def _get_secret(secret_id: str) -> str:
    sm = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT}/secrets/{secret_id}/versions/latest"
    return sm.access_secret_version(request={"name": name}).payload.data.decode("utf-8")


def _synthesize_voicevox(text: str) -> bytes:
    with httpx.Client(base_url=VOICEVOX_URL, timeout=30) as client:
        query_resp = client.post(
            "/audio_query",
            params={"text": text, "speaker": VOICEVOX_SPEAKER_ID},
        )
        query_resp.raise_for_status()
        synth_resp = client.post(
            "/synthesis",
            params={"speaker": VOICEVOX_SPEAKER_ID},
            content=query_resp.content,
            headers={"Content-Type": "application/json"},
        )
        synth_resp.raise_for_status()
        return synth_resp.content


def _synthesize_elevenlabs(text: str) -> bytes:
    client = _get_elevenlabs_client()
    voice_id = _get_elevenlabs_voice_id()
    audio_chunks = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=ELEVENLABS_MODEL,
        output_format="pcm_24000",
    )
    raw_pcm = b"".join(audio_chunks)
    # Wrap raw PCM (24kHz, 16-bit, mono) in a WAV header via pydub
    segment = AudioSegment(raw_pcm, sample_width=2, frame_rate=24000, channels=1)
    buf = io.BytesIO()
    segment.export(buf, format="wav")
    return buf.getvalue()


def _synthesize_line(line: ScriptLine) -> bytes:
    if line.speaker == "kukuri":
        wav_bytes = _synthesize_voicevox(line.text)
    elif line.speaker == "matthew":
        wav_bytes = _synthesize_elevenlabs(line.text)
    else:
        log.warning("Unknown speaker %s, skipping line %d", line.speaker, line.index)
        return b""

    segment = AudioSegment.from_wav(io.BytesIO(wav_bytes))
    if line.pause_after_ms > 0:
        silence = AudioSegment.silent(duration=line.pause_after_ms)
        segment = segment + silence

    buf = io.BytesIO()
    segment.export(buf, format="wav")
    return buf.getvalue()


def _merge_wav_files(wav_list: list[bytes]) -> bytes:
    combined = AudioSegment.empty()
    for wav_bytes in wav_list:
        if wav_bytes:
            combined += AudioSegment.from_wav(io.BytesIO(wav_bytes))
    buf = io.BytesIO()
    combined.export(buf, format="wav")
    return buf.getvalue()


def _download_script(episode_id: str) -> list[ScriptLine]:
    gcs = storage.Client()
    blob = gcs.bucket(MEDIA_BUCKET).blob(f"episodes/{episode_id}/script.json")
    data = json.loads(blob.download_as_text())
    return [ScriptLine(**line) for line in data["lines"]]


def _upload_audio(episode_id: str, wav_bytes: bytes) -> None:
    gcs = storage.Client()
    blob = gcs.bucket(MEDIA_BUCKET).blob(f"episodes/{episode_id}/audio.wav")
    blob.upload_from_string(wav_bytes, content_type="audio/wav")
    log.info("Uploaded audio.wav for episode %s (%d bytes)", episode_id, len(wav_bytes))


def _update_firestore(episode_id: str) -> None:
    db = firestore.Client(project=GCP_PROJECT)
    db.collection("episodes").document(episode_id).update({"status": "rendering"})


def _publish_audio_ready(episode_id: str) -> None:
    publisher = pubsub_v1.PublisherClient()
    msg = json.dumps({"episode_id": episode_id, "status": "audio_ready"}).encode()
    publisher.publish(PIPELINE_TOPIC, msg)


def _process_episode(episode_id: str) -> None:
    log.info("Processing TTS for episode %s", episode_id)
    lines = _download_script(episode_id)

    # Synthesize all lines concurrently using the thread pool
    loop = asyncio.new_event_loop()
    futures = [loop.run_in_executor(_executor, _synthesize_line, line) for line in lines]
    wav_list = loop.run_until_complete(asyncio.gather(*futures))
    loop.close()

    audio_wav = _merge_wav_files(list(wav_list))
    _upload_audio(episode_id, audio_wav)
    _update_firestore(episode_id)
    _publish_audio_ready(episode_id)
    log.info("TTS complete for episode %s", episode_id)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


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

    # Run synchronous processing in thread pool so FastAPI stays responsive
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _process_episode, episode_id)
    return {"ok": True, "episode_id": episode_id}
