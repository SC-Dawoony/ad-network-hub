"""Create App/Media and Unit page"""
import streamlit as st
import logging
from utils.session_manager import SessionManager
from utils.ui_components import DynamicFormRenderer
from utils.network_manager import get_network_manager, handle_api_response
from utils.validators import validate_app_name, validate_package_name, validate_url, validate_slot_name
from network_configs import get_network_config, get_network_display_names

logger = logging.getLogger(__name__)


# Helper functions for Create Unit
def _extract_package_name_from_store_url(store_url: str) -> str:
    """Extract package name from Store URL (for IronSource)
    
    Android: https://play.google.com/store/apps/details?id=io.supercent.brawlmafia
    iOS: https://apps.apple.com/us/app/mob-hunters-idle-rpg/id6444113828
    
    Returns: last part after "." (e.g., "brawlmafia" or "id6444113828")
    """
    if not store_url:
        return ""
    
    # For Android: extract id= value
    if "play.google.com" in store_url and "id=" in store_url:
        try:
            id_part = store_url.split("id=")[1].split("&")[0].split("#")[0]
            # Get last part after "."
            if "." in id_part:
                return id_part.split(".")[-1]
            else:
                return id_part
        except:
            pass
    
    # For iOS: extract last part after "/"
    if "apps.apple.com" in store_url:
        try:
            last_part = store_url.rstrip("/").split("/")[-1]
            # If it starts with "id", use as is; otherwise get last part after "."
            if last_part.startswith("id"):
                return last_part
            elif "." in last_part:
                return last_part.split(".")[-1]
            else:
                return last_part
        except:
            pass
    
    # Fallback: try to get last part after "."
    if "." in store_url:
        return store_url.split(".")[-1].split("/")[0].split("?")[0]
    
    return store_url.split("/")[-1].split("?")[0] if "/" in store_url else store_url


def _generate_slot_name(pkg_name: str, platform_str: str, slot_type: str, network: str = "bigoads", store_url: str = None) -> str:
    """Generate slot name based on network
    
    BigOAds: {last_part}_{platform}_bigoads_{slot_type}_bidding
    IronSource: {last_part}_{os}_ironsource_{ad_type}_bidding (uses Store URL)
    """
    if network == "ironsource" and store_url:
        # IronSource: extract from Store URL
        last_part = _extract_package_name_from_store_url(store_url)
    else:
        # Get last part after "."
        if "." in pkg_name:
            last_part = pkg_name.split(".")[-1]
        else:
            last_part = pkg_name
    
    if network == "ironsource":
        # IronSource: os is "aos" for Android, "ios" for iOS
        # Handle None or empty platform_str
        if platform_str and isinstance(platform_str, str):
            platform_lower = platform_str.lower()
            os = "aos" if platform_lower in ["android", "aos"] else "ios"
        else:
            # Default to "aos" if platform_str is None or invalid
            os = "aos"
        
        # Map slot_type to ad_type
        ad_type_map = {
            "rv": "rewarded",
            "is": "interstitial",
            "bn": "banner"
        }
        ad_type = ad_type_map.get(slot_type.lower(), slot_type.lower())
        return f"{last_part}_{os}_ironsource_{ad_type}_bidding"
    else:
        # BigOAds format
        return f"{last_part}_{platform_str}_bigoads_{slot_type}_bidding"


def _create_default_slot(network: str, app_info: dict, slot_type: str, network_manager, config):
    """Create a default slot with predefined settings"""
    app_code = app_info.get("appCode")
    platform_str = app_info.get("platformStr", "android")
    
    # For BigOAds, use pkgNameDisplay from API response; otherwise use pkgName
    if network == "bigoads" and "pkgNameDisplay" in app_info:
        pkg_name = app_info.get("pkgNameDisplay", "")
    else:
        pkg_name = app_info.get("pkgName", "")
    
    # Generate slot name
    slot_name = _generate_slot_name(pkg_name, platform_str, slot_type, network)
    
    # Build payload based on slot type
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
        payload.update({
            "adType": 2,
            "auctionType": 3,
            "autoRefresh": 2,
            "bannerSize": 2
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
    st.warning(f"⚠️ {network_display} does not support app creation via API")
    st.info("Please create apps manually in the network's dashboard")
    st.stop()

st.info(f"✅ {network_display} - Create API Available")

st.divider()

# Network selector (if multiple networks available)
available_networks = get_network_display_names()
if len(available_networks) > 1:
    selected_display = st.selectbox(
        "Select Network",
        options=list(available_networks.values()),
        index=list(available_networks.values()).index(network_display) if network_display in available_networks.values() else 0
    )
    
    # Find network key
    for key, display in available_networks.items():
        if display == selected_display:
            if key != current_network:
                SessionManager.switch_network(key)
                st.rerun()
            break

st.divider()

# ============================================================================
# CREATE APP SECTION
# ============================================================================
st.subheader("📱 Create App")

# Render form
with st.form("create_app_form"):
    st.markdown("**App Information**")
    
    # For Pangle, pre-fill user_id and role_id from .env and show all required fields
    existing_data = {}
    if current_network == "pangle":
        import os
        from dotenv import load_dotenv
        # Force reload .env file to get latest values
        load_dotenv(override=True)
        user_id = os.getenv("PANGLE_USER_ID")
        role_id = os.getenv("PANGLE_ROLE_ID")
        if user_id:
            try:
                existing_data["user_id"] = int(user_id)
            except ValueError:
                pass
        if role_id:
            try:
                existing_data["role_id"] = int(role_id)
            except ValueError:
                pass
        
        # Show user_id and role_id as read-only
        if existing_data.get("user_id"):
            st.text_input("User ID* (from .env)", value=str(existing_data["user_id"]), disabled=True, help="Master account ID from .env file")
        if existing_data.get("role_id"):
            st.text_input("Role ID* (from .env)", value=str(existing_data["role_id"]), disabled=True, help="Sub account ID from .env file")
        
        # Show fixed values
        st.info("**Version:** 1.0 (fixed) | **Status:** 2 - Live (fixed)")
        
        # Show auto-generated fields info
        import time
        import random
        timestamp = int(time.time())
        nonce = random.randint(100000, 999999)
        st.info(f"**Auto-generated:** Timestamp={timestamp}, Nonce={nonce}, Sign (from security_key + timestamp + nonce)")
        st.divider()
    
    # Render form without sections for all networks
    form_data = DynamicFormRenderer.render_form(config, "app", existing_data=existing_data)
    
    # For Pangle, ensure user_id and role_id are in form_data (they're read-only but needed for API)
    if current_network == "pangle":
        if "user_id" in existing_data:
            form_data["user_id"] = existing_data["user_id"]
        if "role_id" in existing_data:
            form_data["role_id"] = existing_data["role_id"]
    
    # Form buttons
    col1, col2 = st.columns(2)
    with col1:
        reset_button = st.form_submit_button("🔄 Reset", use_container_width=True)
    with col2:
        submit_button = st.form_submit_button("✅ Create App", use_container_width=True)
    
    if reset_button:
        st.rerun()
    
    if submit_button:
        # Validate form data
        validation_passed = True
        error_messages = []
        
        # Debug: Log form_data to console (visible in terminal where streamlit is running)
        if current_network == "bigoads":
            import sys
            print(f"🔍 Debug - Full form_data keys: {list(form_data.keys())}", file=sys.stderr)
            print(f"🔍 Debug - platform value: {form_data.get('platform')}", file=sys.stderr)
            print(f"🔍 Debug - itunesId value: {repr(form_data.get('itunesId'))}", file=sys.stderr)
            print(f"🔍 Debug - platform type: {type(form_data.get('platform'))}", file=sys.stderr)
            print(f"🔍 Debug - itunesId type: {type(form_data.get('itunesId'))}", file=sys.stderr)
        
        # Common validations
        if "name" in form_data:
            valid, msg = validate_app_name(form_data["name"])
            if not valid:
                validation_passed = False
                error_messages.append(msg)
        
        if "pkgName" in form_data:
            valid, msg = validate_package_name(form_data["pkgName"])
            if not valid:
                validation_passed = False
                error_messages.append(msg)
        
        if "storeUrl" in form_data and form_data.get("storeUrl"):
            valid, msg = validate_url(form_data["storeUrl"])
            if not valid:
                validation_passed = False
                error_messages.append(msg)
        
        # Network-specific validation (includes itunesId validation for iOS)
        valid, msg = config.validate_app_data(form_data)
        # Debug: Log validation result to console (visible in terminal where streamlit is running)
        if current_network == "bigoads":
            import sys
            print(f"🔍 Debug - validation result: {valid}, message: {msg}", file=sys.stderr)
        if not valid:
            validation_passed = False
            error_messages.append(msg)
        
        if not validation_passed:
            # Show validation errors as toast notifications (pop-up style)
            for error in error_messages:
                st.toast(f"❌ {error}", icon="🚫")
        else:
            # Build payload
            try:
                payload = config.build_app_payload(form_data)
                
                # Show payload preview
                with st.expander("📋 Payload Preview"):
                    st.json(payload)
                
                # Make API call
                with st.spinner("Creating app..."):
                    network_manager = get_network_manager()
                    response = network_manager.create_app(current_network, payload)
                    
                    result = handle_api_response(response)
                    
                    if result:
                        # Extract app code from actual API response based on network
                        # result is already the normalized response from network_manager
                        app_code = None
                        app_id = None
                        
                        if current_network == "ironsource":
                            # IronSource: result contains appKey directly
                            app_code = result.get("appKey")
                        elif current_network == "pangle":
                            # Pangle: result.data contains site_id, or result itself
                            app_code = result.get("site_id") or (result.get("data", {}) if isinstance(result.get("data"), dict) else {}).get("site_id")
                        elif current_network == "mintegral":
                            # Mintegral: result.data contains app_id, or result itself
                            # Try multiple possible field names
                            data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
                            app_id = data.get("app_id") or data.get("id") or data.get("appId") or result.get("app_id") or result.get("id")
                            app_code = str(app_id) if app_id else None
                        else:
                            # BigOAds: result.data contains appCode, or result itself
                            data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
                            app_code = data.get("appCode") or result.get("appCode")
                        
                        if not app_code:
                            app_code = "N/A"
                        
                        app_name = form_data.get("app_name") or form_data.get("appName") or form_data.get("name", "Unknown")
                        
                        # For IronSource and Pangle, we don't have platform/pkgName in the same way
                        if current_network in ["ironsource", "pangle", "mintegral"]:
                            platform = None
                            platform_str = None
                            pkg_name = None
                            
                            # For IronSource, extract platform from form_data
                            if current_network == "ironsource":
                                platform_value = form_data.get("platform", "Android")
                                platform_str = "android" if platform_value == "Android" else "ios"
                                platform = 1 if platform_value == "Android" else 2
                        else:
                            platform = form_data.get("platform", 1)  # 1 = Android, 2 = iOS
                            platform_str = "android" if platform == 1 else "ios"
                            pkg_name = form_data.get("pkgName", "")
                        
                        # Save to session with full info for slot creation
                        app_data = {
                            "appCode": app_code,  # For IronSource, this is actually appKey
                            "appKey": app_code if current_network == "ironsource" else None,  # Store appKey separately for IronSource
                            "siteId": app_code if current_network == "pangle" else None,  # Store siteId separately for Pangle
                            "app_id": app_id if current_network == "mintegral" else (int(app_code) if app_code and app_code != "N/A" and str(app_code).isdigit() else None),  # Store app_id separately for Mintegral
                            "name": app_name,
                            "pkgName": pkg_name,
                            "platform": platform,
                            "platformStr": platform_str,
                            "storeUrl": form_data.get("storeUrl", "") if current_network == "ironsource" else ""  # Store URL for IronSource slot name generation
                        }
                        SessionManager.add_created_app(current_network, app_data)
                        
                        # Add newly created app to cache so it's immediately available in Create Unit
                        cached_apps = SessionManager.get_cached_apps(current_network)
                        new_app = {
                            "appCode": app_code,
                            "name": app_name,
                            "platform": platform,
                            "status": "Active"
                        }
                        # Check if app already exists in cache (avoid duplicates)
                        if not any(app.get("appCode") == app_code for app in cached_apps):
                            cached_apps.append(new_app)
                            SessionManager.cache_apps(current_network, cached_apps)
                        
                        st.success("🎉 App created successfully!")
                        st.balloons()
                        
                        # Show result details
                        st.subheader("📝 Result")
                        result_col1, result_col2 = st.columns(2)
                        with result_col1:
                            st.write(f"**Network:** {network_display}")
                            st.write(f"**App Code:** {result.get('appCode', app_code)}")
                        with result_col2:
                            st.write(f"**App Name:** {form_data.get('name', app_name)}")
                            if form_data.get('platform'):
                                st.write(f"**Platform:** {'Android' if form_data.get('platform') == 1 else 'iOS'}")
                        
            except Exception as e:
                st.error(f"❌ Error creating app: {str(e)}")
                SessionManager.log_error(current_network, str(e))

# ============================================================================
# CREATE UNIT SECTION
# ============================================================================
st.divider()
st.subheader("🎯 Create Unit")

# Check if network supports unit creation
if not config.supports_create_unit():
    st.warning(f"⚠️ {network_display} does not support unit creation via API")
    st.info("Please create units manually in the network's dashboard")
else:
    network_manager = get_network_manager()
    
    # Load apps from cache (from Create App POST responses)
    cached_apps = SessionManager.get_cached_apps(current_network)
    
    # For BigOAds and IronSource, also fetch from API and get latest 3 apps
    api_apps = []
    if current_network in ["bigoads", "ironsource"]:
        try:
            with st.spinner("Loading apps from API..."):
                api_apps = network_manager.get_apps(current_network)
                # Get latest 3 apps only
                if api_apps:
                    api_apps = api_apps[:3]
                    st.success(f"✅ Loaded {len(api_apps)} apps from API")
        except Exception as e:
            logger.warning(f"[{current_network}] Failed to load apps from API: {str(e)}")
            api_apps = []
    
    # Merge cached apps with API apps (prioritize cached, but add unique API apps)
    # For BigOAds and IronSource, prioritize API apps (they are more recent)
    if current_network in ["bigoads", "ironsource"] and api_apps:
        # Use API apps first, then add cached apps that are not in API
        apps = api_apps.copy()
        # For IronSource, check appKey; for BigOAds, check appCode
        if current_network == "ironsource":
            api_app_keys = {app.get("appKey") or app.get("appCode") for app in api_apps if app.get("appKey") or app.get("appCode")}
            if cached_apps:
                for cached_app in cached_apps:
                    cached_key = cached_app.get("appKey") or cached_app.get("appCode")
                    if cached_key and cached_key not in api_app_keys:
                        apps.append(cached_app)
        else:  # BigOAds
            api_app_codes = {app.get("appCode") for app in api_apps if app.get("appCode")}
            if cached_apps:
                for cached_app in cached_apps:
                    cached_code = cached_app.get("appCode")
                    if cached_code and cached_code not in api_app_codes:
                        apps.append(cached_app)
    else:
        # For other networks, use cached apps
        apps = cached_apps.copy() if cached_apps else []
        if api_apps:
            cached_app_codes = {app.get("appCode") for app in apps if app.get("appCode")}
            for api_app in api_apps:
                api_code = api_app.get("appCode")
                if api_code and api_code not in cached_app_codes:
                    apps.append(api_app)
    
    # Prepare app options for dropdown (always show, even if no apps)
    app_options = []
    app_code_map = {}
    app_info_map = {}  # Store full app info for Quick Create
    
    if apps:
        for app in apps:
            # For IronSource, use appKey; for others, use appCode
            if current_network == "ironsource":
                app_code = app.get("appKey") or app.get("appCode", "N/A")
            else:
                app_code = app.get("appCode", "N/A")
            
            app_name = app.get("name", "Unknown")
            platform = app.get("platform", "")
            display_text = f"{app_code} ({app_name})"
            if platform and platform != "N/A":
                display_text += f" - {platform}"
            app_options.append(display_text)
            app_code_map[display_text] = app_code
            # Store app info for Quick Create
            # For IronSource, use platformNum and platformStr from API response
            if current_network == "ironsource":
                platform_num = app.get("platformNum", 1 if platform == "Android" else 2)
                platform_str = app.get("platformStr", "android" if platform == "Android" else "ios")
                store_url = app.get("storeUrl", "")
            else:
                platform_num = 1 if platform == "Android" else 2
                platform_str = "android" if platform == "Android" else "ios"
                store_url = ""
            
            app_info_map[app_code] = {
                "appCode": app_code,
                "appKey": app_code if current_network == "ironsource" else None,  # Store appKey for IronSource
                "name": app_name,
                "platform": platform_num,  # 1 or 2
                "platformStr": platform_str,  # "android" or "ios"
                "pkgName": app.get("pkgName", ""),  # From API response
                "storeUrl": store_url,  # Store URL for slot name generation
                "platformDisplay": platform  # "Android" or "iOS" for display
            }
    
    # Always add "Manual Entry" option (even if apps exist)
    manual_entry_option = "✏️ Enter manually"
    app_options.append(manual_entry_option)
    
    # If no apps, default to manual entry
    if not apps:
        default_index = 0  # Manual entry will be the only option
        st.info("💡 No apps found. You can enter App Code manually below.")
    else:
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
    
    # App selection (single selection for all slots)
    app_label = "Site ID*" if current_network == "pangle" else "App Code*"
    
    # Ensure app_options is not empty (at least manual entry should be there)
    if not app_options:
        app_options = [manual_entry_option]
    
    selected_app_display = st.selectbox(
        app_label,
        options=app_options if app_options else [manual_entry_option],
        index=default_index if apps and default_index < len(app_options) else 0,
        help="Select the app for the slots or enter manually. Recently created apps are pre-selected." if current_network != "pangle" else "Select the site for the ad placements or enter manually. Recently created sites are pre-selected.",
        key="slot_app_select"
    )
    
    # Check if manual entry is selected
    if selected_app_display == manual_entry_option:
        # Show manual input field
        manual_app_code = st.text_input(
            f"Enter {app_label.lower()}",
            value="",
            help="Enter the app code manually",
            key="manual_app_code_input"
        )
        selected_app_code = manual_app_code.strip() if manual_app_code else ""
        app_name = "Manual Entry"
    else:
        # Get app code from map
        selected_app_code = app_code_map.get(selected_app_display, "")
        
        # If not found in map, try to extract from display text
        if not selected_app_code and selected_app_display != manual_entry_option:
            # Try to extract appCode from display text: "appCode (name)" or "appCode (name) - platform"
            if "(" in selected_app_display:
                # Extract appCode (part before the first parenthesis)
                selected_app_code = selected_app_display.split("(")[0].strip()
            else:
                # If no parenthesis, use the whole string as appCode
                selected_app_code = selected_app_display.strip()
        
        # Extract app name from display text
        app_name = "Unknown"
        if selected_app_display != manual_entry_option and "(" in selected_app_display and ")" in selected_app_display:
            app_name = selected_app_display.split("(")[1].split(")")[0]
    
    # When app code is selected, immediately generate and update slot names
    if selected_app_code:
        # Get pkgNameDisplay/pkgName and platform from apps list
        selected_app_data = None
        for app in apps:
            # For IronSource, check appKey; for others, check appCode
            app_identifier = app.get("appKey") if current_network == "ironsource" else app.get("appCode")
            if app_identifier == selected_app_code:
                selected_app_data = app
                break
        
        if selected_app_data:
            # Get pkgNameDisplay (for BigOAds) or pkgName
            if current_network == "bigoads":
                pkg_name = selected_app_data.get("pkgNameDisplay", selected_app_data.get("pkgName", ""))
            else:
                pkg_name = selected_app_data.get("pkgName", "")
            
            # Get platform
            platform_str_val = selected_app_data.get("platform", "")
            platform_str = "android" if platform_str_val == "Android" else ("ios" if platform_str_val == "iOS" else "android")
            
            # Update all slot names immediately when app is selected
            if pkg_name:
                for slot_key in ["rv", "is", "bn"]:
                    slot_name_key = f"custom_slot_{slot_key.upper()}_name"
                    default_name = _generate_slot_name(pkg_name, platform_str, slot_key, current_network)
                    st.session_state[slot_name_key] = default_name
    
    # Show UI for slot creation (always show, but require app code selection)
    if selected_app_code:
        st.info(f"**Selected app:** {app_name} ({selected_app_code})")
        
        # Get app info for quick create all
        app_info_to_use = None
        last_app_info = SessionManager.get_last_created_app_info(current_network)
        if last_app_info and last_app_info.get("appCode") == selected_app_code:
            app_info_to_use = last_app_info
        elif selected_app_code in app_info_map:
            app_info_to_use = app_info_map[selected_app_code]
            if last_app_info and last_app_info.get("appCode") == selected_app_code:
                app_info_to_use["pkgName"] = last_app_info.get("pkgName", "")
                # For BigOAds, also get pkgNameDisplay if available
                if current_network == "bigoads" and "pkgNameDisplay" in last_app_info:
                    app_info_to_use["pkgNameDisplay"] = last_app_info.get("pkgNameDisplay", "")
        else:
            # For manual entry or API apps, create minimal app info
            app_info_to_use = {
                "appCode": selected_app_code,
                "name": app_name,
                "platform": None,
                "pkgName": "",
                "platformStr": "unknown"
            }
            
            # Try to get platform and pkgNameDisplay from apps list (for BigOAds)
            for app in apps:
                # For IronSource, check appKey; for others, check appCode
                app_identifier = app.get("appKey") if current_network == "ironsource" else app.get("appCode")
                if app_identifier == selected_app_code:
                    platform_str = app.get("platform", "")
                    if platform_str == "Android":
                        app_info_to_use["platform"] = 1
                        app_info_to_use["platformStr"] = "android"
                    elif platform_str == "iOS":
                        app_info_to_use["platform"] = 2
                        app_info_to_use["platformStr"] = "ios"
                    
                    # For IronSource, get storeUrl and platformStr from API response
                    if current_network == "ironsource":
                        app_info_to_use["storeUrl"] = app.get("storeUrl", "")
                        app_info_to_use["platformStr"] = app.get("platformStr", "android")
                        app_info_to_use["platform"] = app.get("platformNum", 1)
                    
                    # For BigOAds, get pkgNameDisplay from API response
                    if current_network == "bigoads" and "pkgNameDisplay" in app:
                        app_info_to_use["pkgNameDisplay"] = app.get("pkgNameDisplay", "")
                    break
    else:
        # Show message if no app code selected
        st.info("💡 Please select an App Code above to create units.")
        app_info_to_use = None
    
    # Create Unit UI (always show, but require app code selection)
    # Show Create Unit UI even if app code is not selected (will show message)
    if True:  # Always show Create Unit UI
        # Ensure app_info_to_use is available for slot name generation
        if selected_app_code and not app_info_to_use:
            # Try to get app info again if not already set
            last_app_info = SessionManager.get_last_created_app_info(current_network)
            if last_app_info and last_app_info.get("appCode") == selected_app_code:
                app_info_to_use = last_app_info
            elif selected_app_code in app_info_map:
                app_info_to_use = app_info_map[selected_app_code]
                if last_app_info and last_app_info.get("appCode") == selected_app_code:
                    app_info_to_use["pkgName"] = last_app_info.get("pkgName", "")
                    if current_network == "bigoads" and "pkgNameDisplay" in last_app_info:
                        app_info_to_use["pkgNameDisplay"] = last_app_info.get("pkgNameDisplay", "")
                    # For IronSource, get storeUrl from last_app_info
                    if current_network == "ironsource":
                        app_info_to_use["storeUrl"] = last_app_info.get("storeUrl", "")
                        app_info_to_use["platformStr"] = last_app_info.get("platformStr", "android")
            else:
                # Try to get from apps list
                for app in apps:
                    # For IronSource, check appKey; for others, check appCode
                    app_identifier = app.get("appKey") if current_network == "ironsource" else app.get("appCode")
                    
                    if app_identifier == selected_app_code:
                        platform_str = app.get("platform", "")
                        # For IronSource, use platformNum and platformStr from API response
                        if current_network == "ironsource":
                            platform_num = app.get("platformNum", 1)
                            platform_str_val = app.get("platformStr", "android")
                            store_url = app.get("storeUrl", "")
                        else:
                            platform_num = 1 if platform_str == "Android" else (2 if platform_str == "iOS" else 1)
                            platform_str_val = "android" if platform_str == "Android" else ("ios" if platform_str == "iOS" else "android")
                            store_url = ""
                        
                        app_info_to_use = {
                            "appCode": selected_app_code,
                            "appKey": selected_app_code if current_network == "ironsource" else None,
                            "name": app.get("name", "Unknown"),
                            "platform": platform_num,
                            "platformStr": platform_str_val,
                            "storeUrl": store_url,
                            "pkgName": "",
                            "pkgNameDisplay": app.get("pkgNameDisplay", "") if current_network == "bigoads" else "",
                            "storeUrl": app.get("storeUrl", "") if current_network == "ironsource" else ""
                        }
                        break
        # Create All 3 Slots button at the top (for BigOAds)
        if current_network == "bigoads":
                if st.button("✨ Create All 3 Slots (RV + IS + BN)", use_container_width=True, type="primary"):
                    with st.spinner("Creating all 3 slots..."):
                        results = []
                        for slot_type in ["rv", "is", "bn"]:
                            try:
                                _create_default_slot(current_network, app_info_to_use, slot_type, network_manager, config)
                                results.append({"type": slot_type.upper(), "status": "success"})
                            except Exception as e:
                                results.append({"type": slot_type.upper(), "status": "error", "error": str(e)})
                        
                        # Show results
                        st.success("🎉 Finished creating slots!")
                        st.balloons()
                        
                        # Display created slots
                        st.subheader("📋 Created Slots")
                        for result in results:
                            if result["status"] == "success":
                                st.success(f"✅ {result['type']} slot created successfully")
                            else:
                                st.error(f"❌ {result['type']} slot failed: {result.get('error', 'Unknown error')}")
                        
                        st.rerun()
        
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
                "rewardItemName": "Reward",
                "rewardAmount": 1,
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
        
        # Default slot configurations for Mintegral
        slot_configs_mintegral = {
            "RV": {
                "name": "Rewarded Video",
                "ad_type": "rewarded_video",
                "integrate_type": "sdk",
                "skip_time": -1,  # Non Skippable
            },
            "IS": {
                "name": "Interstitial",
                "ad_type": "new_interstitial",
                "integrate_type": "sdk",
                "content_type": "both",
                "ad_space_type": 1,
                "skip_time": -1,  # Non Skippable
            },
            "BN": {
                "name": "Banner",
                "ad_type": "banner",
                "integrate_type": "sdk",
                "show_close_button": 0,
                "auto_fresh": 0,
            }
        }
        
        # Select configs based on network
        if current_network == "ironsource":
            slot_configs = slot_configs_ironsource
        elif current_network == "pangle":
            slot_configs = slot_configs_pangle
        elif current_network == "mintegral":
            slot_configs = slot_configs_mintegral
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
                            
                            # Generate default name from Store URL if available
                            if selected_app_code and app_info_to_use:
                                store_url = app_info_to_use.get("storeUrl", "")
                                platform_str = app_info_to_use.get("platformStr", "android")
                                if store_url:
                                    # Map slot_key to slot_type
                                    slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                                    slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                    default_name = _generate_slot_name("", platform_str, slot_type, "ironsource", store_url)
                                    st.session_state[slot_name_key] = default_name
                                elif slot_name_key not in st.session_state:
                                    default_name = f"{slot_key.lower()}-1"
                                    st.session_state[slot_name_key] = default_name
                            elif slot_name_key not in st.session_state:
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
                            
                            # For Reward Video, add reward information
                            if slot_key == "RV" and slot_config.get("adFormat") == "rewarded":
                                reward_item_name = slot_config.get("rewardItemName", "Reward")
                                reward_amount = slot_config.get("rewardAmount", 1)
                                settings_html += f'<li>Reward Item Name: {reward_item_name}</li>'
                                settings_html += f'<li>Reward Amount: {reward_amount}</li>'
                            
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
                                    
                                    # For Reward Video, add reward object (required)
                                    if slot_key == "RV" and slot_config.get("adFormat") == "rewarded":
                                        reward_item_name = slot_config.get("rewardItemName", "Reward")
                                        reward_amount = slot_config.get("rewardAmount", 1)
                                        payload["reward"] = {
                                            "rewardItemName": reward_item_name,
                                            "rewardAmount": reward_amount
                                        }
                                
                                    # Make API call
                                    with st.spinner(f"Creating {slot_key} placement..."):
                                        try:
                                            response = network_manager.create_unit(current_network, payload, app_key=selected_app_code)
                                            
                                            # Check if response is None or invalid
                                            if not response:
                                                st.error("❌ No response from API")
                                                SessionManager.log_error(current_network, "No response from API")
                                            else:
                                                result = handle_api_response(response)
                                        
                                                if result and isinstance(result, dict):
                                                    unit_data = {
                                                        "slotCode": result.get("adUnitId") or result.get("id") or result.get("adUnitId", "N/A"),
                                                        "name": mediation_ad_unit_name,
                                                        "appCode": selected_app_code,
                                                        "slotType": slot_config['adFormat'],
                                                        "adType": slot_config['adFormat'],
                                                        "auctionType": "N/A"
                                                    }
                                                    SessionManager.add_created_unit(current_network, unit_data)
                                                    
                                                    # Add to cache
                                                    cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                                                    if not cached_units:
                                                        cached_units = []
                                                    if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                        cached_units.append(unit_data)
                                                        SessionManager.cache_units(current_network, selected_app_code, cached_units)
                                                    
                                                    st.success(f"✅ {slot_key} placement created successfully!")
                                                    st.rerun()
                                                elif result is None:
                                                    # handle_api_response already displayed error
                                                    pass
                                                else:
                                                    st.error(f"❌ Unexpected response format: {type(result)}")
                                                    SessionManager.log_error(current_network, f"Unexpected response format: {type(result)}")
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
                            st.info(f"**API Version:** 1.1.13 (auto-generated)")
                            
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
                                        "app_id": selected_app_code,  # app_id from selected app (Pangle uses app_id parameter)
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
                                                unit_data = {
                                                    "slotCode": result.get("code_id", result.get("ad_unit_id", "N/A")),
                                                    "name": slot_name,
                                                    "appCode": selected_app_code,
                                                    "slotType": slot_config["ad_slot_type"],
                                                    "adType": f"Type {slot_config['ad_slot_type']}",
                                                    "auctionType": "N/A"
                                                }
                                                SessionManager.add_created_unit(current_network, unit_data)
                                                
                                                # Add to cache
                                                cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                                                if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                    cached_units.append(unit_data)
                                                    SessionManager.cache_units(current_network, selected_app_code, cached_units)
                                                
                                                st.success(f"✅ {slot_key} placement created successfully!")
                                                st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                                            SessionManager.log_error(current_network, str(e))
                        elif current_network == "mintegral":
                            # Mintegral: app_id, placement_name, ad_type, and type-specific fields
                            placement_name_key = f"mintegral_slot_{slot_key}_name"
                            if placement_name_key not in st.session_state:
                                default_name = f"{slot_key.lower()}_placement"
                                st.session_state[placement_name_key] = default_name
                            
                            placement_name = st.text_input(
                                "Placement Name*",
                                value=st.session_state[placement_name_key],
                                key=placement_name_key,
                                help=f"Name for {slot_config['name']} placement"
                            )
                            
                            # App ID: from created app or input
                            app_id_key = f"mintegral_slot_{slot_key}_app_id"
                            # Try to get app_id from last created app
                            last_app_info = SessionManager.get_last_created_app_info(current_network)
                            app_id_from_app = None
                            if last_app_info:
                                # Mintegral Create App response에서 app_id를 가져옴
                                app_id_from_app = last_app_info.get("app_id") or last_app_info.get("appId") or last_app_info.get("appCode")
                            
                            # Determine default value (must be >= 1)
                            if app_id_from_app:
                                try:
                                    default_app_id = max(1, int(app_id_from_app)) if app_id_from_app else 1
                                except (ValueError, TypeError):
                                    default_app_id = 1
                            else:
                                default_app_id = st.session_state.get(app_id_key, 1)
                                if default_app_id < 1:
                                    default_app_id = 1
                            
                            app_id = st.number_input(
                                "App ID*",
                                value=default_app_id,
                                min_value=1,
                                key=app_id_key,
                                help="Media ID from created app or enter manually"
                            )
                            
                            # Display current settings
                            st.markdown("**Current Settings:**")
                            # IS 섹션이 가장 많은 항목(6개)을 가지므로, 모든 섹션의 높이를 IS에 맞춤
                            # IS: Ad Type, Integration Type, Content Type, Ad Space Type, Skip Time, HB Unit Name (6개)
                            # RV: Ad Type, Integration Type, Skip Time, HB Unit Name (4개)
                            # BN: Ad Type, Integration Type, Show Close Button, Auto Refresh, HB Unit Name (5개)
                            settings_html = '<div style="min-height: 180px; margin-bottom: 10px;">'
                            settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
                            settings_html += f'<li>Ad Type: {slot_config["ad_type"].replace("_", " ").title()}</li>'
                            settings_html += f'<li>Integration Type: SDK</li>'
                            
                            if slot_key == "RV":
                                skip_time_text = "Non Skippable" if slot_config["skip_time"] == -1 else f"{slot_config['skip_time']} seconds"
                                settings_html += f'<li>Skip Time: {skip_time_text}</li>'
                                settings_html += f'<li>HB Unit Name: {placement_name if placement_name else "(same as Placement Name)"}</li>'
                                # RV는 4개 항목이므로 빈 줄 2개 추가하여 IS(6개)와 높이 맞춤
                                settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
                                settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
                            elif slot_key == "IS":
                                content_type_text = slot_config.get("content_type", "both").title()
                                ad_space_text = "Full Screen Interstitial" if slot_config.get("ad_space_type", 1) == 1 else "Half Screen Interstitial"
                                skip_time_text = "Non Skippable" if slot_config["skip_time"] == -1 else f"{slot_config['skip_time']} seconds"
                                settings_html += f'<li>Content Type: {content_type_text}</li>'
                                settings_html += f'<li>Ad Space Type: {ad_space_text}</li>'
                                settings_html += f'<li>Skip Time: {skip_time_text}</li>'
                                settings_html += f'<li>HB Unit Name: {placement_name if placement_name else "(same as Placement Name)"}</li>'
                            elif slot_key == "BN":
                                show_close_text = "No" if slot_config.get("show_close_button", 0) == 0 else "Yes"
                                auto_fresh_text = "Turn Off" if slot_config.get("auto_fresh", 0) == 0 else "Turn On"
                                settings_html += f'<li>Show Close Button: {show_close_text}</li>'
                                settings_html += f'<li>Auto Refresh: {auto_fresh_text}</li>'
                                settings_html += f'<li>HB Unit Name: {placement_name if placement_name else "(same as Placement Name)"}</li>'
                                # BN은 5개 항목이므로 빈 줄 1개 추가하여 IS(6개)와 높이 맞춤
                                settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
                            
                            settings_html += '</ul></div>'
                            st.markdown(settings_html, unsafe_allow_html=True)
                            
                            # Editable settings for Mintegral
                            with st.expander("⚙️ Edit Settings"):
                                if slot_key == "RV":
                                    # Rewarded Video specific settings
                                    skip_time = st.number_input(
                                        "Skip Time (seconds)",
                                        min_value=-1,
                                        max_value=30,
                                        value=slot_config.get("skip_time", -1),
                                        key=f"{slot_key}_skip_time",
                                        help="-1 for non-skippable, 0-30 for skippable"
                                    )
                                    slot_config["skip_time"] = skip_time
                                elif slot_key == "IS":
                                    # Interstitial specific settings
                                    content_type = st.selectbox(
                                        "Content Type",
                                        options=[("Image", "image"), ("Video", "video"), ("Both", "both")],
                                        index=2 if slot_config.get("content_type", "both") == "both" else (0 if slot_config.get("content_type") == "image" else 1),
                                        key=f"{slot_key}_content_type",
                                        format_func=lambda x: x[0]
                                    )
                                    slot_config["content_type"] = content_type[1]
                                    
                                    ad_space_type = st.selectbox(
                                        "Ad Space Type",
                                        options=[("Full Screen Interstitial", 1), ("Half Screen Interstitial", 2)],
                                        index=0 if slot_config.get("ad_space_type", 1) == 1 else 1,
                                        key=f"{slot_key}_ad_space_type",
                                        format_func=lambda x: x[0]
                                    )
                                    slot_config["ad_space_type"] = ad_space_type[1]
                                    
                                    skip_time = st.number_input(
                                        "Skip Time (seconds)",
                                        min_value=-1,
                                        max_value=30,
                                        value=slot_config.get("skip_time", -1),
                                        key=f"{slot_key}_skip_time",
                                        help="-1 for non-skippable, 0-30 for skippable"
                                    )
                                    slot_config["skip_time"] = skip_time
                                elif slot_key == "BN":
                                    # Banner specific settings
                                    show_close_button = st.selectbox(
                                        "Show Close Button",
                                        options=[("No", 0), ("Yes", 1)],
                                        index=0 if slot_config.get("show_close_button", 0) == 0 else 1,
                                        key=f"{slot_key}_show_close_button",
                                        format_func=lambda x: x[0]
                                    )
                                    slot_config["show_close_button"] = show_close_button[1]
                                    
                                    auto_fresh = st.selectbox(
                                        "Auto Refresh",
                                        options=[("Turn Off", 0), ("Turn On", 1)],
                                        index=0 if slot_config.get("auto_fresh", 0) == 0 else 1,
                                        key=f"{slot_key}_auto_fresh",
                                        format_func=lambda x: x[0]
                                    )
                                    slot_config["auto_fresh"] = auto_fresh[1]
                            
                            # Create button for Mintegral
                            if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_mintegral_{slot_key}"):
                                if not placement_name:
                                    st.toast("❌ Placement Name is required", icon="🚫")
                                elif not app_id or app_id <= 0:
                                    st.toast("❌ App ID is required", icon="🚫")
                                else:
                                    # Build payload for Mintegral
                                    payload = {
                                        "app_id": int(app_id),
                                        "placement_name": placement_name,
                                        "ad_type": slot_config["ad_type"],
                                        "integrate_type": slot_config["integrate_type"],
                                        "hb_unit_name": placement_name,  # Same as placement_name
                                    }
                                    
                                    # Add type-specific fields
                                    if slot_key == "RV":
                                        payload["skip_time"] = slot_config.get("skip_time", -1)
                                    elif slot_key == "IS":
                                        payload["content_type"] = slot_config.get("content_type", "both")
                                        payload["ad_space_type"] = slot_config.get("ad_space_type", 1)
                                        payload["skip_time"] = slot_config.get("skip_time", -1)
                                    elif slot_key == "BN":
                                        payload["show_close_button"] = slot_config.get("show_close_button", 0)
                                        payload["auto_fresh"] = slot_config.get("auto_fresh", 0)
                                    
                                    # Make API call
                                    with st.spinner(f"Creating {slot_key} placement..."):
                                        try:
                                            response = network_manager.create_unit(current_network, payload)
                                            result = handle_api_response(response)
                                            
                                            if result:
                                                unit_data = {
                                                    "slotCode": result.get("placement_id", result.get("id", "N/A")),
                                                    "name": placement_name,
                                                    "appCode": str(app_id),
                                                    "slotType": slot_config["ad_type"],
                                                    "adType": slot_config["ad_type"],
                                                    "auctionType": "N/A"
                                                }
                                                SessionManager.add_created_unit(current_network, unit_data)
                                                
                                                # Add to cache
                                                cached_units = SessionManager.get_cached_units(current_network, str(app_id))
                                                if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                    cached_units.append(unit_data)
                                                    SessionManager.cache_units(current_network, str(app_id), cached_units)
                                                
                                                st.success(f"✅ {slot_key} placement created successfully!")
                                                st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                                            SessionManager.log_error(current_network, str(e))
                        else:
                            # BigOAds and other networks
                            # Slot name input
                            slot_name_key = f"custom_slot_{slot_key}_name"
                            
                            # Generate default name when app is selected
                            # For BigOAds, try to get pkgNameDisplay from app_info_to_use or apps list
                            pkg_name = ""
                            platform_str = "android"
                            
                            if selected_app_code and app_info_to_use:
                                # Use app_info_to_use if available
                                if current_network == "bigoads":
                                    pkg_name = app_info_to_use.get("pkgNameDisplay", app_info_to_use.get("pkgName", ""))
                                else:
                                    pkg_name = app_info_to_use.get("pkgName", "")
                                platform_str = app_info_to_use.get("platformStr", "android")
                            elif selected_app_code:
                                # Try to get from apps list directly
                                for app in apps:
                                    # For IronSource, check appKey; for others, check appCode
                                    if current_network == "ironsource":
                                        app_identifier = app.get("appKey") or app.get("appCode")
                                    else:
                                        app_identifier = app.get("appCode")
                                    
                                    if app_identifier == selected_app_code:
                                        if current_network == "bigoads":
                                            pkg_name = app.get("pkgNameDisplay", app.get("pkgName", ""))
                                        else:
                                            pkg_name = app.get("pkgName", "")
                                        platform_str_val = app.get("platform", "")
                                        platform_str = "android" if platform_str_val == "Android" else ("ios" if platform_str_val == "iOS" else "android")
                                        break
                            
                            # Update slot name if app is selected and we have pkg_name
                            if selected_app_code and pkg_name:
                                default_name = _generate_slot_name(pkg_name, platform_str, slot_key.lower())
                                # Always update when app is selected (even if key exists)
                                st.session_state[slot_name_key] = default_name
                            elif slot_name_key not in st.session_state:
                                # Only set default if key doesn't exist and no app selected
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
                                            unit_data = {
                                                "slotCode": result.get("slotCode", "N/A"),
                                                "name": slot_name,
                                                "appCode": selected_app_code,
                                                "slotType": slot_key,
                                                "adType": slot_config.get('adType', slot_key),
                                                "auctionType": slot_config.get('auctionType', "N/A")
                                            }
                                            SessionManager.add_created_unit(current_network, unit_data)
                                            
                                            # Add to cache
                                            cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                                            if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                cached_units.append(unit_data)
                                                SessionManager.cache_units(current_network, selected_app_code, cached_units)
                                            
                                            st.success(f"✅ {slot_key} slot created successfully!")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error creating {slot_key} slot: {str(e)}")
                                        SessionManager.log_error(current_network, str(e))

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
