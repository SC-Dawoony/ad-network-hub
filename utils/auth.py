"""Authentication utilities for Google OAuth login gate.

Session persistence strategy:
- st.session_state: per-user, per-tab (cleared on browser refresh)
- JWT cookie: per-browser, persists across refreshes (stores refresh_token)
- NO server-side file: prevents cross-user contamination on shared hosts
"""
import streamlit as st
import os
import json
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_JWT_COOKIE_NAME = "auth_jwt"
_JWT_EXPIRY_DAYS = 7


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _get_env(key: str) -> Optional[str]:
    """Get env var from Streamlit secrets or os.environ."""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


def _get_jwt_secret() -> str:
    """Get JWT signing secret."""
    secret = _get_env("JWT_SECRET")
    if secret:
        return secret
    # Derive from GOOGLE_CLIENT_SECRET as fallback
    client_secret = _get_env("GOOGLE_CLIENT_SECRET") or "default-change-me"
    return f"jwt-{client_secret}"


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _create_jwt(user_info: dict, refresh_token: str) -> str:
    """Create a signed JWT with user info and refresh token."""
    import jwt

    payload = {
        "email": user_info.get("email", ""),
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
        "rt": refresh_token,
        "exp": int(time.time()) + (_JWT_EXPIRY_DAYS * 24 * 60 * 60),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")


def _verify_jwt(token: str) -> Optional[dict]:
    """Verify and decode a JWT. Returns payload or None."""
    import jwt

    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ---------------------------------------------------------------------------
# Browser cookie helpers
# ---------------------------------------------------------------------------

def _get_cookie(name: str) -> Optional[str]:
    """Read a cookie from the browser request."""
    try:
        return st.context.cookies.get(name)
    except Exception:
        return None


def _set_cookie_js(name: str, value: str, max_age: int):
    """Set a browser cookie via JavaScript injection."""
    import streamlit.components.v1 as components

    components.html(
        f'<script>document.cookie="{name}={value};path=/;max-age={max_age};SameSite=Lax";</script>',
        height=0,
    )


def _clear_cookie_js(name: str):
    """Clear a browser cookie."""
    _set_cookie_js(name, "", 0)


# ---------------------------------------------------------------------------
# Core auth functions
# ---------------------------------------------------------------------------

def is_authenticated() -> bool:
    """Check if the current user is authenticated.

    1. st.session_state (fast, same tab)
    2. JWT cookie (persists across page refreshes)
    """
    if st.session_state.get("authenticated"):
        return True
    return _try_restore_from_cookie()


def _try_restore_from_cookie() -> bool:
    """Restore auth session from JWT cookie using refresh_token."""
    token = _get_cookie(_JWT_COOKIE_NAME)
    if not token:
        return False

    payload = _verify_jwt(token)
    if not payload:
        return False

    refresh_token = payload.get("rt")
    if not refresh_token:
        return False

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from utils.network_apis.admob_api import ADMOB_SCOPES

        client_id = _get_env("GOOGLE_CLIENT_ID")
        client_secret = _get_env("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            return False

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=ADMOB_SCOPES,
        )
        creds.refresh(Request())

        if creds.valid:
            st.session_state["authenticated"] = True
            st.session_state["admob_credentials"] = json.loads(creds.to_json())
            st.session_state["user_info"] = {
                "email": payload.get("email", ""),
                "name": payload.get("name", ""),
                "picture": payload.get("picture", ""),
            }
            return True
    except Exception as e:
        logger.warning(f"[Auth] Failed to restore from JWT cookie: {e}")

    return False


def ensure_auth_cookie():
    """Persist auth to browser cookie. Call after confirming authenticated."""
    if st.session_state.get("_auth_cookie_set"):
        return

    # Check if valid cookie already exists
    existing = _get_cookie(_JWT_COOKIE_NAME)
    if existing and _verify_jwt(existing):
        st.session_state["_auth_cookie_set"] = True
        return

    # Create and set new JWT cookie
    creds_data = st.session_state.get("admob_credentials")
    user_info = st.session_state.get("user_info")
    if not creds_data or not user_info:
        return

    refresh_token = creds_data.get("refresh_token") if isinstance(creds_data, dict) else None
    if not refresh_token:
        return

    token = _create_jwt(user_info, refresh_token)
    _set_cookie_js(_JWT_COOKIE_NAME, token, _JWT_EXPIRY_DAYS * 24 * 60 * 60)
    st.session_state["_auth_cookie_set"] = True


def _fetch_and_store_user_info(creds) -> None:
    """Fetch user email/name/picture from Google userinfo endpoint."""
    import requests as req

    try:
        resp = req.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["user_info"] = {
                "email": data.get("email", ""),
                "name": data.get("name", ""),
                "picture": data.get("picture", ""),
            }
            return
    except Exception as e:
        logger.warning(f"[Auth] Failed to fetch user info: {e}")

    st.session_state["user_info"] = {"email": "", "name": "", "picture": ""}


def handle_oauth_callback() -> bool:
    """Handle OAuth callback (?code=XXX in query params).

    Returns True if authentication succeeded.
    """
    if "code" not in st.query_params:
        return False

    from utils.network_apis.admob_api import AdMobAPI

    api = AdMobAPI()
    try:
        creds = api._exchange_auth_code(st.query_params["code"])
        if creds and creds.valid:
            st.session_state["admob_credentials"] = json.loads(creds.to_json())
            st.session_state["authenticated"] = True
            _fetch_and_store_user_info(creds)
            st.query_params.clear()
            return True
    except Exception as e:
        st.query_params.clear()
        st.error(f"Google OAuth 인증 실패: {e}")

    return False


def logout() -> None:
    """Clear all auth-related session state and cookie."""
    for key in ["authenticated", "user_info", "admob_credentials",
                "admob_oauth_state", "_auth_cookie_set"]:
        if key in st.session_state:
            del st.session_state[key]

    _clear_cookie_js(_JWT_COOKIE_NAME)


def require_auth() -> None:
    """Auth guard for sub-pages. Call after st.set_page_config().

    If not authenticated, shows a message and stops page rendering.
    """
    if is_authenticated():
        return

    st.warning("로그인이 필요합니다. 홈 페이지에서 로그인해 주세요.")
    st.page_link("app.py", label="로그인 페이지로 이동", icon="🔐")
    st.stop()


def render_login_page() -> None:
    """Render the login page UI."""
    _left, center, _right = st.columns([1, 2, 1])

    with center:
        st.markdown("---")
        st.markdown(
            "<h1 style='text-align: center;'>Ad Network Management Hub</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: gray;'>"
            "Google 계정으로 로그인하여 서비스를 이용하세요</p>",
            unsafe_allow_html=True,
        )
        st.markdown("")

        login_url = _get_login_url()
        if login_url:
            st.link_button(
                "Sign in with Google",
                login_url,
                use_container_width=True,
                type="primary",
            )
        else:
            st.error(
                "Google OAuth가 설정되지 않았습니다. "
                ".env에 GOOGLE_CLIENT_ID와 GOOGLE_CLIENT_SECRET을 설정하세요."
            )

        st.markdown("---")


def _get_login_url() -> Optional[str]:
    """Generate Google OAuth login URL (reuses AdMobAPI)."""
    from utils.network_apis.admob_api import AdMobAPI

    api = AdMobAPI()
    return api._get_auth_url()
