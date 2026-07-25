"""Interactive script to authorize Google OAuth for Gmail and Google Calendar.

Run this ONCE in your terminal to generate or update `token.json`:
    python src/authorize_gmail.py
"""

import os

from dotenv import load_dotenv
from langchain_google_community.gmail.utils import get_gmail_credentials

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

    print("🔐 Starting Google OAuth flow for Gmail & Calendar...")
    get_gmail_credentials(
        token_file=TOKEN,
        client_sercret_file=CREDENTIALS,
        scopes=SCOPES,
    )
    print(f"\n✅ OAuth Authorization successful! Token saved to '{TOKEN}'.")


if __name__ == "__main__":
    main()
