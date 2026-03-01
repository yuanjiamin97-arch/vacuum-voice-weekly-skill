# vacuum-voice-weekly-skill

Internal VoC weekly analysis skill for robotic vacuum market (Reddit + YouTube).

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.run
```

The report is written to `outputs/weekly_report.md`.

## Notes

- Reddit data uses public JSON endpoints and does not require API credentials.
- YouTube transcript fetching works with the seeded video IDs in `input.example.json`.
- YouTube comments are fetched only when `YOUTUBE_API_KEY` is set.
- If you want fully dynamic YouTube discovery, provide explicit `youtube.videos` entries or extend the current discovery strategy.
