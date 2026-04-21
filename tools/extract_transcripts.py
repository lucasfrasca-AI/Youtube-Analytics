"""
extract_transcripts.py — Free transcript extraction using youtube-transcript-api.

No YouTube API quota consumed. Reads the raw fetch output and pulls transcripts
for the top N videos by view count.

Run directly:  python tools/extract_transcripts.py
"""

import json
import sys
import time
import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from youtube_transcript_api import YouTubeTranscriptApi
try:
    from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
except ImportError:
    try:
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
    except ImportError:
        # Fallback stubs so the except clauses below still work
        class TranscriptsDisabled(Exception): pass
        class NoTranscriptFound(Exception): pass
        class VideoUnavailable(Exception): pass

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.config import TMP_DIR, TRANSCRIPT_TOP_N, OWN_CHANNEL


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_transcript(video_id: str, title: str, channel_name: str,
                        max_chars: int = 8000) -> dict:
    """
    Fetch the transcript for a single video. Never raises.
    Returns a transcript record (transcript_available=False if unavailable).
    Compatible with youtube-transcript-api v1.x (instance-based API).
    """
    record = {
        "video_id":             video_id,
        "title":                title,
        "channel_name":         channel_name,
        "transcript_text":      "",
        "transcript_available": False,
        "language":             "",
        "word_count":           0,
        "extraction_error":     None,
    }

    try:
        api = YouTubeTranscriptApi()

        # Try to list available transcripts and pick best English one
        try:
            transcript_list = api.list(video_id)
            try:
                transcript = transcript_list.find_manually_created_transcript(
                    ["en", "en-US", "en-GB"]
                )
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(
                        ["en", "en-US", "en-GB"]
                    )
                except Exception:
                    transcript = next(iter(transcript_list))

            fetched = transcript.fetch()
            lang = transcript.language_code

        except Exception:
            # Fallback: direct fetch (auto-selects best available)
            fetched = api.fetch(video_id)
            lang = "en"

        # Handle both object-based (v1.x) and dict-based (v0.x) snippet formats
        parts = []
        for e in fetched:
            if hasattr(e, "text"):
                parts.append(e.text)
            elif isinstance(e, dict):
                parts.append(e.get("text", ""))

        full_text = " ".join(parts)
        full_text = full_text.replace("\n", " ").replace("  ", " ").strip()
        full_text = full_text[:max_chars]

        record.update({
            "transcript_text":      full_text,
            "transcript_available": True,
            "language":             lang,
            "word_count":           len(full_text.split()),
        })

    except (TranscriptsDisabled, VideoUnavailable) as e:
        record["extraction_error"] = type(e).__name__
    except StopIteration:
        record["extraction_error"] = "NoTranscriptsAvailable"
    except Exception as e:
        record["extraction_error"] = str(e)[:100]

    return record


# ---------------------------------------------------------------------------
# Batch extraction
# ---------------------------------------------------------------------------

def extract_transcripts_for_videos(fetch_output: dict,
                                    top_n: int = TRANSCRIPT_TOP_N) -> dict:
    """
    Extract transcripts for the top_n keyword videos (by view count).
    Also extracts transcripts for the own channel's recent videos.
    Saves to .tmp/transcripts_YYYY-MM-DD.json.
    """
    date_str = fetch_output.get("fetch_date", datetime.date.today().isoformat())
    out_path = TMP_DIR / f"transcripts_{date_str}.json"

    keyword_videos = fetch_output.get("keyword_videos", [])
    channel_data   = fetch_output.get("channel_data", [])

    # Top N keyword videos
    top_videos = sorted(keyword_videos, key=lambda v: v["view_count"], reverse=True)[:top_n]

    # Own channel recent videos (always included for Slide 11)
    own_channel_videos = []
    for ch in channel_data:
        if ch.get("is_own_channel"):
            own_channel_videos = ch.get("recent_videos", [])
            break

    print(f"[transcripts] Extracting transcripts for {len(top_videos)} keyword videos ...")
    transcripts = []
    successful = 0

    for i, vid in enumerate(top_videos):
        vid_id = vid.get("video_id", "")
        if not vid_id:
            continue

        print(f"  [{i+1}/{len(top_videos)}] {vid['title'][:60]} ...")
        record = extract_transcript(vid_id, vid["title"], vid["channel_name"])
        if record["transcript_available"]:
            successful += 1
        else:
            print(f"    ↳ skipped: {record['extraction_error']}")
        transcripts.append(record)

        time.sleep(0.3)  # polite delay

    # Own channel transcripts
    own_transcripts = []
    if own_channel_videos:
        print(f"[transcripts] Extracting transcripts for {len(own_channel_videos)} own-channel videos ...")
        for vid in own_channel_videos:
            vid_id = vid.get("video_id", "")
            if not vid_id:
                continue
            record = extract_transcript(vid_id, vid["title"], vid["channel_name"])
            own_transcripts.append(record)
            time.sleep(0.3)

    output = {
        "fetch_date":            date_str,
        "videos_attempted":      len(top_videos),
        "videos_successful":     successful,
        "transcripts":           transcripts,
        "own_channel_transcripts": own_transcripts,
    }

    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[transcripts] Done. {successful}/{len(top_videos)} transcripts retrieved.")
    print(f"[transcripts] Own channel: {len(own_transcripts)} transcript(s).")
    print(f"[transcripts] Saved: {out_path}")

    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import glob

    date_str = datetime.date.today().isoformat()
    raw_path = TMP_DIR / f"youtube_raw_{date_str}.json"

    # Fallback: find most recent raw file
    if not raw_path.exists():
        candidates = sorted(TMP_DIR.glob("youtube_raw_*.json"), reverse=True)
        if not candidates:
            print("[error] No youtube_raw_*.json found in .tmp/. Run fetch_youtube_data.py first.",
                  file=sys.stderr)
            sys.exit(1)
        raw_path = candidates[0]
        print(f"[transcripts] Using most recent raw file: {raw_path}")

    fetch_output = json.loads(raw_path.read_text(encoding="utf-8"))
    extract_transcripts_for_videos(fetch_output)
