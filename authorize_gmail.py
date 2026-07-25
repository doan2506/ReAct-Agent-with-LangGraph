"""Interactive script to authorize Google OAuth for Gmail and Google Calendar.

Run this script once from your terminal to generate or update `token.json`:
    python authorize_gmail.py
"""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
]


def main() -> None:
    """Run interactive OAuth flow to create token.json with full required scopes."""
    credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")

    if not os.path.exists(credentials_file):
        print(f"❌ Error: Credentials file '{credentials_file}' not found.")
        print("Please download credentials.json from Google Cloud Console and place it in this directory.")
        return

    print("🔐 Starting Google OAuth flow for Gmail & Calendar...")
    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(token_file, "w") as token:
        token.write(creds.to_json())

    print(f"✅ Authorization successful! Cached token saved to '{token_file}'.")


if __name__ == "__main__":
    main()
