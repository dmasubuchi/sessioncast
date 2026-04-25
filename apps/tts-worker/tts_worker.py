"""TTS Worker — FastAPI service that synthesizes audio for a SessionCast episode.

Receives Pub/Sub push for `status == "script_ready"`, downloads script.json from
GCS, synthesizes each line (VOICEVOX for くくり, Chirp 3 for Matthew), merges into
audio.wav, and uploads back to GCS.

Environment variables:
    GCP_PROJECT       — GCP project ID (required)
    VOICEVOX_URL      — VOICEVOX service URL, default http://localhost:50021
    VOICEVOX_SPEAKER_ID — VOICEVOX speaker ID for くくり, default 1
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
from fastapi import FastAPI, HTTPException, Request
from google.cloud import firestore, pubsub_v1, secretmanager, storage
from google.cloud.texttospeech_v1beta1 import (
    AudioConfig,
    AudioEncoding,
    SynthesisInput,
    TextToSpeechClient,
    VoiceCloneParams,
    VoiceSelectionParams,
)
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

GCP_PROJECT = os.environ["GCP_PROJECT"]
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://localhost:50021")
VOICEVOX_SPEAKER_ID = int(os.environ.get("VOICEVOX_SPEAKER_ID", "1"))
MEDIA_BUCKET = f"{GCP_PROJECT}-media"
SECRET_NAME = f"projects/{GCP_PROJECT}/secrets/sessioncast-matthew-voice-key/versions/latest"
PIPELINE_TOPIC = f"projects/{GCP_PROJECT}/topics/sessioncast-pipeline-events"

# Allowlist for episode_id values (prevents path traversal)
_EPISODE_ID_RE = re.compile(r"^[a-z0-9\-]{1,80}$")

app = FastAPI()
_executor = ThreadPoolExecutor(max_workers=8)

# Cached on first use
_voice_key_cache: Optional[str] = None
_tts_client: Optional[TextToSpeechClient] = None


@dataclass
class ScriptLine:
    index: int
    speaker: str  # "kukuri" or "matthew"
    text: str
    pause_after_ms: int = 300


def _get_voice_cloning_key() -> str:
    global _voice_key_cache
    if _voice_key_cache is None:
        client = secretmanager.SecretManagerServiceClient()
        resp = client.access_secret_version(request={"name": SECRET_NAME})
        _voice_key_cache = resp.payload.data.decode("utf-8")
    return _voice_key_cache


def _get_tts_client() -> TextToSpeechClient:
    global _tts_client
    if _tts_client is None:
        _tts_client = TextToSpeechClient()
    return _tts_client


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


def _synthesize_chirp3(text: str) -> bytes:
    client = _get_tts_client()
    key = _get_voice_cloning_key()
    response = client.synthesize_speech(
        input=SynthesisInput(text=text),
        voice=VoiceSelectionParams(
            voice_clone=VoiceCloneParams(voice_cloning_key=key)
        ),
        audio_config=AudioConfig(audio_encoding=AudioEncoding.LINEAR16),
    )
    return response.audio_content


def _synthesize_line(line: ScriptLine) -> bytes:
    if line.speaker == "kukuri":
        wav_bytes = _synthesize_voicevox(line.text)
    elif line.speaker == "matthew":
        wav_bytes = _synthesize_chirp3(line.text)
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
