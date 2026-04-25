# SessionCast — Setup Guide

**[🇯🇵 日本語版セットアップガイド](SETUP.ja.md)**

For forking this repo and running your own conference radio pipeline.

---

## Prerequisites

| Item | Details |
|---|---|
| Google Cloud project | Billing enabled |
| APIs to enable | Cloud Run, Cloud Build, Firestore, Pub/Sub, Secret Manager, Artifact Registry |
| ElevenLabs account | Starter plan or above (Instant Voice Cloning required) |
| Node.js 20+, Python 3.12+ | Local dev environment |
| `gcloud` CLI | Authenticated |
| `gh` CLI | For GitHub Actions setup |

---

## Step 1: Clone the repository

```bash
git clone https://github.com/dmasubuchi/sessioncast.git
cd sessioncast
export GCP_PROJECT=your-gcp-project-id
export GCP_REGION=asia-northeast1
```

---

## Step 2: Register your voice clone (one-time)

Replace Matthew's voice clone with your own.

### 2-1. Prepare a recording

```
reference.wav
  → Speak freely in your language (30 seconds to 2 minutes)
  → Quality: 24kHz, mono, 16-bit
  → Record in a quiet environment, no background noise
```

Convert from M4A if needed:
```bash
ffmpeg -i your_reference.m4a -ar 24000 -ac 1 -sample_fmt s16 apps/tts-worker/scripts/reference.wav
```

### 2-2. Register with ElevenLabs IVC

```bash
cd apps/tts-worker
pip install elevenlabs

python3 << 'EOF'
from elevenlabs.client import ElevenLabs
import os

client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
with open("scripts/reference.wav", "rb") as f:
    voice = client.voices.ivc.create(
        name="Your Name (SessionCast)",
        files=[("reference.wav", f, "audio/wav")],
    )
print("voice_id:", voice.voice_id)
EOF
```

### 2-3. Save to Secret Manager

```bash
# ElevenLabs API key
echo -n "your-api-key" | gcloud secrets create sessioncast-elevenlabs-api-key \
    --data-file=- --project="${GCP_PROJECT}"

# Voice clone ID from step 2-2
echo -n "YOUR_VOICE_ID" | gcloud secrets create sessioncast-matthew-elevenlabs-voice-id \
    --data-file=- --project="${GCP_PROJECT}"
```

---

## Step 3: GitHub Secrets and Variables

```bash
# Secrets (sensitive)
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --repo=YOUR_ORG/sessioncast
gh secret set GCP_SERVICE_ACCOUNT           --repo=YOUR_ORG/sessioncast
gh secret set FIREBASE_API_KEY              --repo=YOUR_ORG/sessioncast
gh secret set FIREBASE_APP_ID               --repo=YOUR_ORG/sessioncast
gh secret set FIREBASE_SERVICE_ACCOUNT      --repo=YOUR_ORG/sessioncast
gh secret set ANTHROPIC_API_KEY             --repo=YOUR_ORG/sessioncast

# Variables (non-sensitive)
gh variable set GCP_PROJECT   --body="${GCP_PROJECT}" --repo=YOUR_ORG/sessioncast
gh variable set GCP_REGION    --body="${GCP_REGION}"  --repo=YOUR_ORG/sessioncast
gh variable set FIREBASE_MESSAGING_SENDER_ID --body="..." --repo=YOUR_ORG/sessioncast
```

---

## Step 4: Local testing

### Start the PWA

```bash
cd apps/pwa
cp .env.local.example .env.local   # fill in Firebase config
npm install && npm run dev
# → http://localhost:3000
```

### Start the local TTS worker (VOICEVOX)

Start VOICEVOX separately (port 50021), then:

```bash
cd apps/tts-worker
pip install -r requirements.txt

GCP_PROJECT=your-project-id \
VOICEVOX_URL=http://localhost:50021 \
WORKER_ID=local-mac \
python local_worker.py
```

How the worker operates:
```
local_worker.py
    │
    ├─ poll Firestore every 30 seconds
    │
    ├─ find episodes with status="script_ready"
    │
    ├─ atomically claim the episode (prevents double-processing)
    │
    └─ synthesize TTS → upload audio.wav to GCS
```

---

## Step 5: Deploy to Cloud Run

Push to `main` branch to trigger automatic deployment:

```bash
git push origin main
# → GitHub Actions runs ci.yml
# → Cloud Build builds agents + tts-worker + image-analyzer images
# → Cloud Run deploys all three services
# → Firebase Hosting deploys PWA
```

---

## script.json format

The common interface between agents and the TTS Worker:

```
gs://{GCP_PROJECT}-media/episodes/{episode_id}/script.json
```

```json
{
  "episode_id": "my-conference-20260425-001",
  "characters": {
    "host1": {
      "engine": "voicevox",
      "params": { "speaker_id": 1 }
    },
    "host2": {
      "engine": "elevenlabs",
      "params": {
        "voice_id": "YOUR_VOICE_ID",
        "model": "eleven_multilingual_v2"
      }
    }
  },
  "lines": [
    { "index": 0, "speaker": "host1", "text": "Hello!", "pause_after_ms": 300 },
    { "index": 1, "speaker": "host2", "text": "Today's topic is...", "pause_after_ms": 500 }
  ]
}
```

**Engine options:**

| engine | Description |
|---|---|
| `"voicevox"` | VOICEVOX HTTP API (anime-style Japanese, free) |
| `"elevenlabs"` | ElevenLabs IVC (voice clone) |
| `"chirp3"` | Google TTS Chirp 3 (planned) |

---

## Image upload and analysis (A2A)

Upload conference photos from the PWA at `/upload`. The Image Analyzer A2A service (`sessioncast-image-analyzer`) handles:

- **slide** — extract title, key points, speaker context
- **atmosphere** — venue energy, crowd size, radio-ready scene description
- **general** — flexible analysis for any conference photo

The `IMAGE_ANALYZER_URL` environment variable is automatically injected into the agents service by the CI/CD pipeline after deployment.

---

## Troubleshooting

**Local authentication error:**
```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project ${GCP_PROJECT}
```

**VOICEVOX connection check:**
```bash
curl http://localhost:50021/speakers | head -c 100
```

**ElevenLabs PCM output note:**  
ElevenLabs `output_format="pcm_24000"` returns raw PCM with no WAV header. The TTS Worker wraps it automatically:
```python
segment = AudioSegment(raw_pcm, sample_width=2, frame_rate=24000, channels=1)
```

---

## Project structure

```
sessioncast/
├── apps/
│   ├── pwa/              # Next.js PWA (Firebase Hosting)
│   ├── agents/           # Vertex AI ADK agents
│   ├── tts-worker/       # TTS synthesis worker
│   │   ├── tts_worker.py      # Cloud Run FastAPI service
│   │   └── local_worker.py    # Local VOICEVOX polling worker
│   ├── image-analyzer/   # Image analysis A2A service
│   │   ├── main.py            # FastAPI + A2A endpoints
│   │   └── analyzer.py        # Gemini Vision logic
│   └── video-renderer/   # Remotion renderer (in progress)
├── .github/
│   └── workflows/
│       ├── ci.yml         # Cloud Build + Cloud Run + Firebase
│       └── pr-review.yml  # Gemini auto PR review
├── docs/
│   ├── SETUP.md           # This file (English)
│   ├── SETUP.ja.md        # Japanese setup guide
│   ├── README.ja.md       # Japanese README
│   └── images/            # Documentation images
└── examples/
    └── episode-0/         # Sample episode (meta demo)
```

---

## License

MIT — free to fork, modify, and use commercially.

*[← Back to README](../README.md)*
