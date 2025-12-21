"""Main Streamlit app - Ad Network Management Hub"""
import streamlit as st
from datetime import datetime
import os
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
    
    if st.button("📋 View Lists", use_container_width=True):
        switch_to_page("3_View_Lists.py")
    
    st.divider()
    
    # Connection status
    st.subheader("Connection Status")
    network_manager = get_network_manager()
    
    for network in available_networks:
        config = get_network_config(network)
        display_name = display_names.get(network, network.title())
        
        # Check if network credentials are set
        if network == "ironsource":
            # Check IronSource credentials
            bearer_token = os.getenv("IRONSOURCE_BEARER_TOKEN") or os.getenv("IRONSOURCE_API_TOKEN")
            refresh_token = os.getenv("IRONSOURCE_REFRESH_TOKEN")
            secret_key = os.getenv("IRONSOURCE_SECRET_KEY")
            if bearer_token or (refresh_token and secret_key):
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "pangle":
            # Check Pangle credentials
            security_key = os.getenv("PANGLE_SECURITY_KEY")
            user_id = os.getenv("PANGLE_USER_ID")
            role_id = os.getenv("PANGLE_ROLE_ID")
            if security_key and user_id and role_id:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "bigoads":
            # Check for BigOAds credentials
            developer_id = os.getenv("BIGOADS_DEVELOPER_ID")
            token = os.getenv("BIGOADS_TOKEN")
            if developer_id and token:
                status = "✅ Active"
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

# Main content
st.title("🌐 Ad Network Management Hub")
st.markdown("Manage multiple ad networks from a single interface")

# Current network info
current_network = SessionManager.get_current_network()
config = get_network_config(current_network)
display_name = display_names.get(current_network, current_network.title())

st.info(f"**Current Network:** {display_name}")

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
