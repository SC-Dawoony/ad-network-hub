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
    
    # For IronSource and BigOAds, use Create App response as default (no auto API call)
    # For other networks (Mintegral, InMobi), fetch from API automatically
    api_apps = []
    if current_network in ["mintegral", "inmobi"]:
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
    
    # For IronSource and BigOAds, add manual "조회" button to fetch apps from API
    if current_network in ["ironsource", "bigoads"]:
        # Check if user wants to fetch apps from API
        fetch_apps_key = f"{current_network}_fetch_apps_from_api"
        api_apps_key = f"{current_network}_api_apps"
        
        if fetch_apps_key not in st.session_state:
            st.session_state[fetch_apps_key] = False
        if api_apps_key not in st.session_state:
            st.session_state[api_apps_key] = []
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("💡 **Tip:** Create App에서 생성한 앱이 기본값으로 표시됩니다. API에서 최근 앱을 조회하려면 버튼을 클릭하세요.")
        with col2:
            if st.button("🔍 최근 생성한 App 조회", use_container_width=True, key=f"{current_network}_fetch_apps_btn"):
                st.session_state[fetch_apps_key] = True
        
        # Fetch apps from API if button was clicked
        if st.session_state[fetch_apps_key]:
            try:
                with st.spinner("Loading apps from API..."):
                    fetched_apps = network_manager.get_apps(current_network)
                    if fetched_apps:
                        st.session_state[api_apps_key] = fetched_apps
                        st.success(f"✅ Loaded {len(fetched_apps)} apps from API")
                    else:
                        st.session_state[api_apps_key] = []
                    # Reset the flag after fetching
                    st.session_state[fetch_apps_key] = False
            except Exception as e:
                logger.warning(f"[{current_network}] Failed to load apps from API: {str(e)}")
                st.error(f"❌ Failed to load apps: {str(e)}")
                st.session_state[api_apps_key] = []
                st.session_state[fetch_apps_key] = False
        
        # Use stored API apps
        api_apps = st.session_state[api_apps_key]
    
    # Merge cached apps with API apps
    # For IronSource and BigOAds, prioritize cached apps (from Create App response)
    if current_network in ["ironsource", "bigoads"]:
        # Use cached apps first (from Create App response)
        apps = cached_apps.copy() if cached_apps else []
        # Add API apps that are not in cache
        if api_apps:
            if current_network == "ironsource":
                cached_app_keys = {app.get("appKey") or app.get("appCode") for app in apps if app.get("appKey") or app.get("appCode")}
                for api_app in api_apps:
                    api_key = api_app.get("appKey") or api_app.get("appCode")
                    if api_key and api_key not in cached_app_keys:
                        apps.append(api_app)
            elif current_network == "bigoads":
                cached_app_codes = {app.get("appCode") for app in apps if app.get("appCode")}
                for api_app in api_apps:
                    api_code = api_app.get("appCode")
                    if api_code and api_code not in cached_app_codes:
                        apps.append(api_app)
    elif current_network in ["mintegral", "inmobi"] and api_apps:
        # For other networks, prioritize API apps (they are more recent)
        apps = api_apps.copy()
        # For BigOAds, check appCode
        if current_network == "bigoads":
            api_app_codes = {app.get("appCode") for app in api_apps if app.get("appCode")}
            if cached_apps:
                for cached_app in cached_apps:
                    cached_code = cached_app.get("appCode")
                    if cached_code and cached_code not in api_app_codes:
                        apps.append(cached_app)
        else:  # Mintegral, InMobi
            api_app_ids = {app.get("appId") or app.get("appCode") for app in api_apps if app.get("appId") or app.get("appCode")}
            if cached_apps:
                for cached_app in cached_apps:
                    cached_id = cached_app.get("appId") or cached_app.get("appCode")
                    if cached_id and cached_id not in api_app_ids:
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
    
    # For IronSource, group apps by name (to show iOS + Android together)
    if current_network == "ironsource":
        # Group apps by name
        apps_by_name = {}
        for app in apps:
            app_name = app.get("name", "Unknown")
            app_key = app.get("appKey") or app.get("appCode", "N/A")
            platform = app.get("platform", "")
            
            if app_name not in apps_by_name:
                apps_by_name[app_name] = {
                    "android": None,
                    "ios": None,
                    "android_app_key": None,
                    "ios_app_key": None
                }
            
            if platform == "Android":
                apps_by_name[app_name]["android"] = app
                apps_by_name[app_name]["android_app_key"] = app_key
            elif platform == "iOS":
                apps_by_name[app_name]["ios"] = app
                apps_by_name[app_name]["ios_app_key"] = app_key
        
        # Create display options grouped by app name
        for app_name, app_data in apps_by_name.items():
            has_android = app_data["android"] is not None
            has_ios = app_data["ios"] is not None
            
            if has_android and has_ios:
                # Both platforms available
                display_text = f"{app_name} (Android + iOS)"
                app_options.append(display_text)
                # Store both appKeys (use app name as key)
                app_code_map[display_text] = app_name  # Use app name as identifier
                app_info_map[app_name] = {
                    "appCode": app_name,
                    "appKey": app_data["android_app_key"],  # Android appKey (primary)
                    "appKeyIOS": app_data["ios_app_key"],  # iOS appKey
                    "name": app_name,
                    "platform": "both",
                    "platformStr": "both",
                    "hasAndroid": True,
                    "hasIOS": True,
                    "androidApp": app_data["android"],
                    "iosApp": app_data["ios"]
                }
            elif has_android:
                # Android only
                display_text = f"{app_name} (Android)"
                app_options.append(display_text)
                app_code_map[display_text] = app_data["android_app_key"]
                app_info_map[app_data["android_app_key"]] = {
                    "appCode": app_data["android_app_key"],
                    "appKey": app_data["android_app_key"],
                    "name": app_name,
                    "platform": 1,
                    "platformStr": "android",
                    "hasAndroid": True,
                    "hasIOS": False,
                    "androidApp": app_data["android"]
                }
            elif has_ios:
                # iOS only
                display_text = f"{app_name} (iOS)"
                app_options.append(display_text)
                app_code_map[display_text] = app_data["ios_app_key"]
                app_info_map[app_data["ios_app_key"]] = {
                    "appCode": app_data["ios_app_key"],
                    "appKey": app_data["ios_app_key"],
                    "appKeyIOS": app_data["ios_app_key"],
                    "name": app_name,
                    "platform": 2,
                    "platformStr": "ios",
                    "hasAndroid": False,
                    "hasIOS": True,
                    "iosApp": app_data["ios"]
                }
    else:
        # For other networks, use original logic
        if apps:
            for app in apps:
                # For InMobi, use appId or appCode; for others, use appCode
                if current_network == "inmobi":
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
                # Use normalize_platform_str to handle different platform formats (e.g., "ANDROID", "IOS" for Mintegral)
                platform_str = normalize_platform_str(platform, current_network)
                platform_num = 1 if platform_str == "android" else 2
                store_url = ""
                
                app_info_map[app_code] = {
                    "appCode": app_code,
                    "app_id": app.get("app_id") or app.get("appId") if current_network in ["mintegral", "inmobi"] else None,
                    "name": app_name,
                    "platform": platform_num,
                    "platformStr": platform_str,
                    "pkgName": app.get("pkgName", ""),
                    "bundleId": app.get("bundleId", "") if current_network == "inmobi" else "",
                    "storeUrl": store_url,
                    "platformDisplay": platform
                }
                # For BigOAds, add pkgNameDisplay
                if current_network == "bigoads":
                    app_info_map[app_code]["pkgNameDisplay"] = app.get("pkgNameDisplay", "")
    
    # Always add "Manual Entry" option (even if apps exist)
    manual_entry_option = "✏️ Enter manually"
    app_options.append(manual_entry_option)
    
    # Get last created app code and info (from Create App response)
    last_created_app_code = SessionManager.get_last_created_app_code(current_network)
    last_app_info = SessionManager.get_last_created_app_info(current_network)
    
    # For IronSource, if last_app_info exists and has both platforms, add it to options if not already present
    if current_network == "ironsource" and last_app_info:
        last_app_name = last_app_info.get("name", "")
        if last_app_name:
            # Check if this app is already in app_options
            app_already_in_list = False
            for opt in app_options:
                if opt.startswith(last_app_name + " ("):
                    app_already_in_list = True
                    break
            
            # If not in list, add it at the beginning (highest priority)
            if not app_already_in_list:
                has_android = last_app_info.get("hasAndroid", False)
                has_ios = last_app_info.get("hasIOS", False)
                
                if has_android and has_ios:
                    display_text = f"{last_app_name} (Android + iOS)"
                    app_options.insert(0, display_text)
                    app_code_map[display_text] = last_app_name
                    # Add to app_info_map if not already there
                    if last_app_name not in app_info_map:
                        app_info_map[last_app_name] = {
                            "appCode": last_app_name,
                            "appKey": last_app_info.get("appKey"),
                            "appKeyIOS": last_app_info.get("appKeyIOS"),
                            "name": last_app_name,
                            "platform": "both",
                            "platformStr": "both",
                            "hasAndroid": True,
                            "hasIOS": True,
                            "androidApp": None,  # Will be filled from cache if available
                            "iosApp": None
                        }
                elif has_android:
                    display_text = f"{last_app_name} (Android)"
                    app_options.insert(0, display_text)
                    app_code_map[display_text] = last_app_info.get("appKey")
                elif has_ios:
                    display_text = f"{last_app_name} (iOS)"
                    app_options.insert(0, display_text)
                    app_code_map[display_text] = last_app_info.get("appKeyIOS")
    
    # If no apps, default to manual entry
    if not apps and not (current_network == "ironsource" and last_app_info):
        default_index = 0  # Manual entry will be the only option
        st.info("💡 No apps found. You can enter App Code manually below.")
    else:
        # Find default selection index
        default_index = 0
        if last_created_app_code:
            # For IronSource, try to find by app name first
            if current_network == "ironsource":
                for idx, opt in enumerate(app_options):
                    if opt.startswith(last_created_app_code + " ("):
                        default_index = idx
                        break
            else:
                # For other networks, try to find the last created app in the list
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
        
        # If appKey/appId is entered manually, fetch app info from API
        if selected_app_code:
            if current_network == "ironsource":
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
            elif current_network == "fyber":
                try:
                    # Try to parse app_id from entered code
                    app_id = None
                    try:
                        app_id = int(selected_app_code)
                    except (ValueError, TypeError):
                        # Try to extract numeric part
                        import re
                        numeric_match = re.search(r'\d+', str(selected_app_code))
                        if numeric_match:
                            app_id = int(numeric_match.group())
                    
                    if app_id:
                        with st.spinner(f"Loading app info for App ID {app_id}..."):
                            # Fetch specific app using appId
                            # For Fyber, pass app_id as app_key (get_apps will parse it)
                            fetched_apps = network_manager.get_apps(current_network, app_key=str(app_id))
                            if fetched_apps:
                                # Add fetched app to apps list if not already present
                                fetched_app = fetched_apps[0]
                                fetched_app_id = fetched_app.get("appId") or fetched_app.get("id") or str(app_id)
                                
                                # Check if app already exists in apps list
                                existing_app = None
                                for app in apps:
                                    app_identifier = app.get("appId") or app.get("appCode") or app.get("id")
                                    if str(app_identifier) == str(fetched_app_id):
                                        existing_app = app
                                        break
                                
                                if not existing_app:
                                    # Add to apps list
                                    apps.append(fetched_app)
                                    # Update app_options and maps
                                    fetched_app_name = fetched_app.get("name", "Unknown")
                                    fetched_platform = fetched_app.get("platform", "")
                                    fetched_bundle = fetched_app.get("bundle") or fetched_app.get("bundleId", "")
                                    display_text = f"{fetched_app_id} ({fetched_app_name})"
                                    if fetched_platform and fetched_platform != "N/A":
                                        display_text += f" - {fetched_platform}"
                                    
                                    # Insert at the beginning (before manual entry option)
                                    app_options.insert(-1, display_text)
                                    app_code_map[display_text] = str(fetched_app_id)
                                    
                                    # Store app info
                                    platform_num = 1 if fetched_platform.lower() == "android" else 2
                                    platform_str = "android" if fetched_platform.lower() == "android" else "ios"
                                    
                                    app_info_map[str(fetched_app_id)] = {
                                        "appCode": str(fetched_app_id),
                                        "app_id": fetched_app_id,
                                        "appId": fetched_app_id,
                                        "name": fetched_app_name,
                                        "platform": platform_num,
                                        "platformStr": platform_str,
                                        "pkgName": fetched_bundle,
                                        "bundleId": fetched_bundle,
                                        "bundle": fetched_bundle,
                                        "storeUrl": "",
                                        "platformDisplay": fetched_platform
                                    }
                                    
                                    st.success(f"✅ Found app: {fetched_app_name}")
                                    
                                    # Update selected_app_code to use the fetched app_id
                                    selected_app_code = str(fetched_app_id)
                                else:
                                    st.info(f"ℹ️ App {fetched_app_id} already in list")
                                    selected_app_code = str(fetched_app_id)
                            else:
                                st.warning(f"⚠️ App with ID '{app_id}' not found")
                    else:
                        st.warning(f"⚠️ Please enter a valid App ID (numeric value)")
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
        # For IronSource grouped apps, the format is "App Name (Android + iOS)"
        if current_network == "ironsource" and " (Android + iOS)" in selected_app_display:
            app_name = selected_app_display.replace(" (Android + iOS)", "")
        elif current_network == "ironsource" and " (Android)" in selected_app_display:
            app_name = selected_app_display.replace(" (Android)", "")
        elif current_network == "ironsource" and " (iOS)" in selected_app_display:
            app_name = selected_app_display.replace(" (iOS)", "")
        elif selected_app_display != manual_entry_option and "(" in selected_app_display and ")" in selected_app_display:
            app_name = selected_app_display.split("(")[1].split(")")[0]
        else:
            app_name = "Unknown"
    
    # When app code is selected, immediately generate and update slot names
    if selected_app_code:
        # For IronSource, handle grouped apps differently
        if current_network == "ironsource":
            # First check last_app_info (from Create App response)
            last_app_info = SessionManager.get_last_created_app_info(current_network)
            if last_app_info and last_app_info.get("appCode") == selected_app_code:
                # Use cached apps to get bundleId
                cached_apps = SessionManager.get_cached_apps(current_network)
                if last_app_info.get("hasAndroid"):
                    android_app_key = last_app_info.get("appKey")
                    for cached_app in cached_apps:
                        if cached_app.get("appKey") == android_app_key:
                            selected_app_data = cached_app
                            break
                elif last_app_info.get("hasIOS"):
                    ios_app_key = last_app_info.get("appKeyIOS")
                    for cached_app in cached_apps:
                        if cached_app.get("appKey") == ios_app_key:
                            selected_app_data = cached_app
                            break
                else:
                    selected_app_data = None
            elif selected_app_code in app_info_map:
                # Check if this is a grouped app (has both Android and iOS)
                app_info = app_info_map[selected_app_code]
                if app_info.get("platform") == "both":
                    # Use Android app for slot name generation (primary)
                    selected_app_data = app_info.get("androidApp")
                elif app_info.get("hasAndroid"):
                    selected_app_data = app_info.get("androidApp")
                elif app_info.get("hasIOS"):
                    selected_app_data = app_info.get("iosApp")
                else:
                    selected_app_data = None
            else:
                # Try to find in apps list
                selected_app_data = None
                for app in apps:
                    app_identifier = app.get("appKey") or app.get("appCode")
                    if app_identifier == selected_app_code:
                        selected_app_data = app
                        break
        else:
            # For other networks, use original logic
            selected_app_data = None
            for app in apps:
                # For InMobi and Fyber, check appId; for others, check appCode
                if current_network == "inmobi":
                    app_identifier = app.get("appId")
                elif current_network == "fyber":
                    app_identifier = app.get("appId") or app.get("appCode") or app.get("id")
                else:
                    app_identifier = app.get("appCode")
                if str(app_identifier) == str(selected_app_code):
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
        
        # For IronSource, prioritize last_app_info (from Create App response)
        if current_network == "ironsource":
            # Check if selected_app_code matches last_app_info (app name)
            if last_app_info and last_app_info.get("appCode") == selected_app_code:
                # Use last_app_info as base
                app_info_to_use = last_app_info.copy()
                # Try to get bundleId from cached apps
                cached_apps = SessionManager.get_cached_apps(current_network)
                if app_info_to_use.get("hasAndroid"):
                    android_app_key = app_info_to_use.get("appKey")
                    for cached_app in cached_apps:
                        if cached_app.get("appKey") == android_app_key:
                            app_info_to_use["androidApp"] = cached_app
                            app_info_to_use["bundleId"] = cached_app.get("bundleId", "")
                            app_info_to_use["storeUrl"] = cached_app.get("storeUrl", "")
                            break
                if app_info_to_use.get("hasIOS"):
                    ios_app_key = app_info_to_use.get("appKeyIOS")
                    for cached_app in cached_apps:
                        if cached_app.get("appKey") == ios_app_key:
                            app_info_to_use["iosApp"] = cached_app
                            app_info_to_use["bundleIdIOS"] = cached_app.get("bundleId", "")
                            app_info_to_use["storeUrlIOS"] = cached_app.get("storeUrl", "")
                            break
            elif selected_app_code in app_info_map:
                app_info_to_use = app_info_map[selected_app_code]
                # If it's a grouped app, ensure we have bundleId from the apps
                if app_info_to_use.get("platform") == "both":
                    android_app = app_info_to_use.get("androidApp", {})
                    ios_app = app_info_to_use.get("iosApp", {})
                    if android_app:
                        app_info_to_use["bundleId"] = android_app.get("bundleId", "")
                        app_info_to_use["storeUrl"] = android_app.get("storeUrl", "")
                    if ios_app:
                        app_info_to_use["bundleIdIOS"] = ios_app.get("bundleId", "")
                        app_info_to_use["storeUrlIOS"] = ios_app.get("storeUrl", "")
        elif last_app_info and last_app_info.get("appCode") == selected_app_code:
            app_info_to_use = last_app_info
        elif selected_app_code in app_info_map:
            app_info_to_use = app_info_map[selected_app_code].copy()
            if last_app_info and last_app_info.get("appCode") == selected_app_code:
                app_info_to_use["pkgName"] = last_app_info.get("pkgName", "")
                # For BigOAds, also get pkgNameDisplay if available
                if current_network == "bigoads" and "pkgNameDisplay" in last_app_info:
                    app_info_to_use["pkgNameDisplay"] = last_app_info.get("pkgNameDisplay", "")
            else:
                # For BigOAds, ensure pkgNameDisplay is set from apps list if not in app_info_map
                if current_network == "bigoads" and not app_info_to_use.get("pkgNameDisplay"):
                    for app in apps:
                        if app.get("appCode") == selected_app_code:
                            if "pkgNameDisplay" in app:
                                app_info_to_use["pkgNameDisplay"] = app.get("pkgNameDisplay", "")
                            if not app_info_to_use.get("pkgName") and app.get("pkgName"):
                                app_info_to_use["pkgName"] = app.get("pkgName", "")
                            break
            # For Fyber, ensure bundle/bundleId is available from app_info_map
            if current_network == "fyber":
                if not app_info_to_use.get("bundleId") and not app_info_to_use.get("bundle"):
                    # Try to get from apps list
                    for app in apps:
                        app_identifier = app.get("appId") or app.get("appCode") or app.get("id")
                        if str(app_identifier) == str(selected_app_code):
                            app_info_to_use["bundleId"] = app.get("bundle") or app.get("bundleId", "")
                            app_info_to_use["bundle"] = app.get("bundle") or app.get("bundleId", "")
                            break
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
                        
                        # For BigOAds, get pkgNameDisplay and pkgName from API response
                        if current_network == "bigoads":
                            if "pkgNameDisplay" in app:
                                app_info_to_use["pkgNameDisplay"] = app.get("pkgNameDisplay", "")
                            if "pkgName" in app and not app_info_to_use.get("pkgName"):
                                app_info_to_use["pkgName"] = app.get("pkgName", "")
                            app_info_to_use["name"] = app.get("name", app_name)
                        
                        # For Mintegral, get pkgName and app_id from API response
                        if current_network == "mintegral":
                            app_info_to_use["pkgName"] = app.get("pkgName", "")
                            app_info_to_use["name"] = app.get("name", app_name)
                            # Update app_id from selected app
                            app_id_from_app = app.get("app_id") or app.get("appId") or app.get("id")
                            if app_id_from_app:
                                app_info_to_use["app_id"] = app_id_from_app
                                app_info_to_use["appId"] = app_id_from_app
                        
                        # For InMobi, get bundleId and pkgName from API response
                        if current_network == "inmobi":
                            app_info_to_use["bundleId"] = app.get("bundleId", "")
                            app_info_to_use["pkgName"] = app.get("pkgName", "")
                            app_info_to_use["name"] = app.get("name", app_name)
                        
                        # For Fyber, get bundle and bundleId from API response
                        if current_network == "fyber":
                            app_info_to_use["bundleId"] = app.get("bundle") or app.get("bundleId", "")
                            app_info_to_use["bundle"] = app.get("bundle") or app.get("bundleId", "")
                            app_info_to_use["pkgName"] = app.get("bundle") or app.get("bundleId", "")
                            app_info_to_use["name"] = app.get("name", app_name)
                        
                        break
    
    return selected_app_code, app_name, app_info_to_use, apps, app_info_map

