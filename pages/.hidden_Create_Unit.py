"""Create Unit/Slot page"""
import streamlit as st
from utils.session_manager import SessionManager
from utils.ui_components import DynamicFormRenderer
from utils.network_manager import get_network_manager, handle_api_response
from utils.validators import validate_slot_name
from network_configs import get_network_config, get_network_display_names


def _generate_slot_name(pkg_name: str, platform_str: str, slot_type: str) -> str:
    """Generate slot name: pkgName_last_part_platform_bigoads_type_bidding
    
    If app_match_name is set in session, use it instead of pkg_name.
    """
    # Check if app_match_name is set in session
    app_match_name = SessionManager.get_app_match_name()
    if app_match_name and app_match_name.strip():
        last_part = app_match_name.strip().lower()
    else:
        # Get last part after "."
        if "." in pkg_name:
            last_part = pkg_name.split(".")[-1]
        else:
            last_part = pkg_name
    
    return f"{last_part}_{platform_str}_bigoads_{slot_type}_bidding"


def _create_default_slot(network: str, app_info: dict, slot_type: str, network_manager, config):
    """Create a default slot with predefined settings"""
    app_code = app_info.get("appCode")
    pkg_name = app_info.get("pkgName", "")
    platform_str = app_info.get("platformStr", "android")
    
    # Generate slot name
    slot_name = _generate_slot_name(pkg_name, platform_str, slot_type)
    
    # Build payload based on slot type
    payload = {
        "appCode": app_code,
        "name": slot_name,
    }
    
    # Build base payload
    payload = {
        "appCode": app_code,
        "name": slot_name,
    }
    
    if slot_type == "rv":
        # Reward Video: adType = 4, auctionType = 3, musicSwitch = 1
        payload.update({
            "adType": 4,
            "auctionType": 3,
            "musicSwitch": 1
        })
    elif slot_type == "is":
        # Interstitial: adType = 3, auctionType = 3, musicSwitch = 1
        payload.update({
            "adType": 3,
            "auctionType": 3,
            "musicSwitch": 1
        })
    elif slot_type == "bn":
        # Banner: adType = 2, auctionType = 3, bannerAutoRefresh = 2, bannerSize = 2
        # Note: Using values as specified by user (2 for both)
        payload.update({
            "adType": 2,
            "auctionType": 3,
            "autoRefresh": 2,  # As specified: bannerAutoRefresh = 2
            "bannerSize": 2   # As specified: bannerSize = 2
        })
    
    # Make API call
    with st.spinner(f"Creating {slot_type.upper()} slot..."):
        try:
            response = network_manager.create_unit(network, payload)
            result = handle_api_response(response)
            
            if result:
                SessionManager.add_created_unit(network, {
                    "slotCode": result.get("slotCode", "N/A"),
                    "name": slot_name,
                    "appCode": app_code,
                    "slotType": slot_type
                })
                st.success(f"✅ {slot_type.upper()} slot created successfully!")
        except Exception as e:
            st.error(f"❌ Error creating {slot_type.upper()} slot: {str(e)}")
            SessionManager.log_error(network, str(e))


def _create_all_default_slots(network: str, app_info: dict, network_manager, config):
    """Create all 3 default slots (RV, IS, BN)"""
    slot_types = ["rv", "is", "bn"]
    results = []
    
    for slot_type in slot_types:
        try:
            _create_default_slot(network, app_info, slot_type, network_manager, config)
            results.append(f"✅ {slot_type.upper()}")
        except Exception as e:
            results.append(f"❌ {slot_type.upper()}: {str(e)}")
    
    st.success("🎉 Finished creating all 3 slots!")
    st.balloons()

# Page configuration
st.set_page_config(
    page_title="Create Unit",
    page_icon="🎯",
    layout="wide"
)
# Note: This page can also be accessed from the "Create App & Unit" page

# Initialize session
SessionManager.initialize()

# Auth guard
from utils.auth import require_auth
require_auth()

# Get current network
current_network = SessionManager.get_current_network()
config = get_network_config(current_network)
display_names = get_network_display_names()
network_display = display_names.get(current_network, current_network.title())

st.title("🎯 Create New Slot")
st.markdown(f"**Network:** {network_display}")

# Check if network supports unit creation
if not config.supports_create_unit():
    st.warning(f"⚠️ {network_display} does not support unit creation via API")
    st.info("Please create units manually in the network's dashboard")
    st.stop()

network_manager = get_network_manager()

# Load apps for dropdown
with st.spinner("Loading apps..."):
    apps = SessionManager.get_cached_apps(current_network)
    
    if not apps:
        # Try to fetch from API
        try:
            apps = network_manager.get_apps(current_network)
            SessionManager.cache_apps(current_network, apps)
        except Exception as e:
            st.error(f"❌ Failed to load apps: {str(e)}")
            st.info("Please go to 'View Lists' page first to load apps")
            st.stop()

if not apps:
    st.warning("No apps found. Please create an app first.")
    st.stop()

# Prepare app options for dropdown
app_options = []
app_code_map = {}
app_info_map = {}  # Store full app info for Quick Create
for app in apps:
    app_code = app.get("appCode", "N/A")
    app_name = app.get("name", "Unknown")
    platform = app.get("platform", "")
    display_text = f"{app_code} ({app_name})"
    if platform:
        display_text += f" - {platform}"
    app_options.append(display_text)
    app_code_map[display_text] = app_code
    # Store app info for Quick Create
    app_info_map[app_code] = {
        "appCode": app_code,
        "name": app_name,
        "platform": platform,
        "pkgName": "",  # Not available from cache, will need to be provided
        "platform": 1 if platform == "Android" else 2,
        "platformStr": "android" if platform == "Android" else "ios"
    }

# Get last created app code and info
last_created_app_code = SessionManager.get_last_created_app_code(current_network)
last_app_info = SessionManager.get_last_created_app_info(current_network)

# Find default selection index
default_index = 0
if last_created_app_code:
    # Try to find the last created app in the list
    for idx, app in enumerate(apps):
        if app.get("appCode") == last_created_app_code:
            default_index = idx
            break

# Custom slot creation with RV, IS, BN boxes
st.subheader("📝 Create Slot")

# App selection (single selection for all slots)
app_label = "Site ID*" if current_network == "pangle" else "App Code*"
selected_app_display = st.selectbox(
    app_label,
    options=app_options,
    index=default_index,
    help="Select the app for the slots. Recently created apps are pre-selected." if current_network != "pangle" else "Select the site for the ad placements. Recently created sites are pre-selected.",
    key="slot_app_select"
)
selected_app_code = app_code_map.get(selected_app_display, "")
    
if selected_app_code:
    # Get app name from display text
    app_name = "Unknown"
    if "(" in selected_app_display and ")" in selected_app_display:
        app_name = selected_app_display.split("(")[1].split(")")[0]
    st.info(f"**Selected app:** {app_name} ({selected_app_code})")
    
    # IronSource uses RV, IS, BN boxes (same structure as BigOAds but with different fields)
    if current_network == "ironsource":
        # IronSource will use the RV, IS, BN boxes below
        pass
    else:
        # BigOAds and other networks use the existing UI
        # Get app info for quick create all
        app_info_to_use = None
        if last_app_info and last_app_info.get("appCode") == selected_app_code:
            app_info_to_use = last_app_info
        elif selected_app_code in app_info_map:
            app_info_to_use = app_info_map[selected_app_code]
            if last_app_info and last_app_info.get("appCode") == selected_app_code:
                app_info_to_use["pkgName"] = last_app_info.get("pkgName", "")
        
        # Create All 3 Slots button at the top
        # if app_info_to_use and current_network == "bigoads":
        #     if st.button("✨ Create All 3 Slots (RV + IS + BN)", use_container_width=True, type="primary"):
        #         with st.spinner("Creating all 3 slots..."):
        #             results = []
        #             for slot_type in ["rv", "is", "bn"]:
        #                 try:
        #                     _create_default_slot(current_network, app_info_to_use, slot_type, network_manager, config)
        #                     results.append({"type": slot_type.upper(), "status": "success"})
        #                 except Exception as e:
        #                     results.append({"type": slot_type.upper(), "status": "error", "error": str(e)})
                    
        #             # Show results
        #             st.success("🎉 Finished creating slots!")
        #             st.balloons()
                    
        #             # Display created slots
        #             st.subheader("📋 Created Slots")
        #             for result in results:
        #                 if result["status"] == "success":
        #                     st.success(f"✅ {result['type']} slot created successfully")
        #                 else:
        #                     st.error(f"❌ {result['type']} slot failed: {result.get('error', 'Unknown error')}")
                    
        #             st.rerun()
    
    st.divider()
    
# Value mappings for display
AD_TYPE_MAP = {
    1: "Native",
    2: "Banner",
    3: "Interstitial",
    4: "Reward Video",
    12: "Splash Ad",
    20: "Pop Up"
}

AUCTION_TYPE_MAP = {
    1: "Waterfall",
    2: "Client Bidding",
    3: "Server Bidding"
}

MUSIC_SWITCH_MAP = {
    1: "Sound On",
    2: "Sound Off"
}

AUTO_REFRESH_MAP = {
    1: "Yes",
    2: "No"
}

BANNER_SIZE_MAP = {
    1: "300x250",
    2: "320x50"
}

# Reverse maps for getting values from display
AD_TYPE_REVERSE = {v: k for k, v in AD_TYPE_MAP.items()}
AUCTION_TYPE_REVERSE = {v: k for k, v in AUCTION_TYPE_MAP.items()}
MUSIC_SWITCH_REVERSE = {v: k for k, v in MUSIC_SWITCH_MAP.items()}
AUTO_REFRESH_REVERSE = {v: k for k, v in AUTO_REFRESH_MAP.items()}
BANNER_SIZE_REVERSE = {v: k for k, v in BANNER_SIZE_MAP.items()}

# Default slot configurations for BigOAds
slot_configs_bigoads = {
    "RV": {
        "name": "Reward Video",
        "adType": 4,
        "auctionType": 3,
        "musicSwitch": 1,
    },
    "IS": {
        "name": "Interstitial",
        "adType": 3,
        "auctionType": 3,
        "musicSwitch": 1,
    },
    "BN": {
        "name": "Banner",
        "adType": 2,
        "auctionType": 3,
        "autoRefresh": 2,
        "bannerSize": 2,
    }
}

# Default slot configurations for IronSource
slot_configs_ironsource = {
    "RV": {
        "name": "Reward Video",
        "adFormat": "rewarded",
    },
    "IS": {
        "name": "Interstitial",
        "adFormat": "interstitial",
    },
    "BN": {
        "name": "Banner",
        "adFormat": "banner",
    }
}

# Default slot configurations for Pangle
slot_configs_pangle = {
    "RV": {
        "name": "Rewarded Video",
        "ad_slot_type": 5,
        "render_type": 1,
        "orientation": 1,
        "reward_is_callback": 0,
        "reward_name": "Reward",
        "reward_count": 1,
    },
    "IS": {
        "name": "Interstitial",
        "ad_slot_type": 6,
        "render_type": 1,
        "orientation": 1,
    },
    "BN": {
        "name": "Banner",
        "ad_slot_type": 2,
        "render_type": 1,
        "slide_banner": 1,
        "width": 640,
        "height": 100,
    }
}

# Select configs based on network
if current_network == "ironsource":
    slot_configs = slot_configs_ironsource
elif current_network == "pangle":
    slot_configs = slot_configs_pangle
else:
    slot_configs = slot_configs_bigoads

# Create 3 columns for RV, IS, BN
col1, col2, col3 = st.columns(3)

for idx, (slot_key, slot_config) in enumerate(slot_configs.items()):
    with [col1, col2, col3][idx]:
        with st.container():
            st.markdown(f"### 🎯 {slot_key} ({slot_config['name']})")
            
            if current_network == "ironsource":
                # IronSource: mediationAdUnitName and adFormat only
                slot_name_key = f"ironsource_slot_{slot_key}_name"
                if slot_name_key not in st.session_state:
                    default_name = f"{slot_key.lower()}-1"
                    st.session_state[slot_name_key] = default_name
                
                mediation_ad_unit_name = st.text_input(
                    "Mediation Ad Unit Name*",
                    value=st.session_state[slot_name_key],
                    key=slot_name_key,
                    help=f"Name for {slot_config['name']} placement"
                )
                
                # Display current settings (adFormat is fixed)
                st.markdown("**Current Settings:**")
                settings_html = '<div style="min-height: 120px; margin-bottom: 10px;">'
                settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
                settings_html += f'<li>Ad Format: {slot_config["adFormat"].title()}</li>'
                settings_html += '</ul></div>'
                st.markdown(settings_html, unsafe_allow_html=True)
                
                # Create button for IronSource
                if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_ironsource_{slot_key}"):
                    if not mediation_ad_unit_name:
                        st.toast("❌ Mediation Ad Unit Name is required", icon="🚫")
                    else:
                        # Build payload for IronSource
                        payload = {
                            "mediationAdUnitName": mediation_ad_unit_name,
                            "adFormat": slot_config['adFormat'],
                        }
                
                        # Make API call
                        with st.spinner(f"Creating {slot_key} placement..."):
                            try:
                                response = network_manager.create_unit(current_network, payload, app_key=selected_app_code)
                                result = handle_api_response(response)
                    
                                if result:
                                    SessionManager.add_created_unit(current_network, {
                                        "slotCode": result.get("adUnitId", "N/A"),
                                        "name": mediation_ad_unit_name,
                                        "appCode": selected_app_code,
                                        "slotType": slot_config['adFormat']
                                    })
                                    st.success(f"✅ {slot_key} placement created successfully!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                                SessionManager.log_error(current_network, str(e))
            elif current_network == "pangle":
                # Pangle: site_id, ad_slot_type, and type-specific fields
                slot_name_key = f"pangle_slot_{slot_key}_name"
                if slot_name_key not in st.session_state:
                    default_name = f"slot_{slot_key.lower()}"
                    st.session_state[slot_name_key] = default_name
                
                slot_name = st.text_input(
                    "Slot Name*",
                    value=st.session_state[slot_name_key],
                    key=slot_name_key,
                    help=f"Name for {slot_config['name']} ad placement"
                )
                
                # Show version info for Pangle
                st.info(f"**API Version:** 1.0 (auto-generated)")
                
                # Display current settings
                st.markdown("**Current Settings:**")
                # RV 섹션이 가장 많은 항목(6개)을 가지므로, 모든 섹션의 높이를 RV에 맞춤
                # RV: Ad Slot Type, Render Type, Orientation, Reward Name, Reward Count, Reward Callback (6개)
                # IS: Ad Slot Type, Render Type, Orientation (3개)
                # BN: Ad Slot Type, Render Type, Slide Banner, Size (4개)
                settings_html = '<div style="min-height: 180px; margin-bottom: 10px;">'
                settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
                settings_html += f'<li>Ad Slot Type: {slot_config["name"]}</li>'
                settings_html += f'<li>Render Type: Template Render</li>'
                
                if slot_key == "BN":
                    slide_banner_text = "No" if slot_config["slide_banner"] == 1 else "Yes"
                    settings_html += f'<li>Slide Banner: {slide_banner_text}</li>'
                    settings_html += f'<li>Size: {slot_config["width"]}x{slot_config["height"]}px</li>'
                    # BN은 4개 항목이므로 빈 줄 2개 추가하여 RV(6개)와 높이 맞춤
                    settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
                    settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
                elif slot_key == "RV":
                    orientation_text = "Vertical" if slot_config["orientation"] == 1 else "Horizontal"
                    reward_callback_text = "No Server Callback" if slot_config["reward_is_callback"] == 0 else "Server Callback"
                    settings_html += f'<li>Orientation: {orientation_text}</li>'
                    settings_html += f'<li>Reward Name: {slot_config.get("reward_name", "Reward")}</li>'
                    settings_html += f'<li>Reward Count: {slot_config.get("reward_count", 1)}</li>'
                    settings_html += f'<li>Reward Callback: {reward_callback_text}</li>'
                elif slot_key == "IS":
                    orientation_text = "Vertical" if slot_config["orientation"] == 1 else "Horizontal"
                    settings_html += f'<li>Orientation: {orientation_text}</li>'
                    # IS는 3개 항목이므로 빈 줄 3개 추가하여 RV(6개)와 높이 맞춤
                    settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
                    settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
                    settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
                
                settings_html += '</ul></div>'
                st.markdown(settings_html, unsafe_allow_html=True)
                
                # Editable settings for Pangle
                with st.expander("⚙️ Edit Settings"):
                    if slot_key == "BN":
                        # Banner specific settings
                        slide_banner = st.selectbox(
                            "Slide Banner",
                            options=[("No", 1), ("Yes", 2)],
                            index=0 if slot_config["slide_banner"] == 1 else 1,
                            key=f"{slot_key}_slide_banner",
                            format_func=lambda x: x[0]
                        )
                        slot_config["slide_banner"] = slide_banner[1]
                        
                        banner_size = st.selectbox(
                            "Banner Size",
                            options=[("640x100 (320*50)", (640, 100)), ("600x500 (300*250)", (600, 500))],
                            index=0 if (slot_config["width"], slot_config["height"]) == (640, 100) else 1,
                            key=f"{slot_key}_banner_size",
                            format_func=lambda x: x[0]
                        )
                        slot_config["width"] = banner_size[1][0]
                        slot_config["height"] = banner_size[1][1]
                    elif slot_key == "RV":
                        # Rewarded Video specific settings
                        orientation = st.selectbox(
                            "Orientation",
                            options=[("Vertical", 1), ("Horizontal", 2)],
                            index=0 if slot_config["orientation"] == 1 else 1,
                            key=f"{slot_key}_orientation",
                            format_func=lambda x: x[0]
                        )
                        slot_config["orientation"] = orientation[1]
                        
                        reward_name = st.text_input(
                            "Reward Name*",
                            value=st.session_state.get(f"{slot_key}_reward_name", slot_config.get("reward_name", "Reward")),
                            key=f"{slot_key}_reward_name",
                            help="Reward name (1-60 characters)"
                        )
                        slot_config["reward_name"] = reward_name
                        
                        reward_count = st.number_input(
                            "Reward Count*",
                            min_value=0,
                            max_value=9007199254740991,
                            value=st.session_state.get(f"{slot_key}_reward_count", slot_config.get("reward_count", 1)),
                            key=f"{slot_key}_reward_count"
                        )
                        slot_config["reward_count"] = reward_count
                        
                        reward_is_callback = st.selectbox(
                            "Reward Callback",
                            options=[("No Server Callback", 0), ("Server Callback", 1)],
                            index=0 if slot_config["reward_is_callback"] == 0 else 1,
                            key=f"{slot_key}_reward_is_callback",
                            format_func=lambda x: x[0]
                        )
                        slot_config["reward_is_callback"] = reward_is_callback[1]
                        
                        if reward_is_callback[1] == 1:
                            reward_callback_url = st.text_input(
                                "Reward Callback URL*",
                                value=st.session_state.get(f"{slot_key}_reward_callback_url", ""),
                                key=f"{slot_key}_reward_callback_url",
                                help="Required when server callback is enabled"
                            )
                            slot_config["reward_callback_url"] = reward_callback_url
                    elif slot_key == "IS":
                        # Interstitial specific settings
                        orientation = st.selectbox(
                            "Orientation",
                            options=[("Vertical", 1), ("Horizontal", 2)],
                            index=0 if slot_config["orientation"] == 1 else 1,
                            key=f"{slot_key}_orientation",
                            format_func=lambda x: x[0]
                        )
                        slot_config["orientation"] = orientation[1]
                
                # Create button for Pangle
                if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_pangle_{slot_key}"):
                    if not slot_name:
                        st.toast("❌ Slot Name is required", icon="🚫")
                    elif slot_key == "RV" and (not slot_config.get("reward_name") or slot_config.get("reward_count") is None):
                        st.toast("❌ Reward Name and Reward Count are required for Rewarded Video", icon="🚫")
                    else:
                        # Build payload for Pangle
                        payload = {
                            "site_id": selected_app_code,  # site_id from selected app
                            "ad_placement_type": slot_config["ad_slot_type"],
                            "bidding_type": 1,  # Default: 1
                        }
                        
                        # Add type-specific fields
                        if slot_key == "BN":
                            payload.update({
                                "render_type": slot_config["render_type"],
                                "slide_banner": slot_config["slide_banner"],
                                "width": slot_config["width"],
                                "height": slot_config["height"],
                            })
                        elif slot_key == "RV":
                            payload.update({
                                "render_type": slot_config["render_type"],
                                "orientation": slot_config["orientation"],
                                "reward_name": slot_config.get("reward_name", ""),
                                "reward_count": slot_config.get("reward_count", 1),
                                "reward_is_callback": slot_config["reward_is_callback"],
                            })
                            if slot_config["reward_is_callback"] == 1 and slot_config.get("reward_callback_url"):
                                payload["reward_callback_url"] = slot_config["reward_callback_url"]
                        elif slot_key == "IS":
                            payload.update({
                                "render_type": slot_config["render_type"],
                                "orientation": slot_config["orientation"],
                            })
                        
                        # Make API call
                        with st.spinner(f"Creating {slot_key} placement..."):
                            try:
                                response = network_manager.create_unit(current_network, payload)
                                result = handle_api_response(response)
                                
                                if result:
                                    SessionManager.add_created_unit(current_network, {
                                        "slotCode": result.get("code_id", result.get("ad_unit_id", "N/A")),
                                        "name": slot_name,
                                        "appCode": selected_app_code,
                                        "slotType": slot_config["ad_slot_type"]
                                    })
                                    st.success(f"✅ {slot_key} placement created successfully!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                                SessionManager.log_error(current_network, str(e))
            else:
                # BigOAds and other networks
                # Slot name input
                slot_name_key = f"custom_slot_{slot_key}_name"
                if slot_name_key not in st.session_state:
                    # Generate default name
                    last_app_info = SessionManager.get_last_created_app_info(current_network)
                    if last_app_info and last_app_info.get("pkgName"):
                        pkg_name = last_app_info.get("pkgName", "")
                        platform_str = last_app_info.get("platformStr", "android")
                        if "." in pkg_name:
                            last_part = pkg_name.split(".")[-1]
                        else:
                            last_part = pkg_name
                        default_name = f"{last_part}_{platform_str}_bigoads_{slot_key.lower()}_bidding"
                    else:
                        default_name = f"slot_{slot_key.lower()}"
                    st.session_state[slot_name_key] = default_name
                
                slot_name = st.text_input(
                    "Slot Name*",
                    value=st.session_state[slot_name_key],
                    key=slot_name_key,
                    help=f"Name for {slot_config['name']} slot"
                )
                
                # Display current settings
                st.markdown("**Current Settings:**")
                
                # 고정 높이 div 시작
                settings_html = '<div style="min-height: 120px; margin-bottom: 10px;">'
                
                settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
                settings_html += f'<li>Ad Type: {AD_TYPE_MAP[slot_config["adType"]]}</li>'
                settings_html += f'<li>Auction Type: {AUCTION_TYPE_MAP[slot_config["auctionType"]]}</li>'
                
                if slot_key == "BN":
                    settings_html += f'<li>Auto Refresh: {AUTO_REFRESH_MAP[slot_config["autoRefresh"]]}</li>'
                    settings_html += f'<li>Banner Size: {BANNER_SIZE_MAP[slot_config["bannerSize"]]}</li>'
                else:
                    settings_html += f'<li>Music: {MUSIC_SWITCH_MAP[slot_config["musicSwitch"]]}</li>'
                
                settings_html += '</ul></div>'
                
                st.markdown(settings_html, unsafe_allow_html=True)
                
                # Editable settings
                with st.expander("⚙️ Edit Settings"):
                    # Ad Type (read-only, shown for info)
                    st.selectbox(
                        "Ad Type",
                        options=[AD_TYPE_MAP[slot_config['adType']]],
                        key=f"{slot_key}_adType_display",
                        disabled=True
                    )
                    
                    # Auction Type
                    auction_type_display = AUCTION_TYPE_MAP[slot_config['auctionType']]
                    new_auction_type = st.selectbox(
                        "Auction Type",
                        options=list(AUCTION_TYPE_MAP.values()),
                        index=list(AUCTION_TYPE_MAP.values()).index(auction_type_display),
                        key=f"{slot_key}_auctionType"
                    )
                    slot_config['auctionType'] = AUCTION_TYPE_REVERSE[new_auction_type]
                    
                    if slot_key == "BN":
                        # Banner specific settings
                        auto_refresh_display = AUTO_REFRESH_MAP[slot_config['autoRefresh']]
                        new_auto_refresh = st.selectbox(
                            "Auto Refresh",
                            options=list(AUTO_REFRESH_MAP.values()),
                            index=list(AUTO_REFRESH_MAP.values()).index(auto_refresh_display),
                            key=f"{slot_key}_autoRefresh"
                        )
                        slot_config['autoRefresh'] = AUTO_REFRESH_REVERSE[new_auto_refresh]
                        
                        banner_size_display = BANNER_SIZE_MAP[slot_config['bannerSize']]
                        new_banner_size = st.selectbox(
                            "Banner Size",
                            options=list(BANNER_SIZE_MAP.values()),
                            index=list(BANNER_SIZE_MAP.values()).index(banner_size_display),
                            key=f"{slot_key}_bannerSize"
                        )
                        slot_config['bannerSize'] = BANNER_SIZE_REVERSE[new_banner_size]
                    else:
                        # Music switch for RV and IS
                        music_display = MUSIC_SWITCH_MAP[slot_config['musicSwitch']]
                        new_music = st.selectbox(
                            "Music",
                            options=list(MUSIC_SWITCH_MAP.values()),
                            index=list(MUSIC_SWITCH_MAP.values()).index(music_display),
                            key=f"{slot_key}_musicSwitch"
                        )
                        slot_config['musicSwitch'] = MUSIC_SWITCH_REVERSE[new_music]
                
                # Create button
                if st.button(f"✅ Create {slot_key} Slot", use_container_width=True, key=f"create_{slot_key}"):
                    # Build payload with numeric values
                    payload = {
                        "appCode": selected_app_code,
                        "name": slot_name,
                        "adType": slot_config['adType'],
                        "auctionType": slot_config['auctionType'],
                    }
                    
                    if slot_key == "BN":
                        payload["autoRefresh"] = slot_config['autoRefresh']
                        payload["bannerSize"] = slot_config['bannerSize']  # Already numeric (1 or 2)
                    else:
                        payload["musicSwitch"] = slot_config['musicSwitch']
                    
                    # Make API call
                    with st.spinner(f"Creating {slot_key} slot..."):
                        try:
                            response = network_manager.create_unit(current_network, payload)
                            result = handle_api_response(response)
                        
                            if result:
                                SessionManager.add_created_unit(current_network, {
                                    "slotCode": result.get("slotCode", "N/A"),
                                    "name": slot_name,
                                    "appCode": selected_app_code,
                                    "slotType": slot_key
                                })
                                st.success(f"✅ {slot_key} slot created successfully!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error creating {slot_key} slot: {str(e)}")
                            SessionManager.log_error(current_network, str(e))

# Help section
with st.expander("ℹ️ Help"):
    st.markdown("""
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

