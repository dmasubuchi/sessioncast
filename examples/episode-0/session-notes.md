# Episode 0 — Session Notes
## Google Cloud Next '26 Day 3: Agent Context Engineering for Production (AT&T × Google)

**Event**: Google Cloud Next '26
**Date**: 2026-04-24 Las Vegas, Mandalay Bay
**Series**: google-radio
**Speaker**: Google + AT&T engineering team

---

## Raw Notes

### Context Rot
- コンテキストが膨れると精度が落ちる → "Context rot"
- AT&T の実装: Vertex AI Memory Bank でセッション後に自動サマリー
- Memory Profiles: Pydantic スキーマで記憶を型定義 + TTL 管理

### Bad Outputs Compound
- 95% × 95% × 95% ≒ 85.7%
- 95%精度のエージェント3ステップ → 複合誤差 15%近く
- 「99% 目標なら各ステップ 97% 以上が必要」
- AT&T Sales Master Agent + Formatter Master の2エージェント構成で実運用

### Claude Code × CI/CD
- MCP経由でコード修正・テスト・デプロイを一気通貫
- 「CI/CD はインフラチームが設定するもの」という前提が書き換わっている

### CX Agent Studio パターン
- Actionability Test: 「コンテキストなしの新入社員が仕事できるか？」
- internal_agent_reasoning ツールでCoTを強制 → +8〜12% 精度向上
- XML構造化プロンプト (<role>, <persona>, <taskflow>)

### SessionCast自体について（メタ）
- このメモが今まさに SessionCast パイプラインを通っている
- Vertex AI ADK + Memory Bank + Cloud Run で全処理がクラウド上
- MacBook なし、iPad だけで操作できる設計
- Google Next '27 でこの仕組み自体を登壇事例にする予定

---

## Key Quotes
- "Bad outputs compound" — AT&T セッションのスライドより
- "Context rot" — コンテキストが腐る
- "Actionability Test" — エージェントの役割定義の品質テスト

## Follow-up Links
- Vertex AI Memory Bank: https://cloud.google.com/vertex-ai
- ADK: https://github.com/google/adk-python
- SessionCast (この仕組み): https://github.com/dmasubuchi/sessioncast
