"""One-off Gmail OAuth authorization.

Run this ONCE in a normal terminal to create ``token.json``. It opens a browser
so you can grant read-only access. After it succeeds, ``langgraph dev`` will use
the cached token and never needs the interactive login again.

    python authorize_gmail.py
"""

import os

from dotenv import load_dotenv
from langchain_google_community.gmail.utils import get_gmail_credentials

load_dotenv()

CREDENTIALS = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN = os.getenv("GMAIL_TOKEN_FILE", "token.json")

if __name__ == "__main__":
    creds = get_gmail_credentials(
        token_file=TOKEN,
        # NOTE: parameter is misspelled ("sercret") in langchain-google-community.
        client_sercret_file=CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    print(f"\nOK — token saved to '{TOKEN}'. You can now run: langgraph dev")
