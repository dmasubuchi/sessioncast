# Episode 0 — The Meta Episode

> **"The notes I took at Google Cloud Next '26 just ran through this pipeline."**

This is the inaugural demo of SessionCast: a radio episode **about SessionCast itself**,
generated from the session notes taken at the conference where the ideas originated.

## What this demonstrates

```
[Session notes taken at Google Cloud Next '26]
              ↓
[SessionCast pipeline — Vertex AI ADK + Memory Bank]
              ↓
[Radio episode about Context Rot, 95%^3, CX Agent Studio]
              ↓
[YouTube / Note.com — published automatically]
```

## How to run

1. Start the SessionCast PWA (`apps/pwa`)
2. Paste `session-notes.md` into the notes field
3. Select series: `google-radio`
4. Click "生成開始"
5. Watch the pipeline progress in real-time (Firestore → PWA)

## Expected output

- **Script**: ~15-min dialogue between two hosts
- **Audio**: VOICEVOX synthesized (Cloud Run GPU)
- **Video**: Remotion rendered (Cloud Run CPU)
- **Blog**: Note.com draft generated

## Demo at Google Cloud Next '27

This episode is the core of the planned '27 presentation:

> "Last year at this conference, I took these notes.
>  This morning, the pipeline turned them into a radio episode.
>  Here's the Looker Studio dashboard showing the compound accuracy: 86.2%."
