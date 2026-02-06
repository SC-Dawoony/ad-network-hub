"""Login page - Google OAuth"""
import streamlit as st
from utils.auth import AuthManager

st.set_page_config(
    page_title="Login - Ad Network Hub",
    page_icon="🔐",
    layout="centered"
)

# Handle OAuth callback (code in URL)
query_params = st.query_params
code = query_params.get("code")

if code:
    with st.spinner("로그인 처리 중..."):
        if AuthManager.login_with_code(code):
            # Clear code from URL and redirect to main app
            st.query_params.clear()
            st.switch_page("app.py")
        else:
            st.error("❌ 로그인에 실패했습니다. 다시 시도해주세요.")
            # Clear invalid code
            params = dict(st.query_params)
            params.pop("code", None)
            st.query_params.clear()
            for k, v in params.items():
                st.query_params[k] = v

# Show login UI
st.title("🔐 Ad Network Hub 로그인")
st.markdown("Google 계정으로 로그인하여 서비스를 이용하세요.")

auth_url = AuthManager.get_authorization_url()

if auth_url:
    st.link_button("🔑 Google로 로그인", auth_url, type="primary", use_container_width=True)
else:
    st.error("""
    ⚠️ **OAuth 설정이 필요합니다.**
    
    `.env` 파일 또는 Streamlit Secrets에 다음 값을 설정해주세요:
    - `GOOGLE_CLIENT_ID`
    - `GOOGLE_CLIENT_SECRET`
    - `GOOGLE_REDIRECT_URI` (선택, 기본: http://localhost:8501/)
    
    [Google Cloud Console](https://console.cloud.google.com/)에서 OAuth 2.0 클라이언트 ID를 발급받으세요.
    """)
