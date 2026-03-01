---
name: vacuum-voice-weekly
description: Weekly VoC analysis skill for robotic vacuum market using Reddit and YouTube (transcripts + comments). Supports brand filtering and bilingual report output.
---

# vacuum-voice-weekly

Internal weekly Voice-of-Customer analysis skill.

## Operating Modes

- Weekly monitoring mode:
  - Purpose: every Monday summarize the prior full week of social discussion about robotic vacuums.
  - Scope: include own brand plus relevant competitors unless the user narrows the scope.
  - Default output: bilingual weekly report for product, marketing, and competitive tracking.
- Ad hoc research mode:
  - Purpose: answer a specific product or brand research question on demand.
  - Scope: exact target product/brand first, then same-family and competitor context when exact-match volume is thin.
  - Default output: the same structured report format, but tailored to the user’s research objective.

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

## Search Rules (Important)

- Reddit and YouTube are required channels, but they are not hard-scoped to only the default subreddit list or default channel list.
- For model-specific or narrow product requests (for example: `Saros 10R`), search the full Reddit public search index and global YouTube search first, then use the default source lists as fallback coverage.
- Use a two-pass query strategy:
  1. Exact queries: exact model name and close variants
  2. Expanded queries: brand + family + comparison terms
- After broad search, do a second-pass relevance filter on title, body, transcript, and comments so near-match discussions can be included as market context when exact-match volume is low.
- If exact-match Reddit results are sparse, do not treat that as “no market signal” until broader full-site search has been attempted.
- In final reporting, explicitly separate exact model hits, same-family contextual hits, and competitor comparison hits.
- When the sample is dominated by YouTube comparisons or Reddit support threads, state that bias clearly in the data notes.

## Discovery Questions (Ask Before Running)

- Before generating any report, ask the user a short set of clarifying questions first instead of jumping straight into execution.
- Minimum discovery items:
  1. What is the primary goal: weekly monitoring or ad hoc product/brand research?
  2. What exact brands or models should be included?
  3. What time window should be used?
  4. Should the report focus on own-brand only, or own-brand plus competitors?
  5. Are there any specific themes to prioritize (for example: reliability, mopping, pet hair, app, price/value, comparisons)?
- If the user does not specify, make a reasonable default assumption and state it before executing.
- For weekly monitoring, also confirm:
  - which brand is “our brand”
  - which competitors matter most
  - whether the user wants only the past calendar week or the last 7 rolling days
- For ad hoc research, also confirm:
  - whether exact-model-only findings are required, or whether same-family context is acceptable
  - whether the user wants a broad VoC summary or a specific product-analysis angle
- Only start data collection after the discovery questions are answered or after you explicitly state the defaults you are using.
- For formal use, do not stop at thin sample sizes if the evidence is obviously insufficient. Expand query breadth, increase fetch depth, and retry before producing a final report.
- Prefer a defensible, evidence-backed report over a fast but low-signal summary.
- In evidence-heavy sections (for example Feature Demand Trends and Product Evaluation Matrix), prefer direct clickable post/video links instead of generic evidence labels.

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

For model-specific asks, prefer wording like:

Use vacuum-voice-weekly to generate a bilingual VoC report for `Roborock Saros 10R` using full-site Reddit + global YouTube search, with broader family-term fallback if exact matches are sparse.

For weekly monitoring asks, prefer wording like:

Use vacuum-voice-weekly to generate last week’s bilingual social VoC report for our brand plus competitors, then ask me the discovery questions before running.

For ad hoc research asks, prefer wording like:

Use vacuum-voice-weekly to research `Brand/Model X`, ask me the discovery questions first, then return the standard bilingual report format.
