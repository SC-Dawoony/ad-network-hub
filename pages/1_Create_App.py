"""Create App/Media and Unit page"""
import streamlit as st
import logging
from utils.auth import AuthManager
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
from utils.app_store_helper import get_ios_app_details, get_android_app_details, PLAY_STORE_AVAILABLE

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

# Auth check
if not AuthManager.is_authenticated():
    st.switch_page("pages/0_Login.py")

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
        elif key == "admob":
            # Skip AdMob - temporarily disabled
            continue
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
# STORE URL INPUT AND APP INFO FETCH SECTION
# ============================================================================
# Initialize session state for store info
if "store_info_ios" not in st.session_state:
    st.session_state.store_info_ios = None
if "store_info_android" not in st.session_state:
    st.session_state.store_info_android = None
if "app_match_identifier" not in st.session_state:
    st.session_state.app_match_identifier = None

# Step 1: Store URL Input
st.markdown("### 1️⃣ Store URL 입력")
col_android, col_ios = st.columns(2)

with col_android:
    android_url = st.text_input(
        "🤖 Google Play Store URL",
        placeholder="https://play.google.com/store/apps/details?id=...",
        key="new_android_url",
        help="Android 앱의 Google Play Store URL을 입력하세요",
        disabled=not PLAY_STORE_AVAILABLE
    )
    if not PLAY_STORE_AVAILABLE:
        st.caption("⚠️ google-play-scraper 라이브러리가 설치되지 않았습니다. 'pip install google-play-scraper'로 설치해주세요.")

with col_ios:
    ios_url = st.text_input(
        "🍎 App Store URL",
        placeholder="https://apps.apple.com/us/app/...",
        key="new_ios_url",
        help="iOS 앱의 App Store URL을 입력하세요"
    )

# Fetch button
fetch_info_button = st.button("🔍 앱 정보 조회", type="primary", use_container_width=True)

# Fetch app store info
if fetch_info_button:
    ios_info = None
    android_info = None
    
    if ios_url:
        with st.spinner("iOS 앱 정보를 가져오는 중..."):
            try:
                ios_info = get_ios_app_details(ios_url)
                if ios_info:
                    st.session_state.store_info_ios = ios_info
                    st.success(f"✅ iOS 앱 정보 조회 성공: {ios_info.get('name', 'N/A')}")
                else:
                    st.error("❌ iOS 앱 정보를 찾을 수 없습니다.")
            except Exception as e:
                st.error(f"❌ iOS 앱 정보 조회 실패: {str(e)}")
    
    if android_url:
        with st.spinner("Android 앱 정보를 가져오는 중..."):
            try:
                android_info = get_android_app_details(android_url)
                if android_info:
                    st.session_state.store_info_android = android_info
                    st.success(f"✅ Android 앱 정보 조회 성공: {android_info.get('name', 'N/A')}")
                else:
                    st.error("❌ Android 앱 정보를 찾을 수 없습니다.")
            except Exception as e:
                st.error(f"❌ Android 앱 정보 조회 실패: {str(e)}")
    
    if not ios_url and not android_url:
        st.warning("⚠️ 최소 하나의 Store URL을 입력해주세요.")

# Display fetched info
if st.session_state.store_info_ios or st.session_state.store_info_android:
    st.markdown("### 📋 조회된 앱 정보")
    
    info_cols = st.columns(2)
    
    with info_cols[0]:
        if st.session_state.store_info_android:
            info = st.session_state.store_info_android
            st.markdown("**🤖 Android**")
            st.write(f"**이름:** {info.get('name', 'N/A')}")
            st.write(f"**Package Name:** `{info.get('package_name', 'N/A')}`")
            st.write(f"**개발자:** {info.get('developer', 'N/A')}")
            st.write(f"**카테고리:** {info.get('category', 'N/A')}")
            if info.get('icon_url'):
                st.image(info.get('icon_url'), width=100)
    
    with info_cols[1]:
        if st.session_state.store_info_ios:
            info = st.session_state.store_info_ios
            st.markdown("**🍎 iOS**")
            st.write(f"**이름:** {info.get('name', 'N/A')}")
            st.write(f"**Bundle ID:** `{info.get('bundle_id', 'N/A')}`")
            st.write(f"**App ID:** {info.get('app_id', 'N/A')}")
            st.write(f"**개발자:** {info.get('developer', 'N/A')}")
            st.write(f"**카테고리:** {info.get('category', 'N/A')}")
            if info.get('icon_url'):
                st.image(info.get('icon_url'), width=100)

# App match name selection (if Android and iOS have different identifiers)
android_package = None
ios_bundle_id = None

if st.session_state.store_info_android:
    android_package = st.session_state.store_info_android.get('package_name', '')
if st.session_state.store_info_ios:
    ios_bundle_id = st.session_state.store_info_ios.get('bundle_id', '')

# Show App match name selection if both exist and are different
if android_package and ios_bundle_id and android_package != ios_bundle_id:
    st.divider()
    st.markdown("### 🔀 App Match Name 선택")
    
    # Initialize selection in session state if not exists
    if st.session_state.app_match_identifier is None:
        # Default: use Android Package Name (last part), convert to lowercase
        android_package_last = android_package.split('.')[-1] if '.' in android_package else android_package
        st.session_state.app_match_identifier = {
            "source": "android_package",
            "value": android_package_last.lower()
        }
        # Also update SessionManager's app_match_name
        SessionManager.set_app_match_name(android_package_last.lower())
    
    # Show current selection status
    selected_value = st.session_state.app_match_identifier.get("value", "")
    if selected_value:
        st.info(f"**선택된 값:** `{selected_value}` (이 값이 Android와 iOS Ad Unit 이름 생성에 사용됩니다)")
    
    # Define dialog function
    @st.dialog("🔀 App Match Name 선택")
    def identifier_selection_dialog():
        st.markdown("### 🔀 App Match Name")
        st.info("💡 Android Package Name과 iOS Bundle ID가 다릅니다. Ad Unit 이름 생성 시 어떤 값을 사용할지 선택하거나 직접 입력하세요.")
        
        # Extract last part of Android Package Name and iOS Bundle ID
        android_package_last = android_package.split('.')[-1] if '.' in android_package else android_package
        ios_bundle_id_last = ios_bundle_id.split('.')[-1] if '.' in ios_bundle_id else ios_bundle_id
        
        # Selection options (display original case, but store lowercase)
        selection_options = [
            f"Android Package Name: `{android_package_last}`",
            f"iOS Bundle ID: `{ios_bundle_id_last}`",
            "직접 입력"
        ]
        
        # Get current selection
        current_selection = st.session_state.app_match_identifier.get("source", "android_package")
        if current_selection == "android_package":
            current_index = 0
        elif current_selection == "ios_bundle_id":
            current_index = 1
        else:
            current_index = 2
        
        selected_option = st.radio(
            "선택하세요:",
            options=selection_options,
            index=current_index,
            key="app_match_identifier_radio_dialog"
        )
        
        # Update session state based on selection (convert to lowercase)
        if selected_option.startswith("Android Package Name"):
            selected_value = android_package_last.lower()
            st.session_state.app_match_identifier = {
                "source": "android_package",
                "value": selected_value
            }
            SessionManager.set_app_match_name(selected_value)
        elif selected_option.startswith("iOS Bundle ID"):
            selected_value = ios_bundle_id_last.lower()
            st.session_state.app_match_identifier = {
                "source": "ios_bundle_id",
                "value": selected_value
            }
            SessionManager.set_app_match_name(selected_value)
        else:  # 직접 입력
            custom_value = st.text_input(
                "직접 입력:",
                value=st.session_state.app_match_identifier.get("value", ""),
                key="app_match_identifier_custom_dialog",
                help="Ad Unit 이름 생성에 사용할 식별자를 직접 입력하세요 (소문자로 저장됩니다)"
            )
            if custom_value:
                selected_value = custom_value.lower()
                st.session_state.app_match_identifier = {
                    "source": "custom",
                    "value": selected_value
                }
                SessionManager.set_app_match_name(selected_value)
        
        # Show preview
        selected_value = st.session_state.app_match_identifier.get("value", "")
        if selected_value:
            st.success(f"✅ 선택된 값: `{selected_value}` (이 값이 Android와 iOS Ad Unit 이름 생성에 사용됩니다)")
        
        # Close dialog buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 확인", key="confirm_identifier_dialog", use_container_width=True, type="primary"):
                st.rerun()
        with col2:
            if st.button("❌ 취소", key="cancel_identifier_dialog", use_container_width=True):
                st.rerun()
    
    # Button to open dialog
    if st.button("🔀 App Match Name 선택", key="open_identifier_dialog", use_container_width=True):
        identifier_selection_dialog()
elif android_package or ios_bundle_id:
    # If only one platform or both are the same, auto-set app_match_name
    if android_package:
        android_package_last = android_package.split('.')[-1] if '.' in android_package else android_package
        SessionManager.set_app_match_name(android_package_last.lower())
    elif ios_bundle_id:
        ios_bundle_id_last = ios_bundle_id.split('.')[-1] if '.' in ios_bundle_id else ios_bundle_id
        SessionManager.set_app_match_name(ios_bundle_id_last.lower())

# App Match Name input for ad unit name generation (manual override)
st.divider()
app_match_name_input = st.text_input(
    "App Match Name (Optional)",
    value=SessionManager.get_app_match_name(),
    placeholder="e.g., mygame, myapp",
    help="Enter a custom name to use instead of Android package name for ad unit name generation. "
         "Example: If you enter 'mygame', ad unit names will be like 'mygame_aos_bigoads_rv_bidding' instead of using package name."
)

# Save to session if changed
if app_match_name_input != SessionManager.get_app_match_name():
    SessionManager.set_app_match_name(app_match_name_input)

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
