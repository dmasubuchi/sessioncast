"""One-time enrollment script: uploads consent + reference audio to get a Chirp 3
voice cloning key, then stores it in Secret Manager.

Usage:
    python scripts/generate_voice_key.py \
        --consent consent.wav \
        --reference reference.wav \
        --project almeisan-adk-sandbox

Consent statement to record in consent.wav (Japanese):
    私はこの音声の所有者であり、Googleがこの音声を使用して
    音声合成モデルを作成することを承認します。
"""

import argparse
import base64
import re
import sys

import google.auth
import google.auth.transport.requests
import httpx
from google.cloud import secretmanager

SECRET_NAME = "sessioncast-matthew-voice-key"
TTS_ENDPOINT = (
    "https://texttospeech.googleapis.com/v1beta1/voices:generateVoiceCloningKey"
)


def _read_wav_as_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_access_token() -> str:
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


AUDIO_CONFIG = {"audio_encoding": "LINEAR16", "sample_rate_hertz": 24000}

# Consent statement must match what was recorded in consent.wav (Japanese)
CONSENT_SCRIPT_JA = (
    "私はこの音声の所有者であり、"
    "Googleがこの音声を使用して音声合成モデルを作成することを承認します。"
)


def generate_voice_cloning_key(consent_path: str, reference_path: str, project: str) -> str:
    payload = {
        "reference_audio": {
            "audio_config": AUDIO_CONFIG,
            "content": _read_wav_as_b64(reference_path),
        },
        "voice_talent_consent": {
            "audio_config": AUDIO_CONFIG,
            "content": _read_wav_as_b64(consent_path),
        },
        "consent_script": CONSENT_SCRIPT_JA,
        "language_code": "ja-JP",
    }
    resp = httpx.post(
        TTS_ENDPOINT,
        json=payload,
        headers={
            "Authorization": f"Bearer {_get_access_token()}",
            "x-goog-user-project": project,
        },
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    key = result.get("voiceCloningKey")
    if not key:
        raise RuntimeError(f"Unexpected response (no voiceCloningKey): {result}")
    return key


def save_to_secret_manager(project: str, key_value: str) -> None:
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project}"
    secret_path = f"{parent}/secrets/{SECRET_NAME}"

    # Create secret if it doesn't exist
    try:
        client.create_secret(
            request={
                "parent": parent,
                "secret_id": SECRET_NAME,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        print(f"Created secret: {SECRET_NAME}")
    except Exception:
        pass  # Already exists

    client.add_secret_version(
        request={"parent": secret_path, "payload": {"data": key_value.encode("utf-8")}}
    )
    print(f"Stored voiceCloningKey in Secret Manager: {secret_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enroll Matthew's voice for Chirp 3")
    parser.add_argument("--consent", required=True, help="Path to consent WAV file")
    parser.add_argument("--reference", required=True, help="Path to reference WAV file")
    parser.add_argument("--project", required=True, help="GCP project ID")
    args = parser.parse_args()

    # Validate episode_id-style project ID (basic sanity check)
    if not re.match(r"^[a-z0-9\-]+$", args.project):
        print("ERROR: project must be lowercase alphanumeric with hyphens only")
        sys.exit(1)

    print("Calling voices:generateVoiceCloningKey ...")
    key = generate_voice_cloning_key(args.consent, args.reference, args.project)
    print("voiceCloningKey received.")

    save_to_secret_manager(args.project, key)
    print("Done. Verify with:")
    print(
        f"  gcloud secrets versions access latest "
        f"--secret={SECRET_NAME} --project={args.project}"
    )


if __name__ == "__main__":
    main()
