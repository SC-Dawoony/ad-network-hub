"""Google OAuth 2.0 authentication for app login"""
import os
import logging
from typing import Optional, Dict
from urllib.parse import urlencode

import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

# Scopes for Google OAuth - openid, email, profile for basic user info
GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _get_env(key: str) -> Optional[str]:
    """Get env from Streamlit secrets or os.environ"""
    try:
        if hasattr(st, "secrets") and st.secrets:
            # Try direct key, nested, or .get()
            if key in st.secrets:
                val = st.secrets[key]
                return str(val) if val is not None else None
            if hasattr(st.secrets, "get"):
                val = st.secrets.get(key)
                return str(val) if val is not None else None
    except Exception:
        pass
    return os.getenv(key)


def get_redirect_uri() -> str:
    """Get OAuth redirect URI (Login page: 0_Login.py → /login)"""
    return _get_env("GOOGLE_REDIRECT_URI") or "http://localhost:8501/login"


def get_authorization_url() -> Optional[str]:
    """Generate Google OAuth authorization URL"""
    client_id = _get_env("GOOGLE_CLIENT_ID")
    client_secret = _get_env("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("[Google Auth] GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set")
        return None

    redirect_uri = get_redirect_uri()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> Optional[Credentials]:
    """Exchange authorization code for tokens"""
    client_id = _get_env("GOOGLE_CLIENT_ID")
    client_secret = _get_env("GOOGLE_CLIENT_SECRET")
    redirect_uri = get_redirect_uri()

    if not all([client_id, client_secret, code]):
        logger.error("[Google Auth] Missing client credentials or code")
        return None

    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=GOOGLE_OAUTH_SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
        logger.info("[Google Auth] Successfully exchanged code for tokens")
        return credentials
    except Exception as e:
        logger.error(f"[Google Auth] Failed to exchange code: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def get_user_info(credentials: Credentials) -> Optional[Dict]:
    """Fetch user info from Google using access token"""
    try:
        import requests
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error(f"[Google Auth] Failed to get user info: {e}")
    return None


def refresh_credentials(credentials: Credentials) -> Optional[Credentials]:
    """Refresh expired credentials"""
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            return credentials
        except Exception as e:
            logger.error(f"[Google Auth] Failed to refresh: {e}")
    return credentials if credentials.valid else None
