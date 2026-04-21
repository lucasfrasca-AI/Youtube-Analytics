# YouTube AI Niche Daily Intelligence Report

## Objective
Generate and deliver a 14-slide professional PDF analytics report each morning
covering trending AI tools, must-watch videos, community sentiment, learning
recommendations, and a personal recap of the Nate B Jones channel.

**Goal:** Open this PDF with your morning coffee and immediately know what's
happening in AI, what's worth your attention, and what to explore that day.

---

## Prerequisites

All of these must be set before the first run:

### `.env` Variables
```
GOOGLE_API_KEY=           # YouTube Data API v3 key
ANTHROPIC_API_KEY=        # Claude API key
GMAIL_ADDRESS=            # Sender Gmail address
GMAIL_APP_PASSWORD=       # Gmail App Password (NOT account password)
REPORT_RECIPIENT_EMAIL=   # Where to deliver the daily report
```

### One-Time Google Cloud Setup
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. "YouTube Intelligence")
3. Navigate to **APIs & Services → Library**
4. Search for "YouTube Data API v3" → Enable
5. Go to **APIs & Services → Credentials → Create Credentials → API Key**
6. Copy the key into `.env` as `GOOGLE_API_KEY`
7. _(Optional)_ Restrict the key to YouTube Data API v3 only

### Gmail App Password Setup
1. Enable 2-Factor Authentication on the sender Gmail account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. App name: "WAT YouTube Report" → Generate
4. Copy the 16-character password into `.env` as `GMAIL_APP_PASSWORD`
5. **Important:** This is NOT your account password. Do NOT use your account password.

### Python Dependencies
```bash
pip install -r requirements.txt
```

### Verify Setup
```bash
python tools/config.py
```
All credentials should show "OK". Fix any "MISSING" items before proceeding.

---

## Execution Order

Run each step in sequence from the project root directory.

### Step 1 — Fetch YouTube Data
```bash
python tools/fetch_youtube_data.py
```
- **What it does:** Searches 10 keywords, fetches stats for all results, pulls recent videos from 11 tracked channels, and collects comment samples
- **Expected runtime:** 3–5 minutes (API rate limiting built in)
- **Output:** `.tmp/youtube_raw_YYYY-MM-DD.json`
- **Quota used:** ~2,200 units (well within 10,000/day limit)
- **On failure:**
  - `CONFIG ERROR` → run `python tools/config.py` to diagnose
  - `quotaExceeded` → check quota at console.cloud.google.com → wait until midnight Pacific for reset
  - `403` on a specific video → that video has restricted API access, skipped automatically

### Step 2 — Extract Transcripts
```bash
python tools/extract_transcripts.py
```
- **What it does:** Fetches free transcripts for the top 20 videos by view count, plus all videos from the own channel
- **Expected runtime:** 1–3 minutes
- **Output:** `.tmp/transcripts_YYYY-MM-DD.json`
- **Quota used:** 0 (uses youtube-transcript-api, not YouTube Data API)
- **On failure:** Script is fault-tolerant — partial transcripts are fine, pipeline continues. Check output for `transcript_available: false` entries.

### Step 3 — Analyse Trends (Claude AI)
```bash
python tools/analyze_trends.py
```
- **What it does:** Three Claude API calls — trend analysis, sentiment + learning prompts, own-channel recap
- **Expected runtime:** 45–90 seconds
- **Output:** `.tmp/analysis_YYYY-MM-DD.json`
- **Estimated cost:** ~$0.10–0.30 per day (claude-opus-4-6 pricing)
- **On failure:**
  - `CONFIG ERROR` → check `ANTHROPIC_API_KEY` in `.env`
  - JSON parse error → Claude retries automatically once; check `.tmp/` for partial output
  - Rate limit → wait 60 seconds and retry

### Step 3b — Own Channel Deep Dive (NEW)
```bash
python tools/fetch_own_channel_deep.py
```
- **What it does:** Fetches the last 4 Nate B Jones videos, extracts full transcripts (via youtube-transcript-api, no quota cost), then sends all 4 to Claude for per-video bullet-point summaries
- **Expected runtime:** 60–90 seconds (1 Claude call for all 4 videos)
- **Output:** `.tmp/own_channel_deep_YYYY-MM-DD.json`
- **Estimated cost:** ~$0.05–0.10 (one Claude call)
- **On failure:** Pipeline continues — if this file is missing, slides 12–14 are skipped and the report is still generated

### Step 4 — Generate PDF Report
```bash
python tools/generate_report_pdf.py
```
- **What it does:** Builds all 14 slides using matplotlib and saves a PDF (slides 12–14 require `own_channel_deep_*.json`)
- **Expected runtime:** 20–35 seconds
- **Output:** `.tmp/report_YYYY-MM-DD.pdf` (~2–6 MB)
- **On failure:** Check matplotlib installation (`pip install matplotlib`). Partial PDFs are generated if a single slide fails (that slide is skipped).

### Step 5 — Send via Gmail
```bash
python tools/send_gmail.py
```
- **What it does:** Attaches the PDF and emails it to `REPORT_RECIPIENT_EMAIL`
- **Expected runtime:** 5–15 seconds
- **Output:** Email delivered (check Sent folder to confirm)
- **On failure:**
  - `AUTH ERROR` → you're using your account password, not the App Password. Regenerate at myaccount.google.com/apppasswords
  - Connection error → automatically retries twice with 30-second delay
  - PDF not found → ensure Step 4 completed successfully

---

## Single-Command Pipeline

After verifying each step works individually, run everything at once:

```bash
python -c "
import sys, json, datetime
from pathlib import Path
sys.path.insert(0, '.')

from tools.fetch_youtube_data import fetch_all
from tools.extract_transcripts import extract_transcripts_for_videos
from tools.analyze_trends import analyze_trends
from tools.fetch_own_channel_deep import fetch_own_channel_deep
from tools.generate_report_pdf import generate_report_pdf
from tools.send_gmail import send_report

date = datetime.date.today().isoformat()
print(f'Starting pipeline for {date}')

fetch    = fetch_all()
trans    = extract_transcripts_for_videos(fetch)
analysis = analyze_trends(fetch, trans)
deep     = fetch_own_channel_deep(n_videos=4)
pdf      = generate_report_pdf(fetch, trans, analysis, own_channel_deep=deep)

own_count = analysis.get('own_channel_recap', {}).get('videos_found', 0)
ok = send_report(pdf, date,
                 video_count=len(fetch['keyword_videos']),
                 channel_count=len(fetch['channel_data']),
                 own_video_count=own_count)
print('Done!' if ok else 'Email failed — check logs')
"
```

---

## Daily Scheduling (Windows Task Scheduler)

To run automatically every morning at 7:00 AM:

1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Basic Task**
3. Name: "AI YouTube Intelligence Report"
4. Trigger: **Daily** at **7:00 AM**
5. Action: **Start a program**
   - Program: `C:\path\to\python.exe`
   - Arguments: `-c "import subprocess; subprocess.run(['python', r'C:\Users\61424\Documents\Nate Test\tools\fetch_youtube_data.py'])"`
   - Or use a `.bat` file (see below)
6. Finish

**Recommended: create a `run_report.bat` file:**
```bat
@echo off
cd /d "C:\Users\61424\Documents\Nate Test"
python -c "
import sys, datetime
sys.path.insert(0, '.')
from tools.fetch_youtube_data import fetch_all
from tools.extract_transcripts import extract_transcripts_for_videos
from tools.analyze_trends import analyze_trends
from tools.fetch_own_channel_deep import fetch_own_channel_deep
from tools.generate_report_pdf import generate_report_pdf
from tools.send_gmail import send_report
date = datetime.date.today().isoformat()
fetch = fetch_all()
trans = extract_transcripts_for_videos(fetch)
analysis = analyze_trends(fetch, trans)
deep = fetch_own_channel_deep(n_videos=4)
pdf = generate_report_pdf(fetch, trans, analysis, own_channel_deep=deep)
send_report(pdf, date, len(fetch['keyword_videos']), len(fetch['channel_data']))
" >> ".tmp\log_%date:~-4,4%-%date:~-10,2%-%date:~-7,2%.txt" 2>&1
```
Then point Task Scheduler to `run_report.bat`.

---

## Report Structure (14 slides)

| Slide | Title | Purpose |
|-------|-------|---------|
| 1 | Cover | Date, video count, channel count |
| 2 | Executive Summary | 5 AI-generated learning takeaways |
| 3 | Trending AI Topics | Keyword frequency bar chart with momentum |
| 4 | Must-Watch Videos | Top 10 by engagement — highest learning value |
| 5 | Tool & Use-Case Spotlight | AI tools/models/products in the news |
| 6 | Key Videos Today | Top 5 videos with Claude-generated key points |
| 7 | Rising & Viral Content | New videos gaining traction fast (< 7 days old) |
| 8 | Community Sentiment | Positive/neutral/negative % + sample comments |
| 9 | What's New in AI | Notable releases, research, product launches |
| 10 | What to Explore Next | 3 prioritised learning actions |
| 11 | Your Channel Recap | High-level recap of recent Nate B Jones videos |
| 12 | Nate Deep Dive #1 | Full transcript analysis — latest video, 5–7 key points |
| 13 | Nate Deep Dive #2 | Full transcript analysis — 2nd most recent video |
| 14 | Nate Deep Dive #3 & #4 | Compact analysis of 3rd and 4th most recent videos |

---

## Tracked Channels

Edit `tools/config.py → TRACKED_CHANNELS` to add/remove channels.

| Channel | Focus |
|---------|-------|
| Nate B Jones | Own channel (Slide 11 recap) |
| Matt Wolfe | AI tools roundups |
| Lex Fridman | Long-form AI research interviews |
| Fireship | Dev tools, AI coding |
| Two Minute Papers | AI research papers |
| David Shapiro | AI strategy + philosophy |
| Andrej Karpathy | Deep learning fundamentals |
| Sam Witteveen | LLM engineering |
| AI Explained | Accessible AI news |
| Yannic Kilcher | Paper walkthroughs |
| Riley Brown | AI automation |

**To find a channel ID:**
1. Go to the channel on YouTube
2. View page source and search for `"channelId"` OR
3. Use [commentpicker.com/youtube-channel-id.php](https://commentpicker.com/youtube-channel-id.php)

---

## Search Keywords

Edit `tools/config.py → SEARCH_KEYWORDS` to customise:

```python
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
```

Each keyword costs 100 quota units. 10 keywords = 1,000 units out of 10,000/day.

---

## Quota Management

- **Daily quota:** 10,000 units free
- **This pipeline uses:** ~2,200 units (~22% of budget)
- **Monitor at:** [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → YouTube Data API v3 → Quotas
- **Reset time:** Midnight Pacific Time (PT)
- **If quota is exceeded:**
  - The fetch script saves partial data and exits gracefully
  - Wait for midnight PT reset
  - To increase quota: submit a request in Google Cloud Console (approved based on legitimate use)

---

## Edge Cases & Known Constraints

| Situation | Behaviour |
|-----------|-----------|
| Video comments disabled | Skipped silently, pipeline continues |
| Age-restricted video | Transcript unavailable — flagged in output |
| Channel ID missing in config | Warning printed, channel skipped |
| Nate's channel has no video today | Slide 11 shows "No videos published today" |
| Claude returns invalid JSON | Retries once; falls back to placeholder text |
| Claude API timeout | Logged; fallback template used for that analysis |
| Gmail App Password expired | Auth error — regenerate at myaccount.google.com/apppasswords |
| PDF > 25 MB (Gmail limit) | Won't happen at this scale (~2–5 MB typical) |
| youtube-transcript-api rate limit | Add longer sleep between requests in extract_transcripts.py |
| Weekend content volume | Lower — expected. Report notes reduced video count |

---

## Monitoring & Debugging

- **Check pipeline ran:** Look for `report_YYYY-MM-DD.pdf` in `.tmp/`
- **Check email sent:** Check the sender's Gmail Sent folder
- **Quota usage:** Google Cloud Console → YouTube Data API v3 → Quotas tab
- **Transcript coverage:** Check `videos_successful` field in `transcripts_*.json`
- **Claude output quality:** Review `analysis_*.json` — if fields are empty, check API key and prompts
- **Log files (if using .bat):** `.tmp/log_YYYY-MM-DD.txt`

---

## Self-Improvement Loop

When you discover better methods, encounter rate limits, or find edge cases:

1. Fix the relevant tool script
2. Verify the fix works
3. Update this workflow with what you learned
4. Move on with a more robust system

This is the WAT Framework principle: every failure makes the system stronger.

---

*Last updated: 2026-02-25*
