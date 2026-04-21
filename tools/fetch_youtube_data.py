"""
fetch_youtube_data.py — YouTube Data API v3 data collection.

Fetches trending/keyword videos, channel statistics, video stats, and comment
samples for the AI/automation niche. Saves raw data to .tmp/.

Run directly:  python tools/fetch_youtube_data.py
"""

import json
import sys
import time
import datetime
import re
from pathlib import Path

# Force UTF-8 output on Windows (handles Unicode in video titles, emojis, etc.)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Allow running as a script from project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.config import (
    GOOGLE_API_KEY, TRACKED_CHANNELS, SEARCH_KEYWORDS,
    RESULTS_PER_KEYWORD, COMMENT_VIDEOS_N, COMMENTS_PER_VIDEO,
    OWN_CHANNEL_RECENT_N, TMP_DIR
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class QuotaExceededError(Exception):
    def __init__(self, units_used: int, partial_data: dict):
        super().__init__(f"YouTube API quota exceeded after {units_used} units")
        self.units_used = units_used
        self.partial_data = partial_data


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def build_youtube_client():
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set in .env")
    return build("youtube", "v3", developerKey=GOOGLE_API_KEY)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _safe_call(func, *args, retries: int = 3, **kwargs):
    """Retry wrapper for API calls. Raises QuotaExceededError on 403 quota."""
    delay = 2
    for attempt in range(retries):
        try:
            return func(*args, **kwargs).execute()
        except HttpError as e:
            if e.resp.status == 403 and "quotaExceeded" in str(e.content):
                raise QuotaExceededError(0, {}) from e
            if e.resp.status in (500, 502, 503, 504):
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            print(f"  [API error] {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  [error] {e}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return None
    return None


def _parse_iso_duration(duration: str) -> int:
    """Convert ISO 8601 duration (PT4M13S) to total seconds."""
    if not duration:
        return 0
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0
    h, m, s = (int(x or 0) for x in match.groups())
    return h * 3600 + m * 60 + s


def _hours_since(published_at: str) -> float:
    """Return hours elapsed since a YouTube ISO 8601 timestamp."""
    try:
        pub = datetime.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        return max((now - pub).total_seconds() / 3600, 0.1)
    except Exception:
        return 720  # default 30 days if parsing fails


def _build_video_record(snippet: dict, stats: dict, content: dict,
                         source: str, keyword: str | None) -> dict:
    """Merge API fields into a clean video record."""
    view_count    = int(stats.get("viewCount",    0) or 0)
    like_count    = int(stats.get("likeCount",    0) or 0)
    comment_count = int(stats.get("commentCount", 0) or 0)
    published_at  = snippet.get("publishedAt", "")
    hours         = _hours_since(published_at)

    engagement_rate = round(
        ((like_count + comment_count) / view_count * 100) if view_count else 0, 3
    )
    view_velocity = round(view_count / hours, 1)

    return {
        "video_id":      snippet.get("resourceId", {}).get("videoId", "")
                          or snippet.get("id", {}).get("videoId", ""),
        "title":         snippet.get("title", ""),
        "channel_name":  snippet.get("channelTitle", ""),
        "channel_id":    snippet.get("channelId", ""),
        "published_at":  published_at,
        "description":   snippet.get("description", "")[:500],
        "thumbnail_url": (snippet.get("thumbnails", {}).get("medium", {}) or
                          snippet.get("thumbnails", {}).get("default", {})).get("url", ""),
        "view_count":    view_count,
        "like_count":    like_count,
        "comment_count": comment_count,
        "duration_seconds": _parse_iso_duration(content.get("duration", "")),
        "tags":          snippet.get("tags", [])[:10],
        "source":        source,
        "search_keyword": keyword,
        "engagement_rate": engagement_rate,
        "view_velocity": view_velocity,
    }


# ---------------------------------------------------------------------------
# API call functions
# ---------------------------------------------------------------------------

def search_keyword(yt, keyword: str, max_results: int = 10,
                   published_after: str = None) -> list[dict]:
    """Search for videos by keyword. Costs 100 quota units per call."""
    if published_after is None:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = _safe_call(
        yt.search().list,
        part="snippet",
        q=keyword,
        type="video",
        order="relevance",
        maxResults=min(max_results, 50),
        publishedAfter=published_after,
        relevanceLanguage="en",
    )
    if not resp:
        return []
    return resp.get("items", [])


def get_video_stats(yt, video_ids: list[str]) -> dict[str, dict]:
    """Fetch statistics + contentDetails for a batch of video IDs. 1 unit per 50."""
    if not video_ids:
        return {}
    result = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = _safe_call(
            yt.videos().list,
            part="statistics,contentDetails,snippet",
            id=",".join(batch),
        )
        if resp:
            for item in resp.get("items", []):
                result[item["id"]] = {
                    "stats":   item.get("statistics", {}),
                    "content": item.get("contentDetails", {}),
                    "snippet": item.get("snippet", {}),
                }
    return result


def get_channel_stats(yt, channel_ids: list[str]) -> dict[str, dict]:
    """Fetch channel statistics + snippet. 1 unit per 50 channels."""
    if not channel_ids:
        return {}
    result = {}
    for i in range(0, len(channel_ids), 50):
        batch = [cid for cid in channel_ids[i:i + 50] if cid]
        if not batch:
            continue
        resp = _safe_call(
            yt.channels().list,
            part="statistics,snippet,contentDetails",
            id=",".join(batch),
        )
        if resp:
            for item in resp.get("items", []):
                result[item["id"]] = item
    return result


def get_channel_recent_videos(yt, channel_id: str,
                               max_results: int = 5) -> list[dict]:
    """Get recent videos from a channel via search. 100 quota units."""
    if not channel_id:
        return []
    resp = _safe_call(
        yt.search().list,
        part="snippet",
        channelId=channel_id,
        type="video",
        order="date",
        maxResults=min(max_results, 50),
    )
    if not resp:
        return []
    return resp.get("items", [])


def get_comment_samples(yt, video_ids: list[str],
                         max_per_video: int = 10) -> dict[str, list[str]]:
    """Fetch top comments for a list of video IDs. 1 unit per video."""
    result = {}
    for vid in video_ids:
        resp = _safe_call(
            yt.commentThreads().list,
            part="snippet",
            videoId=vid,
            maxResults=min(max_per_video, 100),
            order="relevance",
            textFormat="plainText",
        )
        if not resp:
            continue
        comments = []
        for item in resp.get("items", []):
            text = (item.get("snippet", {})
                       .get("topLevelComment", {})
                       .get("snippet", {})
                       .get("textDisplay", ""))
            if text:
                comments.append(text[:300])
        result[vid] = comments
        time.sleep(0.2)  # gentle rate limiting
    return result


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def fetch_all() -> dict:
    """
    Full pipeline: keyword search → channel stats → video stats → comments.
    Saves output to .tmp/youtube_raw_YYYY-MM-DD.json and returns it.
    """
    date_str = datetime.date.today().isoformat()
    out_path = TMP_DIR / f"youtube_raw_{date_str}.json"

    print(f"[fetch] Starting YouTube data fetch for {date_str}")

    yt = build_youtube_client()
    quota_used = 0

    # ---- 1. Keyword searches -----------------------------------------------
    print(f"[fetch] Searching {len(SEARCH_KEYWORDS)} keywords ({RESULTS_PER_KEYWORD} results each) ...")
    raw_search_items = []
    for kw in SEARCH_KEYWORDS:
        items = search_keyword(yt, kw, max_results=RESULTS_PER_KEYWORD)
        quota_used += 100
        for item in items:
            item["_search_keyword"] = kw
        raw_search_items.extend(items)
        time.sleep(0.5)

    # Deduplicate by video ID (keep first occurrence)
    seen_ids: set[str] = set()
    unique_search_items = []
    for item in raw_search_items:
        vid_id = item.get("id", {}).get("videoId", "")
        if vid_id and vid_id not in seen_ids:
            seen_ids.add(vid_id)
            unique_search_items.append(item)

    print(f"[fetch]   -> {len(unique_search_items)} unique videos from keyword search")

    # ---- 2. Video stats for all found videos --------------------------------
    search_video_ids = [
        item["id"]["videoId"]
        for item in unique_search_items
        if item.get("id", {}).get("videoId")
    ]
    print(f"[fetch] Fetching video stats for {len(search_video_ids)} videos ...")
    video_stats = get_video_stats(yt, search_video_ids)
    quota_used += max(1, len(search_video_ids) // 50 + 1)

    # Build clean keyword_videos list
    keyword_videos = []
    for item in unique_search_items:
        vid_id = item.get("id", {}).get("videoId", "")
        if not vid_id or vid_id not in video_stats:
            continue
        entry = video_stats[vid_id]
        record = _build_video_record(
            snippet=entry.get("snippet", item.get("snippet", {})),
            stats=entry["stats"],
            content=entry["content"],
            source="keyword_search",
            keyword=item.get("_search_keyword"),
        )
        record["video_id"] = vid_id
        keyword_videos.append(record)

    # Sort by view count descending
    keyword_videos.sort(key=lambda v: v["view_count"], reverse=True)

    # ---- 3. Channel stats + recent videos -----------------------------------
    print(f"[fetch] Fetching stats for {len(TRACKED_CHANNELS)} tracked channels ...")
    channel_ids = [c["channel_id"] for c in TRACKED_CHANNELS if c["channel_id"]]
    channel_stats_raw = get_channel_stats(yt, channel_ids)
    quota_used += max(1, len(channel_ids) // 50 + 1)

    channel_data = []
    for ch in TRACKED_CHANNELS:
        cid = ch["channel_id"]
        if not cid:
            print(f"  [warn] No channel_id set for '{ch['name']}' — skipping", file=sys.stderr)
            continue

        raw = channel_stats_raw.get(cid, {})
        stats = raw.get("statistics", {})

        # Fetch recent videos (own channel gets more)
        n_recent = OWN_CHANNEL_RECENT_N if ch.get("is_own_channel") else 5
        recent_items = get_channel_recent_videos(yt, cid, max_results=n_recent)
        quota_used += 100

        # Fallback for own channel: if direct channel search returned nothing,
        # try a keyword search by channel name to find their latest content
        if not recent_items and ch.get("is_own_channel"):
            print(f"  [warn] Own channel '{ch['name']}' returned no videos via channel ID — trying name search ...")
            recent_items = search_keyword(yt, f'"{ch["name"]}" AI', max_results=n_recent)
            quota_used += 100
            if not recent_items:
                recent_items = search_keyword(yt, ch["name"], max_results=n_recent)
                quota_used += 100
            if recent_items:
                print(f"  [info] Found {len(recent_items)} videos via name search fallback")

        # Get stats for recent videos
        recent_ids = [i["id"]["videoId"] for i in recent_items if i.get("id", {}).get("videoId")]
        recent_stats = get_video_stats(yt, recent_ids) if recent_ids else {}
        quota_used += 1 if recent_ids else 0

        recent_videos = []
        for item in recent_items:
            vid_id = item.get("id", {}).get("videoId", "")
            if not vid_id:
                continue
            entry = recent_stats.get(vid_id, {})
            record = _build_video_record(
                snippet=entry.get("snippet", item.get("snippet", {})),
                stats=entry.get("stats", {}),
                content=entry.get("content", {}),
                source="channel_feed",
                keyword=None,
            )
            record["video_id"] = vid_id
            record["channel_name"] = ch["name"]
            recent_videos.append(record)

        channel_data.append({
            "channel_id":       cid,
            "channel_name":     ch["name"],
            "is_own_channel":   ch.get("is_own_channel", False),
            "subscriber_count": int(stats.get("subscriberCount", 0) or 0),
            "total_view_count": int(stats.get("viewCount", 0) or 0),
            "video_count":      int(stats.get("videoCount", 0) or 0),
            "recent_videos":    recent_videos,
        })
        time.sleep(0.3)

    # ---- 4. Comment samples (top N most-viewed keyword videos) --------------
    top_vids_for_comments = [v["video_id"] for v in keyword_videos[:COMMENT_VIDEOS_N]]
    print(f"[fetch] Fetching comments for top {len(top_vids_for_comments)} videos ...")
    comment_samples = get_comment_samples(yt, top_vids_for_comments, COMMENTS_PER_VIDEO)
    quota_used += len(top_vids_for_comments)

    # ---- 5. Assemble output -------------------------------------------------
    all_video_ids = list({v["video_id"] for v in keyword_videos})
    for ch in channel_data:
        for v in ch["recent_videos"]:
            all_video_ids.append(v["video_id"])
    all_video_ids = list(set(all_video_ids))

    output = {
        "fetch_date":      date_str,
        "fetch_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "quota_used":      quota_used,
        "keyword_videos":  keyword_videos,
        "channel_data":    channel_data,
        "all_video_ids":   all_video_ids,
        "comment_samples": comment_samples,
    }

    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[fetch] Done. {len(keyword_videos)} keyword videos, {len(channel_data)} channels.")
    print(f"[fetch] Estimated quota used: ~{quota_used} units")
    print(f"[fetch] Saved: {out_path}")

    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        fetch_all()
    except QuotaExceededError as e:
        print(f"\n[QUOTA EXCEEDED] {e}", file=sys.stderr)
        print("Check quota at: console.cloud.google.com -> APIs -> YouTube Data API v3 -> Quotas")
        sys.exit(1)
    except ValueError as e:
        print(f"\n[CONFIG ERROR] {e}", file=sys.stderr)
        print("Run  python tools/config.py  to check your .env setup.")
        sys.exit(1)
