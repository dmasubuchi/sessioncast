"""Local polling worker — runs on your Mac with local VOICEVOX.

Polls Firestore every POLL_INTERVAL seconds for episodes with
status="script_ready", claims them atomically, and processes via tts_worker.

Usage:
    GCP_PROJECT=almeisan-adk-sandbox \
    VOICEVOX_URL=http://localhost:50021 \
    WORKER_ID=local-mac \
    python local_worker.py

VOICEVOX must be running locally before starting this script.
ElevenLabs lines are also processed (API key read from Secret Manager or env).
"""

import logging
import os
import time

from google.cloud import firestore

# tts_worker contains all processing logic
from tts_worker import GCP_PROJECT, WORKER_ID, _claim_episode, _process_episode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))


def _find_queued_episodes() -> list[str]:
    db = firestore.Client(project=GCP_PROJECT)
    snaps = (
        db.collection("episodes")
        .where("status", "==", "script_ready")
        .limit(5)
        .stream()
    )
    return [snap.id for snap in snaps]


def run_loop() -> None:
    log.info("Local worker started (worker_id=%s, poll=%ds)", WORKER_ID, POLL_INTERVAL)
    while True:
        try:
            episode_ids = _find_queued_episodes()
            if not episode_ids:
                log.debug("No queued episodes, waiting %ds...", POLL_INTERVAL)
            for episode_id in episode_ids:
                if _claim_episode(episode_id):
                    log.info("Claimed episode %s", episode_id)
                    _process_episode(episode_id)
                else:
                    log.info("Episode %s already taken", episode_id)
        except Exception:
            log.exception("Poll cycle error (will retry)")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_loop()
