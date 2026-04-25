# SessionCast（日本語版）

**ノートからラジオへ。Google Cloudだけで、全自動で。**

**[🇺🇸 English README](../README.md)** | [セットアップガイド（日本語）](SETUP.ja.md)

![SessionCast hero illustration](images/hero-sessioncast.png)
<!-- 🍌 Nanobanana prompt: a journalist at a conference takes handwritten notes, and those notes transform into radio waves, then into a podcast, then into a YouTube video — shown as a flowing river of data in warm golden tones. 21:9 cinematic -->

---

> *"ラスベガスで3日間メモを取り続けた。帰国したら、そのメモがラジオ番組になっていた。"*
>
> — Daisuke Masubuchi（増渕大輔）, Google Cloud Next '26 にて

---

## これは何？

カンファレンスのメモやセッションノートを入れると、**ラジオ番組が生成されます。**

```
  あなたのメモ（テキスト・写真・何でも可）
          │
          ▼
  ┌───────────────────────────────────────┐
  │                                       │
  │   📝  →  🤖  →  🎙️  →  🎬  →  📺   │
  │  メモ   AI脚本   音声合成  動画生成   公開  │
  │                                       │
  └───────────────────────────────────────┘
          │
          ▼
  ラジオエピソード（YouTube / Podcast）
```

全処理が **Google Cloud** 上で動きます。ローカルGPUも、重いPCも不要。

---

## なぜ作ったか — ラスベガスのホテルの部屋で

2026年4月22〜24日、**Google Cloud Next '26**（ラスベガス）に参加してきました。

![Google Cloud Next '26 impressions](images/next26-vibes.png)
<!-- 🍌 Nanobanana prompt: a person taking notes at a massive tech conference, screens behind them showing AI demos, the atmosphere energetic and a bit overwhelming. Warm evening lighting. 16:9 -->

400社以上のブース。PlayStation × Geminiのゲームキャラクター音声デモ。「数週間かかっていた作業をワンクリックで」と言い切ったデモ。毎日10時間以上のセッション漬け。

**問題は「記憶に定着させること」でした。**

写真を撮る。テキストメモを書く。でも3日間の密度はそれでは足りない。

ホテルの部屋で思いついたのが **「ラジオ形式なら頭に入るんじゃないか」**。

でも自分はセッションに出っぱなしで脚本を書く暇がない。
だったら**全部AIにやらせればいい。**

```
  ┌─────────────────────────────────────────────────┐
  │  Day 1夜                                        │
  │  セッション中のメモ → パイプラインに投げる       │
  │                                                 │
  │  Day 2朝                                        │
  │  昨日のセッションがラジオエピソードになっている  │
  └─────────────────────────────────────────────────┘
```

これが SessionCast の始まりです。

> **このカンファレンス体験をNote.comにブログとして書いています。**  
> ラジオシリーズ（YouTube）も近日公開予定。

---

## 何ができるか — パイプラインの全体像

```
  ╔═══════════════════════════════════════════════════════╗
  ║  STEP 1: 前段処理（企画・脚本）                       ║
  ╠═══════════════════════════════════════════════════════╣
  ║                                                       ║
  ║   📄 あなたのメモ                                     ║
  ║       │                                               ║
  ║       ▼                                               ║
  ║   🔍 Research Agent  ← Gemini 2.5 Pro               ║
  ║       │  事実確認・引用・補足情報の収集              ║
  ║       │  + 写真をアップロードした場合は画像解析（A2A）║
  ║       ▼                                               ║
  ║   ✍️  Script Writer Agent  ← Gemini 2.5 Pro          ║
  ║       │  ラジオ台本（2人のホストの対話形式）を生成    ║
  ║       ▼                                               ║
  ║   💾 script.json → GCS に保存                        ║
  ║       │  Firestore に「script_ready」と記録          ║
  ║                                                       ║
  ╠═══════════════════════════════════════════════════════╣
  ║  STEP 2: 音声合成                                     ║
  ╠═══════════════════════════════════════════════════════╣
  ║                                                       ║
  ║   🔔 Firestore で「script_ready」を検知              ║
  ║       │                                               ║
  ║       ▼                                               ║
  ║   🎙️  TTS Worker（キャラクターごとにエンジンを選択）  ║
  ║       │                                               ║
  ║       ├── くくり（日本語アニメ声）→ VOICEVOX         ║
  ║       └── マシュー（本人の声クローン）→ ElevenLabs   ║
  ║       │                                               ║
  ║       ▼                                               ║
  ║   💾 audio.wav → GCS に保存                          ║
  ║                                                       ║
  ╠═══════════════════════════════════════════════════════╣
  ║  STEP 3: 動画生成・公開                               ║
  ╠═══════════════════════════════════════════════════════╣
  ║                                                       ║
  ║   🎬 Remotion Renderer（実装中）                     ║
  ║       │  スライド + 音声 → video.mp4                 ║
  ║       ▼                                               ║
  ║   📺 Publishing Hub                                   ║
  ║       YouTube / Note.com / GCS アーカイブ            ║
  ║                                                       ║
  ╚═══════════════════════════════════════════════════════╝
```

---

## 2人のホスト

このラジオ番組には2人の固定ホストがいます。

```
  ┌─────────────────────────┐   ┌─────────────────────────┐
  │         くくり           │   │        マシュー          │
  │                         │   │                         │
  │  🎀 日本語アニメ風音声  │   │  🎙️ 本人（増渕）の声    │
  │     VOICEVOX 使用       │   │     ElevenLabs IVC 使用  │
  │                         │   │     声クローン技術       │
  └─────────────────────────┘   └─────────────────────────┘
```

声の種類はエピソードごとに設定ファイルで変更できます。
自分でフォークすれば、**あなたの声でラジオを作れます。**

---

## 事前セッション計画

カンファレンスに行く前に、セッション一覧を SessionCast に貼り付けます。Gemini が登壇者やトピックを調査して、優先スケジュールと事前メモを返します。

```
  PWA /plan ページ
       │  セッション一覧をペースト（自由形式・CSV・URLどれでも可）
       │  興味タグを選択
       │  このイベントで得たいことを入力
       ▼
  Session Planner Agent  ← Gemini 2.5 Pro + google_search
       │  登壇者・トピックを調査
       │  スケジュール重複を検出
       │  関連度でランキング
       ▼
  優先スケジュール
       │  おすすめセッション + 理由
       │  時間重複の解決案
       │  事前メモ → エピソードの下地として保存
       ▼
  当日
       事前メモの上にライブメモを追記
```

**Google Deep Research API** が公開されたタイミングでエージェント内部のツールを差し替える設計になっています（エンドポイントのインターフェースは変わりません）。

Google Cloud Next・Google I/O など、セッションカタログを公開しているイベントとの相性が特に良いです。

---

## 写真アップロード + AI解析（A2A）

カンファレンスで撮った写真をアップロードすると、AI がその内容を解析してスクリプトに反映します。スライドだけでなく、会場の雰囲気やレセプションの写真にも対応しています。

```
  PWA アップロードページ（/upload）
       │  ドラッグ＆ドロップ または カメラロールから選択
       │  カテゴリ: スライド / 雰囲気・会場 / その他
       ▼
  Firebase Storage → GCS
       │
       ▼
  sessioncast-image-analyzer（Cloud Run、A2A エンドポイント）
       │  Gemini Vision が GCS URI を直接読み込み
       │  返却: title, key_points, radio_description
       ▼
  Research Agent が画像解析結果を取り込む
       │  テキストメモと統合
       ▼
  スクリプトに写真の文脈が織り込まれる
```

Image Analyzer は独立した A2A サービスです。他のエージェントは `/.well-known/agent.json` の **Agent Card** を通じてこのサービスを発見・呼び出します。

---

## AIが作ったAIシステム — 自然言語開発の実験

SessionCast 開発で最も実験的だったのは「**コードをほぼ書かずに作った**」という点です。

```
  ┌─────────────────────────────────────────────────────┐
  │  従来の開発                                         │
  │                                                     │
  │  アイデア → 設計書 → コーディング → テスト → 完成  │
  │  ~~~~~~~~~~~~~~~~~~~~~~                             │
  │  ここに数週間〜数ヶ月かかる                         │
  └─────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │  SessionCast の開発方法                             │
  │                                                     │
  │  「こういうパイプラインを作りたい」と話す           │
  │      ↓                                              │
  │  「TTS Worker を ElevenLabs に切り替えて」          │
  │      ↓                                              │
  │  「Cloud Build が失敗している、直して」             │
  │      ↓                                              │
  │  完成                                               │
  │                                                     │
  │  コードを書いたのはほぼゼロ。全部自然言語の指示。   │
  └─────────────────────────────────────────────────────┘
```

これは Google Cloud Next '26 で学んだ **「意図を設計する」** という考え方の実践です。

> コードを書くのではなく、*何を作りたいか*を設計し、AIに翻訳させる。

---

## 精度の複利問題 — なぜ「計測」が重要か

![Compound accuracy diagram](images/compound-accuracy.png)
<!-- 🍌 Nanobanana prompt: three dominoes each labeled "95%", falling into each other and producing an output labeled "85.7%". Clean, minimal infographic style with red accents. 4:3 -->

Google Cloud Next '26 のセッションで学んだ重要な概念です。

```
  各ステップが 95% の精度だとすると...

  ステップ 1 だけ:  ████████████████████ 95.0%

  ステップ 2 まで:  ██████████████████░░ 90.3%

  ステップ 3 まで:  █████████████████░░░ 85.7%  ← 3段階で14%落ちる!

  ステップ 5 まで:  ███████████████░░░░░ 77.4%
```

AIパイプラインはステップが増えるほど**精度が複利で落ちる**。

SessionCast はこれを計測可能にします:

```
  各エージェントステップ
      │  信頼スコアを記録（0.0〜1.0）
      ▼
  PipelineAccuracyTracker
      │  複合精度をリアルタイム計算
      ▼
  BigQuery + Looker Studio
      │  エピソード単位の精度推移を可視化
      ▼
  目標: 複合精度 90% 以上を維持
```

---

## AI-Powered CI/CD — コーディングエージェントが PR をレビュー

![CI/CD pipeline illustration](images/cicd-review.png)
<!-- 🍌 Nanobanana prompt: a pull request icon being carefully examined by two robot reviewers, one with Google colors, one with Anthropic colors. Clean GitHub-style interface in background. 16:9 -->

このリポジトリへのすべての PR は **Gemini 2.5 Pro が自動レビュー**します。

```
  PR オープン
      │
      ▼
  Gemini 2.5 Pro が diff を読む
      │
      ▼
  構造化レビューをコメント投稿
      │
      ├── ✅ Looks good
      │
      └── ⚠️ 2 issues found
              │
              ├── 1. セキュリティ問題（必須修正）
              ├── 2. ロジックバグ（修正推奨）
              └── 3. コード品質（検討）

  PR コメントに /fix と書くと
      │
      ▼
  Claude Code が自動修正してコミット
```

Google Cloud Next '26 の「Accelerate CI/CD with Coding Agents」セッションで見たパターンを、**このリポジトリで実際に実装したもの**です。

---

## Episode 0: メタなデモ

このプロジェクトの最初のエピソードは意図的に **自己言及的** に作りました。

```
  入力:  session-notes.md
         ↑ これは Google Cloud Next '26 で取ったメモ

  処理:  SessionCast パイプラインが処理

  出力:  SessionCast について語るラジオ番組
         ↑ SessionCast 自身が自分の誕生物語を語る
```

*道具が自分自身の誕生物語を語る。*

このエピソードを **Google Cloud Next '27** で流す予定です。

> 「去年このカンファレンスで取ったメモを、このパイプラインに通しました。再生してみます。」

---

## 現在のステータス

| コンポーネント | 状態 | 備考 |
|---|---|---|
| Vertex AI ADK エージェント | ✅ 稼働中 | Research + Script Writer |
| Firebase PWA | ✅ 稼働中 | Firebase Hosting |
| CI/CD（Gemini レビュー + Claude /fix） | ✅ 稼働中 | Vertex AI Workload Identity |
| ElevenLabs 声クローン（マシュー） | ✅ 稼働中 | eleven_multilingual_v2 |
| TTS Worker (Cloud Run) | ✅ 稼働中 | Firestore ジョブキュー |
| ローカルワーカー（VOICEVOX） | ✅ 稼働中 | local_worker.py |
| Image Analyzer A2A サービス | ✅ 構築済み | Gemini Vision |
| 写真アップロード UI（/upload） | ✅ 構築済み | Firebase Storage |
| 事前セッション計画（/plan） | ✅ 構築済み | Gemini + google_search |
| Remotion 動画レンダリング | 🚧 実装中 | |
| YouTube 自動公開 | 📋 予定 | |
| Looker Studio ダッシュボード | 📋 予定 | |

---

## Google Cloud Next '27 へ向けて

このプロジェクトの最終目標は、**Google Cloud Next '27** のステージに立つことです。

```
  ┌────────────────────────────────────────────────────────┐
  │  目標のセリフ                                          │
  │                                                        │
  │  「去年のこのカンファレンスで、私はこのメモを取った。  │
  │   今朝、パイプラインがそれをラジオエピソードにした。  │
  │                                                        │
  │   これがその Looker Studio ダッシュボードです。        │
  │   50エピソード、複合精度 91.2%。」                    │
  └────────────────────────────────────────────────────────┘
```

もしあなたが同じような夢を持っているなら、PR を送ってください。

---

## PoC からエンタープライズへ — 移行の背景

SessionCast は個人実験として始まりました。Claude Code 一本で、ラスベガスのホテルの部屋から。

PoC はすべて Claude Code を通じて動かしました。自然言語の指示だけで、手書きコードはほぼゼロ。これが成り立ったのは、**完全に信頼できる運用者が自分一人だったから**。アクセス制御も監査ログも不要。ただ速く動かすだけでよかった。

```
  PoC: 人間1人 + AI + ホテルの部屋
  ─────────────────────────────────
  「TTSワーカー作って」    →  tts_worker.py  ✓
  「ElevenLabsに切替えて」 →  エンジン変更   ✓
  「Cloud Buildが失敗してる」→  修正&コミット ✓

  人間が書いたコード: ≈ 0行
```

でも同じパイプラインをエンタープライズで動かすなら、構成が変わります。複数チーム、複数シリーズ、個人の認証情報ではなく Workload Identity、会話履歴ではなく Cloud Audit Log、信頼ではなくプロンプトインジェクション対策。

**これが SessionCast が設計・文書化しながら解いている課題です。**

### PoC モデル vs エンタープライズモデル

中心的な違いは「**誰がパラメーターを制御し、どう変更するか**」にあります。

| 項目 | PoC（くくりモデル） | エンタープライズ |
|---|---|---|
| 誰が変更できるか | マシュー（全部） | 役割別に階層管理 |
| 変更方法 | 自然言語でチャット | 構造化フォーム + 承認フロー |
| 記憶の場所 | Claude の会話コンテキスト | Firestore（永続・テナント分離） |
| パラメーターの形式 | 自由テキスト | 構造化 enum + テンプレート |
| 変更の追跡 | なし | Cloud Audit Log（全履歴） |
| プロンプトへの反映 | 直接 | テンプレート展開（インジェクション防止） |

PoC では「秘書のくくり」がどのパラメーターも調整できました。ループの中に信頼できる人間がただ一人いたから。エンタープライズでは、パラメーターは構造化された型に固定され、ユーザーの自由テキストが直接プロンプトに流れ込まない設計になります。ポリシー階層のイメージ:

```
  プラットフォームのデフォルト
       ↓ 上書き
  組織ポリシー        (例: 承認済みの音声エンジンのみ)
       ↓ 上書き
  シリーズ設定        (例: このラジオのくくり声)
       ↓ 上書き
  エピソードパラメーター (例: ゲストスピーカーの言語)
```

このリポジトリはその生きたケーススタディです。ラップトップの Claude Code から始め、Google Cloud の Vertex AI にスケールアップする。

---

## フォークして使いたい方へ

セットアップ手順・script.json フォーマット・トラブルシューティングは別ページにまとめています:

### 👉 [SETUP.ja.md — セットアップガイド（日本語）](SETUP.ja.md)

---

## ライセンス

MIT — [LICENSE](LICENSE) 参照

フォーク自由、改変自由、商用利用自由。カンファレンスで発表したら教えてください。

---

*Daisuke Masubuchi / [Papukaija LLC](https://papukaija.jp/)*  
*Google Cloud Next '26 → '27 ケーススタディとして開発中*

![Footer illustration](images/footer-pipeline.png)
<!-- 🍌 Nanobanana prompt: a warm and satisfying final frame — a radio tower at sunset, with data streams flowing upward becoming sound waves, becoming stars. 21:9 cinematic -->
