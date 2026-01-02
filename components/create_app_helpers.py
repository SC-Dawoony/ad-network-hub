"""Helper functions for Create App & Unit page"""
import logging

logger = logging.getLogger(__name__)


def extract_package_name_from_store_url(store_url: str) -> str:
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


def normalize_platform_str(platform_value: str, network: str = None) -> str:
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


def get_bigoads_pkg_name_display(pkg_name: str, bundle_id: str, network_manager, app_name: str = None, platform_str: str = None) -> str:
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
                            # Extract last part and convert to lowercase for consistency
                            if app_pkg_name_display:
                                if "." in app_pkg_name_display:
                                    last_part = app_pkg_name_display.split(".")[-1].lower()
                                    return last_part
                                return app_pkg_name_display.lower()
                            elif app_pkg_name:
                                if "." in app_pkg_name:
                                    last_part = app_pkg_name.split(".")[-1].lower()
                                    return last_part
                                return app_pkg_name.lower()
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
                    # Extract last part and convert to lowercase for consistency
                    if app_pkg_name_display:
                        if "." in app_pkg_name_display:
                            last_part = app_pkg_name_display.split(".")[-1].lower()
                            return last_part
                        return app_pkg_name_display.lower()
                    break
    except Exception as e:
        logger.warning(f"Failed to fetch BigOAds apps for pkgNameDisplay lookup: {str(e)}")
    
    # Fallback: if it's an iTunes ID, return empty to avoid using it
    if is_itunes_id:
        return ""
    
    # Fallback: return original pkg_name or bundle_id for valid package names
    # Extract last part and convert to lowercase for consistency
    if "." in search_key:
        last_part = search_key.split(".")[-1].lower()
        return last_part
    return search_key.lower()


def generate_slot_name(pkg_name: str, platform_str: str, slot_type: str, network: str = "bigoads", store_url: str = None, bundle_id: str = None, network_manager=None, app_name: str = None) -> str:
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
    # If pkg_name is empty, use bundle_id as fallback
    source_pkg_name = pkg_name if pkg_name else (bundle_id if bundle_id else "")
    final_pkg_name = source_pkg_name
    
    if network_manager and (pkg_name or bundle_id):
        bigoads_pkg = get_bigoads_pkg_name_display(pkg_name, bundle_id, network_manager, app_name, platform_str)
        if bigoads_pkg:
            final_pkg_name = bigoads_pkg
        elif not bigoads_pkg and source_pkg_name and source_pkg_name.startswith("id") and source_pkg_name[2:].isdigit():
            # iTunes ID but couldn't find Android version - this should not happen if app_name is provided
            # Return empty to avoid using iTunes ID
            logger.warning(f"Could not find package name for iTunes ID: {source_pkg_name}. App name: {app_name}")
            return ""
        elif not bigoads_pkg and bundle_id and not pkg_name:
            # If pkg_name was empty but bundle_id exists, use bundle_id
            final_pkg_name = bundle_id
    
    # If final_pkg_name is still empty, return empty string
    if not final_pkg_name:
        logger.warning(f"Could not generate slot name: pkg_name={pkg_name}, bundle_id={bundle_id}")
        return ""
    
    # Extract last part after "."
    if "." in final_pkg_name:
        last_part = final_pkg_name.split(".")[-1]
    else:
        last_part = final_pkg_name
    
    # For IronSource and InMobi, ALWAYS convert last_part to lowercase (whether from pkg_name, bundle_id, or BigOAds pkgNameDisplay)
    # This ensures consistent lowercase naming for IronSource and InMobi ad units
    if network.lower() in ["ironsource", "inmobi"]:
        last_part = last_part.lower()
        # Double-check: ensure it's actually lowercase (defensive programming)
        if last_part != last_part.lower():
            logger.warning(f"{network}: last_part was not lowercase: {last_part}, forcing lowercase")
            last_part = last_part.lower()
    
    # Normalize platform_str first, then map to os: Android -> aos, iOS -> ios
    normalized_platform = normalize_platform_str(platform_str, network)
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


def create_default_slot(network: str, app_info: dict, slot_type: str, network_manager, config):
    """Create a default slot with predefined settings"""
    import streamlit as st
    from utils.network_manager import handle_api_response
    from utils.session_manager import SessionManager
    
    app_code = app_info.get("appCode")
    platform_str = app_info.get("platformStr", "android")
    
    # Get package name (prefer BigOAds pkgNameDisplay via unified function)
    pkg_name = app_info.get("pkgName", "")
    bundle_id = app_info.get("bundleId", "")
    app_name = app_info.get("name", "")
    
    # Generate slot name using unified function (will automatically use BigOAds pkgNameDisplay if available)
    slot_name = generate_slot_name(pkg_name, platform_str, slot_type, network, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name)
    
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

