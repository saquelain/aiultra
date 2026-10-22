"""YouTube Data API access using credentials from environment variables.

Env vars (set in the cloud environment settings, never committed), either:
  YT_TOKEN_JSON  the full contents of an OAuth token.json, or
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import json
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_URI = "https://oauth2.googleapis.com/token"


def creds():
    if os.environ.get("YT_TOKEN_JSON"):
        # the whole token.json from an earlier OAuth login, pasted as one value
        info = json.loads(os.environ["YT_TOKEN_JSON"])
        return Credentials.from_authorized_user_info(info)
    missing = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"set YT_TOKEN_JSON, or all of: {', '.join(missing)}")
    return Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
    )


def api():
    return build("youtube", "v3", credentials=creds(), cache_discovery=False)


def analytics():
    return build("youtubeAnalytics", "v2", credentials=creds(), cache_discovery=False)


def upload(path, title, description, tags, publish_at=None, category="24"):
    """Upload a video. With publish_at (RFC3339 UTC) it stays private until then."""
    status = {"selfDeclaredMadeForKids": False, "containsSyntheticMedia": False}
    if publish_at:
        status.update(privacyStatus="private", publishAt=publish_at)
    else:
        status["privacyStatus"] = "public"
    body = {
        "snippet": {"title": title, "description": description, "tags": tags, "categoryId": category},
        "status": status,
    }
    req = api().videos().insert(part="snippet,status", body=body,
                                media_body=MediaFileUpload(path, chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def channel_uploads(limit=50):
    yt = api()
    ch = yt.channels().list(part="contentDetails,snippet,statistics", mine=True).execute()["items"][0]
    pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt.playlistItems().list(part="contentDetails,snippet", playlistId=pl, maxResults=limit).execute()["items"]
    return ch, [(i["contentDetails"]["videoId"], i["snippet"]["title"]) for i in items]


def stats(video_ids):
    out = {}
    yt = api()
    for i in range(0, len(video_ids), 50):
        r = yt.videos().list(part="statistics,status,snippet", id=",".join(video_ids[i:i + 50])).execute()
        for v in r["items"]:
            s = v["statistics"]
            out[v["id"]] = {
                "title": v["snippet"]["title"],
                "privacy": v["status"]["privacyStatus"],
                "publishAt": v["status"].get("publishAt"),
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
            }
    return out


def retention(video_ids, start, end):
    """Average view % and duration per video. Needs the yt-analytics.readonly scope; returns {} without it."""
    try:
        r = analytics().reports().query(
            ids="channel==MINE", startDate=start, endDate=end,
            metrics="views,averageViewDuration,averageViewPercentage",
            dimensions="video", filters="video==" + ",".join(video_ids),
        ).execute()
    except Exception as e:
        print("analytics unavailable:", str(e)[:200])
        return {}
    return {row[0]: {"views": row[1], "avg_sec": row[2], "avg_pct": row[3]} for row in r.get("rows", [])}
