# SessionCast — セットアップガイド

フォークして自分のカンファレンスラジオを作りたい方向けのガイドです。

---

## 前提条件

| 項目 | 詳細 |
|---|---|
| Google Cloud プロジェクト | billing 有効 |
| 有効化が必要な API | Cloud Run, Cloud Build, Firestore, Pub/Sub, Secret Manager, Artifact Registry |
| ElevenLabs アカウント | Starter プラン以上（Instant Voice Cloning 対応） |
| Node.js 20+, Python 3.12+ | ローカル開発環境 |
| `gcloud` CLI | 認証済み |
| `gh` CLI | GitHub Actions 設定用 |

---

## Step 1: リポジトリのクローン

```bash
git clone https://github.com/dmasubuchi/sessioncast.git
cd sessioncast
export GCP_PROJECT=your-gcp-project-id
export GCP_REGION=asia-northeast1
```

---

## Step 2: 声クローンの登録（一回だけ）

あなた自身の声クローンを ElevenLabs に登録します。

### 2-1. 録音ファイルの準備

```
reference.wav
  → 自由な日本語スピーチ（30秒〜2分）
  → 品質: 24kHz, モノラル, 16bit
  → ノイズの少ない環境で録音
```

M4A から変換する場合:
```bash
ffmpeg -i your_reference.m4a -ar 24000 -ac 1 -sample_fmt s16 scripts/reference.wav
```

### 2-2. ElevenLabs IVC に登録

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

### 2-3. Secret Manager に保存

```bash
echo -n "your-api-key" | gcloud secrets create sessioncast-elevenlabs-api-key \
    --data-file=- --project="${GCP_PROJECT}"

# Step 2-2 で表示された voice_id
echo -n "YOUR_VOICE_ID" | gcloud secrets create sessioncast-matthew-elevenlabs-voice-id \
    --data-file=- --project="${GCP_PROJECT}"
```

---

## Step 3: GitHub Secrets と Variables

```bash
# 機密情報（Secrets）
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --repo=YOUR_ORG/sessioncast
gh secret set GCP_SERVICE_ACCOUNT           --repo=YOUR_ORG/sessioncast
gh secret set FIREBASE_API_KEY              --repo=YOUR_ORG/sessioncast
gh secret set FIREBASE_APP_ID               --repo=YOUR_ORG/sessioncast
gh secret set FIREBASE_SERVICE_ACCOUNT      --repo=YOUR_ORG/sessioncast
gh secret set ANTHROPIC_API_KEY             --repo=YOUR_ORG/sessioncast

# 環境変数（Variables）
gh variable set GCP_PROJECT   --body="${GCP_PROJECT}" --repo=YOUR_ORG/sessioncast
gh variable set GCP_REGION    --body="${GCP_REGION}"  --repo=YOUR_ORG/sessioncast
gh variable set FIREBASE_MESSAGING_SENDER_ID --body="..." --repo=YOUR_ORG/sessioncast
```

---

## Step 4: ローカル動作確認

### PWA の起動

```bash
cd apps/pwa
cp .env.local.example .env.local   # Firebase 設定を記入
npm install && npm run dev
# → http://localhost:3000
```

### ローカル TTS ワーカー（VOICEVOX）

VOICEVOX を別途起動（ポート 50021）してから:

```bash
cd apps/tts-worker
pip install -r requirements.txt

GCP_PROJECT=your-project-id \
VOICEVOX_URL=http://localhost:50021 \
WORKER_ID=local-mac \
python local_worker.py
```

ワーカーの動作フロー:
```
local_worker.py
    │
    ├─ 30秒ごとに Firestore をポーリング
    │
    ├─ status="script_ready" のエピソードを検索
    │
    ├─ トランザクションで排他クレーム（他のワーカーが取らないよう）
    │
    └─ TTS 合成 → audio.wav を GCS にアップロード
```

---

## Step 5: Cloud Run へのデプロイ

main ブランチへの push で自動デプロイ:

```bash
git push origin main
# GitHub Actions → Cloud Build → Cloud Run + Firebase Hosting
```

---

## script.json フォーマット

エージェントが GCS に保存し、TTS Worker が読み込む共通インターフェース:

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
    { "index": 0, "speaker": "host1", "text": "こんにちは！", "pause_after_ms": 300 },
    { "index": 1, "speaker": "host2", "text": "今日のテーマは...", "pause_after_ms": 500 }
  ]
}
```

**エンジンの選択肢:**

| engine | 説明 |
|---|---|
| `"voicevox"` | VOICEVOX HTTP API（アニメ風日本語、無料） |
| `"elevenlabs"` | ElevenLabs IVC（本人の声クローン） |
| `"chirp3"` | Google TTS Chirp 3（将来対応予定） |

---

## トラブルシューティング

**ローカル認証エラー:**
```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project ${GCP_PROJECT}
```

**VOICEVOX 接続確認:**
```bash
curl http://localhost:50021/speakers | head -c 100
```

---

*[← README に戻る](../README.md)*
