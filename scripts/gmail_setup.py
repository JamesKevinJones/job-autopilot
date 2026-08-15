"""One-time Gmail authorisation for the daily digest.

Run this once. It opens a browser, you approve sending mail as yourself, and
a refresh token is written to gmail.token.json (gitignored). Your password is
never involved and never seen by this script.

Before running:

  1. Go to https://console.cloud.google.com/ and create a project.
  2. APIs & Services -> Library -> enable "Gmail API".
  3. APIs & Services -> OAuth consent screen -> External -> add
     kj6384647@gmail.com as a test user.
  4. APIs & Services -> Credentials -> Create credentials ->
     OAuth client ID -> Desktop app.
  5. Download the JSON and save it as credentials.json in the project root.

Then:

  python -m pip install google-auth-oauthlib google-api-python-client
  python scripts/gmail_setup.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autopilot.notify import CLIENT_PATH, SCOPES, TOKEN_PATH  # noqa: E402


def main() -> int:
    if not CLIENT_PATH.exists():
        print(f"Missing {CLIENT_PATH}")
        print("Follow steps 1-5 in this file's docstring first.")
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Install the dependencies first:")
        print("  python -m pip install google-auth-oauthlib google-api-python-client")
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    print(f"Authorised. Token written to {TOKEN_PATH}")
    print("The 21:00 digest will now be emailed as well as written to docs/DAILY/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
