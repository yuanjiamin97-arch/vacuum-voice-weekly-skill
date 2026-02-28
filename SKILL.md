---
name: vacuum-voice-weekly
description: Weekly VoC analysis skill for robotic vacuum market using Reddit and YouTube (transcripts + comments). Supports brand filtering and bilingual report output.
---

# vacuum-voice-weekly

Internal weekly Voice-of-Customer analysis skill.

## Default Scope

- Time window: last 7 days
- Sources: Reddit + YouTube
- Filter mode: brand
- Default brands: ["Roborock","Dreame","Ecovacs","Narwal","MOVA"]
- YouTube channels:
  - Vacuum Wars
  - Smart Home Solver
  - The Hook Up
- Include: transcript + title/description + comments
- Output: bilingual Markdown report + evidence.jsonl + metrics.json

---

## What this skill does

1. Extract feature demand trends (Top 5 + emerging signals)
2. Generate Feature Priority Board (data-driven scoring)
3. Map praise/complaints to specific models
4. Detect competitive heat shifts
5. Output structured weekly report for product & marketing teams

---

## How to use

Call:

Use vacuum-voice-weekly to generate weekly VoC report for selected brands.

Or explicitly:

$vacuum-voice-weekly
