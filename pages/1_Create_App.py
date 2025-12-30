"""Create App/Media and Unit page"""
import streamlit as st
import logging
from utils.session_manager import SessionManager
from utils.ui_components import DynamicFormRenderer
from utils.network_manager import get_network_manager, handle_api_response, _mask_sensitive_data
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


def _normalize_platform_str(platform_value: str, network: str = None) -> str:
    """Normalize platform string to "android" or "ios"
    
    Args:
        platform_value: Platform value from API (can be "ANDROID", "IOS", "Android", "iOS", etc.)
        network: Network name for network-specific handling (optional)
    
    Returns:
        Normalized platform string: "android" or "ios"
    """
    if not platform_value:
        return "android"  # Default
    
    platform_str = str(platform_value).strip()
    platform_upper = platform_str.upper()
    platform_lower = platform_str.lower()
    
    # Handle Mintegral format: "ANDROID" or "IOS" (uppercase)
    if platform_upper == "ANDROID" or platform_upper == "AND":
        return "android"
    elif platform_upper == "IOS" or platform_upper == "IPHONE":
        return "ios"
    
    # Handle common formats
    if platform_lower in ["android", "1", "and", "aos"]:
        return "android"
    elif platform_lower in ["ios", "2", "iphone"]:
        return "ios"
    elif platform_str == "Android":
        return "android"
    elif platform_str == "iOS":
        return "ios"
    
    # Default to android
    return "android"


def _get_bigoads_pkg_name_display(pkg_name: str, bundle_id: str, network_manager, app_name: str = None, platform_str: str = None) -> str:
    """Get BigOAds pkgNameDisplay by matching package name or bundleId
    
    For iOS apps with iTunes ID (id123456), try to find Android version of the same app
    by matching app name, then use Android package name.
    
    Args:
        pkg_name: Package name from current network
        bundle_id: Bundle ID from current network (optional)
        network_manager: Network manager instance to fetch BigOAds apps
        app_name: App name for matching (optional, used when pkg_name is iTunes ID)
        platform_str: Platform string ("android" or "ios") for filtering
    
    Returns:
        BigOAds pkgNameDisplay if found, otherwise returns empty string for iTunes ID,
        or original pkg_name/bundle_id for valid package names
    """
    if not pkg_name and not bundle_id:
        return ""
    
    # Use bundle_id if available, otherwise use pkg_name
    search_key = bundle_id if bundle_id else pkg_name
    if not search_key:
        return ""
    
    # Check if search_key is an iTunes ID (starts with "id" followed by numbers)
    is_itunes_id = search_key.startswith("id") and search_key[2:].isdigit()
    
    try:
        # Fetch BigOAds apps
        bigoads_apps = network_manager.get_apps("bigoads")
        
        if is_itunes_id:
            # For iTunes ID, try to find Android version of the same app by app name
            if app_name:
                for app in bigoads_apps:
                    app_platform = app.get("platform", "")
                    app_pkg_name_display = app.get("pkgNameDisplay", "")
                    app_pkg_name = app.get("pkgName", "")
                    app_app_name = app.get("name", "")
                    
                    # Match by app name and platform (Android)
                    if app_platform == "Android" and app_app_name and app_name:
                        # Simple name matching (case-insensitive, partial match)
                        if app_app_name.lower().strip() == app_name.lower().strip():
                            # Found Android version, use its package name
                            if app_pkg_name_display:
                                return app_pkg_name_display
                            elif app_pkg_name:
                                return app_pkg_name
                            break
            # If no match found for iTunes ID, return empty to avoid using iTunes ID
            logger.warning(f"Could not find Android package name for iTunes ID: {search_key}. App name: {app_name}")
            return ""
        else:
            # For normal package name, match by pkgName or pkgNameDisplay
            for app in bigoads_apps:
                app_pkg_name = app.get("pkgName", "")
                app_pkg_name_display = app.get("pkgNameDisplay", "")
                
                # Match by pkgName or pkgNameDisplay
                if app_pkg_name == search_key or app_pkg_name_display == search_key:
                    # Return pkgNameDisplay if available, otherwise return original
                    if app_pkg_name_display:
                        return app_pkg_name_display
                    break
    except Exception as e:
        logger.warning(f"Failed to fetch BigOAds apps for pkgNameDisplay lookup: {str(e)}")
    
    # Fallback: if it's an iTunes ID, return empty to avoid using it
    if is_itunes_id:
        return ""
    
    # Fallback: return original pkg_name or bundle_id for valid package names
    return search_key


def _generate_slot_name(pkg_name: str, platform_str: str, slot_type: str, network: str = "bigoads", store_url: str = None, bundle_id: str = None, network_manager=None, app_name: str = None) -> str:
    """Generate unified slot name for all networks
    
    Format: {package_name_last_part}_{os}_{network}_{adtype}_bidding
    
    Rules:
    - package_name: Use BigOAds pkgNameDisplay if available, otherwise use current network's pkg_name/bundle_id
    - For iOS apps with iTunes ID (id123456), find Android version by app name and use its package name
    - Extract last part after "." (e.g., com.example.app -> app)
    - os: "aos" for Android, "ios" for iOS
    - network: network name in lowercase (bigoads, ironsource, fyber, etc.)
    - adtype: "rv", "is", "bn" (unified for all networks)
    - Always append "_bidding"
    """
    # Get package name (prefer BigOAds pkgNameDisplay)
    final_pkg_name = pkg_name
    if network_manager and (pkg_name or bundle_id):
        bigoads_pkg = _get_bigoads_pkg_name_display(pkg_name, bundle_id, network_manager, app_name, platform_str)
        if bigoads_pkg:
            final_pkg_name = bigoads_pkg
        elif not bigoads_pkg and pkg_name and pkg_name.startswith("id") and pkg_name[2:].isdigit():
            # iTunes ID but couldn't find Android version - this should not happen if app_name is provided
            # Return empty to avoid using iTunes ID
            logger.warning(f"Could not find package name for iTunes ID: {pkg_name}. App name: {app_name}")
            return ""
    
    # Extract last part after "."
    if "." in final_pkg_name:
        last_part = final_pkg_name.split(".")[-1]
    else:
        last_part = final_pkg_name
    
    # Normalize platform_str first, then map to os: Android -> aos, iOS -> ios
    normalized_platform = _normalize_platform_str(platform_str, network)
    os = "aos" if normalized_platform == "android" else "ios"
    
    # Map slot_type to adtype (unified: rv, is, bn)
    slot_type_lower = slot_type.lower()
    adtype_map = {
        "rv": "rv",
        "rewarded": "rv",
        "is": "is",
        "interstitial": "is",
        "bn": "bn",
        "banner": "bn"
    }
    adtype = adtype_map.get(slot_type_lower, slot_type_lower)
    
    # Network name in lowercase
    network_lower = network.lower()
    
    # Generate unified format: {last_part}_{os}_{network}_{adtype}_bidding
    return f"{last_part}_{os}_{network_lower}_{adtype}_bidding"


def _create_default_slot(network: str, app_info: dict, slot_type: str, network_manager, config):
    """Create a default slot with predefined settings"""
    app_code = app_info.get("appCode")
    platform_str = app_info.get("platformStr", "android")
    
    # Get package name (prefer BigOAds pkgNameDisplay via unified function)
    pkg_name = app_info.get("pkgName", "")
    bundle_id = app_info.get("bundleId", "")
    app_name = app_info.get("name", "")
    
    # Generate slot name using unified function (will automatically use BigOAds pkgNameDisplay if available)
    slot_name = _generate_slot_name(pkg_name, platform_str, slot_type, network, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name)
    
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
        # Banner: adType = 2, auctionType = 3, autoRefresh = 2, bannerSize = 2
        payload.update({
            "adType": 2,
            "auctionType": 3,
            "autoRefresh": 2,
            "bannerSize": 2  # Numeric value (1 or 2) for API
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
    # Sort networks: AppLovin first, then others
    network_items = list(available_networks.items())
    applovin_item = None
    other_items = []
    for key, display in network_items:
        if key == "applovin":
            applovin_item = (key, display)
        else:
            other_items.append((key, display))
    
    # Reorder: AppLovin first, then others
    if applovin_item:
        sorted_items = [applovin_item] + other_items
    else:
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
st.subheader("📱 Create App")

# For AppLovin, skip app creation form
if current_network == "applovin":
    st.info("💡 AppLovin은 API를 통한 앱 생성 기능을 지원하지 않습니다. 대시보드에서 앱을 생성한 후, 아래 'Create Unit' 섹션에서 Ad Unit을 생성할 수 있습니다.")
else:
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
            
            # Show auto-generated fields info (values will be generated when Create App is clicked)
            st.info("**Auto-generated (on submit):** Timestamp, Nonce, Sign (from security_key + timestamp + nonce)")
            st.divider()
        
        # Render form without sections for all networks
        form_data = DynamicFormRenderer.render_form(config, "app", existing_data=existing_data)
        
        # For Pangle, ensure user_id and role_id are in form_data (they're read-only but needed for API)
        if current_network == "pangle":
            if "user_id" in existing_data:
                form_data["user_id"] = existing_data["user_id"]
            if "role_id" in existing_data:
                form_data["role_id"] = existing_data["role_id"]
        
        # Form buttons - conditional layout based on network
        if current_network == "mintegral":
            # 3 columns for Mintegral
            col1, col2, col3 = st.columns(3)
            with col1:
                reset_button = st.form_submit_button("🔄 Reset", use_container_width=True)
            with col2:
                submit_button = st.form_submit_button("✅ Create App", use_container_width=True)
            with col3:
                test_api_button = st.form_submit_button("🔍 Test Media List API", use_container_width=True, help="Test Mintegral Media List API to check permissions")
        else:
            # 2 columns for other networks
            col1, col2 = st.columns(2)
            with col1:
                reset_button = st.form_submit_button("🔄 Reset", use_container_width=True)
            with col2:
                submit_button = st.form_submit_button("✅ Create App", use_container_width=True)
            test_api_button = False
    
    # Handle form submission (outside form block)
    if current_network != "applovin":
        try:
            if reset_button:
                st.rerun()
        except NameError:
            pass
        
        # Test Media List API for Mintegral
        try:
            if test_api_button and current_network == "mintegral":
                with st.spinner("Testing Mintegral Media List API..."):
                    try:
                        network_manager = get_network_manager()
                        apps = network_manager.get_apps(current_network)
                        if apps:
                            st.success(f"✅ Media List API 호출 성공! {len(apps)}개의 앱을 찾았습니다.")
                            st.json(apps[:3])  # 최대 3개만 표시
                        else:
                            st.warning("⚠️ Media List API 호출은 성공했지만 앱이 없습니다. 터미널 로그를 확인하세요.")
                    except Exception as e:
                        st.error(f"❌ Media List API 호출 실패: {str(e)}")
                        st.info("💡 터미널 로그를 확인하여 자세한 에러 정보를 확인하세요.")
        except NameError:
            pass
        
        # Display persisted create app response if exists (for all networks)
        response_key = f"{current_network}_last_app_response"
        if response_key in st.session_state:
            last_response = st.session_state[response_key]
            st.info(f"📥 Last Create App Response (persisted) - {network_display}")
            with st.expander("📥 Last API Response", expanded=True):
                import json
                st.json(_mask_sensitive_data(last_response))
                result = last_response.get('result', {})
                if result:
                    st.subheader("📝 Result Data")
                    st.json(_mask_sensitive_data(result))
            if st.button("🗑️ Clear Response", key=f"clear_{current_network}_response"):
                del st.session_state[response_key]
                st.rerun()
            st.divider()
        
        try:
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
                            
                            # Store response in session_state to persist it (for all networks)
                            st.session_state[f"{current_network}_last_app_response"] = response
                            
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
                                elif current_network == "inmobi":
                                    # InMobi: result.data contains appId, or result itself
                                    # Try multiple possible field names
                                    data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
                                    app_id = data.get("appId") or data.get("id") or data.get("app_id") or result.get("appId") or result.get("id")
                                    app_code = str(app_id) if app_id else None
                                else:
                                    # BigOAds: result.data contains appCode, or result itself
                                    data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
                                    app_code = data.get("appCode") or result.get("appCode")
                                
                                if not app_code:
                                    app_code = "N/A"
                                
                                app_name = form_data.get("app_name") or form_data.get("appName") or form_data.get("name", "Unknown")
                                
                                # For IronSource, Pangle, Mintegral, and InMobi, we don't have platform/pkgName in the same way
                                if current_network in ["ironsource", "pangle", "mintegral", "inmobi"]:
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
                                    "app_id": app_id if current_network in ["mintegral", "inmobi"] else (int(app_code) if app_code and app_code != "N/A" and str(app_code).isdigit() else None),  # Store app_id separately for Mintegral and InMobi
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
                                    # Display platform correctly for all networks
                                    if current_network in ["ironsource", "pangle", "mintegral", "inmobi"]:
                                        # For these networks, use platform_str or platform_value
                                        if current_network == "ironsource":
                                            platform_value = form_data.get("platform", "Android")
                                            platform_display = "Android" if platform_value == "Android" else "iOS"
                                        else:
                                            platform_display = "Android" if platform_str == "android" else "iOS"
                                        st.write(f"**Platform:** {platform_display}")
                                    elif form_data.get('platform'):
                                        # For other networks, platform is numeric (1 = Android, 2 = iOS)
                                        st.write(f"**Platform:** {'Android' if form_data.get('platform') == 1 else 'iOS'}")
                                
                    except Exception as e:
                        st.error(f"❌ Error creating app: {str(e)}")
                        SessionManager.log_error(current_network, str(e))
        except NameError:
            pass

# ============================================================================
# CREATE UNIT SECTION
# ============================================================================
st.divider()
st.subheader("🎯 Create Unit")

# Check if network supports unit creation
if not config.supports_create_unit():
    st.warning(f"⚠️ {network_display} does not support unit creation via API")
    st.info("Please create units manually in the network's dashboard")
elif current_network == "applovin":
    # AppLovin-specific unit creation UI
    st.info("""
    ⚠️ **주의사항:**
    
    이미 활성화된 앱/플랫폼/광고 형식 조합에 대해서는 이 API를 통해 추가 Ad Unit을 생성할 수 없습니다. 
    추가 생성은 대시보드에서 직접 진행해주세요.
    """)
    
    st.divider()
    
    # Common input fields (outside form, shared by all ad formats)
    st.markdown("**Ad Unit Information**")
    
    # App Name input (optional, used for Ad Unit Name generation)
    app_name = st.text_input(
        "App Name",
        placeholder="Glamour Boutique",
        help="App name (optional, used for Ad Unit Name generation)",
        key="applovin_app_name"
    )
    
    # Package name input
    package_name = st.text_input(
        "Package Name*",
        placeholder="com.test.app",
        help="Package name (Android) or Bundle ID (iOS)",
        key="applovin_package_name"
    )
    
    # Platform radio button
    platform = st.radio(
        "Platform*",
        options=["android", "ios"],
        format_func=lambda x: "Android" if x == "android" else "iOS",
        help="Select platform",
        key="applovin_platform",
        horizontal=True
    )
    
    st.divider()
    
    # AppLovin slot configs (similar to BigOAds)
    slot_configs_applovin = {
        "RV": {
            "name": "Rewarded Video",
            "ad_format": "REWARD"
        },
        "IS": {
            "name": "Interstitial",
            "ad_format": "INTER"
        },
        "BN": {
            "name": "Banner",
            "ad_format": "BANNER"
        }
    }
    
    # Create 3 columns for RV, IS, BN
    col1, col2, col3 = st.columns(3)
    
    for idx, (slot_key, slot_config) in enumerate(slot_configs_applovin.items()):
        with [col1, col2, col3][idx]:
            with st.container():
                st.markdown(f"### 🎯 {slot_key} ({slot_config['name']})")
                
                # Slot name input
                slot_name_key = f"applovin_slot_{slot_key}_name"
                
                # Generate default name based on app_name or package_name
                if app_name:
                    # Use app_name: {app_name} {os} {adformat}
                    os_str = "AOS" if platform == "android" else "iOS"
                    adformat_map = {"RV": "RV", "IS": "IS", "BN": "BN"}
                    adformat = adformat_map.get(slot_key, slot_key)
                    default_name = f"{app_name} {os_str} {adformat}"
                    st.session_state[slot_name_key] = default_name
                elif package_name:
                    # Fallback to package name format if app_name is not provided
                    pkg_last_part = package_name.split(".")[-1] if "." in package_name else package_name
                    os_str = "aos" if platform == "android" else "ios"
                    adtype_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                    adtype = adtype_map.get(slot_key, slot_key.lower())
                    default_name = f"{pkg_last_part}_{os_str}_applovin_{adtype}_bidding"
                    st.session_state[slot_name_key] = default_name
                elif slot_name_key not in st.session_state:
                    default_name = f"{slot_key.lower()}_ad_unit"
                    st.session_state[slot_name_key] = default_name
                
                # Update slot name if app_name, package_name, or platform changes
                if app_name:
                    # Priority: app_name format
                    os_str = "AOS" if platform == "android" else "iOS"
                    adformat_map = {"RV": "RV", "IS": "IS", "BN": "BN"}
                    adformat = adformat_map.get(slot_key, slot_key)
                    default_name = f"{app_name} {os_str} {adformat}"
                    st.session_state[slot_name_key] = default_name
                elif package_name:
                    # Fallback to package name format
                    pkg_last_part = package_name.split(".")[-1] if "." in package_name else package_name
                    os_str = "aos" if platform == "android" else "ios"
                    adtype_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                    adtype = adtype_map.get(slot_key, slot_key.lower())
                    default_name = f"{pkg_last_part}_{os_str}_applovin_{adtype}_bidding"
                    st.session_state[slot_name_key] = default_name
                
                slot_name = st.text_input(
                    "Ad Unit Name*",
                    value=st.session_state.get(slot_name_key, ""),
                    key=slot_name_key,
                    help=f"Name for {slot_config['name']} ad unit"
                )
                
                # Display current settings
                st.markdown("**Current Settings:**")
                settings_html = '<div style="min-height: 80px; margin-bottom: 10px;">'
                settings_html += '<ul style="margin: 0; padding-left: 20px;">'
                settings_html += f'<li>Ad Format: {slot_config["ad_format"]}</li>'
                settings_html += f'<li>Platform: {"Android" if platform == "android" else "iOS"}</li>'
                settings_html += f'<li>Package Name: {package_name if package_name else "Not set"}</li>'
                settings_html += '</ul></div>'
                st.markdown(settings_html, unsafe_allow_html=True)
                
                # Create button for AppLovin
                if st.button(f"✅ Create {slot_key} Ad Unit", use_container_width=True, key=f"create_applovin_{slot_key}"):
                    # Validate inputs
                    if not slot_name:
                        st.toast("❌ Ad Unit Name is required", icon="🚫")
                    elif not package_name:
                        st.toast("❌ Package Name is required", icon="🚫")
                    else:
                        # Build payload
                        payload = {
                            "name": slot_name,
                            "platform": platform,
                            "package_name": package_name,
                            "ad_format": slot_config["ad_format"]
                        }
                        
                        # Make API call
                        with st.spinner(f"Creating {slot_key} ad unit..."):
                            try:
                                network_manager = get_network_manager()
                                response = network_manager.create_unit(current_network, payload)
                                
                                if not response:
                                    st.error("❌ No response from API")
                                    SessionManager.log_error(current_network, "No response from API")
                                else:
                                    result = handle_api_response(response)
                                    
                                    if result is not None:
                                        unit_data = {
                                            "slotCode": result.get("id", result.get("adUnitId", "N/A")),
                                            "name": slot_name,
                                            "appCode": package_name,
                                            "slotType": slot_config["ad_format"],
                                            "adType": slot_config["ad_format"],
                                            "auctionType": "N/A"
                                        }
                                        SessionManager.add_created_unit(current_network, unit_data)
                                        
                                        st.success(f"✅ {slot_key} ad unit created successfully!")
                                        st.rerun()
                                    else:
                                        # handle_api_response already displayed error
                                        pass
                            except Exception as e:
                                st.error(f"❌ Error creating {slot_key} ad unit: {str(e)}")
                                SessionManager.log_error(current_network, str(e))
else:
    network_manager = get_network_manager()
    
    # Load apps from cache (from Create App POST responses)
    cached_apps = SessionManager.get_cached_apps(current_network)
    
    # For BigOAds, IronSource, Mintegral, and InMobi, also fetch from API and get latest 3 apps
    api_apps = []
    if current_network in ["bigoads", "ironsource", "mintegral", "inmobi"]:
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
    # For BigOAds, IronSource, Mintegral, and InMobi, prioritize API apps (they are more recent)
    if current_network in ["bigoads", "ironsource", "mintegral", "inmobi"] and api_apps:
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
            # For IronSource, use appKey; for InMobi, use appId or appCode; for others, use appCode
            if current_network == "ironsource":
                app_code = app.get("appKey") or app.get("appCode", "N/A")
            elif current_network == "inmobi":
                app_code = app.get("appId") or app.get("appCode", "N/A")
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
                "app_id": app.get("app_id") or app.get("appId") if current_network in ["mintegral", "inmobi"] else None,  # Store app_id for Mintegral and InMobi
                "name": app_name,
                "platform": platform_num,  # 1 or 2
                "platformStr": platform_str,  # "android" or "ios"
                "pkgName": app.get("pkgName", ""),  # From API response
                "bundleId": app.get("bundleId", "") if current_network in ["ironsource", "inmobi"] else "",  # bundleId for IronSource and InMobi (for placement name generation)
                "storeUrl": store_url,  # Store URL (optional)
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
        
        # If appKey is entered manually, fetch app info from API
        if selected_app_code and current_network == "ironsource":
            try:
                with st.spinner(f"Loading app info for {selected_app_code}..."):
                    # Fetch specific app using appKey as filter
                    fetched_apps = network_manager.get_apps(current_network, app_key=selected_app_code)
                    if fetched_apps:
                        # Add fetched app to apps list if not already present
                        fetched_app = fetched_apps[0]
                        fetched_app_key = fetched_app.get("appKey") or fetched_app.get("appCode")
                        
                        # Check if app already exists in apps list
                        existing_app = None
                        for app in apps:
                            app_identifier = app.get("appKey") if current_network == "ironsource" else app.get("appCode")
                            if app_identifier == fetched_app_key:
                                existing_app = app
                                break
                        
                        if not existing_app:
                            # Add to apps list
                            apps.append(fetched_app)
                            # Update app_options and maps
                            fetched_app_name = fetched_app.get("name", "Unknown")
                            fetched_platform = fetched_app.get("platform", "")
                            display_text = f"{fetched_app_key} ({fetched_app_name})"
                            if fetched_platform and fetched_platform != "N/A":
                                display_text += f" - {fetched_platform}"
                            
                            # Insert at the beginning (before manual entry option)
                            app_options.insert(-1, display_text)
                            app_code_map[display_text] = fetched_app_key
                            
                            # Store app info
                            if current_network == "ironsource":
                                platform_num = fetched_app.get("platformNum", 1 if fetched_platform == "Android" else 2)
                                platform_str = fetched_app.get("platformStr", "android" if fetched_platform == "Android" else "ios")
                                bundle_id = fetched_app.get("bundleId", "")
                                store_url = fetched_app.get("storeUrl", "")
                            else:
                                platform_num = 1 if fetched_platform == "Android" else 2
                                platform_str = "android" if fetched_platform == "Android" else "ios"
                                bundle_id = ""
                                store_url = ""
                            
                            app_info_map[fetched_app_key] = {
                                "appCode": fetched_app_key,
                                "appKey": fetched_app_key if current_network == "ironsource" else None,
                                "name": fetched_app_name,
                                "platform": platform_num,
                                "platformStr": platform_str,
                                "pkgName": fetched_app.get("pkgName", ""),
                                "bundleId": bundle_id,
                                "storeUrl": store_url,
                                "platformDisplay": fetched_platform
                            }
                            
                            st.success(f"✅ Found app: {fetched_app_name}")
                        else:
                            st.info(f"ℹ️ App {fetched_app_key} already in list")
                    else:
                        st.warning(f"⚠️ App with key '{selected_app_code}' not found")
            except Exception as e:
                logger.warning(f"[{current_network}] Failed to fetch app info: {str(e)}")
                st.warning(f"⚠️ Failed to load app info: {str(e)}")
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
            # Get pkgNameDisplay (for BigOAds) or pkgName/bundleId
            if current_network == "bigoads":
                pkg_name = selected_app_data.get("pkgNameDisplay", selected_app_data.get("pkgName", ""))
            elif current_network == "ironsource":
                # IronSource: use bundleId for Mediation Ad Unit Name generation
                pkg_name = selected_app_data.get("bundleId", selected_app_data.get("pkgName", ""))
            else:
                pkg_name = selected_app_data.get("pkgName", "")
            
            # Get platform and normalize it using helper function
            platform_str_val = selected_app_data.get("platform", "")
            platform_str = _normalize_platform_str(platform_str_val, current_network)
            
            # Get bundleId for IronSource
            bundle_id = selected_app_data.get("bundleId", "") if current_network == "ironsource" else None
            
            # Update all slot names immediately when app is selected
            if pkg_name or bundle_id:
                # Get app name from selected_app_data
                app_name_for_slot = selected_app_data.get("name", app_name) if selected_app_data else app_name
                for slot_key in ["rv", "is", "bn"]:
                    slot_name_key = f"custom_slot_{slot_key.upper()}_name"
                    default_name = _generate_slot_name(pkg_name, platform_str, slot_key, current_network, store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
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
                    # Normalize platform using helper function
                    platform_from_app = app.get("platform", "")
                    normalized_platform = _normalize_platform_str(platform_from_app, current_network)
                    
                    app_info_to_use["platformStr"] = normalized_platform
                    app_info_to_use["platform"] = 1 if normalized_platform == "android" else 2
                    
                    # For IronSource, get bundleId, storeUrl and platformStr from API response
                    if current_network == "ironsource":
                        app_info_to_use["bundleId"] = app.get("bundleId", "")
                        app_info_to_use["storeUrl"] = app.get("storeUrl", "")
                        app_info_to_use["platformStr"] = app.get("platformStr", "android")
                        app_info_to_use["platform"] = app.get("platformNum", 1)
                    
                    # For BigOAds, get pkgNameDisplay from API response
                    if current_network == "bigoads" and "pkgNameDisplay" in app:
                        app_info_to_use["pkgNameDisplay"] = app.get("pkgNameDisplay", "")
                    
                    # For Mintegral, get pkgName from API response
                    if current_network == "mintegral":
                        app_info_to_use["pkgName"] = app.get("pkgName", "")
                        app_info_to_use["name"] = app.get("name", app_name)
                    
                    # For InMobi, get bundleId and pkgName from API response
                    if current_network == "inmobi":
                        app_info_to_use["bundleId"] = app.get("bundleId", "")
                        app_info_to_use["pkgName"] = app.get("pkgName", "")
                        app_info_to_use["name"] = app.get("name", app_name)
                    
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
                    # For IronSource, get bundleId, storeUrl from last_app_info
                    if current_network == "ironsource":
                        app_info_to_use["bundleId"] = last_app_info.get("bundleId", app_info_to_use.get("bundleId", ""))
                        app_info_to_use["storeUrl"] = last_app_info.get("storeUrl", "")
                        app_info_to_use["platformStr"] = last_app_info.get("platformStr", "android")
            else:
                # Try to get from apps list
                for app in apps:
                    # For IronSource, check appKey; for InMobi, check appId or appCode; for others, check appCode
                    if current_network == "ironsource":
                        app_identifier = app.get("appKey") or app.get("appCode")
                    elif current_network == "inmobi":
                        app_identifier = app.get("appId") or app.get("appCode")
                    else:
                        app_identifier = app.get("appCode")
                    
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
                            "app_id": app.get("app_id") or app.get("appId") if current_network in ["mintegral", "inmobi"] else None,
                            "name": app.get("name", "Unknown"),
                            "platform": platform_num,
                            "platformStr": platform_str_val,
                            "storeUrl": store_url,
                            "pkgName": "",
                            "pkgNameDisplay": app.get("pkgNameDisplay", "") if current_network == "bigoads" else "",
                            "bundleId": app.get("bundleId", "") if current_network in ["ironsource", "inmobi"] else "",
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
        
        # Default slot configurations for InMobi
        slot_configs_inmobi = {
            "RV": {
                "name": "Rewarded Video",
                "placementType": "REWARDED_VIDEO",
                "isAudienceBiddingEnabled": True,
                "audienceBiddingPartner": "MAX",
            },
            "IS": {
                "name": "Interstitial",
                "placementType": "INTERSTITIAL",
                "isAudienceBiddingEnabled": True,
                "audienceBiddingPartner": "MAX",
            },
            "BN": {
                "name": "Banner",
                "placementType": "BANNER",
                "isAudienceBiddingEnabled": True,
                "audienceBiddingPartner": "MAX",
            }
        }
        
        # Default slot configurations for Fyber (DT)
        slot_configs_fyber = {
            "RV": {
                "name": "Rewarded",
                "placementType": "Rewarded",
                "coppa": False,
            },
            "IS": {
                "name": "Interstitial",
                "placementType": "Interstitial",
                "coppa": False,
            },
            "BN": {
                "name": "Banner",
                "placementType": "Banner",
                "coppa": False,
            }
        }
        
        # Select configs based on network
        if current_network == "ironsource":
            slot_configs = slot_configs_ironsource
        elif current_network == "pangle":
            slot_configs = slot_configs_pangle
        elif current_network == "mintegral":
            slot_configs = slot_configs_mintegral
        elif current_network == "inmobi":
            slot_configs = slot_configs_inmobi
        elif current_network == "fyber":
            slot_configs = slot_configs_fyber
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
                            
                            # Generate default name from Store URL if available (only when app is first selected)
                            # Use a flag to track if name was auto-generated to avoid overwriting user edits
                            auto_gen_flag_key = f"{slot_name_key}_auto_generated"
                            
                            if selected_app_code and app_info_to_use:
                                # Only auto-generate if name hasn't been set yet or was previously auto-generated
                                if slot_name_key not in st.session_state or st.session_state.get(auto_gen_flag_key, False):
                                    bundle_id = app_info_to_use.get("bundleId", "")
                                    platform_str = app_info_to_use.get("platformStr", "android")
                                    app_name_for_slot = app_info_to_use.get("name", app_name)
                                    if bundle_id:
                                        # Map slot_key to slot_type
                                        slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                                        slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                        default_name = _generate_slot_name(bundle_id, platform_str, slot_type, "ironsource", store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                                        st.session_state[slot_name_key] = default_name
                                        st.session_state[auto_gen_flag_key] = True
                                    elif slot_name_key not in st.session_state:
                                        default_name = f"{slot_key.lower()}-1"
                                        st.session_state[slot_name_key] = default_name
                                        st.session_state[auto_gen_flag_key] = True
                            elif slot_name_key not in st.session_state:
                                default_name = f"{slot_key.lower()}-1"
                                st.session_state[slot_name_key] = default_name
                                st.session_state[auto_gen_flag_key] = True
                            
                            # Track if user manually edits the name (clear auto-generated flag)
                            # Only auto-generate if flag is True (meaning it was auto-generated before)
                            mediation_ad_unit_name = st.text_input(
                                "Mediation Ad Unit Name*",
                                value=st.session_state.get(slot_name_key, ""),
                                key=slot_name_key,
                                help=f"Name for {slot_config['name']} placement"
                            )
                            
                            # If user edits the name manually, clear the auto-generated flag
                            # This prevents re-generation when app code is re-selected
                            if mediation_ad_unit_name:
                                # Check if this is a manual edit (different from auto-generated value)
                                if selected_app_code and app_info_to_use:
                                    bundle_id = app_info_to_use.get("bundleId", "")
                                    if bundle_id:
                                        platform_str = app_info_to_use.get("platformStr", "android")
                                        app_name_for_slot = app_info_to_use.get("name", app_name)
                                        slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                                        slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                        expected_name = _generate_slot_name(bundle_id, platform_str, slot_type, "ironsource", store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                                        if mediation_ad_unit_name != expected_name:
                                            # User has manually edited, clear auto-generated flag
                                            st.session_state[auto_gen_flag_key] = False
                            
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
                                        
                                                if result is not None and isinstance(result, dict):
                                                    # Check if result has any data (empty dict is also valid for some networks like Mintegral)
                                                    slot_code = result.get("adUnitId") or result.get("id") or result.get("placement_id") or result.get("placementId")
                                                    
                                                    if slot_code or not result:  # If has slot_code or empty dict (valid success response)
                                                        if slot_code:  # Only add to cache if we have slot_code
                                                            unit_data = {
                                                                "slotCode": slot_code,
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
                                                    else:
                                                        # Empty dict but no slot_code - this is a valid success response (e.g., Mintegral)
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
                            
                            # Generate placement name using unified function
                            if selected_app_code and app_info_to_use:
                                pkg_name = app_info_to_use.get("pkgName", "")
                                platform_str = app_info_to_use.get("platformStr", "android")
                                app_name_for_slot = app_info_to_use.get("name", app_name)
                                
                                if pkg_name:
                                    default_name = _generate_slot_name(pkg_name, platform_str, slot_key.lower(), "pangle", network_manager=network_manager, app_name=app_name_for_slot)
                                    if slot_name_key not in st.session_state:
                                        st.session_state[slot_name_key] = default_name
                            elif slot_name_key not in st.session_state:
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
                            
                            # Generate placement name using unified function
                            if selected_app_code:
                                # Get pkg_name and platform_str from app_info_to_use or apps list
                                pkg_name = ""
                                platform_str = "android"
                                app_name_for_slot = app_name
                                
                                if app_info_to_use:
                                    pkg_name = app_info_to_use.get("pkgName", "")
                                    platform_str = app_info_to_use.get("platformStr", "android")
                                    app_name_for_slot = app_info_to_use.get("name", app_name)
                                
                                # If not found in app_info_to_use, try to get from apps list directly
                                if not pkg_name or not platform_str or platform_str == "unknown":
                                    for app in apps:
                                        app_identifier = app.get("appCode")
                                        if app_identifier == selected_app_code:
                                            if not pkg_name:
                                                pkg_name = app.get("pkgName", "")
                                            if not platform_str or platform_str == "unknown":
                                                platform_from_app = app.get("platform", "")
                                                platform_str = _normalize_platform_str(platform_from_app, "mintegral")
                                            if not app_name_for_slot or app_name_for_slot == app_name:
                                                app_name_for_slot = app.get("name", app_name)
                                            break
                                
                                # Normalize platform_str (ensure it's "android" or "ios")
                                platform_str = _normalize_platform_str(platform_str, "mintegral")
                                
                                if pkg_name:
                                    default_name = _generate_slot_name(pkg_name, platform_str, slot_key.lower(), "mintegral", network_manager=network_manager, app_name=app_name_for_slot)
                                    # Always update when app is selected (even if key exists) - same as RV, IS, BN
                                    st.session_state[placement_name_key] = default_name
                                elif placement_name_key not in st.session_state:
                                    default_name = f"{slot_key.lower()}_placement"
                                    st.session_state[placement_name_key] = default_name
                            elif placement_name_key not in st.session_state:
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
                        elif current_network == "inmobi":
                            # InMobi: appId, placementName, placementType, isAudienceBiddingEnabled, audienceBiddingPartner
                            placement_name_key = f"inmobi_slot_{slot_key}_name"
                            
                            # Get appId from selected app (required)
                            app_id = None
                            if selected_app_code:
                                # Try to get from app_info_to_use first
                                if app_info_to_use:
                                    app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId")
                                
                                # If not found, try to parse from selected_app_code
                                if not app_id:
                                    try:
                                        app_id = int(selected_app_code)
                                    except (ValueError, TypeError):
                                        app_id = None
                                
                                # If still not found, try to get from apps list
                                if not app_id:
                                    for app in apps:
                                        app_identifier = app.get("appId") or app.get("appCode")
                                        if str(app_identifier) == str(selected_app_code):
                                            app_id = app.get("appId") or app.get("app_id")
                                            if not app_id:
                                                try:
                                                    app_id = int(app_identifier)
                                                except (ValueError, TypeError):
                                                    app_id = None
                                            break
                            
                            # Generate placement name using unified function
                            if selected_app_code:
                                # Always get bundle_id, pkg_name and platform_str from apps list directly (most reliable)
                                bundle_id = ""
                                pkg_name = ""
                                platform_str = "android"
                                app_name_for_slot = app_name
                                
                                # Get from apps list directly (most reliable source)
                                for app in apps:
                                    app_identifier = app.get("appId") or app.get("appCode")
                                    if str(app_identifier) == str(selected_app_code):
                                        bundle_id = app.get("bundleId", "")
                                        pkg_name = app.get("pkgName", "")
                                        platform_from_app = app.get("platform", "")
                                        platform_str = _normalize_platform_str(platform_from_app, "inmobi")
                                        app_name_for_slot = app.get("name", app_name)
                                        break
                                
                                # Fallback to app_info_to_use if not found in apps list
                                if (not bundle_id and not pkg_name) or not platform_str or platform_str == "unknown":
                                    if app_info_to_use:
                                        if not bundle_id:
                                            bundle_id = app_info_to_use.get("bundleId", "")
                                        if not pkg_name:
                                            pkg_name = app_info_to_use.get("pkgName", "")
                                        if not platform_str or platform_str == "unknown":
                                            platform_str_from_info = app_info_to_use.get("platformStr", "android")
                                            platform_str = _normalize_platform_str(platform_str_from_info, "inmobi")
                                        if not app_name_for_slot or app_name_for_slot == app_name:
                                            app_name_for_slot = app_info_to_use.get("name", app_name)
                                
                                # Normalize platform_str one more time to ensure correctness
                                platform_str = _normalize_platform_str(platform_str, "inmobi")
                                
                                # Use bundleId if available, otherwise use pkgName
                                source_pkg = bundle_id if bundle_id else pkg_name
                                
                                if source_pkg:
                                    slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                                    slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                    default_name = _generate_slot_name(source_pkg, platform_str, slot_type, "inmobi", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                                    # Always update when app is selected (even if key exists) - same as RV, IS, BN
                                    st.session_state[placement_name_key] = default_name
                            elif placement_name_key not in st.session_state:
                                default_name = f"{slot_key.lower()}-placement-1"
                                st.session_state[placement_name_key] = default_name
                            
                            placement_name = st.text_input(
                                "Placement Name*",
                                value=st.session_state[placement_name_key],
                                key=placement_name_key,
                                help=f"Name for {slot_config['name']} placement"
                            )
                            
                            # Display current settings
                            st.markdown("**Current Settings:**")
                            settings_html = '<div style="min-height: 120px; margin-bottom: 10px;">'
                            settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
                            settings_html += f'<li>Placement Type: {slot_config["placementType"].replace("_", " ").title()}</li>'
                            settings_html += f'<li>Audience Bidding: {"Enabled" if slot_config["isAudienceBiddingEnabled"] else "Disabled"}</li>'
                            if slot_config["isAudienceBiddingEnabled"]:
                                settings_html += f'<li>Audience Bidding Partner: {slot_config["audienceBiddingPartner"]}</li>'
                            settings_html += '</ul></div>'
                            st.markdown(settings_html, unsafe_allow_html=True)
                            
                            # Create button for InMobi
                            if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_inmobi_{slot_key}"):
                                if not selected_app_code:
                                    st.toast("❌ Please select an App Code", icon="🚫")
                                elif not app_id or app_id <= 0:
                                    st.toast("❌ App ID is required. Please select an App Code.", icon="🚫")
                                elif not placement_name:
                                    st.toast("❌ Placement Name is required", icon="🚫")
                                else:
                                    # Build payload for InMobi
                                    payload = {
                                        "appId": int(app_id),
                                        "placementName": placement_name,
                                        "placementType": slot_config["placementType"],
                                        "isAudienceBiddingEnabled": slot_config["isAudienceBiddingEnabled"],
                                    }
                                    
                                    # Add audienceBiddingPartner if Audience Bidding is enabled
                                    if slot_config["isAudienceBiddingEnabled"]:
                                        payload["audienceBiddingPartner"] = slot_config["audienceBiddingPartner"]
                                    
                                    # Make API call
                                    with st.spinner(f"Creating {slot_key} placement..."):
                                        try:
                                            response = network_manager.create_unit(current_network, payload)
                                            result = handle_api_response(response)
                                            
                                            if result:
                                                unit_data = {
                                                    "slotCode": result.get("placementId", result.get("id", "N/A")),
                                                    "name": placement_name,
                                                    "appCode": str(app_id),
                                                    "slotType": slot_config["placementType"],
                                                    "adType": slot_config["placementType"],
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
                        elif current_network == "fyber":
                            # Fyber: name, appId, placementType, coppa
                            placement_name_key = f"fyber_slot_{slot_key}_name"
                            
                            # Get appId from selected app (required)
                            app_id = None
                            if selected_app_code:
                                # Try to get from app_info_to_use first
                                if app_info_to_use:
                                    app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId")
                                
                                # If not found, try to get from apps list
                                if not app_id:
                                    for app in apps:
                                        app_identifier = app.get("appId") or app.get("appCode")
                                        if str(app_identifier) == str(selected_app_code):
                                            app_id = app.get("appId") or app.get("app_id")
                                            if not app_id:
                                                try:
                                                    app_id = int(app_identifier)
                                                except (ValueError, TypeError):
                                                    app_id = None
                                            break
                                
                                # If still not found, use selected_app_code directly (manual entry)
                                # This handles the case when user enters app code manually
                                if not app_id:
                                    try:
                                        app_id = int(selected_app_code)
                                    except (ValueError, TypeError):
                                        app_id = None
                            
                            # Generate placement name using unified function
                            if placement_name_key not in st.session_state:
                                if selected_app_code and app_info_to_use:
                                    bundle_id = app_info_to_use.get("bundleId", "")
                                    pkg_name = app_info_to_use.get("pkgName", "")
                                    platform_str = app_info_to_use.get("platformStr", "android")
                                    app_name_for_slot = app_info_to_use.get("name", app_name)
                                    
                                    # Use bundleId if available, otherwise use pkgName
                                    source_pkg = bundle_id if bundle_id else pkg_name
                                    
                                    if source_pkg:
                                        slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                                        slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                        default_name = _generate_slot_name(source_pkg, platform_str, slot_type, "fyber", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                                        st.session_state[placement_name_key] = default_name
                                else:
                                    default_name = f"{slot_key.lower()}_placement"
                                    st.session_state[placement_name_key] = default_name
                            
                            placement_name = st.text_input(
                                "Placement Name*",
                                value=st.session_state.get(placement_name_key, ""),
                                key=placement_name_key,
                                help=f"Name for {slot_config['name']} placement"
                            )
                            
                            # Display current settings
                            st.markdown("**Current Settings:**")
                            settings_html = '<div style="min-height: 80px; margin-bottom: 10px;">'
                            settings_html += '<ul style="margin: 0; padding-left: 20px;">'
                            settings_html += f'<li>Placement Type: {slot_config["placementType"]}</li>'
                            settings_html += f'<li>COPPA: {"No" if not slot_config["coppa"] else "Yes"}</li>'
                            settings_html += '</ul></div>'
                            st.markdown(settings_html, unsafe_allow_html=True)
                            
                            # Show app ID info
                            if app_id:
                                st.info(f"📱 App ID: {app_id}")
                            elif selected_app_code:
                                st.warning(f"⚠️ App ID not found. Will use entered code: {selected_app_code}")
                            
                            # Create button for Fyber
                            if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_fyber_{slot_key}"):
                                if not placement_name:
                                    st.toast("❌ Placement Name is required", icon="🚫")
                                elif not selected_app_code:
                                    st.toast("❌ App Code is required. Please select an app or enter manually.", icon="🚫")
                                else:
                                    # Ensure app_id is set (try parsing selected_app_code if app_id is still None)
                                    if not app_id or app_id <= 0:
                                        try:
                                            app_id = int(selected_app_code)
                                        except (ValueError, TypeError):
                                            st.toast("❌ Invalid App ID. Please enter a valid numeric App ID.", icon="🚫")
                                            app_id = None
                                    
                                    if not app_id or app_id <= 0:
                                        st.toast("❌ App ID is required. Please select an app or enter a valid App ID.", icon="🚫")
                                    else:
                                        # Build payload for Fyber
                                        # Ensure appId is properly set as string (API expects string)
                                        payload = {
                                            "name": placement_name.strip(),
                                            "appId": str(app_id),  # Must be string, not integer
                                            "placementType": slot_config["placementType"],
                                            "coppa": bool(slot_config["coppa"]),  # Must be boolean, not string
                                        }
                                        
                                        # Debug: Log payload to verify appId is included
                                        logger.info(f"[Fyber] Creating placement - appId: {app_id}, payload: {payload}")
                                        
                                        # Make API call
                                        with st.spinner(f"Creating {slot_key} placement..."):
                                            try:
                                                response = network_manager.create_unit(current_network, payload)
                                                # handle_api_response displays the response automatically
                                                result = handle_api_response(response)
                                                
                                                if result:
                                                    unit_data = {
                                                        "slotCode": result.get("id", result.get("placementId", "N/A")),
                                                        "name": placement_name,
                                                        "appCode": str(app_id),
                                                        "slotType": slot_config["placementType"],
                                                        "adType": slot_config["placementType"],
                                                        "auctionType": "N/A"
                                                    }
                                                    SessionManager.add_created_unit(current_network, unit_data)
                                                    
                                                    # Add to cache
                                                    cached_units = SessionManager.get_cached_units(current_network, str(app_id))
                                                    if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                        cached_units.append(unit_data)
                                                        SessionManager.cache_units(current_network, str(app_id), cached_units)
                                                    
                                                    # Note: handle_api_response already displayed success message and response
                                                    # Don't rerun immediately to let user see the response
                                                    # Add a refresh button if needed
                                                    if st.button("🔄 Refresh Page", key=f"refresh_after_{slot_key}", use_container_width=True):
                                                        st.rerun()
                                                else:
                                                    # If result is None, handle_api_response already displayed the error
                                                    # Don't rerun on error - let user see the error message
                                                    pass
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
                                # Get bundleId if available (for networks that use it)
                                bundle_id = app_info_to_use.get("bundleId", "") if app_info_to_use else ""
                                app_name_for_slot = app_info_to_use.get("name", app_name) if app_info_to_use else app_name
                                default_name = _generate_slot_name(pkg_name, platform_str, slot_key.lower(), current_network, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
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
                                    payload["bannerSize"] = slot_config['bannerSize']  # Numeric value (1 or 2) for API
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
