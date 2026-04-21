"""
generate_report_pdf.py — Professional PDF report using matplotlib PdfPages.

Clean white corporate design — readable, spacious, text-first layout.
Paginated: long sections overflow to continuation pages automatically.
No LibreOffice or external dependencies — pure Python.

Run directly:  python tools/generate_report_pdf.py
"""

import json
import sys
import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.config import TMP_DIR


# ---------------------------------------------------------------------------
# Corporate white design tokens
# ---------------------------------------------------------------------------

C = {
    "bg":        "#FFFFFF",   # page background
    "bg_card":   "#F8FAFC",   # card / panel background
    "bg_header": "#F1F5F9",   # header band background
    "accent":    "#2563EB",   # primary blue — titles, borders, key numbers
    "green":     "#16A34A",   # positive sentiment, growth
    "red":       "#DC2626",   # negative sentiment, warnings
    "amber":     "#D97706",   # highlights, featured items
    "purple":    "#7C3AED",   # secondary data series
    "text":      "#0F172A",   # body text (near black)
    "muted":     "#64748B",   # secondary text, labels
    "border":    "#E2E8F0",   # card borders, dividers
    "row_alt":   "#F1F5F9",   # alternating table row
    "bar_colors": ["#2563EB", "#16A34A", "#D97706", "#7C3AED", "#DC2626"],
}

FS = {
    "h1":    28,    # cover title
    "h2":    17,    # slide title
    "h3":    12,    # card title / section heading
    "body":  10,    # body text
    "small":  9,    # labels, captions
    "xs":     8,    # fine print
}

FIG_W, FIG_H, DPI = 11.0, 8.5, 150

# Vertical layout (axes coordinates 0–1)
HEADER_Y  = 0.900   # header occupies 0.900 → 1.000
FOOTER_Y  = 0.045   # footer rule at y=0.045
CONTENT_T = 0.888   # top of content area
CONTENT_B = 0.058   # bottom of content area
CONTENT_H = CONTENT_T - CONTENT_B   # ≈ 0.830


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fig():
    """Create a blank white corporate figure."""
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def _header(ax, title, subtitle=""):
    """Clean header: light-gray band + blue left accent bar + dark title."""
    # Header band
    ax.add_patch(mpatches.Rectangle(
        (0, HEADER_Y), 1.0, 1.0 - HEADER_Y,
        facecolor=C["bg_header"], edgecolor="none",
        transform=ax.transAxes, zorder=1,
    ))
    # Blue left accent bar
    ax.add_patch(mpatches.Rectangle(
        (0, HEADER_Y), 0.007, 1.0 - HEADER_Y,
        facecolor=C["accent"], edgecolor="none",
        transform=ax.transAxes, zorder=2,
    ))
    # Title
    ax.text(0.025, 0.953, title,
            transform=ax.transAxes, fontsize=FS["h2"], fontweight="bold",
            color=C["text"], va="center", zorder=3)
    # Subtitle
    if subtitle:
        ax.text(0.025, 0.912, subtitle,
                transform=ax.transAxes, fontsize=FS["small"],
                color=C["muted"], va="center", zorder=3)
    # Bottom rule
    ax.axhline(y=HEADER_Y, color=C["border"], linewidth=1.2)


def _footer(ax, page_num, date):
    """Simple corporate footer: date left, page number right."""
    ax.axhline(y=FOOTER_Y, color=C["border"], linewidth=0.8)
    ax.text(0.025, FOOTER_Y * 0.48, f"AI Intelligence Report — {date}",
            transform=ax.transAxes, fontsize=FS["xs"],
            color=C["muted"], va="center")
    ax.text(0.975, FOOTER_Y * 0.48, f"Page {page_num}",
            transform=ax.transAxes, fontsize=FS["xs"],
            color=C["muted"], va="center", ha="right")


def _card(ax, x, y, w, h):
    """Light-gray card with subtle border."""
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.006",
        facecolor=C["bg_card"], edgecolor=C["border"],
        linewidth=0.8, transform=ax.transAxes, zorder=1,
    ))


def _trunc(text, n):
    if not text:
        return ""
    return text[:n] + "…" if len(text) > n else text


def _fmt_num(n):
    n = int(n) if n else 0
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _wrap_text(text, max_chars):
    """Wrap text at word boundaries to max_chars per line."""
    if not text:
        return []
    words = text.split()
    lines, line = [], []
    for w in words:
        line.append(w)
        if len(" ".join(line)) > max_chars:
            if len(line) > 1:
                lines.append(" ".join(line[:-1]))
                line = [w]
            else:
                lines.append(line[0])
                line = []
    if line:
        lines.append(" ".join(line))
    return lines


# ---------------------------------------------------------------------------
# Slide 1 — Cover
# ---------------------------------------------------------------------------

def slide_01_cover(date, video_count, channel_count):
    fig, ax = _fig()

    # Top accent bar
    ax.add_patch(mpatches.Rectangle(
        (0, 0.94), 1.0, 0.06,
        facecolor=C["accent"], edgecolor="none", transform=ax.transAxes,
    ))
    ax.text(0.04, 0.970, "WAT FRAMEWORK",
            transform=ax.transAxes, fontsize=9, fontweight="bold",
            color="#FFFFFF", va="center", alpha=0.92)

    # Main title
    ax.text(0.5, 0.735, "AI NICHE INTELLIGENCE",
            transform=ax.transAxes, fontsize=36, fontweight="bold",
            color=C["text"], ha="center", va="center")

    # Blue rule under title
    ax.add_patch(mpatches.Rectangle(
        (0.28, 0.678), 0.44, 0.004,
        facecolor=C["accent"], transform=ax.transAxes,
    ))

    # Subtitle
    ax.text(0.5, 0.620, "YouTube Analytics & Learning Report",
            transform=ax.transAxes, fontsize=16, color=C["muted"],
            ha="center", va="center")

    # Date
    ax.text(0.5, 0.534, date,
            transform=ax.transAxes, fontsize=14, color=C["text"],
            ha="center", va="center", fontweight="bold")

    # Stats boxes
    for x0, val, label, col in [
        (0.255, _fmt_num(video_count), "Videos Analysed", C["accent"]),
        (0.530, str(channel_count),    "Channels Tracked", C["green"]),
    ]:
        _card(ax, x0, 0.285, 0.215, 0.120)
        ax.text(x0 + 0.1075, 0.370, val,
                transform=ax.transAxes, fontsize=22, fontweight="bold",
                color=col, ha="center", va="center")
        ax.text(x0 + 0.1075, 0.302, label,
                transform=ax.transAxes, fontsize=FS["small"],
                color=C["muted"], ha="center", va="center")

    ax.text(0.5, 0.150, "Powered by YouTube Data API v3 + Claude AI",
            transform=ax.transAxes, fontsize=8, color=C["muted"],
            ha="center", alpha=0.75)

    # Bottom rule
    ax.add_patch(mpatches.Rectangle(
        (0, 0), 1.0, 0.045,
        facecolor=C["bg_header"], edgecolor="none", transform=ax.transAxes,
    ))
    return fig


# ---------------------------------------------------------------------------
# Slide 2 — Executive Summary
# ---------------------------------------------------------------------------

def slide_02_executive_summary(analysis, date, page_num=2):
    fig, ax = _fig()
    _header(ax, "EXECUTIVE SUMMARY", "Key learning takeaways from today's AI landscape")
    _footer(ax, page_num, date)

    bullets = analysis.get("executive_summary", [])[:5]
    if not bullets:
        ax.text(0.5, 0.5, "No data available", transform=ax.transAxes,
                ha="center", color=C["muted"], fontsize=12)
        return fig

    card_h  = 0.144
    gap     = 0.012
    y_start = CONTENT_T - card_h - 0.008   # y is card bottom; top = y+card_h = CONTENT_T-0.008

    for i, bullet in enumerate(bullets):
        y = y_start - i * (card_h + gap)
        if y < CONTENT_B:
            break
        _card(ax, 0.03, y, 0.94, card_h)

        # Numbered circle
        col  = C["bar_colors"][i % len(C["bar_colors"])]
        circ = plt.Circle((0.068, y + card_h / 2), 0.021,
                           color=col, transform=ax.transAxes, zorder=3)
        ax.add_patch(circ)
        ax.text(0.068, y + card_h / 2, str(i + 1),
                transform=ax.transAxes, fontsize=9, fontweight="bold",
                color="#FFFFFF", ha="center", va="center", zorder=4)

        # Wrapped bullet text — up to 3 lines, no hard truncation
        wrapped = _wrap_text(bullet, 100)[:3]
        n = len(wrapped)
        step  = 0.030
        top_y = y + card_h / 2 + (n - 1) * step / 2
        for j, ln in enumerate(wrapped):
            ax.text(0.100, top_y - j * step, ln,
                    transform=ax.transAxes, fontsize=FS["body"],
                    color=C["text"], va="center")

    return fig


# ---------------------------------------------------------------------------
# Slide 3 — Today's AI Narrative  (paginated if sections are long)
# ---------------------------------------------------------------------------

def slide_03_narrative_briefing(analysis, date, page_num=3):
    """Three full narrative sections with automatic overflow to continuation pages."""
    sections = [
        ("TOPIC TRENDS",   "topic_trends_narrative",    C["accent"]),
        ("WHAT'S WORKING", "whats_working_narrative",   C["green"]),
        ("RISING SIGNALS", "rising_content_insights",   C["amber"]),
    ]

    # Gather wrapped lines for each section
    section_data = []
    for label, key, color in sections:
        text    = analysis.get(key, "")
        has_data = bool(text)
        lines   = _wrap_text(text, 108) if text else ["No data available for today."]
        section_data.append((label, lines, color, has_data))

    # Layout constants
    LABEL_H = 0.042   # height consumed by the section label row
    LINE_H  = 0.034   # height per wrapped text line
    PAD_H   = 0.020   # bottom padding inside each card
    GAP     = 0.016   # gap between cards
    MAX_LPG = 10      # max lines shown per section per page

    figs = []

    def _new_page(pn, cont=False):
        f, a = _fig()
        sub = ("What's driving AI discourse today — full analysis"
               if not cont else "continued")
        _header(a, "TODAY'S AI NARRATIVE", sub)
        _footer(a, pn, date)
        return f, a

    fig, ax = _new_page(page_num)
    y           = CONTENT_T - 0.010
    current_pn  = page_num
    is_cont     = False

    for label, lines, color, has_data in section_data:
        remaining_y = y - CONTENT_B
        # Ensure at least label + 2 lines fit; otherwise start a new page
        min_needed = LABEL_H + 2 * LINE_H + PAD_H
        if remaining_y < min_needed and len(figs) > 0 or (remaining_y < min_needed):
            figs.append(fig)
            current_pn += 1
            fig, ax = _new_page(current_pn, cont=True)
            y = CONTENT_T - 0.010
            remaining_y = y - CONTENT_B
            is_cont = True

        # Render this section, possibly across multiple pages
        pending = list(lines)
        first_chunk = True

        while pending:
            remaining_y = y - CONTENT_B
            lines_fit = max(1, int((remaining_y - LABEL_H - PAD_H) / LINE_H))
            lines_fit = min(lines_fit, MAX_LPG)
            chunk     = pending[:lines_fit]
            pending   = pending[lines_fit:]

            section_h = LABEL_H + len(chunk) * LINE_H + PAD_H
            _card(ax, 0.030, y - section_h, 0.940, section_h)

            # Label
            lbl_text = label if first_chunk else f"{label} (cont.)"
            ax.text(0.048, y - 0.018, lbl_text,
                    transform=ax.transAxes, fontsize=FS["small"],
                    color=color, fontweight="bold", va="top")

            # Text lines
            for j, ln in enumerate(chunk):
                ax.text(0.048, y - LABEL_H - j * LINE_H, ln,
                        transform=ax.transAxes,
                        fontsize=FS["body"],
                        color=C["text"] if has_data else C["muted"],
                        style="normal" if has_data else "italic", va="top")

            y -= section_h + GAP
            first_chunk = False

            # If there are more lines for this section, start a new page
            if pending:
                figs.append(fig)
                current_pn += 1
                fig, ax = _new_page(current_pn, cont=True)
                y = CONTENT_T - 0.010

    figs.append(fig)
    return figs if len(figs) > 1 else figs[0]


# ---------------------------------------------------------------------------
# Slide 4 — Must-Watch Videos (table)
# ---------------------------------------------------------------------------

def slide_04_must_watch(keyword_videos, date, page_num=4):
    fig, ax = _fig()
    _header(ax, "MUST-WATCH VIDEOS",
            "Top 10 by engagement rate — most valuable for learning")
    _footer(ax, page_num, date)

    top = sorted(keyword_videos, key=lambda v: v["engagement_rate"], reverse=True)[:10]
    if not top:
        ax.text(0.5, 0.5, "No video data", transform=ax.transAxes,
                ha="center", color=C["muted"], fontsize=12)
        return fig

    cols  = ["#",   "Title",   "Channel",   "Views",  "Eng%"]
    col_x = [0.025, 0.068,     0.614,       0.770,    0.902]

    # Column header row
    y_hdr  = CONTENT_T - 0.004
    hdr_h  = 0.042
    ax.add_patch(mpatches.Rectangle(
        (0.020, y_hdr - hdr_h), 0.962, hdr_h,
        facecolor=C["accent"], alpha=0.12, edgecolor="none",
        transform=ax.transAxes,
    ))
    for col, cx in zip(cols, col_x):
        ax.text(cx, y_hdr - hdr_h / 2, col,
                transform=ax.transAxes, fontsize=FS["small"],
                color=C["accent"], fontweight="bold", va="center")

    # Data rows
    row_h = 0.078
    for i, vid in enumerate(top):
        y = y_hdr - hdr_h - (i + 1) * row_h
        if y < CONTENT_B:
            break
        bg = C["row_alt"] if i % 2 == 0 else C["bg"]
        ax.add_patch(mpatches.Rectangle(
            (0.020, y), 0.962, row_h - 0.003,
            facecolor=bg, edgecolor="none", transform=ax.transAxes,
        ))
        rank_col = C["amber"] if i < 3 else C["muted"]
        ax.text(col_x[0], y + row_h / 2, str(i + 1),
                transform=ax.transAxes, fontsize=FS["body"],
                color=rank_col, va="center", fontweight="bold")
        ax.text(col_x[1], y + row_h / 2, _trunc(vid["title"], 60),
                transform=ax.transAxes, fontsize=FS["small"],
                color=C["text"], va="center")
        ax.text(col_x[2], y + row_h / 2, _trunc(vid["channel_name"], 20),
                transform=ax.transAxes, fontsize=FS["small"],
                color=C["muted"], va="center")
        ax.text(col_x[3], y + row_h / 2, _fmt_num(vid["view_count"]),
                transform=ax.transAxes, fontsize=FS["small"],
                color=C["muted"], va="center")
        eng     = vid["engagement_rate"]
        eng_col = C["green"] if eng > 5 else C["amber"] if eng > 2 else C["red"]
        ax.text(col_x[4], y + row_h / 2, f"{eng:.1f}%",
                transform=ax.transAxes, fontsize=FS["small"],
                color=eng_col, va="center", fontweight="bold")
    return fig


# ---------------------------------------------------------------------------
# Slide 5 — Tool & Use-Case Spotlight  (paginated: 6 per page)
# ---------------------------------------------------------------------------

def slide_05_tool_spotlight(analysis, date, page_num=5):
    all_items = analysis.get("whats_new", [])
    if not all_items:
        fig, ax = _fig()
        _header(ax, "TOOL & USE-CASE SPOTLIGHT",
                "AI tools, models, and capabilities dominating discussion today")
        _footer(ax, page_num, date)
        ax.text(0.5, 0.5, "No tool data available",
                transform=ax.transAxes, ha="center", color=C["muted"], fontsize=12)
        return fig

    figs      = []
    current_pn = page_num
    BATCH     = 6

    for batch_start in range(0, len(all_items), BATCH):
        batch = all_items[batch_start:batch_start + BATCH]
        fig, ax = _fig()
        sub = ("AI tools, models, and capabilities dominating discussion today"
               if batch_start == 0 else "continued")
        _header(ax, "TOOL & USE-CASE SPOTLIGHT", sub)
        _footer(ax, current_pn, date)

        # 2-column × 3-row grid
        card_w, card_h = 0.456, 0.234
        positions = [
            (0.028, 0.635), (0.516, 0.635),
            (0.028, 0.385), (0.516, 0.385),
            (0.028, 0.135), (0.516, 0.135),
        ]

        for i, item in enumerate(batch):
            if i >= len(positions):
                break
            x, y = positions[i]
            _card(ax, x, y, card_w, card_h)

            # Item name
            ax.text(x + 0.014, y + card_h - 0.028, _trunc(item.get("item", ""), 54),
                    transform=ax.transAxes, fontsize=FS["h3"],
                    color=C["amber"], fontweight="bold", va="top")

            # Significance — word-wrap, up to 5 lines, no hard truncation
            sig      = item.get("significance", "")
            sig_lines = _wrap_text(sig, 74)[:5]
            for li, ln in enumerate(sig_lines):
                ax.text(x + 0.014, y + card_h - 0.066 - li * 0.032,
                        ln, transform=ax.transAxes, fontsize=FS["xs"],
                        color=C["text"], va="top")

            # Source
            src = item.get("source_video", "")
            if src:
                ax.text(x + 0.014, y + 0.014, f"Source: {_trunc(src, 52)}",
                        transform=ax.transAxes, fontsize=FS["xs"] - 1,
                        color=C["muted"], va="bottom", style="italic")

        figs.append(fig)
        current_pn += 1

    return figs if len(figs) > 1 else figs[0]


# ---------------------------------------------------------------------------
# Slide 6 — Key Videos Today  (paginated: 5 per page)
# ---------------------------------------------------------------------------

def slide_06_key_videos(analysis, keyword_videos, date, page_num=6):
    summaries = analysis.get("top_video_summaries", [])
    top10     = sorted(keyword_videos, key=lambda v: v["view_count"], reverse=True)[:10]

    if not summaries:
        summaries = [
            {"title": v["title"], "channel": v["channel_name"],
             "why_watch": "", "key_points": []}
            for v in top10
        ]

    vid_by_title  = {v["title"]: v for v in keyword_videos}
    all_summaries = summaries[:10]

    if not all_summaries:
        fig, ax = _fig()
        _header(ax, "KEY VIDEOS TODAY",
                "Top stories — what people are watching and why it matters")
        _footer(ax, page_num, date)
        ax.text(0.5, 0.5, "No video summaries available",
                transform=ax.transAxes, ha="center", color=C["muted"], fontsize=12)
        return fig

    figs      = []
    current_pn = page_num
    BATCH     = 5

    for batch_start in range(0, len(all_summaries), BATCH):
        batch  = all_summaries[batch_start:batch_start + BATCH]
        fig, ax = _fig()
        sub = ("Top stories — what people are watching and why it matters"
               if batch_start == 0 else "continued")
        _header(ax, "KEY VIDEOS TODAY", sub)
        _footer(ax, current_pn, date)

        card_h = 0.152
        gap    = 0.010
        y_cur  = CONTENT_T - card_h - 0.008   # y is card bottom; top = y+card_h

        for i, summary in enumerate(batch):
            y = y_cur - i * (card_h + gap)
            if y < CONTENT_B:
                break
            _card(ax, 0.030, y, 0.940, card_h)

            title   = summary.get("title", "")
            channel = summary.get("channel", "")
            abs_i   = batch_start + i
            vid     = vid_by_title.get(title) or (top10[abs_i] if abs_i < len(top10) else {})
            views   = vid.get("view_count", 0) if vid else 0
            eng     = vid.get("engagement_rate", 0.0) if vid else 0.0

            # Left column — title / channel / stats
            ax.text(0.046, y + card_h - 0.022, _trunc(title, 56),
                    transform=ax.transAxes, fontsize=FS["small"],
                    color=C["amber"], fontweight="bold", va="top")
            ax.text(0.046, y + card_h - 0.050, _trunc(channel, 28),
                    transform=ax.transAxes, fontsize=FS["xs"],
                    color=C["muted"], va="top")
            stats_str = _fmt_num(views) + " views"
            if eng > 0:
                stats_str += f"  |  {eng:.1f}% eng"
            ax.text(0.046, y + card_h - 0.078, stats_str,
                    transform=ax.transAxes, fontsize=FS["xs"],
                    color=C["green"], va="top")

            # Vertical divider
            ax.plot([0.340, 0.340], [y + 0.010, y + card_h - 0.010],
                    color=C["border"], linewidth=1.0, transform=ax.transAxes)

            # Right column — key points / why_watch
            key_points = summary.get("key_points", [])
            if key_points:
                for j, pt in enumerate(key_points[:3]):
                    ax.text(0.356, y + card_h - 0.024 - j * 0.042,
                            f"• {_trunc(pt, 100)}",
                            transform=ax.transAxes, fontsize=FS["xs"],
                            color=C["text"], va="top")
            else:
                why = summary.get("why_watch", "")
                if why:
                    for j, ln in enumerate(_wrap_text(why, 86)[:3]):
                        ax.text(0.356, y + card_h - 0.024 - j * 0.042, ln,
                                transform=ax.transAxes, fontsize=FS["xs"],
                                color=C["text"], va="top")

        figs.append(fig)
        current_pn += 1

    return figs if len(figs) > 1 else figs[0]


# ---------------------------------------------------------------------------
# Slide 7 — Rising & Viral Content
# ---------------------------------------------------------------------------

def slide_07_rising_content(keyword_videos, analysis, date, page_num=7):
    import datetime as dt

    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.patch.set_facecolor(C["bg"])

    ax_text = fig.add_axes([0, 0, 1, 1])
    ax_text.set_xlim(0, 1)
    ax_text.set_ylim(0, 1)
    ax_text.axis("off")
    _header(ax_text, "RISING & VIRAL CONTENT",
            "New videos gaining traction fast — signals of emerging interest")
    _footer(ax_text, page_num, date)

    cutoff = dt.datetime.utcnow() - dt.timedelta(days=7)
    rising = []
    for v in keyword_videos:
        try:
            pub = dt.datetime.fromisoformat(v["published_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            if pub > cutoff:
                rising.append(v)
        except Exception:
            pass

    if not rising:
        ax_text.text(0.5, 0.5, "No videos < 7 days old in today's data",
                     transform=ax_text.transAxes, ha="center",
                     color=C["muted"], fontsize=12)
        return fig

    hours, views_list, engs, labels = [], [], [], []
    for v in rising:
        try:
            pub = dt.datetime.fromisoformat(v["published_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            h = max((dt.datetime.utcnow() - pub).total_seconds() / 3600, 1)
        except Exception:
            h = 72
        hours.append(h)
        views_list.append(v["view_count"])
        engs.append(max(v["engagement_rate"] * 25, 20))
        labels.append(_trunc(v["title"], 32))

    # Scatter plot — white background chart
    ax = fig.add_axes([0.07, 0.12, 0.54, 0.70])
    ax.set_facecolor(C["bg_card"])
    for spine in ax.spines.values():
        spine.set_edgecolor(C["border"])
    ax.scatter(hours, views_list, s=engs, c=C["accent"],
               alpha=0.70, edgecolors=C["accent"], linewidths=0.5)
    ax.tick_params(colors=C["muted"], labelsize=FS["xs"])
    ax.set_xlabel("Hours since published", color=C["muted"], fontsize=FS["xs"])
    ax.set_ylabel("View count", color=C["muted"], fontsize=FS["xs"])
    ax.grid(color=C["border"], alpha=0.7, linestyle="--", linewidth=0.5)

    # Label top 3
    top3 = sorted(range(len(views_list)), key=lambda i: views_list[i], reverse=True)[:3]
    for idx in top3:
        ax.annotate(labels[idx], (hours[idx], views_list[idx]),
                    textcoords="offset points", xytext=(5, 5),
                    fontsize=7, color=C["text"])

    # Insight panel
    insight = analysis.get("rising_content_insights", "")
    ax_text.text(0.680, 0.800, "What this signals:",
                 transform=ax_text.transAxes, fontsize=FS["small"],
                 color=C["accent"], fontweight="bold")
    if insight:
        for i, ln in enumerate(_wrap_text(insight, 42)[:13]):
            ax_text.text(0.680, 0.758 - i * 0.050, ln,
                         transform=ax_text.transAxes, fontsize=FS["xs"],
                         color=C["text"])
    return fig


# ---------------------------------------------------------------------------
# Slide 8 — Community Sentiment
# ---------------------------------------------------------------------------

def slide_08_sentiment(analysis, date, page_num=8):
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.patch.set_facecolor(C["bg"])

    ax_text = fig.add_axes([0, 0, 1, 1])
    ax_text.set_xlim(0, 1)
    ax_text.set_ylim(0, 1)
    ax_text.axis("off")
    _header(ax_text, "COMMUNITY SENTIMENT",
            "How the AI community feels today — based on comment analysis")
    _footer(ax_text, page_num, date)

    sb      = analysis.get("sentiment_breakdown", {})
    pos     = sb.get("positive_pct", 33)
    neu     = sb.get("neutral_pct", 34)
    neg     = sb.get("negative_pct", 33)
    emotion = sb.get("dominant_emotion", "—")
    quotes  = sb.get("sample_quotes", [])
    score   = analysis.get("overall_sentiment_score", 0.0)

    # Donut chart — white background
    ax_pie = fig.add_axes([0.03, 0.14, 0.42, 0.70])
    ax_pie.set_facecolor(C["bg"])
    wedges, _ = ax_pie.pie(
        [pos, neu, neg],
        colors=[C["green"], C["accent"], C["red"]],
        startangle=90,
        wedgeprops={"linewidth": 2, "edgecolor": "#FFFFFF", "width": 0.55},
        counterclock=False,
    )
    ax_pie.text(0, 0.05, emotion.upper(),
                ha="center", va="center", fontsize=12,
                fontweight="bold", color=C["text"])
    ax_pie.text(0, -0.28, "dominant feeling",
                ha="center", va="center", fontsize=7, color=C["muted"])

    legend = [
        mpatches.Patch(color=C["green"],  label=f"Positive  {pos:.0f}%"),
        mpatches.Patch(color=C["accent"], label=f"Neutral   {neu:.0f}%"),
        mpatches.Patch(color=C["red"],    label=f"Negative  {neg:.0f}%"),
    ]
    ax_pie.legend(handles=legend, loc="lower center",
                  facecolor=C["bg_card"], edgecolor=C["border"],
                  labelcolor=C["muted"], fontsize=FS["small"],
                  ncol=3, bbox_to_anchor=(0.5, -0.12))

    # Sample comments
    ax_text.text(0.525, 0.845, "SAMPLE COMMENTS",
                 transform=ax_text.transAxes, fontsize=FS["small"],
                 color=C["accent"], fontweight="bold")
    q_y = 0.808
    for q in quotes[:3]:
        card_h = 0.118
        _card(ax_text, 0.510, q_y - card_h, 0.470, card_h)
        for j, ln in enumerate(_wrap_text(f'"{_trunc(q, 92)}"', 56)[:2]):
            ax_text.text(0.524, q_y - 0.022 - j * 0.036, ln,
                         transform=ax_text.transAxes, fontsize=FS["xs"],
                         color=C["text"], style="italic", va="top")
        ax_text.text(0.524, q_y - card_h + 0.014, "— YouTube comment",
                     transform=ax_text.transAxes, fontsize=FS["xs"] - 1,
                     color=C["muted"], va="bottom")
        q_y -= card_h + 0.012

    # Sentiment score bar
    bx, by, bw, bh = 0.510, 0.118, 0.470, 0.040
    ax_text.add_patch(mpatches.FancyBboxPatch(
        (bx, by), bw, bh, boxstyle="round,pad=0.002",
        facecolor=C["bg_card"], edgecolor=C["border"], linewidth=0.8,
        transform=ax_text.transAxes,
    ))
    fill_color = C["green"] if score >= 0 else C["red"]
    fill_start = bx + bw * 0.5 if score >= 0 else bx + bw * max(0, 0.5 + score / 2)
    ax_text.add_patch(mpatches.FancyBboxPatch(
        (fill_start, by), bw * abs(float(score)) / 2, bh,
        boxstyle="round,pad=0.001", facecolor=fill_color, alpha=0.55,
        edgecolor="none", transform=ax_text.transAxes,
    ))
    ax_text.text(bx + bw / 2, by + bh / 2,
                 f"Overall sentiment score: {score:+.2f}",
                 transform=ax_text.transAxes, fontsize=FS["xs"],
                 color=C["text"], ha="center", va="center")
    return fig


# ---------------------------------------------------------------------------
# Slide 9 — What's New in AI  (paginated: 5 per page)
# ---------------------------------------------------------------------------

def slide_09_whats_new(analysis, date, page_num=9):
    all_items = analysis.get("whats_new", [])
    if not all_items:
        fig, ax = _fig()
        _header(ax, "WHAT'S NEW IN AI",
                "Notable releases, models, research, and product launches (past 24-48h)")
        _footer(ax, page_num, date)
        ax.text(0.5, 0.5, "No new items identified today",
                transform=ax.transAxes, ha="center", color=C["muted"], fontsize=12)
        return fig

    figs      = []
    current_pn = page_num
    BATCH     = 5

    for batch_start in range(0, len(all_items), BATCH):
        batch  = all_items[batch_start:batch_start + BATCH]
        fig, ax = _fig()
        sub = ("Notable releases, models, research, and product launches (past 24-48h)"
               if batch_start == 0 else "continued")
        _header(ax, "WHAT'S NEW IN AI", sub)
        _footer(ax, current_pn, date)

        card_h = 0.144
        gap    = 0.012
        y_cur  = CONTENT_T - card_h - 0.008   # y is card bottom; top = y+card_h

        for i, item in enumerate(batch):
            y = y_cur - i * (card_h + gap)
            if y < CONTENT_B:
                break
            _card(ax, 0.030, y, 0.940, card_h)

            # NEW badge
            ax.add_patch(mpatches.FancyBboxPatch(
                (0.897, y + card_h - 0.038), 0.072, 0.026,
                boxstyle="round,pad=0.002",
                facecolor=C["accent"], alpha=0.14,
                edgecolor=C["accent"], linewidth=0.8,
                transform=ax.transAxes,
            ))
            ax.text(0.933, y + card_h - 0.025, "NEW",
                    transform=ax.transAxes, fontsize=7, fontweight="bold",
                    color=C["accent"], ha="center", va="center")

            # Item name
            ax.text(0.048, y + card_h - 0.026, _trunc(item.get("item", ""), 70),
                    transform=ax.transAxes, fontsize=FS["body"],
                    color=C["amber"], fontweight="bold", va="top")

            # Significance — 3 wrapped lines
            sig      = item.get("significance", "")
            sig_lines = _wrap_text(sig, 102)[:3]
            for li, ln in enumerate(sig_lines):
                ax.text(0.048, y + card_h - 0.060 - li * 0.030,
                        ln, transform=ax.transAxes, fontsize=FS["xs"],
                        color=C["text"], va="top")

        figs.append(fig)
        current_pn += 1

    return figs if len(figs) > 1 else figs[0]


# ---------------------------------------------------------------------------
# Slide 10 — What to Explore Next
# ---------------------------------------------------------------------------

def slide_10_explore_next(analysis, date, page_num=10):
    fig, ax = _fig()
    _header(ax, "WHAT TO EXPLORE NEXT",
            "Prioritised learning actions based on today's AI landscape")
    _footer(ax, page_num, date)

    prompts = analysis.get("learning_prompts", [])[:3]
    if not prompts:
        ax.text(0.5, 0.5, "No learning prompts available",
                transform=ax.transAxes, ha="center", color=C["muted"], fontsize=12)
        return fig

    priority_colors = {"high": C["red"], "medium": C["amber"], "low": C["green"]}
    card_w  = 0.295
    card_h  = CONTENT_H - 0.010
    pos_x   = [0.028, 0.352, 0.676]

    for i, prompt in enumerate(prompts):
        if i >= len(pos_x):
            break
        x = pos_x[i]
        y = CONTENT_B + 0.005
        _card(ax, x, y, card_w, card_h)

        p    = prompt.get("priority", "medium").lower()
        pcol = priority_colors.get(p, C["amber"])

        # Priority badge
        ax.add_patch(mpatches.FancyBboxPatch(
            (x + 0.010, y + card_h - 0.046), 0.092, 0.030,
            boxstyle="round,pad=0.003", facecolor=pcol, alpha=0.14,
            edgecolor=pcol, linewidth=1, transform=ax.transAxes,
        ))
        ax.text(x + 0.056, y + card_h - 0.031, p.upper(),
                transform=ax.transAxes, fontsize=7, fontweight="bold",
                color=pcol, ha="center", va="center")

        # Number circle
        circ = plt.Circle((x + card_w - 0.036, y + card_h - 0.031), 0.020,
                           color=pcol, transform=ax.transAxes, zorder=3, alpha=0.85)
        ax.add_patch(circ)
        ax.text(x + card_w - 0.036, y + card_h - 0.031, str(i + 1),
                transform=ax.transAxes, fontsize=9, fontweight="bold",
                color="#FFFFFF", ha="center", va="center", zorder=4)

        # Action title — up to 3 wrapped lines
        action = prompt.get("action", "")
        for j, ln in enumerate(_wrap_text(action, 34)[:3]):
            ax.text(x + 0.014, y + card_h - 0.084 - j * 0.038, ln,
                    transform=ax.transAxes, fontsize=FS["body"],
                    color=C["text"], fontweight="bold", va="top")

        # Thin rule
        rule_y = y + card_h - 0.210
        ax.plot([x + 0.012, x + card_w - 0.012], [rule_y, rule_y],
                color=C["border"], linewidth=0.8, transform=ax.transAxes)

        # Rationale — many lines, full text
        rat = prompt.get("rationale", "")
        for j, ln in enumerate(_wrap_text(rat, 34)[:10]):
            ax.text(x + 0.014, y + card_h - 0.230 - j * 0.054, ln,
                    transform=ax.transAxes, fontsize=FS["xs"],
                    color=C["muted"], va="top")

    return fig


# ---------------------------------------------------------------------------
# Slide 11 — Nate B Jones Daily Recap
# ---------------------------------------------------------------------------

def _build_recap_from_deep(deep_videos):
    """Map own_channel_deep video records to recap format."""
    summaries = []
    for v in deep_videos[:3]:
        s = v.get("summary", {})
        summaries.append({
            "title": v.get("title", ""),
            "engagement_snapshot": {
                "views":    v.get("view_count", 0),
                "likes":    v.get("like_count", 0),
                "comments": v.get("comment_count", 0),
            },
            "key_points":        s.get("key_points", []),
            "standout_insights": [s.get("one_liner", "")] if s.get("one_liner") else [],
        })
    return {"recap_available": bool(summaries), "video_summaries": summaries}


def _render_video_recap(ax, summary, x, y, w, h):
    """Render one video recap card in white corporate style."""
    _card(ax, x, y, w, h)

    # Title
    ax.text(x + 0.014, y + h - 0.020, _trunc(summary.get("title", ""), 96),
            transform=ax.transAxes, fontsize=FS["h3"],
            color=C["amber"], fontweight="bold", va="top")

    # Engagement row
    snap     = summary.get("engagement_snapshot", {})
    eng_text = (f"Views: {_fmt_num(snap.get('views', 0))}   "
                f"Likes: {_fmt_num(snap.get('likes', 0))}   "
                f"Comments: {_fmt_num(snap.get('comments', 0))}")
    ax.text(x + 0.014, y + h - 0.052, eng_text,
            transform=ax.transAxes, fontsize=FS["small"],
            color=C["muted"], va="top")

    # Rule
    ax.plot([x + 0.012, x + w - 0.012], [y + h - 0.072, y + h - 0.072],
            color=C["border"], linewidth=0.8, transform=ax.transAxes)

    # Key points — up to 5
    points = summary.get("key_points", [])
    for i, point in enumerate(points[:5]):
        py = y + h - 0.092 - i * 0.050
        if py < y + 0.028:
            break
        ax.text(x + 0.022, py, f"• {_trunc(point, 115)}",
                transform=ax.transAxes, fontsize=FS["small"],
                color=C["text"], va="top")

    # Standout insight
    insights = summary.get("standout_insights", [])
    if insights and insights[0]:
        ax.text(x + 0.014, y + 0.018, f">> {_trunc(insights[0], 126)}",
                transform=ax.transAxes, fontsize=FS["xs"],
                color=C["accent"], va="bottom", style="italic")


def slide_11_own_channel_recap(analysis, date, page_num=11, own_channel_deep=None):
    fig, ax = _fig()
    _header(ax, "NATE B JONES — TODAY'S VIDEO RECAP", "Latest videos from @NateBJones")
    _footer(ax, page_num, date)

    # Primary source: own_channel_deep (reliable)
    recap = {}
    if own_channel_deep:
        deep_videos = own_channel_deep.get("videos", [])
        if deep_videos:
            recap = _build_recap_from_deep(deep_videos)

    # Fallback
    if not recap.get("recap_available"):
        recap = analysis.get("own_channel_recap", {})

    if not recap.get("recap_available") or not recap.get("video_summaries"):
        note = recap.get("note", "No Nate B Jones data available — run fetch_own_channel_deep.py")
        ax.text(0.5, 0.5, note, transform=ax.transAxes, ha="center",
                color=C["muted"], fontsize=12)
        return fig

    summaries = recap.get("video_summaries", [])
    count     = min(len(summaries), 3)
    h         = (CONTENT_H - 0.016 * (count - 1)) / count

    for i, summary in enumerate(summaries[:count]):
        y = CONTENT_T - (i + 1) * h - i * 0.016
        _render_video_recap(ax, summary, 0.030, y, 0.940, h)

    return fig


# ---------------------------------------------------------------------------
# Slides 12–14 — Nate B Jones Video Deep Dives
# ---------------------------------------------------------------------------

def _render_nate_video_card(ax, video, x, y, w, h, compact=False):
    """Nate deep-dive card — white corporate style."""
    _card(ax, x, y, w, h)

    summary    = video.get("summary", {})
    title      = video.get("title", "Untitled")
    pub        = video.get("published_at", "")[:10]
    views      = video.get("view_count", 0)
    likes      = video.get("like_count", 0)
    one_liner  = summary.get("one_liner", "")
    key_points = summary.get("key_points", [])

    if compact:
        title_fs, stats_fs, liner_fs, bullet_fs = 11, 8.0, 8.5, 8.5
        t_off, s_off, l_off, d_off, b_off       = 0.036, 0.074, 0.108, 0.128, 0.150
        bullet_step, max_bullets = 0.056, 4
        t_chars, l_chars, b_chars = 82, 112, 110
    else:
        title_fs, stats_fs, liner_fs, bullet_fs = 14, 9.0, 10.0, 9.5
        t_off, s_off, l_off, d_off, b_off       = 0.036, 0.080, 0.126, 0.148, 0.175
        bullet_step, max_bullets = 0.082, 7
        t_chars, l_chars, b_chars = 90, 124, 112

    top = y + h
    ax.text(x + 0.018, top - t_off, _trunc(title, t_chars),
            transform=ax.transAxes, fontsize=title_fs,
            color=C["amber"], fontweight="bold", va="top")

    stats = f"{pub}   |   {_fmt_num(views)} views   |   {_fmt_num(likes)} likes"
    ax.text(x + 0.018, top - s_off, stats,
            transform=ax.transAxes, fontsize=stats_fs,
            color=C["muted"], va="top")

    if one_liner:
        ax.text(x + 0.018, top - l_off, _trunc(one_liner, l_chars),
                transform=ax.transAxes, fontsize=liner_fs,
                color=C["accent"], va="top", style="italic")

    ax.plot([x + 0.014, x + w - 0.014], [top - d_off, top - d_off],
            color=C["border"], linewidth=1.0, transform=ax.transAxes)

    for i, pt in enumerate(key_points[:max_bullets]):
        by = top - b_off - i * bullet_step
        if by < y + 0.018:
            break
        ax.text(x + 0.022, by, f"• {_trunc(pt, b_chars)}",
                transform=ax.transAxes, fontsize=bullet_fs,
                color=C["text"], va="top")


def slide_12_nate_deep(video, date, page_num=12):
    fig, ax = _fig()
    _header(ax, "NATE B JONES — VIDEO DEEP DIVE", _trunc(video.get("title", ""), 88))
    _footer(ax, page_num, date)
    _render_nate_video_card(ax, video, 0.025, CONTENT_B, 0.950, CONTENT_H, compact=False)
    return fig


def slide_13_nate_deep(video, date, page_num=13):
    fig, ax = _fig()
    _header(ax, "NATE B JONES — VIDEO DEEP DIVE", _trunc(video.get("title", ""), 88))
    _footer(ax, page_num, date)
    _render_nate_video_card(ax, video, 0.025, CONTENT_B, 0.950, CONTENT_H, compact=False)
    return fig


def slide_14_nate_deep_pair(video3, video4, date, page_num=14):
    fig, ax = _fig()
    _header(ax, "NATE B JONES — RECENT EPISODES", "Key insights from the last 4 videos")
    _footer(ax, page_num, date)
    pair_h = (CONTENT_H - 0.018) / 2
    y_top  = CONTENT_B + pair_h + 0.018
    _render_nate_video_card(ax, video3, 0.025, y_top,    0.950, pair_h, compact=True)
    if video4:
        _render_nate_video_card(ax, video4, 0.025, CONTENT_B, 0.950, pair_h, compact=True)
    return fig


# ---------------------------------------------------------------------------
# Main PDF generator
# ---------------------------------------------------------------------------

def generate_report_pdf(fetch_output, transcript_output, analysis_output,
                         own_channel_deep=None, output_path=None):
    """
    Orchestrate all slides into a multi-page PDF.
    Page numbers are assigned dynamically so overflow/continuation pages
    are numbered correctly. Returns the path to the generated file.
    """
    date_str      = fetch_output.get("fetch_date", datetime.date.today().isoformat())
    keyword_videos = fetch_output.get("keyword_videos", [])
    channel_data   = fetch_output.get("channel_data", [])
    video_count    = len(keyword_videos)
    channel_count  = len(channel_data)
    deep_videos    = (own_channel_deep or {}).get("videos", [])

    if output_path is None:
        output_path = TMP_DIR / f"report_{date_str}.pdf"

    print(f"[pdf] Generating {output_path.name} ...")

    # --- Build slide list with sequential page numbers ---
    slides = []   # list of (name, figure)
    pn     = 1    # current page number counter

    def _add(name, result):
        """Append one or more figures, incrementing pn for each."""
        nonlocal pn
        if isinstance(result, list):
            for i, fig in enumerate(result):
                label = name if i == 0 else f"{name} (cont.)"
                slides.append((label, fig))
                pn += 1
        else:
            slides.append((name, result))
            pn += 1

    # Cover — no footer page number
    slides.append(("Cover", slide_01_cover(date_str, video_count, channel_count)))
    pn += 1

    # Core slides — each function receives current pn at time of call
    _add("Executive Summary",  slide_02_executive_summary(analysis_output, date_str, pn))
    _add("AI Narrative",       slide_03_narrative_briefing(analysis_output, date_str, pn))
    _add("Must-Watch Videos",  slide_04_must_watch(keyword_videos, date_str, pn))
    _add("Tool Spotlight",     slide_05_tool_spotlight(analysis_output, date_str, pn))
    _add("Key Videos",         slide_06_key_videos(analysis_output, keyword_videos, date_str, pn))
    _add("Rising Content",     slide_07_rising_content(keyword_videos, analysis_output, date_str, pn))
    _add("Sentiment",          slide_08_sentiment(analysis_output, date_str, pn))
    _add("What's New",         slide_09_whats_new(analysis_output, date_str, pn))
    _add("Explore Next",       slide_10_explore_next(analysis_output, date_str, pn))
    _add("Nate B Jones Recap", slide_11_own_channel_recap(
        analysis_output, date_str, pn, own_channel_deep=own_channel_deep))

    # Nate deep-dive slides (conditional on own_channel_deep data)
    if len(deep_videos) >= 1:
        _add("Nate Deep #1",  slide_12_nate_deep(deep_videos[0], date_str, pn))
    if len(deep_videos) >= 2:
        _add("Nate Deep #2",  slide_13_nate_deep(deep_videos[1], date_str, pn))
    if len(deep_videos) >= 3:
        v4 = deep_videos[3] if len(deep_videos) >= 4 else None
        _add("Nate Deep #3+4", slide_14_nate_deep_pair(deep_videos[2], v4, date_str, pn))

    print(f"[pdf] Total pages: {len(slides)}")

    # --- Write PDF ---
    with PdfPages(str(output_path)) as pdf:
        d = pdf.infodict()
        d["Title"]    = f"AI Intelligence Report — {date_str}"
        d["Author"]   = "WAT Framework"
        d["Subject"]  = "YouTube AI/Automation Niche Analytics"
        d["Keywords"] = "YouTube, AI, Analytics, Automation, Learning"

        for name, fig in slides:
            try:
                pdf.savefig(fig, dpi=DPI, bbox_inches="tight",
                            facecolor=fig.get_facecolor())
                print(f"  [pdf] Slide: {name}")
            except Exception as e:
                print(f"  [pdf] WARNING: slide '{name}' failed: {e}", file=sys.stderr)
            finally:
                plt.close(fig)

    print(f"[pdf] Saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    date_str = datetime.date.today().isoformat()

    def _load_latest(pattern):
        path = TMP_DIR / pattern.replace("*", date_str)
        if not path.exists():
            candidates = sorted(TMP_DIR.glob(pattern), reverse=True)
            if not candidates:
                print(f"[error] No {pattern} found. Run earlier pipeline steps first.",
                      file=sys.stderr)
                sys.exit(1)
            path = candidates[0]
            print(f"[pdf] Using: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    fetch_out      = _load_latest("youtube_raw_*.json")
    transcript_out = _load_latest("transcripts_*.json")
    analysis_out   = _load_latest("analysis_*.json")

    deep_path = TMP_DIR / f"own_channel_deep_{date_str}.json"
    if not deep_path.exists():
        candidates = sorted(TMP_DIR.glob("own_channel_deep_*.json"), reverse=True)
        deep_path  = candidates[0] if candidates else None

    own_deep = json.loads(deep_path.read_text(encoding="utf-8")) if deep_path else None
    if own_deep:
        print(f"[pdf] Loaded own-channel deep data: {deep_path.name}")
    else:
        print("[pdf] No own_channel_deep_*.json found — slides 12-14 skipped")

    generate_report_pdf(fetch_out, transcript_out, analysis_out, own_channel_deep=own_deep)
