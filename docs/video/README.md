# Video Renderer: Remotion on Cloud Run

![Video renderer illustration](../images/video-renderer.png)
<!-- 🍌 Nanobanana prompt: a filmstrip being rendered in a futuristic server room, progress bar at 87%, Cloud Run logo subtly visible. 16:9 -->

## Overview

SessionCast renders podcast-style videos using **Remotion** — a framework for creating videos programmatically in React.

Rendering runs as a **Cloud Run Job** (CPU-only, 8 vCPU / 16 GB RAM). No GPU needed for video composition.

## What the video looks like

- Waveform animation synced to audio
- Host name + current line displayed
- Episode title card intro / outro
- Chapter markers matching the script sections

## Cloud Run Job Configuration

```yaml
# cloud-run-job spec
cpu: 8
memory: 16Gi
timeout: 3600s  # 1-hour max render
```

Large CPU allocation is intentional — Remotion parallelizes frame rendering across all available cores.

## Input / Output

| Item | Location |
|---|---|
| Input audio | `gs://${GCP_PROJECT}-media/episodes/{id}/audio.wav` |
| Input script | `gs://${GCP_PROJECT}-media/episodes/{id}/script.json` |
| Output video | `gs://${GCP_PROJECT}-media/episodes/{id}/video.mp4` |

## Files

```
apps/video-renderer/
├── src/
│   ├── Root.tsx        # Remotion composition root
│   ├── Episode.tsx     # Main episode composition
│   └── Waveform.tsx    # Audio-synced waveform
├── Dockerfile
└── package.json
```
