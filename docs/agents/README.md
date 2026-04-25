# Vertex AI ADK Agents

![Agents overview](../images/agents-overview.png)
<!-- 🍌 Nanobanana prompt: robot editorial team in a newsroom, each agent with a job badge (Research, Writer), warm lighting, Studio Ghibli-esque. 16:9 -->

## Overview

SessionCast's brain is a **SequentialAgent** built on Vertex AI ADK. Two agents run in order:

```
Input notes
    ↓
Research Agent   — fact-check, enrich, query Memory Bank
    ↓
Script Writer    — two-host dialogue in natural Japanese
    ↓
Structured script output
```

## Key Patterns

### XML-Structured Prompts

Prompts use `<role>`, `<persona>`, and `<taskflow>` tags. This prevents instruction confusion and consistently outperforms plain prose.

### InternalReasoningTool

Before important editorial decisions, the agent calls `internal_agent_reasoning(question=...)`. Chain-of-thought exposed as a tool call — a pattern from Google Cloud Next '26's CX Agent Studio. Adds ~8–12% accuracy.

### Context Rot Monitor

`before_model_callback` tracks token count:
- **> 50k tokens** → warning logged to Cloud Monitoring
- **> 100k tokens** → forced context reset

Based on the **95%³ = 85.7%** compounding formula.

## Files

```
apps/agents/
├── agents/pipeline.py           # SequentialAgent
├── monitoring/context_monitor.py
├── monitoring/accuracy_tracker.py
├── tools/internal_reasoning.py
└── main.py
```
