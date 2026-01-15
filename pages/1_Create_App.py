"""Create App/Media and Unit page"""
import streamlit as st
import logging
import json
from utils.session_manager import SessionManager
from utils.ui_components import DynamicFormRenderer
from utils.network_manager import get_network_manager, handle_api_response, _mask_sensitive_data
from utils.validators import validate_app_name, validate_package_name, validate_url, validate_slot_name
from network_configs import get_network_config, get_network_display_names
from components.unity_update_ad_units import render_unity_update_ad_units
from components.create_app_ui import render_create_app_ui
from components.create_unit_applovin import render_applovin_create_unit_ui
from components.create_unit_unity import render_unity_create_unit_ui
from components.create_unit_app_selector import render_app_code_selector
from components.create_unit_common import render_create_unit_common_ui
from components.create_app_helpers import (
    extract_package_name_from_store_url,
    normalize_platform_str,
    get_bigoads_pkg_name_display,
    generate_slot_name,
    create_default_slot
)

logger = logging.getLogger(__name__)

# Alias for backward compatibility (to avoid breaking existing code)
_extract_package_name_from_store_url = extract_package_name_from_store_url
_normalize_platform_str = normalize_platform_str
_get_bigoads_pkg_name_display = get_bigoads_pkg_name_display
_generate_slot_name = generate_slot_name
_create_default_slot = create_default_slot


# Page configuration
st.set_page_config(
    page_title="Create App & Unit",
    page_icon="📱",
    layout="wide"
)

# Initialize session
SessionManager.initialize()

# Get current network
current_network = SessionManager.get_current_network()
config = get_network_config(current_network)
display_names = get_network_display_names()
network_display = display_names.get(current_network, current_network.title())

st.title("📱 Create App & Unit")
st.markdown(f"**Network:** {network_display}")

# Check if network supports app creation
if not config.supports_create_app():
    if current_network == "applovin":
        st.warning(f"⚠️ {network_display}는 API를 통한 앱 생성 기능을 지원하지 않습니다.")
        st.info("💡 AppLovin에서는 앱을 수동으로 생성해야 합니다. 대시보드에서 앱을 생성한 후, 아래 'Create Unit' 섹션에서 Ad Unit을 생성할 수 있습니다.")
    else:
        st.warning(f"⚠️ {network_display} does not support app creation via API")
        st.info("Please create apps manually in the network's dashboard")
        st.stop()

if current_network != "applovin":
    st.info(f"✅ {network_display} - Create API Available")

st.divider()

# Network selector (if multiple networks available)
available_networks = get_network_display_names()
if len(available_networks) > 1:
    # Sort networks: AppLovin first, Unity second, then others
    network_items = list(available_networks.items())
    applovin_item = None
    unity_item = None
    other_items = []
    for key, display in network_items:
        if key == "applovin":
            applovin_item = (key, display)
        elif key == "unity":
            unity_item = (key, display)
        else:
            other_items.append((key, display))
    
    # Reorder: AppLovin first, Unity second, then others
    sorted_items = []
    if applovin_item:
        sorted_items.append(applovin_item)
    if unity_item:
        sorted_items.append(unity_item)
    sorted_items.extend(other_items)
    
    if not sorted_items:
        sorted_items = network_items
    
    # Create sorted dict and list of display names
    sorted_networks = dict(sorted_items)
    sorted_display_names = list(sorted_networks.values())
    
    selected_display = st.selectbox(
        "Select Network",
        options=sorted_display_names,
        index=sorted_display_names.index(network_display) if network_display in sorted_display_names else 0
    )
    
    # Find network key from sorted networks
    for key, display in sorted_networks.items():
        if display == selected_display:
            if key != current_network:
                SessionManager.switch_network(key)
                st.rerun()
            break

st.divider()

# ============================================================================
# CREATE APP SECTION
# ============================================================================
render_create_app_ui(current_network, network_display, config)

# ============================================================================
# UNITY UPDATE AD-UNITS SECTION (Before Create Unit)
# ============================================================================
render_unity_update_ad_units(current_network)

# ============================================================================
# VUNGLE DEACTIVATE PLACEMENTS SECTION (Before Create Unit)
# ============================================================================
if current_network == "vungle":
    from components.vungle_deactivate_placements import render_vungle_deactivate_placements
    render_vungle_deactivate_placements(current_network)

# ============================================================================
# IRONSOURCE DEACTIVATE AD-UNITS SECTION (Before Create Unit)
# ============================================================================
if current_network == "ironsource":
    from components.ironsource_deactivate_ad_units import render_ironsource_deactivate_ad_units
    render_ironsource_deactivate_ad_units(current_network)

# ============================================================================
# CREATE UNIT / CREATE AD UNIT SECTION
# ============================================================================
st.divider()

# For IronSource, show "Create Ad Unit" (minimize space like GET Instance)
if current_network == "ironsource":
    st.subheader("🎯 Create Ad Unit")
    # Minimize space between subheader and buttons (like GET Instance)
    st.markdown("""
    <style>
    div[data-testid='stVerticalBlock']:has(> div[data-testid='stButton']) {
        margin-top: -1rem !important;
    }
    div[data-testid='stVerticalBlock']:has(> div[data-testid='stSelectbox']) {
        margin-top: -1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.subheader("🎯 Create Unit")

# Check if network supports unit creation
if not config.supports_create_unit():
    st.warning(f"⚠️ {network_display} does not support unit creation via API")
    st.info("Please create units manually in the network's dashboard")
elif current_network == "applovin":
    render_applovin_create_unit_ui()
elif current_network == "unity":
    render_unity_create_unit_ui(current_network)
elif current_network == "ironsource":
    # For IronSource, skip App Code selector and go directly to Create Ad Unit UI
    network_manager = get_network_manager()
    render_create_unit_common_ui(
        current_network=current_network,
        selected_app_code="",  # Not used for IronSource
        app_name="",
        app_info_to_use=None,
        apps=[],
        app_info_map={},
        network_manager=network_manager,
        config=config
    )
else:
    network_manager = get_network_manager()
    
    # Render App Code selector
    selected_app_code, app_name, app_info_to_use, apps, app_info_map = render_app_code_selector(current_network, network_manager)
    
    # Show UI for slot creation (always show, but require app code selection)
    if selected_app_code:
        st.info(f"**Selected app:** {app_name} ({selected_app_code})")
    else:
        # Show message if no app code selected (only for non-Unity networks)
        if current_network != "unity":
            st.info("💡 Please select an App Code above to create units.")
        app_info_to_use = None
    
    # Create Unit UI (always show, but require app code selection)
    # Show Create Unit UI even if app code is not selected (will show message)
    render_create_unit_common_ui(
        current_network=current_network,
        selected_app_code=selected_app_code,
        app_name=app_name,
        app_info_to_use=app_info_to_use,
        apps=apps,
        app_info_map=app_info_map,
        network_manager=network_manager,
        config=config
    )

# ============================================================================
# IRONSOURCE GET INSTANCES SECTION (After Create Unit)
# ============================================================================
if current_network == "ironsource":
    from components.ironsource_get_instances import render_ironsource_get_instances
    render_ironsource_get_instances(current_network)

# Help section
with st.expander("ℹ️ Help"):
    st.markdown("""
    ### Creating an App
    
    1. **App Name**: Enter a descriptive name for your app
    2. **Package Name**: Android package name (e.g., com.example.app)
    3. **Platform**: Select Android or iOS
    4. **Store URL**: Optional link to app store listing
    5. **Media Type**: Application or Site
    6. **Category**: Select the appropriate app category
    7. **Mediation Platform**: Select one or more mediation platforms
    8. **COPPA**: Indicate if your app targets children
    9. **Orientation**: Vertical or Horizontal screen orientation
    
    **Note**: For iOS apps, iTunes ID is required.
    
    ### Creating a Slot/Unit
    
    1. **App Code**: Select the app for this slot
    2. **Slot Name**: Enter a descriptive name
    3. **Ad Type**: Select the ad format (Native, Banner, Interstitial, etc.)
    4. **Auction Type**: Choose Waterfall, Client Bidding, or Server Bidding
    
    ### Conditional Fields
    
    Fields will appear based on your selections:
    
    - **Waterfall**: Reserve Price
    - **Native/Interstitial/Reward/PopUp**: Music Switch
    - **Native**: Creative Type, Video Auto Replay
    - **Banner**: Auto Refresh, Refresh Seconds, Banner Size
    - **Splash**: Full Screen, Show Duration, Turn Off, Show Count Max, Interactive
    
    All required fields are marked with *.
    """)
