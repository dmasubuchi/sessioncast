# SessionCast

**Turn conference session notes into radio shows, blogs, and videos — fully automated on Google Cloud.**

> Presented at Google Cloud Next '27 as a 100% Google technology case study.

---

## What is SessionCast?

SessionCast is an open-source AI content pipeline that transforms your conference notes into:

- **Radio episodes** (dialogue-style audio + video)
- **Blog posts** (Note.com / Medium)
- **Session reports** (academic + press formats)

All processing runs on Google Cloud — no local GPU or heavy laptop required.

## Architecture

```
[Conference Notes]
       ↓
[Vertex AI Agent Engine]  ←→  [Memory Bank]
  Research Agent
  Editorial Agent
  Script Writer Agent       ←  XML-structured prompts
       ↓
[VOICEVOX / Chirp HD TTS]   ← Cloud Run Jobs (GPU)
       ↓
[Remotion Video Renderer]   ← Cloud Run Jobs (CPU)
       ↓
[YouTube / Note.com / GCS]  ← Publishing Hub
```

**Key Google Cloud services used:**
- Vertex AI Agent Engine (ADK) + Memory Bank
- Cloud Run Jobs (VOICEVOX GPU, Remotion CPU)
- Firebase + Firestore (PWA + real-time state)
- Cloud Trace + Monitoring + BigQuery (Observability)
- Google Managed MCP Servers (60+)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/dmasubuchi/sessioncast.git
cd sessioncast

# Set your GCP project
export GCP_PROJECT=your-project-id

# Deploy infrastructure
cd terraform && terraform apply

# Start the PWA locally
cd apps/pwa && npm install && npm run dev
```

## Project Structure

```
sessioncast/
├── apps/
│   ├── pwa/              # Firebase Hosting PWA (Next.js)
│   ├── agents/           # Vertex AI ADK agents
│   ├── tts-worker/       # VOICEVOX Cloud Run Job
│   ├── video-renderer/   # Remotion Cloud Run Job
│   └── functions/        # Cloud Functions (Genkit)
├── terraform/            # Infrastructure as Code
├── examples/             # Example configs & personas
├── docs/                 # Architecture docs
├── cloudbuild.yaml       # CI/CD pipeline
└── LICENSE               # MIT
```

## Observability

SessionCast implements the **Bad Outputs Compound** pattern from Google Cloud Next '26:

```
95% × 95% × 95% ≈ 85.7%  →  tracked per episode in BigQuery
```

- Cloud Trace: per-agent spans (1 episode = 1 root span)
- Context Rot monitoring: 50k token warning / 100k forced reset
- Looker Studio dashboard: pipeline health + content performance

## License

MIT — see [LICENSE](LICENSE)

---

*Built with ❤️ by [Papukaija LLC](https://papukaija.jp/) as a Google Cloud Next '27 showcase.*
