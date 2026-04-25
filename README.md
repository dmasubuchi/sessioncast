# SessionCast

**ノートからラジオへ。Google Cloudだけで、全自動で。**

![SessionCast hero illustration](docs/images/hero-sessioncast.png)
<!-- 🍌 Nanobanana prompt: a journalist at a conference takes handwritten notes, and those notes transform into radio waves, then into a podcast, then into a YouTube video — shown as a flowing river of data in warm golden tones. 21:9 cinematic -->

---

> *"ラスベガスで3日間メモを取り続けた。帰国したら、そのメモがラジオ番組になっていた。"*
>
> — Daisuke Masubuchi, Google Cloud Next '26 にて

---

## はじめに — なぜこれを作ったか

2026年4月22日、ラスベガスのMandalay Bay Convention Center。

400社以上のブースが並ぶ会場で、私は必死にメモを取っていた。

PlayStation × Geminiで生み出されたゲームキャラクターの声。Inspired Entertainmentが「数週間かかっていた作業をワンクリックで」と言い切ったデモ。そして、ある研究者が黒板に書いた数式：

```
95% × 95% × 95% = 85.7%
```

「AIパイプラインを3ステップつなぐだけで、精度は85.7%に落ちる。これが**Context Rot（コンテキスト腐敗）**だ。」

帰りのフライトで、私はラップトップを開いた。そして、このシステムを作り始めた。

![Google Cloud Next '26 impressions](docs/images/next26-vibes.png)
<!-- 🍌 Nanobanana prompt: a person taking notes at a massive tech conference, screens behind them showing AI demos, the atmosphere energetic and a bit overwhelming. Warm evening lighting. 16:9 -->

---

## SessionCast とは

**SessionCast** は、カンファレンスのメモをラジオ・ブログ・動画に変換する、オープンソースのAIコンテンツパイプラインです。

全処理が **Google Cloud** 上で動きます。ローカルGPUも、重いPCも不要。スマホからでもエピソードを生成できます。

```
あなたのメモ（何でも可）
        ↓
   Research Agent    ── 事実確認・引用・Memory Bank参照
        ↓
  Script Writer Agent ── ラジオ台本（ホスト2人の対話形式）
        ↓
  音声合成              ── くくり: VOICEVOX / マシュー: Chirp 3 声クローン
        ↓
  動画レンダリング       ── Remotion × Cloud Run
        ↓
  自動公開              ── YouTube / Note.com / GCS
```

---

## Episode 0: メタなデモ

このプロジェクトの最初のエピソードは、意図的に**自己言及的**に作りました。

```
入力:  session-notes.md
       ↑ これは Google Cloud Next '26 で取ったメモ

出力:  SessionCast について語るラジオ番組
       ↑ SessionCast 自身が処理した
```

*道具が自分自身の誕生物語を語る。*

このエピソードを **Google Cloud Next '27** で流す予定です。「去年このカンファレンスで取ったメモを、このパイプラインに通しました。再生してみます。」

詳細: [`examples/episode-0/`](examples/episode-0/)

---

## 「Bad Outputs Compound」問題と、その解法

![Compound accuracy diagram](docs/images/compound-accuracy.png)
<!-- 🍌 Nanobanana prompt: three dominoes each labeled "95%", falling into each other and producing an output labeled "85.7%". Clean, minimal infographic style with red accents. 4:3 -->

Google Cloud Next '26 のセッションで学んだ最重要の概念がこれです。

| パイプラインのステップ数 | 各ステップ95%精度での最終精度 |
|---|---|
| 1ステップ | 95.0% |
| 2ステップ | 90.3% |
| 3ステップ | **85.7%** |
| 5ステップ | 77.4% |

SessionCast はこれを**計測可能にする**ことで戦います:

- 各エージェントステップが信頼スコアを記録
- `PipelineAccuracyTracker` が複合精度をリアルタイム計算
- BigQuery + Looker Studio でエピソード単位の精度推移を可視化
- 目標: **複合精度90%以上**を維持

> 📊 [観測性ドキュメント → docs/observability/](docs/observability/README.md)

---

## システムアーキテクチャ

![Architecture overview](docs/images/architecture-full.png)
<!-- 🍌 Nanobanana prompt: beautiful system diagram showing notes flowing through agents → voices → video → YouTube, Google Cloud color palette (blue/white/yellow), glowing connections. 21:9 -->

```
┌─────────────────────────────────────────────────┐
│  SessionCast PWA  (Firebase Hosting / Next.js)  │
│  Firestore onSnapshot → リアルタイム進捗表示      │
└─────────────────────┬───────────────────────────┘
                      │ Pub/Sub
                      ▼
┌─────────────────────────────────────────────────┐
│  Vertex AI Agent Engine (ADK)                   │
│  ├── Research Agent   (Gemini 2.5 Pro)          │
│  └── Script Writer    (Gemini 2.5 Pro)          │
│                                                 │
│  Context Rot Monitor: 50k 警告 / 100k 強制リセット│
│  InternalReasoningTool: 意思決定前に内省強制      │
└──────────┬──────────────────────┬───────────────┘
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────────┐
│  VOICEVOX        │   │  Chirp 3 Custom Voice    │
│  (Cloud Run GPU) │   │  (Matthew の声クローン)    │
│  くくり の声      │   │  TTS API v1beta1         │
└────────┬─────────┘   └──────────┬───────────────┘
         └──────────┬─────────────┘
                    ▼
         ┌──────────────────────┐
         │  Remotion Renderer   │
         │  (Cloud Run CPU)     │
         │  8vCPU / 16GB RAM    │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  Publishing Hub      │
         │  YouTube / Note.com  │
         │  GCS アーカイブ       │
         └──────────────────────┘
```

> 📐 [詳細アーキテクチャ → docs/architecture/overview.md](docs/architecture/overview.md)

---

## AI-Powered CI/CD — コーディングエージェントが PR をレビューする

![CI/CD pipeline illustration](docs/images/cicd-review.png)
<!-- 🍌 Nanobanana prompt: a pull request icon being carefully examined by two robot reviewers, one with Google colors, one with Anthropic colors. Clean GitHub-style interface in background. 16:9 -->

このリポジトリへの**すべてのプルリクエストはGemini 2.5 Proが自動レビュー**します。

```
PR オープン
    ↓
Gemini 2.5 Pro がdiffを読む
    ↓
構造化レビューをコメント投稿:
  ✅ Looks good  または  ⚠️ 2 issues found
  1. セキュリティ問題（必須修正）
  2. ロジックバグ（修正推奨）
  3. コード品質（検討）
  4. 良い点
```

そして、PRのコメントに `/fix 〇〇を直して` と書くと **Claude Code** が自動修正してコミットします。

これは Google Cloud Next '26 の「Accelerate CI/CD with Coding Agents」セッションで見たパターンを、このリポジトリで実際に実装したものです。**デモではなく、本番稼働中です。**

> ⚙️ [CI/CDドキュメント → docs/ci-cd/](docs/ci-cd/README.md)

---

## 声のクローン — Chirp 3 Instant Custom Voice

![Voice cloning illustration](docs/images/voice-clone.png)
<!-- 🍌 Nanobanana prompt: a sound waveform splitting into two: one labeled "VOICEVOX" with an anime character icon, one labeled "Chirp 3" with a human silhouette. Elegant, scientific visualization. 16:9 -->

ラジオ番組のホストは2人います:

- **くくり** — VOICEVOXによるアニメ風日本語音声
- **マシュー** — Chirp 3 Instant Custom Voiceによる本人の声クローン

Chirp 3 の声クローンは事前申請不要。Google TTS API v1beta1 で今すぐ使えます。

```python
# 1. 一度だけ声を登録（consent.wav + reference.wav → voiceCloningKey）
python scripts/generate_voice_key.py

# 2. 以後は voiceCloningKey で合成するだけ
voice = VoiceSelectionParams(
    voice_clone=VoiceCloneParams(voice_cloning_key=key)
)
```

> 🎙️ [音声合成ドキュメント → docs/tts/](docs/tts/README.md)

---

## コラム: Google Cloud Next '26 で感じたこと

![Next '26 column illustration](docs/images/next26-column.png)
<!-- 🍌 Nanobanana prompt: a lone Japanese developer walking through a massive tech convention floor, looking up in awe at giant LED screens showing AI demos. Slightly cinematic, contemplative mood. 16:9 -->

ラスベガスに3日間いて、一番強く感じたのは「**Googleはもうクラウド会社じゃない**」ということでした。

ADK（Agent Development Kit）、A2A（Agent-to-Agent Protocol）、A2UI——これらは単なる製品名ではなく、Googleが描く「エージェントが世界を動かす未来」の設計図でした。

特に印象的だったのはAT&Tのセッション。彼らは Context Engineering（コンテキスト設計）を語り、「1Mトークンのコンテキストウィンドウがあっても、設計が悪ければ意味がない」と言いました。

**コンテキストサイズより、コンテキスト設計が大事。**

その言葉がSessionCastの設計思想の核になっています。巨大なコンテキストに頼るのではなく、Memory Bankで必要なものだけを選択的に渡し、Context Rot Monitorでトークン予算を管理する。

---

## クイックスタート

### 前提条件

- Google Cloudプロジェクト（billing有効）
- `gcloud` CLI 認証済み
- Node.js 20+, Python 3.12+, Terraform

### セットアップ

```bash
git clone https://github.com/dmasubuchi/sessioncast.git
cd sessioncast

# 1. GCPインフラをデプロイ（1回だけ）
export GCP_PROJECT=your-gcp-project-id
cd terraform && terraform init && terraform apply

# 2. PWAをローカル起動
cd ../apps/pwa
cp .env.local.example .env.local   # Firebase設定を記入
npm install && npm run dev

# 3. http://localhost:3000 を開く
#    メモを貼り付け → 生成開始 → リアルタイムで進捗確認
```

### GitHub Secrets（CI/CD利用時）

| Secret | 用途 |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | GitHub→GCP認証 |
| `GCP_SERVICE_ACCOUNT` | デプロイ用SA |
| `FIREBASE_API_KEY`, `FIREBASE_APP_ID`, `FIREBASE_SERVICE_ACCOUNT` | Firebase |
| `GEMINI_API_KEY` | PRレビュー（Vertex AI移行予定） |
| `ANTHROPIC_API_KEY` | `/fix`コマンド用 |

---

## プロジェクト構成

```
sessioncast/
├── apps/
│   ├── pwa/              # Next.js PWA (Firebase Hosting)
│   ├── agents/           # Vertex AI ADK エージェント群
│   ├── tts-worker/       # VOICEVOX + Chirp 3 音声合成
│   └── video-renderer/   # Remotion 動画レンダリング
├── terraform/            # GCPインフラ全量をコードで管理
├── examples/
│   └── episode-0/        # メタエピソード（Next '26のメモ→ラジオ）
├── docs/
│   ├── architecture/     # システム設計
│   ├── agents/           # ADKエージェント詳細
│   ├── tts/              # 音声合成詳細
│   ├── video/            # 動画レンダリング詳細
│   ├── pwa/              # PWA詳細
│   ├── ci-cd/            # CI/CDパイプライン詳細
│   └── observability/    # 精度トラッキング・ダッシュボード
└── .github/workflows/    # Geminiレビュー + Claude Code自動修正
```

---

## 現在のステータス

| コンポーネント | 状態 |
|---|---|
| Vertex AI ADK エージェント | ✅ 実装済み |
| Firebase PWA | ✅ 実装済み |
| CI/CD（Gemini レビュー + Claude 自動修正） | ✅ 本番稼働中 |
| VOICEVOX 合成 | ✅ Dockerファイル完成 |
| Chirp 3 声クローン | 🚧 実装中 |
| Remotion 動画レンダリング | 🚧 実装中 |
| YouTube 自動公開 | 📋 予定 |
| Looker Studio ダッシュボード | 📋 予定 |

---

## Google Cloud Next '27 へ向けて

このプロジェクトの最終目標は、**Google Cloud Next '27** のステージに立つことです。

そのとき流したいのはこのセリフ:

> *「去年のこのカンファレンスで、私はこのメモを取りました。
>  今朝、パイプラインがそれをラジオエピソードに変えました。
>  これがそのLooker Studioダッシュボードです。50エピソード、複合精度91.2%。」*

もしあなたが同じような夢を持っているなら、PRを送ってください。

---

## ライセンス

MIT — [LICENSE](LICENSE) 参照

フォーク自由、改変自由、商用利用自由。カンファレンスで発表したら教えてください。

---

*Daisuke Masubuchi / [Papukaija LLC](https://papukaija.jp/)*
*Google Cloud Next '26 → '27 ケーススタディとして開発中*

![Footer illustration](docs/images/footer-pipeline.png)
<!-- 🍌 Nanobanana prompt: a warm and satisfying final frame — a radio tower at sunset, with data streams flowing upward becoming sound waves, becoming stars. 21:9 cinematic -->
