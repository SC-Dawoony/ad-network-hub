"""App Code selector component for Create Unit"""
import streamlit as st
import logging
from utils.session_manager import SessionManager
from utils.network_manager import get_network_manager
from components.create_app_helpers import normalize_platform_str, generate_slot_name

logger = logging.getLogger(__name__)


def render_app_code_selector(current_network: str, network_manager):
    """Render App Code selector UI and return selected app code and related info
    
    Args:
        current_network: Current network identifier
        network_manager: Network manager instance
    
    Returns:
        tuple: (selected_app_code, app_name, app_info_to_use, apps, app_info_map)
    """
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
    
    # Unity network doesn't need App Code selection
    if current_network == "unity":
        selected_app_code = None
        selected_app_display = None
        app_name = "Unity Project"
    else:
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
            platform_str = normalize_platform_str(platform_str_val, current_network)
            
            # Get bundleId for IronSource
            bundle_id = selected_app_data.get("bundleId", "") if current_network == "ironsource" else None
            
            # Update all slot names immediately when app is selected
            if pkg_name or bundle_id:
                # Get app name from selected_app_data
                app_name_for_slot = selected_app_data.get("name", app_name) if selected_app_data else app_name
                for slot_key in ["rv", "is", "bn"]:
                    slot_name_key = f"custom_slot_{slot_key.upper()}_name"
                    default_name = generate_slot_name(pkg_name, platform_str, slot_key, current_network, store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                    st.session_state[slot_name_key] = default_name
    
    # Get app info for quick create all
    app_info_to_use = None
    if selected_app_code:
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
                        normalized_platform = normalize_platform_str(platform_from_app, current_network)
                        
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
    
    return selected_app_code, app_name, app_info_to_use, apps, app_info_map

