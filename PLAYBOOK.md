# Operating playbook

Read this at the start of every loop run.

## Goal

Grow the owner's YouTube channel to Shorts that get **thousands of views each**. The owner gave full freedom over format, topic and language: do whatever the data says works. The old videos on the channel were set to private on purpose; leave them alone.

## Files

- `manifest.jsonl`: one line per Short made (exp id, settings, file, and after upload: video id, title, publish time).
- `stats.jsonl`: append-only stats snapshots from `python run.py stats`.
- `LEARNINGS.md`: experiment table and what each result taught us. Update it every run.
- `reports/YYYY-MM-DD.md`: one short daily report for the owner.
- `out/`: rendered videos. Git-ignored; they are rebuilt from the manifest settings if needed.

## Each run

1. `python run.py stats` and log the numbers.
2. Judge only videos that have been public for **48 hours or more**. Earlier numbers are noise.
3. Write in `LEARNINGS.md` what changed versus the previous experiment and what the result suggests.
4. Decide the next experiment: **change one thing at a time** (hook text, title style, ring count, gap, palette, length, publish time).
5. Make it with `python run.py make ...`. Look at a few frames before uploading.
6. Upload with `python run.py upload ... --publish-at <UTC time>`, keeping at most **3 Shorts a day**. Publish slots (IST): 7:00 PM, 12:00 AM, 5:00 AM.
7. Once a day, write `reports/YYYY-MM-DD.md`: views per video, what worked, what's next, and whether a paid tool would clearly help.
8. Commit and push `manifest.jsonl`, `stats.jsonl`, `LEARNINGS.md` and `reports/`.

## Switching formats

If a format has had about **6 Shorts judged** and none reached 1,000 views, switch to a new one (marble race, "which ball wins", quiz, satisfying loops). Keep the best variant of the old format in rotation.

## Hard rules

- Never delete videos, never change account settings, never buy anything.
- No fake engagement, no misleading titles, no reuploading other people's content.
- Vary each video. No near-identical bulk uploads; YouTube's inauthentic-content policy punishes them.
- Never commit secrets. Credentials only come from environment variables (`YT_TOKEN_JSON`, or `YT_CLIENT_ID`, `YT_CLIENT_SECRET` and `YT_REFRESH_TOKEN`).
- Recommend a paid tool only when the data shows free tools are the bottleneck, and name the exact product and why.
