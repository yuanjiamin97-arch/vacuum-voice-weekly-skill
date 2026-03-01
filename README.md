# vacuum-voice-weekly-skill

Internal VoC weekly analysis skill for robotic vacuum market (Reddit + YouTube).

## Supported Workflows

- Weekly monitoring:
  - summarize the prior week of discussion every Monday
  - track own brand plus competitors
  - best for recurring product / marketing review
- Ad hoc research:
  - deep-dive a specific brand or model on demand
  - best for product analysis, launch reviews, and competitive checks

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.run
```

The report is written to `outputs/weekly_report.md`.

By default, `python -m src.run` uses `input.weekly.json`.

To run ad hoc research with the structured intake config:

```bash
VACUUM_VOICE_CONFIG=input.research.json python -m src.run
```

## Notes

- Reddit data uses public JSON endpoints and does not require API credentials.
- YouTube transcript fetching works with the seeded video IDs in `input.example.json`.
- YouTube comments are fetched only when `YOUTUBE_API_KEY` is set.
- If you want fully dynamic YouTube discovery, provide explicit `youtube.videos` entries or extend the current discovery strategy.

## Search Method

- Do not assume analysis must stay inside the default subreddit list or the default channel list.
- For model-level requests, the runtime searches full-site Reddit and global YouTube first, then uses fixed source lists as fallback.
- Use exact queries first, then broader family/brand/comparison queries, and clearly label exact hits vs contextual same-family hits.
- Full-site search queries are built from selected brands, selected models, query keywords, and focus terms from the intake config.

## Required Intake Before Running

- Ask the user to confirm:
  - goal: weekly monitoring or ad hoc research
  - exact brands/models
  - time window
  - own-brand-only vs competitor-inclusive scope
  - priority themes (reliability, mopping, pet hair, app, price/value, etc.)
- Do not run the report until those questions are answered, unless you clearly state and use defaults.
- For formal usage, prefer deeper fetch depth and broader retries before accepting a low-sample report.
- Reports should favor direct evidence links over generic source labels whenever source URLs are available.

## Config Files

- `input.weekly.json`: default weekly monitoring intake config
- `input.research.json`: ad hoc product / brand research intake config
- `input.example.json`: legacy-compatible example config still supported by the runtime
- `reddit.global_search_first` and `youtube.global_search_first`: enable full-site search before fixed-source fallback
- `reddit.per_query_limit`, `reddit.per_sub_limit`, `reddit.per_post_comment_limit`: increase or reduce how many Reddit posts/comments are pulled into analysis
- `youtube.max_videos_total`: caps how many global-search hits are collected before transcript fetch
