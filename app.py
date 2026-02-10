"""Main Streamlit app - Ad Network Management Hub"""
import streamlit as st
from datetime import datetime
import os
from typing import Optional
from pathlib import Path
from utils.session_manager import SessionManager
from utils.network_manager import get_network_manager
from network_configs import get_available_networks, get_network_display_names, get_network_config


def switch_to_page(page_filename: str):
    """Switch to a page"""
    # Streamlit expects path relative to main script
    # Try different path formats
    page_paths = [
        f"pages/{page_filename}",  # Standard format
        page_filename,  # Just filename (Streamlit auto-detects pages/)
    ]
    
    for page_path in page_paths:
        if Path(page_path).exists():
            try:
                st.switch_page(page_path)
                return
            except Exception as e:
                continue
    
    # If all attempts fail, show error
    st.error(f"Could not navigate to page: {page_filename}. Please use the sidebar navigation.")

# Page configuration
st.set_page_config(
    page_title="Ad Network Management Hub",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
SessionManager.initialize()

# Handle OAuth callback (Google redirects here with ?code=XXX)
if "code" in st.query_params:
    from utils.network_apis.admob_api import AdMobAPI
    import json
    _api = AdMobAPI()
    try:
        _creds = _api._exchange_auth_code(st.query_params["code"])
        if _creds and _creds.valid:
            st.session_state["admob_credentials"] = json.loads(_creds.to_json())
            token_file = os.path.join(os.path.dirname(__file__), 'admob_token.json')
            with open(token_file, 'w') as f:
                f.write(_creds.to_json())
            st.query_params.clear()
            st.toast("AdMob 인증 완료!")
            st.rerun()
    except Exception as e:
        st.query_params.clear()
        st.error(f"AdMob OAuth 인증 실패: {e}")

# Sidebar - Network Selection
with st.sidebar:
    st.title("🌐 Ad Network Hub")
    st.divider()
    
    # Network selector
    available_networks = get_available_networks()
    display_names = get_network_display_names()
    
    network_options = [display_names.get(n, n.title()) for n in available_networks]
    current_network_display = display_names.get(SessionManager.get_current_network(), SessionManager.get_current_network().title())
    
    selected_network_display = st.selectbox(
        "Active Network",
        options=network_options,
        index=network_options.index(current_network_display) if current_network_display in network_options else 0
    )
    
    # Find network key from display name
    selected_network = None
    for key, display in display_names.items():
        if display == selected_network_display:
            selected_network = key
            break
    
    if selected_network and selected_network != SessionManager.get_current_network():
        SessionManager.switch_network(selected_network)
        st.rerun()
    
    st.divider()
    
    # Quick actions
    st.subheader("Quick Actions")
    
    if st.button("📱 Create App", use_container_width=True):
        switch_to_page("1_Create_App.py")
    
    if st.button("🎯 Create Unit", use_container_width=True):
        switch_to_page(".hidden_Create_Unit.py")

    # Hidden: View Lists menu item
    # if st.button("📋 View Lists", use_container_width=True):
    #     switch_to_page(".hidden_3_View_Lists.py")

    if st.button("⚙️ Update Ad Unit", use_container_width=True):
        switch_to_page("4_Update_Ad_Unit.py")
    
    st.divider()
    
    # Connection status
    st.subheader("Connection Status")
    network_manager = get_network_manager()
    
    for network in available_networks:
        config = get_network_config(network)
        display_name = display_names.get(network, network.title())
        
        # Helper function to get env vars from Streamlit secrets or .env
        def get_env(key: str) -> Optional[str]:
            try:
                if hasattr(st, 'secrets') and st.secrets and key in st.secrets:
                    return st.secrets[key]
            except:
                pass
            return os.getenv(key)
        
        # Check if network credentials are set
        if network == "ironsource":
            # Check IronSource credentials
            bearer_token = get_env("IRONSOURCE_BEARER_TOKEN") or get_env("IRONSOURCE_API_TOKEN")
            refresh_token = get_env("IRONSOURCE_REFRESH_TOKEN")
            secret_key = get_env("IRONSOURCE_SECRET_KEY")
            if bearer_token or (refresh_token and secret_key):
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "pangle":
            # Check Pangle credentials
            security_key = get_env("PANGLE_SECURITY_KEY")
            user_id = get_env("PANGLE_USER_ID")
            role_id = get_env("PANGLE_ROLE_ID")
            if security_key and user_id and role_id:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "bigoads":
            # Check for BigOAds credentials
            developer_id = get_env("BIGOADS_DEVELOPER_ID")
            token = get_env("BIGOADS_TOKEN")
            if developer_id and token:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "mintegral":
            # Check for Mintegral credentials
            skey = get_env("MINTEGRAL_SKEY")
            secret = get_env("MINTEGRAL_SECRET")
            if skey and secret:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "inmobi":
            # Check for InMobi credentials
            account_name = get_env("INMOBI_ACCOUNT_NAME")
            account_id = get_env("INMOBI_ACCOUNT_ID")
            username = get_env("INMOBI_USERNAME")
            client_secret = get_env("INMOBI_CLIENT_SECRET")
            # InMobi 인증 방식에 따라 필요한 필드 확인 (API 문서 참조 필요)
            if account_name and account_id and username and client_secret:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "fyber":
            # Check for Fyber (DT) credentials
            client_id = get_env("DT_CLIENT_ID")
            client_secret = get_env("DT_CLIENT_SECRET")
            access_token = get_env("FYBER_ACCESS_TOKEN")
            publisher_id = get_env("FYBER_PUBLISHER_ID")
            # Fyber 인증 방식에 따라 필요한 필드 확인 (API 문서 참조 필요)
            if client_id and client_secret and access_token and publisher_id:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "applovin":
            # Check for AppLovin credentials
            api_key = get_env("APPLOVIN_API_KEY")
            if api_key:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "unity":
            # Check for Unity credentials
            organization_id = get_env("UNITY_ORGANIZATION_ID")
            key_id = get_env("UNITY_KEY_ID")
            secret_key = get_env("UNITY_SECRET_KEY")
            if organization_id and key_id and secret_key:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "vungle":
            # Check for Vungle (Liftoff) credentials
            # Either JWT token or Secret token is sufficient (secret token can get JWT automatically)
            jwt_token = get_env("LIFTOFF_JWT_TOKEN") or get_env("VUNGLE_JWT_TOKEN")
            secret_token = get_env("LIFTOFF_SECRET_TOKEN") or get_env("VUNGLE_SECRET_TOKEN")
            if jwt_token or secret_token:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "admob":
            # Check for AdMob credentials (OAuth-based, multiple sources)
            admob_token_json = get_env("ADMOB_TOKEN_JSON")
            admob_account_id = get_env("ADMOB_ACCOUNT_ID")
            admob_token_file = os.path.exists(
                os.path.join(os.path.dirname(__file__), 'admob_token.json')
            )
            admob_session_creds = st.session_state.get("admob_credentials")
            google_client_id = get_env("GOOGLE_CLIENT_ID")
            google_client_secret = get_env("GOOGLE_CLIENT_SECRET")

            if (admob_token_json or admob_token_file or admob_session_creds) and admob_account_id:
                status = "✅ Active"
            elif admob_account_id and google_client_id and google_client_secret:
                status = "🔑 Login Required"
            else:
                status = "⚠️ Not Set"
        else:
            # For other networks, check credentials
            status = "⚠️ Not Set"

        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{display_name}**")
        with col2:
            st.write(status)

        # AdMob: show login button when OAuth Ready
        if network == "admob" and status == "🔑 Login Required":
            from utils.network_apis.admob_api import AdMobAPI
            _admob_api = AdMobAPI()
            auth_url = _admob_api._get_auth_url()
            if auth_url:
                st.link_button("🔐 Google 로그인", auth_url, use_container_width=True)

# Main content
st.title("🌐 Ad Network Management Hub")
st.markdown("Manage multiple ad networks from a single interface")

# Current network info
current_network = SessionManager.get_current_network()
config = get_network_config(current_network)
display_name = display_names.get(current_network, current_network.title())

st.info(f"**Current Network:** {display_name}")

# AdMob Authentication Section
_admob_token_exists = os.path.exists(os.path.join(os.path.dirname(__file__), 'admob_token.json'))
_admob_session = st.session_state.get("admob_credentials")
_admob_has_token = _admob_token_exists or _admob_session or os.getenv("ADMOB_TOKEN_JSON")
_google_cid = os.getenv("GOOGLE_CLIENT_ID")
_google_csec = os.getenv("GOOGLE_CLIENT_SECRET")

if _google_cid and _google_csec:
    with st.expander("🔐 AdMob Authentication", expanded=not _admob_has_token):
        if _admob_has_token:
            st.success("AdMob 인증 완료")
            if st.button("재인증 (스코프 변경 시)"):
                # Clear existing credentials
                if os.path.exists(os.path.join(os.path.dirname(__file__), 'admob_token.json')):
                    os.remove(os.path.join(os.path.dirname(__file__), 'admob_token.json'))
                if "admob_credentials" in st.session_state:
                    del st.session_state["admob_credentials"]
                st.rerun()
        else:
            st.warning("AdMob을 사용하려면 Google 계정으로 인증이 필요합니다.")
            from utils.network_apis.admob_api import AdMobAPI
            _admob_login_api = AdMobAPI()
            _auth_url = _admob_login_api._get_auth_url()
            if _auth_url:
                st.link_button("Google 계정으로 로그인", _auth_url, use_container_width=True)

# Network statistics
st.subheader("📊 Network Statistics")

# Get cached data
apps_cache = SessionManager.get_cached_apps(current_network)
last_sync = st.session_state.get('last_sync_time', {}).get(current_network)

# Create statistics table
stats_data = []
for network in available_networks:
    network_display = display_names.get(network, network.title())
    apps = SessionManager.get_cached_apps(network)
    sync_time = st.session_state.get('last_sync_time', {}).get(network)
    
    stats_data.append({
        "Network": network_display,
        "Apps": len(apps) if apps else "-",
        "Units": "-",  # Would need to aggregate from units_cache
        "Last Sync": sync_time.strftime("%Y-%m-%d %H:%M") if sync_time else "Never"
    })

if stats_data:
    st.dataframe(stats_data, use_container_width=True, hide_index=True)
else:
    st.info("No data available. Use 'View Lists' to fetch data from networks.")

# Refresh button
if st.button("🔄 Refresh All Networks"):
    with st.spinner("Refreshing network data..."):
        network_manager = get_network_manager()
        for network in available_networks:
            try:
                apps = network_manager.get_apps(network)
                SessionManager.cache_apps(network, apps)
                st.success(f"✅ {display_names.get(network, network)} refreshed")
            except Exception as e:
                st.error(f"❌ Failed to refresh {network}: {str(e)}")
                SessionManager.log_error(network, str(e))
        st.rerun()

# Recent activity
st.subheader("📝 Recent Activity")

col1, col2 = st.columns(2)

with col1:
    st.write("**Created Apps**")
    created_apps = st.session_state.get('created_apps', [])
    if created_apps:
        for app in created_apps[-5:]:  # Show last 5
            st.write(f"- {app.get('name', 'Unknown')} ({app.get('network', 'unknown')})")
    else:
        st.info("No apps created yet")

with col2:
    st.write("**Created Units**")
    created_units = st.session_state.get('created_units', [])
    if created_units:
        for unit in created_units[-5:]:  # Show last 5
            st.write(f"- {unit.get('name', 'Unknown')} ({unit.get('network', 'unknown')})")
    else:
        st.info("No units created yet")

# Settings section
with st.expander("⚙️ Settings"):
    st.write("**Network Credentials**")
    st.info("Configure network API credentials in environment variables or settings file")
    
    st.write("**Export/Import**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export All Data"):
            st.info("Export functionality coming soon")
    with col2:
        if st.button("📤 Import Data"):
            st.info("Import functionality coming soon")
