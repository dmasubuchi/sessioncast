# PWA: SessionCast Web App

![PWA screenshot illustration](../images/pwa-screenshot.png)
<!-- 🍌 Nanobanana prompt: a clean mobile-first web app dashboard showing a podcast pipeline progress, Firestore realtime animation, dark mode. 9:16 -->

## Overview

The SessionCast PWA is a **Next.js** app deployed to **Firebase Hosting**. It's the user-facing control panel for the pipeline.

URL: `https://almeisan-adk-sandbox.web.app`

## What you can do

1. **Paste session notes** — any markdown or plain text
2. **Select a radio series** — e.g., `google-radio`, `ai-weekly`
3. **Click 生成開始** — triggers the full pipeline via Firestore
4. **Watch in real-time** — Firestore `onSnapshot` pushes status updates live:
   `pending → researching → writing → tts → rendering → publishing → done`

## Architecture Notes

### Static Export for Firebase Hosting

```typescript
// next.config.ts
const nextConfig: NextConfig = {
  output: "export",   // All pages pre-rendered at build time
  trailingSlash: true,
};
```

All pages use `"use client"` — there's no server-side rendering needed. Firebase Hosting serves from the `out/` directory.

### Real-time Updates via Firestore

```typescript
// No polling. onSnapshot fires instantly when the agent updates status.
subscribeToEpisode(episodeId, (episode) => {
  setStatus(episode.status);
  setAccuracy(episode.compoundAccuracy);
});
```

### Security Headers

`firebase.json` sets protective HTTP headers on every response:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Files

```
apps/pwa/
├── src/
│   ├── app/
│   │   ├── page.tsx           # Submit form
│   │   └── episodes/page.tsx  # Real-time episode list
│   └── lib/
│       ├── firebase.ts        # Firebase init
│       └── firestore.ts       # Type-safe Firestore helpers
├── next.config.ts
└── firebase.json
```
