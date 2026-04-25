# CI/CD: Gemini Review + Claude Code Auto-Fix

![CI/CD pipeline illustration](../images/cicd-agents.png)
<!-- 🍌 Nanobanana prompt: a pull request being reviewed by two AI robots (one Google-branded, one Anthropic-branded), thumbs up/fix icons, pipeline flow chart. 16:9 -->

## Overview

Every pull request in this repo is reviewed automatically by AI — and fixable with a single comment.

This implements the **"Accelerate CI/CD with Coding Agents"** pattern from Google Cloud Next '26.

## Workflow

### On PR open/update

```
PR opened or updated
    ↓
Gemini 2.5 Pro reads the diff (Python/TS/Terraform/Dockerfile)
    ↓
Posts a structured review comment:

## Gemini Code Review 🤖

✅ Looks good  (or ⚠️ 2 issues found)

**Security** (critical, must fix)
**Logic bugs** (should fix)
**Code quality** (consider fixing)
**Positive observations**
```

### On `/fix` comment

```
PR reviewer comments: "/fix the null check on line 42"
    ↓
Claude Code reads the instruction
    ↓
Applies the fix directly to the PR branch
    ↓
Commits and pushes: "fix: auto-fix via Claude Code (/fix command)"
```

## Security Design

GitHub context values (`github.sha`, comment body, etc.) are always passed through **environment variables**, never interpolated directly into `run:` commands. This prevents command injection attacks.

```yaml
# Safe: value goes through env var
env:
  COMMIT_SHA: ${{ github.sha }}
run: |
  gcloud builds submit --tag="${AGENTS_IMAGE}:${COMMIT_SHA}"
```

## Authentication

GitHub Actions authenticates to GCP via **Workload Identity Federation** — no JSON service account keys stored as secrets.

Required GitHub Secrets:
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `FIREBASE_API_KEY`, `FIREBASE_APP_ID`, `FIREBASE_SERVICE_ACCOUNT`
- `GEMINI_API_KEY` *(temporary — will migrate to Vertex AI auth)*
- `ANTHROPIC_API_KEY` *(for `/fix` command)*

## Files

```
.github/workflows/
├── ci.yml          # Build, type-check, deploy to Cloud Run + Firebase
└── pr-review.yml   # Gemini auto-review + Claude Code /fix
```
