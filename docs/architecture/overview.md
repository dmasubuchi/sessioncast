# System Architecture Overview

![Full architecture diagram](../images/architecture-full.png)
<!-- 🍌 Nanobanana prompt: a detailed but beautiful infographic showing the full SessionCast pipeline from "notes" input to "YouTube" output, connected by glowing arrows, Google Cloud color palette (blue/white/yellow). 21:9 cinematic -->

## Design Philosophy

SessionCast is built on three constraints:

1. **Google Cloud only** — every component is a managed GCP service. No third-party platforms.
2. **Accuracy is measurable** — every step logs a score. Compound accuracy is always visible.
3. **Context rot is a first-class concern** — token budgets are monitored and enforced, not hoped for.

## Component Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  INPUT LAYER                                                        │
│  Conference notes (markdown) → submitted via PWA                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Firestore write
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER                                                │
│  Pub/Sub topic: sessioncast-episodes                                │
│  Cloud Run (agents service) receives Pub/Sub push                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  INTELLIGENCE LAYER — Vertex AI Agent Engine (ADK)                  │
│                                                                     │
│  SequentialAgent                                                    │
│  ├── ResearchAgent         (Gemini 2.5 Pro)                         │
│  │   └── tools: Memory Bank query, Google Search, InternalReasoning │
│  └── ScriptWriterAgent     (Gemini 2.5 Pro)                         │
│      └── tools: InternalReasoning, style_guide_lookup               │
│                                                                     │
│  Callbacks:                                                         │
│  ├── before_model: ContextRotMonitor (50k warn / 100k reset)        │
│  └── after_agent:  PipelineAccuracyTracker → BigQuery               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ script.json → GCS
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SYNTHESIS LAYER                                                    │
│  ├── VOICEVOX (Cloud Run Job, GPU L4)    → くくり voice              │
│  └── Chirp 3 Voice Clone (TTS API v1b1)  → Matthew voice            │
│  Output: per-line WAV files → merged audio.wav → GCS                │
└────────────────────────────┬────────────────────────────────────────┘
                             │ audio.wav + script.json
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RENDERING LAYER                                                    │
│  Remotion (Cloud Run Job, 8 vCPU / 16 GB)                           │
│  Output: video.mp4 → GCS                                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PUBLISHING LAYER                                                   │
│  ├── YouTube Data API v3   → video upload + metadata                │
│  ├── Note.com              → blog post (markdown → HTML)            │
│  └── GCS archive           → permanent episode storage              │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

| Step | Trigger | Output | Stored in |
|---|---|---|---|
| 1. Notes submitted | User clicks 生成開始 | Firestore episode doc | Firestore |
| 2. Research | Pub/Sub push | Enriched notes + citations | GCS |
| 3. Script writing | After research | `script.json` | GCS |
| 4. TTS | After script | Per-line WAV files | GCS |
| 5. Video render | After TTS | `video.mp4` | GCS |
| 6. Publish | After render | YouTube URL, Note.com URL | Firestore |

## Infrastructure as Code

Everything in `terraform/` — run `terraform apply` once to provision:
- Artifact Registry (Docker images)
- GCS buckets (media + build artifacts)
- Pub/Sub topic + subscription
- BigQuery dataset + episode_metrics table
- All required API enablement (13 APIs)
