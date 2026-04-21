"""
analyze_trends.py — AI-powered trend analysis via Claude API.

Three focused Claude calls:
  1. Trend & learning analysis (what's happening in AI today)
  2. Sentiment + what to explore next
  3. Own-channel daily recap (Nate B Jones)

Deterministic topic counting runs locally (no Claude needed for that step).

Run directly:  python tools/analyze_trends.py
"""

import json
import sys
import time
import re
import datetime
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.config import (
    ANTHROPIC_API_KEY, SEARCH_KEYWORDS, RISING_CONTENT_DAYS, TMP_DIR
)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def build_anthropic_client() -> anthropic.Anthropic:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set in .env")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ---------------------------------------------------------------------------
# Deterministic topic counting (no AI needed)
# ---------------------------------------------------------------------------

def calculate_topic_trends(keyword_videos: list[dict]) -> list[dict]:
    """
    Count keyword frequency across video titles, descriptions, and tags.
    Also flags 'rising' if the majority of hits are from recent videos.
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=RISING_CONTENT_DAYS)

    counts: Counter = Counter()
    recent_counts: Counter = Counter()

    for vid in keyword_videos:
        text = " ".join([
            vid.get("title", ""),
            vid.get("description", ""),
            " ".join(vid.get("tags", [])),
        ]).lower()

        pub = vid.get("published_at", "")
        try:
            pub_dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None)
            is_recent = pub_dt > cutoff
        except Exception:
            is_recent = False

        for kw in SEARCH_KEYWORDS:
            if kw.lower() in text:
                counts[kw] += 1
                if is_recent:
                    recent_counts[kw] += 1

    results = []
    for topic, count in counts.most_common(15):
        recent = recent_counts.get(topic, 0)
        momentum = "rising" if recent >= count * 0.6 else (
                    "fading" if recent <= count * 0.2 else "stable")
        results.append({
            "topic":     topic,
            "count":     count,
            "momentum":  momentum,
        })

    return results


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def _prepare_video_summary(keyword_videos: list[dict], top_n: int = 30) -> str:
    top = sorted(keyword_videos, key=lambda v: v["view_count"], reverse=True)[:top_n]
    slim = [{
        "title":           v["title"],
        "channel":         v["channel_name"],
        "views":           v["view_count"],
        "likes":           v["like_count"],
        "comments":        v["comment_count"],
        "engagement_pct":  v["engagement_rate"],
        "published":       v["published_at"][:10],
        "tags":            v.get("tags", [])[:5],
        "description":     v.get("description", "")[:200],
        "keyword":         v.get("search_keyword", ""),
    } for v in top]
    return json.dumps(slim, ensure_ascii=False)


def _prepare_transcript_summary(transcripts: list[dict],
                                  max_per: int = 800) -> str:
    available = [t for t in transcripts if t.get("transcript_available")][:15]
    slim = [{
        "title":    t["title"],
        "channel":  t["channel_name"],
        "excerpt":  t["transcript_text"][:max_per],
    } for t in available]
    return json.dumps(slim, ensure_ascii=False)


def _prepare_comment_summary(comment_samples: dict[str, list],
                               keyword_videos: list[dict]) -> str:
    id_to_title = {v["video_id"]: v["title"] for v in keyword_videos}
    slim = {
        id_to_title.get(vid_id, vid_id): comments[:5]
        for vid_id, comments in comment_samples.items()
    }
    return json.dumps(slim, ensure_ascii=False)


def _prepare_channel_summary(channel_data: list[dict]) -> str:
    slim = [{
        "channel":     ch["channel_name"],
        "subscribers": ch["subscriber_count"],
        "total_views": ch["total_view_count"],
        "recent_videos": [{
            "title":      v["title"],
            "views":      v["view_count"],
            "engagement": v["engagement_rate"],
            "published":  v["published_at"][:10],
        } for v in ch.get("recent_videos", [])[:3]],
    } for ch in channel_data if not ch.get("is_own_channel")]
    return json.dumps(slim, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Claude API calls
# ---------------------------------------------------------------------------

def _call_claude(client: anthropic.Anthropic, system: str,
                  user: str, max_tokens: int = 2000,
                  temperature: float = 0.3, retries: int = 2) -> dict | None:
    """
    Call Claude and parse JSON from the response.
    Returns parsed dict or None on failure.
    """
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = response.content[0].text.strip()

            # Strip markdown code fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            return json.loads(text)

        except json.JSONDecodeError as e:
            print(f"  [claude] JSON parse error (attempt {attempt+1}): {e}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(5)
        except anthropic.APIError as e:
            print(f"  [claude] API error: {e}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(10)

    return None


def call_claude_trends(client, video_meta: str, transcripts: str,
                        date: str) -> dict:
    """Call 1: Trend & learning analysis."""
    system = (
        "You are an expert AI/tech analyst. Your job is to help someone stay at the "
        "forefront of AI tools, research, and trends. Focus on learning value — what's "
        "new, what's important, what tools or concepts are gaining momentum. "
        f"Today's date: {date}. "
        "Respond ONLY with valid JSON matching the exact schema provided. No markdown, no explanation."
    )

    user = f"""Analyse this YouTube data from the AI/automation niche for {date}.

VIDEO METADATA (top videos by views):
{video_meta}

TRANSCRIPT EXCERPTS (where available):
{transcripts}

Return a JSON object with EXACTLY this schema:
{{
  "executive_summary": [
    "5 strings — key learning-focused takeaways about what's happening in AI today"
  ],
  "topic_trends_narrative": "1-2 sentence description of the dominant topics/themes",
  "whats_new": [
    {{
      "item": "name of AI tool, model, paper, or product release",
      "significance": "why it matters for someone learning AI",
      "source_video": "title of the video that mentioned it"
    }}
  ],
  "whats_working_narrative": "paragraph on what content types and topics are resonating and why",
  "rising_content_insights": "paragraph on new/fast-growing videos and what they signal about AI community interest",
  "top_video_summaries": [
    {{
      "title": "exact video title",
      "channel": "channel name",
      "why_watch": "one punchy sentence on why this is worth your time right now",
      "key_points": [
        "most important idea or fact from this video",
        "second key takeaway",
        "third key takeaway"
      ]
    }}
  ]
}}

For top_video_summaries: pick the 5 most informative/important videos from the metadata above.
Focus on educational value, not just view count. Each key_point should be a complete, informative sentence.
If transcript excerpts are available for a video, use them to make the key_points more specific."""

    result = _call_claude(client, system, user, max_tokens=3000)
    if result is None:
        return {
            "executive_summary":        ["Analysis unavailable — check ANTHROPIC_API_KEY"],
            "topic_trends_narrative":   "",
            "whats_new":                [],
            "whats_working_narrative":  "",
            "rising_content_insights":  "",
            "top_video_summaries":      [],
        }
    if "top_video_summaries" not in result:
        result["top_video_summaries"] = []
    return result


def call_claude_sentiment(client, comments: str, channel_data: str,
                           trends_summary: str, date: str) -> dict:
    """Call 2: Sentiment analysis + what to explore next."""
    system = (
        "You are an AI learning strategist. Analyse YouTube comment sentiment and "
        "community discussion to surface what the AI community is excited about, "
        "concerned about, or actively exploring. Your goal is to help a learner "
        "decide what to focus on next. "
        f"Today's date: {date}. "
        "Respond ONLY with valid JSON. No markdown, no explanation."
    )

    user = f"""Analyse comment sentiment and channel activity in the AI/automation niche.

COMMENT SAMPLES (by video):
{comments}

CHANNEL PERFORMANCE DATA:
{channel_data}

TREND ANALYSIS (from prior step):
{trends_summary}

Return a JSON object with EXACTLY this schema:
{{
  "sentiment_breakdown": {{
    "positive_pct": 0.0,
    "neutral_pct":  0.0,
    "negative_pct": 0.0,
    "dominant_emotion": "one word describing the prevailing feeling, e.g. excited / cautious / skeptical",
    "sample_quotes": [
      "direct quote 1 from comments",
      "direct quote 2 from comments",
      "direct quote 3 from comments"
    ]
  }},
  "overall_sentiment_score": 0.0,
  "learning_prompts": [
    {{
      "action":    "specific thing to try, read, or explore — e.g. 'Install and test Cursor Agent mode'",
      "rationale": "why this is worth your time right now based on today's data",
      "priority":  "high"
    }},
    {{
      "action":    "second learning prompt",
      "rationale": "rationale",
      "priority":  "medium"
    }},
    {{
      "action":    "third learning prompt",
      "rationale": "rationale",
      "priority":  "low"
    }}
  ]
}}

Note: overall_sentiment_score must be a float between -1.0 (very negative) and 1.0 (very positive).
Percentages must sum to 100."""

    result = _call_claude(client, system, user, max_tokens=1500, temperature=0.4)
    if result is None:
        return {
            "sentiment_breakdown": {
                "positive_pct": 0, "neutral_pct": 100, "negative_pct": 0,
                "dominant_emotion": "unknown",
                "sample_quotes": ["Analysis unavailable"],
            },
            "overall_sentiment_score": 0.0,
            "learning_prompts": [],
        }
    return result


def call_claude_own_channel_recap(client, own_transcripts: list[dict],
                                   own_channel_videos: list[dict],
                                   date: str) -> dict:
    """Call 3: Recap of Nate's own channel videos."""
    if not own_transcripts and not own_channel_videos:
        return {
            "videos_found":     0,
            "recap_available":  False,
            "video_summaries":  [],
            "note":             "No videos published today on the own channel.",
        }

    # Combine metadata + transcripts
    combined = []
    vid_map = {v["video_id"]: v for v in own_channel_videos}
    for t in own_transcripts:
        meta = vid_map.get(t["video_id"], {})
        combined.append({
            "title":      t["title"],
            "views":      meta.get("view_count", 0),
            "likes":      meta.get("like_count", 0),
            "comments":   meta.get("comment_count", 0),
            "published":  meta.get("published_at", "")[:10],
            "transcript": t.get("transcript_text", "")[:3000],
        })

    system = (
        "You are summarising the creator's own YouTube videos for their personal daily briefing. "
        "Be concise, accurate, and extract the most important learning points. "
        f"Today's date: {date}. "
        "Respond ONLY with valid JSON. No markdown, no explanation."
    )

    user = f"""Summarise these videos from the 'AI News & Strategy Daily | Nate B Jones' channel.

VIDEOS:
{json.dumps(combined, ensure_ascii=False)}

Return a JSON object with EXACTLY this schema:
{{
  "videos_found":    {len(combined)},
  "recap_available": true,
  "video_summaries": [
    {{
      "title":        "video title",
      "key_points":   [
        "bullet 1 — most important idea from the video",
        "bullet 2",
        "bullet 3",
        "bullet 4",
        "bullet 5"
      ],
      "standout_insights": [
        "notable quote or idea worth remembering (verbatim or close paraphrase)"
      ],
      "engagement_snapshot": {{
        "views":    0,
        "likes":    0,
        "comments": 0
      }}
    }}
  ]
}}"""

    result = _call_claude(client, system, user, max_tokens=1500, temperature=0.2)
    if result is None:
        return {
            "videos_found":    len(combined),
            "recap_available": False,
            "video_summaries": [],
            "note":            "Claude analysis failed — check API key.",
        }
    return result


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def analyze_trends(fetch_output: dict, transcript_output: dict) -> dict:
    """
    Run all three Claude analysis calls and save output.
    Reads from fetch_output + transcript_output, saves to .tmp/analysis_YYYY-MM-DD.json.
    """
    date_str = fetch_output.get("fetch_date", datetime.date.today().isoformat())
    out_path = TMP_DIR / f"analysis_{date_str}.json"

    print(f"[analyze] Starting trend analysis for {date_str}")

    client = build_anthropic_client()

    keyword_videos = fetch_output.get("keyword_videos", [])
    channel_data   = fetch_output.get("channel_data", [])
    comment_samples = fetch_output.get("comment_samples", {})
    transcripts     = transcript_output.get("transcripts", [])
    own_transcripts = transcript_output.get("own_channel_transcripts", [])

    # Own channel videos
    own_channel_videos = []
    for ch in channel_data:
        if ch.get("is_own_channel"):
            own_channel_videos = ch.get("recent_videos", [])
            break

    # Deterministic topic counting
    print("[analyze] Calculating topic trends (deterministic) ...")
    topic_trends = calculate_topic_trends(keyword_videos)

    # Claude Call 1: Trends
    print("[analyze] Claude call 1/3 — trend & learning analysis ...")
    trends_result = call_claude_trends(
        client,
        video_meta=_prepare_video_summary(keyword_videos),
        transcripts=_prepare_transcript_summary(transcripts),
        date=date_str,
    )
    time.sleep(2)

    # Claude Call 2: Sentiment + learning prompts
    print("[analyze] Claude call 2/3 — sentiment & what to explore ...")
    sentiment_result = call_claude_sentiment(
        client,
        comments=_prepare_comment_summary(comment_samples, keyword_videos),
        channel_data=_prepare_channel_summary(channel_data),
        trends_summary=json.dumps({
            "executive_summary":     trends_result.get("executive_summary", []),
            "topic_trends_narrative": trends_result.get("topic_trends_narrative", ""),
        }, ensure_ascii=False),
        date=date_str,
    )
    time.sleep(2)

    # Claude Call 3: Own channel recap
    print("[analyze] Claude call 3/3 — own channel recap ...")
    own_recap = call_claude_own_channel_recap(
        client,
        own_transcripts=own_transcripts,
        own_channel_videos=own_channel_videos,
        date=date_str,
    )

    # Assemble final output
    output = {
        "analysis_date":          date_str,
        "model_used":             "claude-opus-4-6",
        "executive_summary":      trends_result.get("executive_summary", []),
        "topic_trends":           topic_trends,
        "topic_trends_narrative": trends_result.get("topic_trends_narrative", ""),
        "whats_new":              trends_result.get("whats_new", []),
        "whats_working_narrative": trends_result.get("whats_working_narrative", ""),
        "rising_content_insights": trends_result.get("rising_content_insights", ""),
        "top_video_summaries":    trends_result.get("top_video_summaries", []),
        "sentiment_breakdown":    sentiment_result.get("sentiment_breakdown", {}),
        "overall_sentiment_score": sentiment_result.get("overall_sentiment_score", 0.0),
        "learning_prompts":       sentiment_result.get("learning_prompts", []),
        "own_channel_recap":      own_recap,
    }

    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[analyze] Done. Saved: {out_path}")
    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    date_str = datetime.date.today().isoformat()

    raw_path = TMP_DIR / f"youtube_raw_{date_str}.json"
    transcript_path = TMP_DIR / f"transcripts_{date_str}.json"

    # Fallback to most recent if today's not found
    for path, pattern in [(raw_path, "youtube_raw_*.json"),
                           (transcript_path, "transcripts_*.json")]:
        if not path.exists():
            candidates = sorted(TMP_DIR.glob(pattern), reverse=True)
            if not candidates:
                print(f"[error] No {pattern} found. Run the fetch/transcript steps first.",
                      file=sys.stderr)
                sys.exit(1)
            path = candidates[0]
            print(f"[analyze] Using: {path}")

    fetch_output      = json.loads(raw_path.read_text(encoding="utf-8"))
    transcript_output = json.loads(transcript_path.read_text(encoding="utf-8"))

    try:
        analyze_trends(fetch_output, transcript_output)
    except ValueError as e:
        print(f"\n[CONFIG ERROR] {e}", file=sys.stderr)
        sys.exit(1)
