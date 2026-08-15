"""Digest delivery: Windows toast always, Gmail when authorised.

Gmail uses OAuth with a token you create once in a browser. No password or
app password is ever stored or handled here — only a refresh token that
Google issues to you and that lives in a gitignored file.
"""

from __future__ import annotations

import base64
import json
import subprocess
from email.message import EmailMessage
from pathlib import Path

from .config import ROOT, load_profile

TOKEN_PATH = ROOT / "gmail.token.json"
CLIENT_PATH = ROOT / "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def toast(title: str, message: str) -> None:
    """Windows notification. Best effort — never raises."""
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
        "ContentType = WindowsRuntime] > $null; "
        "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
        "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
        f"$t.GetElementsByTagName('text')[0].AppendChild($t.CreateTextNode('{title}')) > $null; "
        f"$t.GetElementsByTagName('text')[1].AppendChild($t.CreateTextNode('{message}')) > $null; "
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
        "'Job Autopilot').Show([Windows.UI.Notifications.ToastNotification]::new($t))"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, timeout=20, check=False,
        )
    except Exception:
        pass


def gmail_ready() -> bool:
    return TOKEN_PATH.exists()


def send_gmail(subject: str, body_markdown: str) -> str:
    """Send the digest to yourself. Returns a status string, never raises."""
    if not gmail_ready():
        return "gmail: not authorised (run scripts/gmail_setup.py)"

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        return "gmail: google-api-python-client not installed"

    try:
        creds = Credentials.from_authorized_user_info(
            json.loads(TOKEN_PATH.read_text(encoding="utf-8")), SCOPES
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

        profile = load_profile()
        to_addr = profile["delivery"]["gmail_to"]

        msg = EmailMessage()
        msg["To"] = to_addr
        msg["From"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body_markdown)

        service = build("gmail", "v1", credentials=creds)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"gmail: sent to {to_addr}"
    except Exception as exc:
        return f"gmail: failed ({type(exc).__name__}: {str(exc)[:80]})"


def deliver(path: str, summary_line: str, body_markdown: str, subject: str) -> list[str]:
    """Deliver the digest through every configured channel."""
    results = [f"file: {path}"]
    toast("Job Autopilot", summary_line)
    results.append("toast: shown")
    results.append(send_gmail(subject, body_markdown))
    return results
