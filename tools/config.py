"""
config.py — Central configuration hub for the YouTube AI Intelligence pipeline.
All other tools import from here. Edit this file to customise channels, keywords,
email settings, and visual design.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)
(TMP_DIR / "thumbs").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# API CREDENTIALS (pulled from .env — never hardcode here)
# ---------------------------------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
REPORT_RECIPIENT_EMAIL = os.getenv("REPORT_RECIPIENT_EMAIL")

# ---------------------------------------------------------------------------
# TRACKED CHANNELS
# is_own_channel=True  →  data routed to Slide 11 (Nate B Jones Daily Recap)
# ---------------------------------------------------------------------------
TRACKED_CHANNELS = [
    {
        "name": "Nate B Jones",
        "channel_id": "UC0C-17n9iuUQPylguM1d-lQ",
        "is_own_channel": True,
    },
    {
        "name": "Matt Wolfe",
        "channel_id": "UCX7oe65cdos3yfEsQylBIvQ",
        "is_own_channel": False,
    },
    {
        "name": "Lex Fridman",
        "channel_id": "UCSHZKyawb77ixDdsGog4iWA",
        "is_own_channel": False,
    },
    {
        "name": "Fireship",
        "channel_id": "UCsBjURrPoezykLs9EqgamOA",
        "is_own_channel": False,
    },
    {
        "name": "Two Minute Papers",
        "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
        "is_own_channel": False,
    },
    {
        "name": "David Shapiro",
        "channel_id": "UCddiUEpeqJcYeBxX1IVBKvQ",
        "is_own_channel": False,
    },
    {
        "name": "Andrej Karpathy",
        "channel_id": "UCnM64YKEcFDN91NXGL-4rug",
        "is_own_channel": False,
    },
    {
        "name": "Sam Witteveen",
        "channel_id": "UCyR2Ct3pDOeZSRyZH5hPO-Q",
        "is_own_channel": False,
    },
    {
        "name": "AI Explained",
        "channel_id": "UCNJ1Ymd5yFuUPtn21xtRbbw",
        "is_own_channel": False,
    },
    {
        "name": "Yannic Kilcher",
        "channel_id": "UCZHmQk67mSJgfCCTn7xBfew",
        "is_own_channel": False,
    },
    {
        "name": "Riley Brown",
        "channel_id": "",  # Fill in channel ID — search YouTube for @RileyBrownAI or similar
        "is_own_channel": False,
    },
]

# Convenience: own channel config
OWN_CHANNEL = next(c for c in TRACKED_CHANNELS if c["is_own_channel"])

# ---------------------------------------------------------------------------
# SEARCH KEYWORDS
# These are used to discover trending videos outside tracked channels.
# ---------------------------------------------------------------------------
SEARCH_KEYWORDS = [
    "AI automation 2026",
    "Claude AI",
    "GPT-4o",
    "LLM agents",
    "n8n automation",
    "AI tools",
    "artificial intelligence news",
    "OpenAI 2026",
    "Anthropic Claude",
    "AI productivity",
]

# Results to fetch per keyword (max 50 per API call)
RESULTS_PER_KEYWORD = 10

# Top N videos (by view count) to extract transcripts for
TRANSCRIPT_TOP_N = 20

# Videos published within this many days are flagged as "rising content"
RISING_CONTENT_DAYS = 7

# How many videos to pull from own channel for daily recap
OWN_CHANNEL_RECENT_N = 4

# How many comment threads to fetch per video (top N most-viewed)
COMMENT_VIDEOS_N = 15
COMMENTS_PER_VIDEO = 10

# ---------------------------------------------------------------------------
# QUOTA BUDGET (documentation only — not enforced at runtime)
# YouTube Data API v3 free tier: 10,000 units/day
# ---------------------------------------------------------------------------
QUOTA_BUDGET = {
    "keyword_searches":   len(SEARCH_KEYWORDS) * 100,          # 1,000 units
    "video_stats":        len(SEARCH_KEYWORDS) * RESULTS_PER_KEYWORD,  # 100 units
    "channel_stats":      len(TRACKED_CHANNELS),                # 11 units
    "channel_recent":     len(TRACKED_CHANNELS) * 100,          # 1,100 units (search per channel)
    "comment_threads":    COMMENT_VIDEOS_N,                     # 15 units
    # Estimated total: ~2,226 units  (22% of daily budget)
}

# ---------------------------------------------------------------------------
# EMAIL TEMPLATES
# ---------------------------------------------------------------------------
REPORT_EMAIL_SUBJECT = "AI Intelligence Report — {date}"

REPORT_EMAIL_BODY = """\
Hi Gem,

Your daily AI niche intelligence report is attached.

Date: {date}
Videos analysed: {video_count}
Channels tracked: {channel_count}
Nate B Jones videos found: {own_video_count}

Stay at the forefront.

— WAT Framework (automated)
"""

# ---------------------------------------------------------------------------
# DESIGN SYSTEM
# Referenced by generate_report_pdf.py.
# Dark GitHub-style palette, professional and clean.
# ---------------------------------------------------------------------------
DESIGN = {
    # Palette
    "bg_dark":       "#0D1117",   # slide background
    "bg_card":       "#161B22",   # card / panel backgrounds
    "accent_blue":   "#58A6FF",   # primary accent — headlines, primary bars
    "accent_green":  "#3FB950",   # positive sentiment, growth, rising
    "accent_red":    "#F85149",   # negative sentiment, drops, warnings
    "accent_gold":   "#D29922",   # highlights, featured items, high priority
    "accent_purple": "#A371F7",   # secondary data series
    "text_primary":  "#E6EDF3",   # body text
    "text_muted":    "#8B949E",   # secondary text, labels, captions
    "divider":       "#21262D",   # separator lines, grid lines

    # Typography (matplotlib built-ins, no font install needed)
    "font":          "DejaVu Sans",
    "size_h1":       32,
    "size_h2":       20,
    "size_h3":       14,
    "size_body":     10,
    "size_small":    8,

    # Slide dimensions — landscape letter
    "fig_w":         11.0,
    "fig_h":         8.5,
    "dpi":           150,

    # Chart colour cycle (used for multi-series charts)
    "bar_colors":    ["#58A6FF", "#3FB950", "#D29922", "#A371F7", "#F78166"],
}


# ---------------------------------------------------------------------------
# QUICK SELF-TEST — run  python tools/config.py  to verify setup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("WAT Framework — YouTube Intelligence Pipeline")
    print("=" * 60)

    checks = {
        "GOOGLE_API_KEY":         GOOGLE_API_KEY,
        "ANTHROPIC_API_KEY":      ANTHROPIC_API_KEY,
        "GMAIL_ADDRESS":          GMAIL_ADDRESS,
        "GMAIL_APP_PASSWORD":     GMAIL_APP_PASSWORD,
        "REPORT_RECIPIENT_EMAIL": REPORT_RECIPIENT_EMAIL,
    }

    all_ok = True
    for key, val in checks.items():
        status = "OK" if val else "MISSING"
        masked = (val[:4] + "****") if val else "—"
        print(f"  {status:8}  {key}: {masked}")
        if not val:
            all_ok = False

    print()
    print(f"  Tracked channels:  {len(TRACKED_CHANNELS)}")
    print(f"  Own channel:       {OWN_CHANNEL['name']} ({OWN_CHANNEL['channel_id'] or 'ID not set'})")
    print(f"  Search keywords:   {len(SEARCH_KEYWORDS)}")
    print(f"  Est. quota/day:    ~{sum(QUOTA_BUDGET.values())} units  (budget: 10,000)")
    print(f"  Output directory:  {TMP_DIR}")
    print()

    if all_ok:
        print("  All credentials present. Ready to run.")
    else:
        print("  WARNING: Missing credentials — update .env before running.")
        sys.exit(1)
