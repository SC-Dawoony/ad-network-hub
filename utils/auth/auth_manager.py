"""Auth state management and token persistence for login persistence"""
import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict

import streamlit as st

from .google_auth import (
    get_authorization_url,
    exchange_code_for_tokens,
    get_user_info,
    refresh_credentials,
)
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# Directory to store tokens (persistent across restarts)


def is_auth_required() -> bool:
    """Check if auth should be enforced.
    
    Returns True only when ENABLE_AUTH is explicitly set to true/1.
    Localhost: ENABLE_AUTH not set or false → skip auth
    Production: ENABLE_AUTH=true in secrets/env → require auth
    """
    try:
        if hasattr(st, "secrets") and st.secrets:
            val = st.secrets.get("ENABLE_AUTH", os.getenv("ENABLE_AUTH", ""))
        else:
            val = os.getenv("ENABLE_AUTH", "")
    except Exception:
        val = os.getenv("ENABLE_AUTH", "")
    return str(val).lower() in ("true", "1", "yes")


AUTH_TOKENS_DIR = Path(__file__).resolve().parent.parent.parent / "auth_tokens"
SESSION_KEY_USER = "auth_user"
SESSION_KEY_CREDENTIALS = "auth_credentials"


def _get_token_file_path() -> Path:
    """Get path to token storage file (single user for now)"""
    AUTH_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    return AUTH_TOKENS_DIR / "tokens.json"


def _credentials_to_dict(creds: Credentials) -> dict:
    """Convert Credentials to serializable dict"""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
    }


def _dict_to_credentials(data: dict) -> Credentials:
    """Restore Credentials from dict"""
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", []),
    )


def save_tokens(credentials: Credentials, user_info: Dict) -> bool:
    """Persist tokens to file for login persistence"""
    try:
        token_path = _get_token_file_path()
        data = {
            "credentials": _credentials_to_dict(credentials),
            "user": user_info,
        }
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"[Auth] Tokens saved to {token_path}")
        return True
    except Exception as e:
        logger.error(f"[Auth] Failed to save tokens: {e}")
        return False


def load_tokens() -> Optional[Dict]:
    """Load persisted tokens from file"""
    token_path = _get_token_file_path()
    if not token_path.exists():
        return None
    try:
        with open(token_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Auth] Failed to load tokens: {e}")
        return None


def clear_tokens() -> bool:
    """Remove persisted tokens (logout)"""
    token_path = _get_token_file_path()
    if token_path.exists():
        try:
            token_path.unlink()
            logger.info("[Auth] Tokens cleared")
            return True
        except Exception as e:
            logger.error(f"[Auth] Failed to clear tokens: {e}")
    return False


class AuthManager:
    """Manage authentication state and persistence"""

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is logged in (session or persisted tokens).
        If auth is not required (localhost), always returns True."""
        if not is_auth_required():
            return True  # Skip auth on localhost
        # 1. Check session state
        if SESSION_KEY_USER in st.session_state and st.session_state[SESSION_KEY_USER]:
            return True

        # 2. Try restore from persisted tokens
        return AuthManager._restore_from_persisted()

    @staticmethod
    def _restore_from_persisted() -> bool:
        """Restore session from persisted tokens"""
        data = load_tokens()
        if not data:
            return False

        creds_dict = data.get("credentials", {})
        user_info = data.get("user", {})

        if not creds_dict or not creds_dict.get("refresh_token"):
            return False

        try:
            creds = _dict_to_credentials(creds_dict)
            if creds.expired:
                creds = refresh_credentials(creds)
            if creds and creds.valid:
                st.session_state[SESSION_KEY_USER] = user_info
                st.session_state[SESSION_KEY_CREDENTIALS] = creds
                logger.info(f"[Auth] Restored session for {user_info.get('email', 'unknown')}")
                return True
        except Exception as e:
            logger.error(f"[Auth] Failed to restore: {e}")

        return False

    @staticmethod
    def get_user() -> Optional[Dict]:
        """Get current user info"""
        if SESSION_KEY_USER in st.session_state:
            return st.session_state[SESSION_KEY_USER]
        return None

    @staticmethod
    def login_with_code(code: str) -> bool:
        """Exchange code and establish session, persist tokens"""
        creds = exchange_code_for_tokens(code)
        if not creds:
            return False

        user_info = get_user_info(creds)
        if not user_info:
            return False

        st.session_state[SESSION_KEY_USER] = user_info
        st.session_state[SESSION_KEY_CREDENTIALS] = creds
        save_tokens(creds, user_info)
        logger.info(f"[Auth] Logged in: {user_info.get('email')}")
        return True

    @staticmethod
    def logout() -> bool:
        """Clear session and persisted tokens"""
        for key in [SESSION_KEY_USER, SESSION_KEY_CREDENTIALS]:
            if key in st.session_state:
                del st.session_state[key]
        clear_tokens()
        return True

    @staticmethod
    def get_authorization_url() -> Optional[str]:
        """Get Google OAuth URL for login button"""
        return get_authorization_url()
