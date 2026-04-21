# Youtube Analytics

A fully automated YouTube AI niche intelligence pipeline that fetches data from
the YouTube Data API, extracts transcripts, runs Claude AI analysis, and delivers
a professional multi-slide PDF report via Gmail — daily.

## Pipeline

```
fetch_youtube_data.py       → keyword search + channel stats + comments
        ↓
extract_transcripts.py      → free transcript extraction (no API quota)
        ↓
fetch_own_channel_deep.py   → own channel deep dive + Claude per-video summaries
        ↓
analyze_trends.py           → 3x Claude calls: trends + sentiment + recap
        ↓
generate_report_pdf.py      → 14-slide professional PDF report
        ↓
send_gmail.py               → deliver PDF via Gmail SMTP
```

## What It Produces

A 14-slide corporate PDF report covering:

| Slide | Content |
|---|---|
| 1 | Cover — date, video count, channels tracked |
| 2 | Executive Summary — 5 key AI learning takeaways |
| 3 | Today's AI Narrative — topic trends, what's working, rising signals |
| 4 | Must-Watch Videos — top 10 by engagement rate |
| 5 | Tool & Use-Case Spotlight — AI tools gaining momentum |
| 6 | Key Videos Today — top video summaries with key points |
| 7 | Rising & Viral Content — new videos gaining traction fast |
| 8 | Community Sentiment — comment analysis + sentiment score |
| 9 | What's New in AI — notable releases and product launches |
| 10 | What to Explore Next — prioritised learning prompts |
| 11 | Own Channel Recap — Nate B Jones daily video summary |
| 12–14 | Own Channel Deep Dives — per-video AI analysis |

## Tracked Channels

Matt Wolfe, Lex Fridman, Fireship, Two Minute Papers, David Shapiro, Andrej Karpathy, Sam Witteveen, AI Explained, Yannic Kilcher + own channel.

## Requirements

| Credential | Where to get it |
|---|---|
| `GOOGLE_API_KEY` | [console.cloud.google.com](https://console.cloud.google.com) → YouTube Data API v3 |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |
| `REPORT_RECIPIENT_EMAIL` | Recipient email address |

## Setup

Clone and install, then create a .env file in the project root with your credentials:

    GOOGLE_API_KEY=your_key
    ANTHROPIC_API_KEY=your_key
    GMAIL_ADDRESS=you@gmail.com
    GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
    REPORT_RECIPIENT_EMAIL=recipient@email.com

Then verify your config by running: python tools/config.py

## Usage

Run each step individually or chain them:

    python tools/fetch_youtube_data.py        # ~2,200 YouTube API quota units
    python tools/extract_transcripts.py       # free — no quota used
    python tools/fetch_own_channel_deep.py    # own channel + Claude analysis
    python tools/analyze_trends.py            # 3x Claude API calls
    python tools/generate_report_pdf.py       # builds PDF
    python tools/send_gmail.py                # emails the report

## Quota Usage

YouTube Data API v3 free tier: 10,000 units/day. Estimated daily usage: ~2,226 units (~22% of budget).

## Project Structure

    Youtube-Analytics/
    ├── .env                    # credentials — never committed
    ├── .env.example            # template — commit this
    ├── tools/
    │   ├── config.py
    │   ├── fetch_youtube_data.py
    │   ├── extract_transcripts.py
    │   ├── fetch_own_channel_deep.py
    │   ├── analyze_trends.py
    │   ├── generate_report_pdf.py
    │   └── send_gmail.py
    └── .tmp/                   # intermediate JSON + final PDF (gitignored)

## Compliance Note

All API credentials must be stored in .env and never committed to version control.
Gmail App Password authentication requires 2FA enabled on the sender account.
