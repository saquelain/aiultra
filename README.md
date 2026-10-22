# aiultra

An automated YouTube Shorts experiment: make original Shorts with code, publish them, read the numbers, and change one thing at a time until videos reliably get thousands of views.

- `shortsgen/rings.py`: "Can the ball escape all the rings?" physics simulation, rendered with cairo and ffmpeg (1080×1920, 60 fps).
- `shortsgen/audio.py`: synthesized soundtrack (a note on each bounce, a chime on each ring break).
- `shortsgen/yt.py`: YouTube Data API upload and stats.
- `run.py`: command line (`make`, `upload`, `stats`, `channel`).
- `PLAYBOOK.md`: how each loop run works. `LEARNINGS.md`: results so far.

## Setup

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py make --exp test --rings 20
```

Needs `ffmpeg` and the cairo library. Uploading needs `YT_CLIENT_ID`, `YT_CLIENT_SECRET` and `YT_REFRESH_TOKEN` in the environment.
