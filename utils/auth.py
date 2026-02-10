"""Authentication utilities for Google OAuth login gate"""
import streamlit as st
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_TOKEN_FILE = os.path.join(_PROJECT_ROOT, "admob_token.json")


def is_authenticated() -> bool:
    """Check if the current user is authenticated.

    Returns True if session has a valid authenticated flag,
    or if session can be restored from admob_token.json.
    """
    if st.session_state.get("authenticated"):
        return True
    return _try_restore_session()


def _try_restore_session() -> bool:
    """Try to restore session from admob_token.json."""
    if not os.path.exists(_TOKEN_FILE):
        return False

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from utils.network_apis.admob_api import ADMOB_SCOPES

        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, ADMOB_SCOPES)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        if creds.valid:
            st.session_state["authenticated"] = True
            st.session_state["admob_credentials"] = json.loads(creds.to_json())
            if "user_info" not in st.session_state:
                _fetch_and_store_user_info(creds)
            return True
    except Exception as e:
        logger.warning(f"[Auth] Failed to restore session from token file: {e}")
        try:
            os.remove(_TOKEN_FILE)
        except OSError:
            pass

    return False


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
            with open(_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            st.session_state["authenticated"] = True
            _fetch_and_store_user_info(creds)
            st.query_params.clear()
            return True
    except Exception as e:
        st.query_params.clear()
        st.error(f"Google OAuth 인증 실패: {e}")

    return False


def logout() -> None:
    """Clear all auth-related session state and token file."""
    for key in ["authenticated", "user_info", "admob_credentials", "admob_oauth_state"]:
        if key in st.session_state:
            del st.session_state[key]

    if os.path.exists(_TOKEN_FILE):
        try:
            os.remove(_TOKEN_FILE)
        except OSError:
            pass


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
