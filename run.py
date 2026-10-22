"""Command line for the Shorts loop.

  python run.py make  --exp E4 --rings 20 --gap 55 --palette rainbow --hook "Can the ball escape\\nall {n} rings?"
  python run.py upload --exp E4 --title "..." [--publish-at 2026-10-23T13:30:00Z]
  python run.py stats            # refresh stats for everything in manifest.jsonl
  python run.py channel          # list the channel's latest uploads
"""
import argparse
import datetime as dt
import json
import os
import sys

MANIFEST = "manifest.jsonl"
STATS_LOG = "stats.jsonl"


def load_manifest():
    if not os.path.exists(MANIFEST):
        return []
    return [json.loads(line) for line in open(MANIFEST) if line.strip()]


def save_manifest(rows):
    with open(MANIFEST, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cmd_make(a):
    from shortsgen.rings import Params, make
    p = Params(rings=a.rings, gap_deg=a.gap, palette=a.palette, seed=a.seed,
               target_min=a.min_len, target_max=a.max_len)
    if a.hook:
        p.hook = a.hook.replace("\\n", "\n")
    os.makedirs("out", exist_ok=True)
    path = f"out/{a.exp}.mp4"
    sim = make(p, path)
    meta = {"exp": a.exp, "format": "escape_rings", "file": path, "rings": p.rings, "gap_deg": p.gap_deg,
            "palette": p.palette, "seed": p.seed, "hook": p.hook.format(n=p.rings), "length_s": round(sim.duration, 1),
            "made_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"}
    rows = [r for r in load_manifest() if r["exp"] != a.exp] + [meta]
    save_manifest(rows)
    print(json.dumps(meta, ensure_ascii=False))


def cmd_upload(a):
    from shortsgen import yt
    rows = load_manifest()
    row = next(r for r in rows if r["exp"] == a.exp)
    if row.get("video_id"):
        sys.exit(f"{a.exp} already uploaded as {row['video_id']}")
    desc = a.description or f"{a.title}\n\n#shorts #satisfying #physics #simulation"
    tags = ["shorts", "satisfying", "physics", "simulation", "ball", "rings", "oddly satisfying"]
    vid = yt.upload(row["file"], a.title, desc, tags, publish_at=a.publish_at)
    row.update(video_id=vid, title=a.title, publish_at=a.publish_at,
               uploaded_at=dt.datetime.utcnow().isoformat(timespec="seconds") + "Z")
    save_manifest(rows)
    print(vid, f"https://youtube.com/shorts/{vid}")


def cmd_stats(a):
    from shortsgen import yt
    rows = [r for r in load_manifest() if r.get("video_id")]
    if not rows:
        sys.exit("nothing uploaded yet")
    s = yt.stats([r["video_id"] for r in rows])
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with open(STATS_LOG, "a") as f:
        for r in rows:
            v = s.get(r["video_id"], {})
            f.write(json.dumps({"t": now, "exp": r["exp"], "video_id": r["video_id"], **v}, ensure_ascii=False) + "\n")
            print(f"{r['exp']:5} {v.get('views', '?'):>7} views {v.get('likes', '?'):>5} likes  {v.get('privacy', '?'):8} {v.get('title', '')}")


def cmd_channel(a):
    from shortsgen import yt
    ch, items = yt.channel_uploads(a.limit)
    print(ch["snippet"]["title"], ch["id"], ch["statistics"])
    s = yt.stats([v for v, _ in items])
    for vid, title in items:
        v = s.get(vid, {})
        print(f"{vid}  {v.get('views', '?'):>7}  {v.get('privacy', '?'):8} {title}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--exp", required=True)
    m.add_argument("--rings", type=int, default=20)
    m.add_argument("--gap", type=float, default=55)
    m.add_argument("--palette", default="rainbow")
    m.add_argument("--seed", type=int, default=1)
    m.add_argument("--hook")
    m.add_argument("--min-len", type=float, default=25)
    m.add_argument("--max-len", type=float, default=45)
    u = sub.add_parser("upload")
    u.add_argument("--exp", required=True)
    u.add_argument("--title", required=True)
    u.add_argument("--description")
    u.add_argument("--publish-at")
    sub.add_parser("stats")
    c = sub.add_parser("channel")
    c.add_argument("--limit", type=int, default=50)
    a = ap.parse_args()
    {"make": cmd_make, "upload": cmd_upload, "stats": cmd_stats, "channel": cmd_channel}[a.cmd](a)


if __name__ == "__main__":
    main()
