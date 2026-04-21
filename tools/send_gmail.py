"""
send_gmail.py — Send the daily PDF report via Gmail SMTP.

Uses App Password authentication (not OAuth — simpler for automation).
Attaches the PDF and sends to REPORT_RECIPIENT_EMAIL.

Prerequisites:
  1. Gmail 2FA enabled on the sender account
  2. App Password generated at myaccount.google.com/apppasswords
  3. GMAIL_ADDRESS, GMAIL_APP_PASSWORD, REPORT_RECIPIENT_EMAIL set in .env

Run directly:  python tools/send_gmail.py
"""

import sys
import time
import smtplib
import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.config import (
    GMAIL_ADDRESS, GMAIL_APP_PASSWORD, REPORT_RECIPIENT_EMAIL,
    REPORT_EMAIL_SUBJECT, REPORT_EMAIL_BODY, TMP_DIR
)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


# ---------------------------------------------------------------------------
# Build MIME message
# ---------------------------------------------------------------------------

def build_message(recipient: str, sender: str, subject: str,
                   body: str, pdf_path: Path) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    attachment = MIMEApplication(pdf_data, _subtype="pdf")
    attachment.add_header(
        "Content-Disposition", "attachment",
        filename=pdf_path.name
    )
    msg.attach(attachment)
    return msg


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def send_report(pdf_path: Path, date: str,
                video_count: int = 0,
                channel_count: int = 0,
                own_video_count: int = 0) -> bool:
    """
    Send the daily report PDF via Gmail SMTP.
    Returns True on success, False on failure (logs error, does not raise).
    Retries twice on connection errors. Fails immediately on auth errors.
    """
    if not GMAIL_ADDRESS:
        print("[email] ERROR: GMAIL_ADDRESS not set in .env", file=sys.stderr)
        return False
    if not GMAIL_APP_PASSWORD:
        print("[email] ERROR: GMAIL_APP_PASSWORD not set in .env", file=sys.stderr)
        return False
    if not REPORT_RECIPIENT_EMAIL:
        print("[email] ERROR: REPORT_RECIPIENT_EMAIL not set in .env", file=sys.stderr)
        return False
    if not pdf_path.exists():
        print(f"[email] ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return False

    subject = REPORT_EMAIL_SUBJECT.format(date=date)
    body = REPORT_EMAIL_BODY.format(
        date=date,
        video_count=video_count,
        channel_count=channel_count,
        own_video_count=own_video_count,
    )

    msg = build_message(
        recipient=REPORT_RECIPIENT_EMAIL,
        sender=GMAIL_ADDRESS,
        subject=subject,
        body=body,
        pdf_path=pdf_path,
    )

    retries = 2
    delay = 30

    for attempt in range(retries + 1):
        try:
            print(f"[email] Connecting to {SMTP_HOST}:{SMTP_PORT} ...")
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_ADDRESS, REPORT_RECIPIENT_EMAIL, msg.as_string())

            print(f"[email] Report sent to {REPORT_RECIPIENT_EMAIL} ({pdf_path.name})")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"[email] AUTH ERROR — check App Password (not account password): {e}",
                  file=sys.stderr)
            return False  # no point retrying

        except (smtplib.SMTPException, OSError) as e:
            print(f"[email] Connection error (attempt {attempt+1}/{retries+1}): {e}",
                  file=sys.stderr)
            if attempt < retries:
                print(f"[email] Retrying in {delay}s ...")
                time.sleep(delay)
            else:
                print("[email] All retry attempts failed.", file=sys.stderr)
                return False

    return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    date_str = datetime.date.today().isoformat()

    # Find today's PDF (or most recent)
    pdf_path = TMP_DIR / f"report_{date_str}.pdf"
    if not pdf_path.exists():
        candidates = sorted(TMP_DIR.glob("report_*.pdf"), reverse=True)
        if not candidates:
            print("[error] No report_*.pdf found in .tmp/. Run generate_report_pdf.py first.",
                  file=sys.stderr)
            sys.exit(1)
        pdf_path = candidates[0]
        print(f"[email] Using most recent PDF: {pdf_path.name}")
        date_str = pdf_path.stem.replace("report_", "")

    # Load real counts from today's data files
    video_count, channel_count, own_count = 0, 0, 0
    raw_path = TMP_DIR / f"youtube_raw_{date_str}.json"
    analysis_path = TMP_DIR / f"analysis_{date_str}.json"
    if raw_path.exists():
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        video_count   = len(raw.get("keyword_videos", []))
        channel_count = len(raw.get("channel_data", []))
    if analysis_path.exists():
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        own_count = analysis.get("own_channel_recap", {}).get("videos_found", 0)

    success = send_report(pdf_path, date_str, video_count, channel_count, own_count)
    sys.exit(0 if success else 1)
