"""View Lists page - Apps and Slots"""
import streamlit as st
import pandas as pd
from utils.session_manager import SessionManager
from utils.network_manager import get_network_manager
from network_configs import get_network_config, get_network_display_names

# Page configuration
st.set_page_config(
    page_title="View Lists",
    page_icon="📋",
    layout="wide"
)

# Initialize session
SessionManager.initialize()

# Get current network
current_network = SessionManager.get_current_network()
config = get_network_config(current_network)
display_names = get_network_display_names()
network_display = display_names.get(current_network, current_network.title())

st.title("📋 View Apps & Slots")
st.markdown(f"**Network:** {network_display}")

st.divider()

# Filters
col1, col2 = st.columns([3, 1])

with col1:
    view_type = st.radio(
        "View",
        options=["Apps", "Slots"],
        horizontal=True
    )

with col2:
    refresh_button = st.button("🔄 Refresh", use_container_width=True)

st.divider()

# Load data
network_manager = get_network_manager()

if view_type == "Apps":
    st.subheader("📊 Apps List")
    
    # Load apps
    with st.spinner("Loading apps..."):
        apps = SessionManager.get_cached_apps(current_network)
        
        if refresh_button or not apps:
            try:
                apps = network_manager.get_apps(current_network)
                SessionManager.cache_apps(current_network, apps)
                if refresh_button:
                    st.success("✅ Apps refreshed")
            except Exception as e:
                st.error(f"❌ Failed to load apps: {str(e)}")
                SessionManager.log_error(current_network, str(e))
                apps = []
    
    if apps:
        # Convert to DataFrame
        df_data = []
        for app in apps:
            df_data.append({
                "App Code": app.get("appCode", "N/A"),
                "Name": app.get("name", "Unknown"),
                "Platform": app.get("platform", "N/A"),
                "Status": app.get("status", "N/A")
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.info(f"**Total:** {len(apps)} apps")
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Export CSV",
                data=csv,
                file_name=f"{current_network}_apps.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            json_str = df.to_json(orient="records", indent=2)
            st.download_button(
                label="📥 Export JSON",
                data=json_str,
                file_name=f"{current_network}_apps.json",
                mime="application/json",
                use_container_width=True
            )
    else:
        st.info("No apps found. Create an app first or check your network connection.")

else:  # Slots
    st.subheader("📊 Slots List")
    
    # Load apps first for selection
    with st.spinner("Loading apps..."):
        apps = SessionManager.get_cached_apps(current_network)
        
        if not apps:
            try:
                apps = network_manager.get_apps(current_network)
                SessionManager.cache_apps(current_network, apps)
            except Exception as e:
                st.error(f"❌ Failed to load apps: {str(e)}")
                apps = []
    
    if not apps:
        st.warning("No apps found. Please create an app first.")
        st.stop()
    
    # App selection
    app_options = []
    app_code_map = {}
    for app in apps:
        app_code = app.get("appCode", "N/A")
        app_name = app.get("name", "Unknown")
        display_text = f"{app_code} ({app_name})"
        app_options.append(display_text)
        app_code_map[display_text] = app_code
    
    selected_app_display = st.selectbox(
        "Select App",
        options=app_options,
        help="Select an app to view its slots"
    )
    
    selected_app_code = app_code_map.get(selected_app_display, "")
    selected_app_name = selected_app_display.split("(")[1].split(")")[0] if "(" in selected_app_display else "Unknown"
    
    st.write(f"**App:** {selected_app_name} ({selected_app_code})")
    
    st.divider()
    
    # Load slots
    with st.spinner("Loading slots..."):
        units = SessionManager.get_cached_units(current_network, selected_app_code)
        
        if refresh_button or not units:
            try:
                units = network_manager.get_units(current_network, selected_app_code)
                SessionManager.cache_units(current_network, selected_app_code, units)
                if refresh_button:
                    st.success("✅ Slots refreshed")
            except Exception as e:
                st.error(f"❌ Failed to load slots: {str(e)}")
                SessionManager.log_error(current_network, str(e))
                units = []
    
    if units:
        # Convert to DataFrame
        df_data = []
        for unit in units:
            df_data.append({
                "Slot Code": unit.get("slotCode", "N/A"),
                "Name": unit.get("name", "Unknown"),
                "Ad Type": unit.get("adType", "N/A"),
                "Auction Type": unit.get("auctionType", "N/A")
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.info(f"**Total:** {len(units)} slots")
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Export CSV",
                data=csv,
                file_name=f"{current_network}_{selected_app_code}_slots.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            json_str = df.to_json(orient="records", indent=2)
            st.download_button(
                label="📥 Export JSON",
                data=json_str,
                file_name=f"{current_network}_{selected_app_code}_slots.json",
                mime="application/json",
                use_container_width=True
            )
    else:
        st.info(f"No slots found for app {selected_app_code}. Create a slot first.")

# Network selector
st.divider()
st.subheader("Switch Network")
available_networks = get_network_display_names()
network_options = list(available_networks.values())
selected_network_display = st.selectbox(
    "Select Network",
    options=network_options,
    index=network_options.index(network_display) if network_display in network_options else 0
)

# Find network key
for key, display in available_networks.items():
    if display == selected_network_display:
        if key != current_network:
            SessionManager.switch_network(key)
            st.rerun()
        break

