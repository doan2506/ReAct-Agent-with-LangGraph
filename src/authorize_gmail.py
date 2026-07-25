"""Interactive script to authorize Google OAuth for Gmail and Google Calendar.

Run this ONCE in your terminal to generate or update `token.json`:
    python src/authorize_gmail.py
"""

import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

CREDENTIALS = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN = os.getenv("GMAIL_TOKEN_FILE", "token.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
]


def main() -> None:
    """Run interactive OAuth flow to create or update token.json."""
    if not os.path.exists(CREDENTIALS):
        print(f"❌ Error: Credentials file '{CREDENTIALS}' not found.")
        print("Please download credentials.json from Google Cloud Console and place it in the project root.")
        return

    # Delete outdated token.json if existing token has old/mismatching scope
    if os.path.exists(TOKEN):
        try:
            os.remove(TOKEN)
            print(f"🔄 Removed outdated '{TOKEN}' to request updated OAuth scopes.")
        except Exception as e:
            print(f"Warning: Could not remove old token file: {e}")

    print("🔐 Starting Google OAuth flow for Gmail & Calendar...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN, "w") as f:
        f.write(creds.to_json())

    print(f"\n✅ OAuth Authorization successful! Token saved to '{TOKEN}'.")


if __name__ == "__main__":
    main()
