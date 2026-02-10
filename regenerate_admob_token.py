#!/usr/bin/env python3
"""Regenerate AdMob OAuth token locally.

Usage:
    python regenerate_admob_token.py

Prerequisites:
    - .env file with GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
    - pip install google-auth-oauthlib python-dotenv
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

SCOPES = [
    'https://www.googleapis.com/auth/admob.monetization',
    'https://www.googleapis.com/auth/admob.googlebidding.readwrite'
]


def main():
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("ERROR: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env")
        print()
        print("Example .env:")
        print("  GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com")
        print("  GOOGLE_CLIENT_SECRET=your-client-secret")
        return

    # Construct client config (no client_secrets.json file needed)
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }

    print("[AdMob] Browser will open for OAuth authentication...")
    print("[AdMob] Please sign in with your Google account and authorize the app.")
    print()

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save token to file
    token_path = Path(__file__).parent / 'admob_token.json'
    token_json = creds.to_json()
    with open(token_path, 'w') as f:
        f.write(token_json)

    print(f"[AdMob] Token saved to: {token_path}")
    print()
    print("=" * 60)
    print("For Streamlit Cloud deployment, copy the JSON below")
    print("into Streamlit Secrets as ADMOB_TOKEN_JSON:")
    print("=" * 60)
    print(token_json)


if __name__ == '__main__':
    main()
