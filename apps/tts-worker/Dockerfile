# VOICEVOX TTS Worker — Cloud Run Job (GPU: NVIDIA L4)
# Requires: Cloud Run with GPU support enabled in the region
FROM voicevox/voicevox_engine:nvidia-ubuntu20.04-latest

# VOICEVOX listens on port 50021 by default
EXPOSE 50021

# Health check for Cloud Run readiness probe
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s \
  CMD curl -f http://localhost:50021/version || exit 1
