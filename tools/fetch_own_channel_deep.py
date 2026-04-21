"""
fetch_own_channel_deep.py — Fetch last N videos from Nate B Jones' channel with
per-video AI analysis (bullet-point summaries for slides 12–14).

Pipeline:
  YouTube API → last 4 video IDs → stats + comments → transcript attempt
  → Claude: per-video 5–7 key-point summaries
  → .tmp/own_channel_deep_YYYY-MM-DD.json

Run directly:  python tools/fetch_own_channel_deep.py
"""

import json
import re
import sys
import time
import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import anthropic
from youtube_transcript_api import YouTubeTranscriptApi
try:
    from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
except ImportError:
    try:
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
    except ImportError:
        class TranscriptsDisabled(Exception): pass
        class NoTranscriptFound(Exception): pass
        class VideoUnavailable(Exception): pass

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.config import GOOGLE_API_KEY, ANTHROPIC_API_KEY, OWN_CHANNEL, TMP_DIR


# ---------------------------------------------------------------------------
# Transcript extraction
# ---------------------------------------------------------------------------

def _get_transcript(video_id: str, max_chars: int = 12000) -> str:
    """Attempt to fetch transcript. Returns empty string if unavailable."""
    try:
        api = YouTubeTranscriptApi()
        try:
            tlist = api.list(video_id)
            try:
                t = tlist.find_manually_created_transcript(["en", "en-US", "en-GB"])
            except Exception:
                try:
                    t = tlist.find_generated_transcript(["en", "en-US", "en-GB"])
                except Exception:
                    t = next(iter(tlist))
            fetched = t.fetch()
        except Exception:
            fetched = api.fetch(video_id)

        parts = []
        for e in fetched:
            if hasattr(e, "text"):
                parts.append(e.text)
            elif isinstance(e, dict):
                parts.append(e.get("text", ""))
        full = " ".join(parts).replace("\n", " ").strip()
        return full[:max_chars]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Claude analysis
# ---------------------------------------------------------------------------

def _call_claude_summaries(client, prompt_data: list[dict], date: str) -> list[dict]:
    """Send video data to Claude and get per-video bullet-point summaries."""
    system = (
        "You are summarising YouTube videos from 'AI News & Strategy Daily | Nate B Jones' "
        "for the creator's personal daily briefing. Your job is to extract the most important, "
        "specific, and actionable points made in each video. Be concrete — avoid vague generalisations. "
        f"Today's date: {date}. "
        "Respond ONLY with valid JSON. No markdown fences, no explanation."
    )

    user = f"""Analyse these videos from the Nate B Jones YouTube channel and produce per-video summaries.

VIDEOS:
{json.dumps(prompt_data, ensure_ascii=False, indent=2)}

Return a JSON object with EXACTLY this schema:
{{
  "video_summaries": [
    {{
      "video_id": "exact video_id from input",
      "one_liner": "One sentence capturing the core thesis or argument of this video",
      "key_points": [
        "Specific insight, claim, or fact Nate discusses — include enough detail to be useful without watching the video",
        "Another concrete takeaway — name tools, numbers, or concepts where relevant",
        "Third key insight",
        "Fourth key insight",
        "Fifth key insight",
        "Sixth key insight — include if content warrants it",
        "Seventh key insight — include if content warrants it"
      ]
    }}
  ]
}}

Rules:
- Generate 5–7 key_points per video (never fewer than 5)
- Each key_point must be a complete sentence with specific, concrete detail
- If a transcript is provided, extract actual claims, data, and insights from it
- If no transcript, infer from the title, description, and top comments
- Order key_points from most important to least important
- One entry per video — include all {len(prompt_data)} videos"""

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4000,
                temperature=0.25,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = resp.content[0].text.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            result = json.loads(text)
            summaries = result.get("video_summaries", [])
            print(f"  [claude] Received {len(summaries)} video summaries")
            return summaries
        except json.JSONDecodeError as e:
            print(f"  [claude] JSON parse error (attempt {attempt+1}): {e}", file=sys.stderr)
            if attempt < 2:
                time.sleep(5)
        except Exception as e:
            print(f"  [claude] Error: {e}", file=sys.stderr)
            if attempt < 2:
                time.sleep(10)

    return []


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def fetch_own_channel_deep(n_videos: int = 4) -> dict:
    """
    Fetch last n_videos from the own channel, extract transcripts + comments,
    run Claude analysis, and save to .tmp/own_channel_deep_YYYY-MM-DD.json.
    """
    date_str = datetime.date.today().isoformat()
    out_path = TMP_DIR / f"own_channel_deep_{date_str}.json"

    channel_id   = OWN_CHANNEL["channel_id"]
    channel_name = OWN_CHANNEL["name"]

    print(f"[own_deep] Fetching last {n_videos} videos from: {channel_name}")
    print(f"[own_deep] Channel ID: {channel_id}")

    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in .env")
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    yt     = build("youtube", "v3", developerKey=GOOGLE_API_KEY)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 1. Recent video IDs from channel
    try:
        search_resp = yt.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            order="date",
            maxResults=n_videos,
        ).execute()
    except HttpError as e:
        print(f"  [error] YouTube API: {e}", file=sys.stderr)
        output = {
            "fetch_date": date_str, "channel_name": channel_name,
            "channel_id": channel_id, "videos": [], "error": str(e),
        }
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        return output

    items = search_resp.get("items", [])
    if not items:
        print(f"  [warn] No videos returned — check channel ID: {channel_id}", file=sys.stderr)
        output = {
            "fetch_date": date_str, "channel_name": channel_name,
            "channel_id": channel_id, "videos": [],
        }
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        return output

    video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]
    print(f"[own_deep] Found {len(video_ids)} videos")

    # 2. Stats + full metadata
    stats_resp = yt.videos().list(
        part="statistics,contentDetails,snippet",
        id=",".join(video_ids),
    ).execute()
    stats_by_id = {item["id"]: item for item in stats_resp.get("items", [])}

    # 3. Comment samples (top 5 per video)
    comments_by_id: dict[str, list[str]] = {}
    for vid_id in video_ids:
        try:
            cmt_resp = yt.commentThreads().list(
                part="snippet",
                videoId=vid_id,
                maxResults=5,
                order="relevance",
                textFormat="plainText",
            ).execute()
            comments = []
            for cmt in cmt_resp.get("items", []):
                text = (cmt.get("snippet", {})
                           .get("topLevelComment", {})
                           .get("snippet", {})
                           .get("textDisplay", ""))
                if text:
                    comments.append(text[:200])
            comments_by_id[vid_id] = comments
        except Exception:
            comments_by_id[vid_id] = []
        time.sleep(0.2)

    # 4. Transcript extraction
    print(f"[own_deep] Attempting transcript extraction for {len(video_ids)} videos ...")
    transcript_by_id: dict[str, str] = {}
    for vid_id in video_ids:
        info  = stats_by_id.get(vid_id, {})
        title = info.get("snippet", {}).get("title", vid_id)
        print(f"  {vid_id} — {title[:60]} ...")
        tx = _get_transcript(vid_id, max_chars=12000)
        transcript_by_id[vid_id] = tx
        words = len(tx.split()) if tx else 0
        print(f"    -> {'%d words' % words if tx else 'no transcript'}")
        time.sleep(0.5)

    # 5. Build video records
    videos = []
    for vid_id in video_ids:
        info = stats_by_id.get(vid_id, {})
        sn   = info.get("snippet", {})
        st   = info.get("statistics", {})
        videos.append({
            "video_id":            vid_id,
            "title":               sn.get("title", ""),
            "published_at":        sn.get("publishedAt", ""),
            "description":         sn.get("description", "")[:500],
            "view_count":          int(st.get("viewCount",    0) or 0),
            "like_count":          int(st.get("likeCount",    0) or 0),
            "comment_count":       int(st.get("commentCount", 0) or 0),
            "transcript":          transcript_by_id.get(vid_id, ""),
            "transcript_available": bool(transcript_by_id.get(vid_id, "")),
            "comments":            comments_by_id.get(vid_id, []),
        })

    # 6. Claude analysis — all 4 videos in one call
    print(f"[own_deep] Sending {len(videos)} videos to Claude for analysis ...")
    prompt_data = []
    for v in videos:
        entry = {
            "video_id":    v["video_id"],
            "title":       v["title"],
            "published":   v["published_at"][:10],
            "views":       v["view_count"],
            "likes":       v["like_count"],
            "description": v["description"],
            "top_comments": v["comments"][:5],
        }
        if v["transcript"]:
            entry["transcript"] = v["transcript"][:8000]
        prompt_data.append(entry)

    summaries = _call_claude_summaries(client, prompt_data, date_str)
    summaries_by_id = {s["video_id"]: s for s in summaries}

    for v in videos:
        v["summary"] = summaries_by_id.get(v["video_id"], {
            "one_liner": "",
            "key_points": [],
        })

    output = {
        "fetch_date":   date_str,
        "channel_name": channel_name,
        "channel_id":   channel_id,
        "videos":       videos,
    }

    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    tx_count = sum(1 for v in videos if v["transcript_available"])
    print(f"[own_deep] Done. {len(videos)} videos, {tx_count}/{len(videos)} transcripts.")
    print(f"[own_deep] Saved: {out_path}")

    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        fetch_own_channel_deep(n_videos=4)
    except ValueError as e:
        print(f"\n[CONFIG ERROR] {e}", file=sys.stderr)
        sys.exit(1)
