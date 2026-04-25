# Voice Synthesis: VOICEVOX + Chirp 3

![TTS worker illustration](../images/tts-voice-blend.png)
<!-- 🍌 Nanobanana prompt: two microphones side by side, one labeled "くくり" (anime style, soft), one labeled "Matthew" (realistic, warm). Sound waves blending in center. 16:9 -->

## Two Voices, Two Engines

SessionCast uses a hybrid TTS approach:

| Host | Engine | Style |
|---|---|---|
| くくり (Kukuri) | VOICEVOX | Japanese anime-style voice |
| Matthew | Chirp 3 Custom Voice Clone | Matthew's actual voice |

The `tts_worker.py` script routes each dialogue line to the correct engine based on the speaker label in the script.

## VOICEVOX

Runs as a **Cloud Run Job** with an NVIDIA L4 GPU.

- Docker image: `voicevox/voicevox_engine:nvidia-ubuntu20.04-latest`
- API: HTTP on port 50021 (`/audio_query` + `/synthesis`)
- No API key required — self-hosted

## Chirp 3: Instant Custom Voice

Matthew's voice is synthesized using Google's **Chirp 3 Instant Custom Voice** — available in the Text-to-Speech API v1beta1, no special preview access needed.

### Enrollment (one-time)

```bash
python scripts/generate_voice_key.py \
  --consent consent.wav \
  --reference reference.wav
```

This calls `POST /v1beta1/voices:generateVoiceCloningKey` and stores the returned `voiceCloningKey` in **Secret Manager** as `sessioncast-matthew-voice-key`.

**Consent statement (read aloud in consent.wav):**
> 私はこの音声の所有者であり、Googleがこの音声を使用して音声合成モデルを作成することを承認します。

### Synthesis

```python
voice=VoiceSelectionParams(
    voice_clone=VoiceCloneParams(voice_cloning_key=key)
)
```

## Files

```
apps/tts-worker/
├── tts_worker.py          # Route + synthesize all lines
├── scripts/
│   └── generate_voice_key.py  # One-time enrollment
├── requirements.txt
└── Dockerfile             # VOICEVOX GPU base image
```
