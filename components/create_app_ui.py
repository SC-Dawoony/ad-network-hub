"""Create App UI component"""
import streamlit as st
import logging
from typing import List, Tuple
from utils.session_manager import SessionManager
from utils.ui_components import DynamicFormRenderer
from utils.network_manager import get_network_manager, handle_api_response, _mask_sensitive_data
from utils.validators import validate_app_name, validate_package_name, validate_url
from utils.app_store_helper import (
    map_android_category_to_bigoads,
    map_android_category_to_ironsource_taxonomy,
    map_android_category_to_tiktok_category,
    map_android_category_to_fyber_android_category,
    map_android_category_to_vungle_category
)
from network_configs import get_network_config

logger = logging.getLogger(__name__)


def render_create_app_ui(current_network: str, network_display: str, config):
    """Render the Create App UI section
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        config: Network configuration object
    """
    st.subheader("📱 Create App")

    # For AppLovin, skip app creation form
    if current_network == "applovin":
        st.info("💡 AppLovin은 API를 통한 앱 생성 기능을 지원하지 않습니다. 대시보드에서 앱을 생성한 후, 아래 'Create Unit' 섹션에서 Ad Unit을 생성할 수 있습니다.")
        return
    
    # Render form
    with st.form("create_app_form"):
        st.markdown("**App Information**")
        
        # Pre-fill data from store info if available
        existing_data = {}
        
        # Get store info from session state
        store_info_android = st.session_state.get("store_info_android")
        store_info_ios = st.session_state.get("store_info_ios")
        
        # Map store info to network-specific fields
        if store_info_android:
            android_package = store_info_android.get("package_name", "")
            android_name = store_info_android.get("name", "")
            
            # Network-specific field mapping
            if current_network == "bigoads":
                existing_data["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_package}"
                existing_data["androidPkgName"] = android_package
                existing_data["name"] = android_name
                android_category = store_info_android.get("category", "")
                if android_category:
                    existing_data["category"] = map_android_category_to_bigoads(android_category)
            elif current_network == "inmobi":
                existing_data["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_package}"
                if android_name:
                    existing_data["appName"] = android_name
            elif current_network == "pangle":
                existing_data["androidDownloadUrl"] = f"https://play.google.com/store/apps/details?id={android_package}"
                if android_name:
                    existing_data["app_name"] = android_name
                android_category = store_info_android.get("category", "")
                if android_category:
                    existing_data["app_category_code"] = map_android_category_to_tiktok_category(android_category)
            elif current_network == "unity":
                existing_data["google_storeId"] = android_package
                existing_data["google_storeUrl"] = f"https://play.google.com/store/apps/details?id={android_package}"
                existing_data["name"] = android_name
            elif current_network == "fyber":
                existing_data["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_package}"
                existing_data["androidBundle"] = android_package
                if android_name:
                    existing_data["name"] = android_name
                android_category = store_info_android.get("category", "")
                if android_category:
                    fyber_category = map_android_category_to_fyber_android_category(android_category)
                    existing_data["androidCategory1"] = fyber_category
                    logger.info(f"Fyber: Mapped Android category '{android_category}' to '{fyber_category}', existing_data keys: {list(existing_data.keys())}")
            elif current_network == "mintegral":
                existing_data["androidPackage"] = android_package
                existing_data["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_package}" if android_package else ""
                if android_name:
                    existing_data["app_name"] = android_name
            elif current_network == "vungle":
                existing_data["androidStoreId"] = android_package
                existing_data["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_package}"
                if android_name:
                    existing_data["app_name"] = android_name
                android_category = store_info_android.get("category", "")
                if android_category:
                    vungle_category = map_android_category_to_vungle_category(android_category)
                    existing_data["category"] = vungle_category
                    logger.info(f"Vungle: Mapped Android category '{android_category}' to '{vungle_category}', existing_data keys: {list(existing_data.keys())}")
            elif current_network == "ironsource":
                existing_data["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_package}"
                if android_name:
                    existing_data["appName"] = android_name
                android_category = store_info_android.get("category", "")
                if android_category:
                    taxonomy_value = map_android_category_to_ironsource_taxonomy(android_category)
                    existing_data["taxonomy"] = taxonomy_value
                    logger.debug(f"IronSource: Mapped Android category '{android_category}' to taxonomy '{taxonomy_value}'")
            elif current_network == "admob":
                existing_data["androidAppStoreId"] = android_package
                if android_name:
                    existing_data["androidAppName"] = android_name
        
        if store_info_ios:
            ios_bundle_id = store_info_ios.get("bundle_id", "")
            ios_app_id = store_info_ios.get("app_id", "")
            ios_name = store_info_ios.get("name", "")
            ios_store_url = f"https://apps.apple.com/app/id{ios_app_id}" if ios_app_id else ""
            
            # Network-specific field mapping
            if current_network == "bigoads":
                if ios_store_url:
                    existing_data["iosStoreUrl"] = ios_store_url
                existing_data["iosPkgName"] = ios_bundle_id
                if not existing_data.get("name") and ios_name:
                    existing_data["name"] = ios_name
            elif current_network == "inmobi":
                if ios_store_url:
                    existing_data["iosStoreUrl"] = ios_store_url
                if not existing_data.get("appName") and ios_name:
                    existing_data["appName"] = ios_name
            elif current_network == "pangle":
                if ios_store_url:
                    existing_data["iosDownloadUrl"] = ios_store_url
                if not existing_data.get("app_name") and ios_name:
                    existing_data["app_name"] = ios_name
            elif current_network == "unity":
                existing_data["apple_storeId"] = ios_app_id
                if ios_store_url:
                    existing_data["apple_storeUrl"] = ios_store_url
                if not existing_data.get("name") and ios_name:
                    existing_data["name"] = ios_name
            elif current_network == "fyber":
                if ios_store_url:
                    existing_data["iosStoreUrl"] = ios_store_url
                if ios_bundle_id:
                    existing_data["iosBundle"] = ios_bundle_id
                if not existing_data.get("name") and ios_name:
                    existing_data["name"] = ios_name
            elif current_network == "mintegral":
                existing_data["iosPackage"] = ios_bundle_id
                existing_data["iosStoreUrl"] = f"https://apps.apple.com/app/id{ios_app_id}" if ios_app_id else ""
                if not existing_data.get("app_name") and ios_name:
                    existing_data["app_name"] = ios_name
            elif current_network == "vungle":
                if ios_app_id:
                    existing_data["iosStoreId"] = ios_app_id
                if ios_store_url:
                    existing_data["iosStoreUrl"] = ios_store_url
                if not existing_data.get("app_name") and ios_name:
                    existing_data["app_name"] = ios_name
                # Note: Category is set from Android, but iOS will always use "Games" in payload builder
            elif current_network == "ironsource":
                if ios_store_url:
                    existing_data["iosStoreUrl"] = ios_store_url
                # App Name: prefer Android, fallback to iOS if Android not available
                if not existing_data.get("appName") and ios_name:
                    existing_data["appName"] = ios_name
                # Taxonomy is already set from Android category if available
                # If only iOS, we could try to map iOS category, but Android is more reliable
            elif current_network == "admob":
                if ios_app_id:
                    existing_data["iosAppStoreId"] = ios_app_id
                if ios_name:
                    existing_data["iosAppName"] = ios_name
        
        # For Pangle, pre-fill user_id and role_id from .env and show all required fields
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
        
        # Show info if data was pre-filled from store info
        if existing_data and (store_info_android or store_info_ios):
            pre_filled_fields = [k for k in existing_data.keys() if k not in ["user_id", "role_id"]]
            if pre_filled_fields:
                st.info(f"💡 {len(pre_filled_fields)}개 필드가 Store URL에서 조회된 정보로 자동 채워졌습니다.")
                # Debug: Show pre-filled values for IronSource, Fyber, and Vungle (use INFO level for visibility)
                if current_network == "ironsource":
                    logger.info(f"IronSource existing_data: {existing_data}")
                elif current_network == "fyber":
                    logger.info(f"Fyber existing_data: {existing_data}")
                elif current_network == "vungle":
                    logger.info(f"Vungle existing_data: {existing_data}")
        else:
            # Log when existing_data is empty or store_info is missing
            if current_network == "fyber":
                logger.info(f"Fyber: existing_data is empty or store_info missing. existing_data={existing_data}, store_info_android={bool(store_info_android)}, store_info_ios={bool(store_info_ios)}")
            elif current_network == "vungle":
                logger.info(f"Vungle: existing_data is empty or store_info missing. existing_data={existing_data}, store_info_android={bool(store_info_android)}, store_info_ios={bool(store_info_ios)}")
        
        # Clear Streamlit widget keys from session_state if existing_data is provided
        # This ensures that widgets use the new values from existing_data instead of cached values
        if existing_data and (store_info_android or store_info_ios):
            # Get all field names from config
            fields = config.get_app_creation_fields()
            for field in fields:
                # Clear widget key from session_state to force re-initialization
                widget_key = f"app_{field.name}"
                if widget_key in st.session_state:
                    # Only clear if we have a new value in existing_data
                    if field.name in existing_data:
                        del st.session_state[widget_key]
                        logger.info(f"Cleared widget key '{widget_key}' to force re-initialization with value: {existing_data[field.name]}")
        
        # Render form without sections for all networks
        form_data = DynamicFormRenderer.render_form(config, "app", existing_data=existing_data)
        
        # Debug: Log form_data after rendering for IronSource, Fyber, and Vungle (use INFO level for visibility)
        if current_network == "ironsource":
            logger.info(f"IronSource form_data after render: {form_data}")
        elif current_network == "fyber":
            logger.info(f"Fyber form_data after render: {form_data}")
        elif current_network == "vungle":
            logger.info(f"Vungle form_data after render: {form_data}")
        
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
    
            # For BigOAds, validate androidPkgName and iosPkgName instead of pkgName
            if current_network == "bigoads":
                android_pkg_name = form_data.get("androidPkgName", "").strip()
                ios_pkg_name = form_data.get("iosPkgName", "").strip()
                android_store_url = form_data.get("androidStoreUrl", "").strip()
                ios_store_url = form_data.get("iosStoreUrl", "").strip()
                
                # Validate Android package name if Android Store URL is provided
                if android_store_url and android_pkg_name:
                    valid, msg = validate_package_name(android_pkg_name)
                    if not valid:
                        validation_passed = False
                        error_messages.append(f"Android {msg}")
                
                # Validate iOS package name if iOS Store URL is provided
                if ios_store_url and ios_pkg_name:
                    valid, msg = validate_package_name(ios_pkg_name)
                    if not valid:
                        validation_passed = False
                        error_messages.append(f"iOS {msg}")
            elif "pkgName" in form_data:
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
                    # For IronSource, InMobi, BigOAds, Fyber, Pangle, and Vungle, handle both iOS and Android platforms (using Store URLs)
                    if current_network in ["ironsource", "inmobi", "bigoads", "fyber", "pangle", "vungle", "mintegral"]:
                        # For Pangle, use Download URL instead of Store URL
                        if current_network == "pangle":
                            ios_store_url = form_data.get("iosDownloadUrl", "").strip()
                            android_store_url = form_data.get("androidDownloadUrl", "").strip()
                        else:
                            ios_store_url = form_data.get("iosStoreUrl", "").strip()
                            android_store_url = form_data.get("androidStoreUrl", "").strip()
                        
                        if not ios_store_url and not android_store_url:
                            st.error("❌ At least one Store URL (iOS or Android) must be provided")
                        else:
                            results = []
                            platforms_created = []
                            
                            # Create Android app if URL provided
                            if android_store_url:
                                with st.spinner("Creating Android app..."):
                                    android_payload = config.build_app_payload(form_data, platform="Android")
                                    network_manager = get_network_manager()
                                    android_response = network_manager.create_app(current_network, android_payload)
                                    
                                    if android_response:
                                        android_result = handle_api_response(android_response)
                                        if android_result:
                                            results.append(("Android", android_result, android_response))
                                            platforms_created.append("Android")
                            
                            # Create iOS app if URL provided
                            if ios_store_url:
                                with st.spinner("Creating iOS app..."):
                                    ios_payload = config.build_app_payload(form_data, platform="iOS")
                                    network_manager = get_network_manager()
                                    ios_response = network_manager.create_app(current_network, ios_payload)
                                    
                                    if ios_response:
                                        ios_result = handle_api_response(ios_response)
                                        if ios_result:
                                            results.append(("iOS", ios_result, ios_response))
                                            platforms_created.append("iOS")
                    
                    # For AdMob, handle both iOS and Android platforms (using App Name + App Store ID)
                    elif current_network == "admob":
                        android_app_name = form_data.get("androidAppName", "").strip()
                        android_app_store_id = form_data.get("androidAppStoreId", "").strip()
                        ios_app_name = form_data.get("iosAppName", "").strip()
                        ios_app_store_id = form_data.get("iosAppStoreId", "").strip()
                        has_android = android_app_name or android_app_store_id
                        has_ios = ios_app_name or ios_app_store_id

                        if not has_android and not has_ios:
                            st.error("❌ At least one platform (Android or iOS) must be provided")
                        else:
                            results = []
                            platforms_created = []

                            # Create Android app if Android fields provided
                            if has_android:
                                with st.spinner("Creating Android app..."):
                                    android_payload = config.build_app_payload(form_data, platform="Android")
                                    network_manager = get_network_manager()
                                    android_response = network_manager.create_app(current_network, android_payload)

                                    if android_response:
                                        android_result = handle_api_response(android_response)
                                        if android_result:
                                            results.append(("Android", android_result, android_response))
                                            platforms_created.append("Android")

                            # Create iOS app if iOS fields provided
                            if has_ios:
                                with st.spinner("Creating iOS app..."):
                                    ios_payload = config.build_app_payload(form_data, platform="iOS")
                                    network_manager = get_network_manager()
                                    ios_response = network_manager.create_app(current_network, ios_payload)

                                    if ios_response:
                                        ios_result = handle_api_response(ios_response)
                                        if ios_result:
                                            results.append(("iOS", ios_result, ios_response))
                                            platforms_created.append("iOS")
                            
                            # Store responses and process results
                            if results:
                                # Store the last response (for backward compatibility)
                                st.session_state[f"{current_network}_last_app_response"] = results[-1][2]
                                
                                # Process all results
                                if current_network == "ironsource":
                                    _process_ironsource_create_app_results(
                                        current_network, network_display, form_data, results
                                    )
                                elif current_network == "inmobi":
                                    _process_inmobi_create_app_results(
                                        current_network, network_display, form_data, results
                                    )
                                elif current_network == "bigoads":
                                    _process_bigoads_create_app_results(
                                        current_network, network_display, form_data, results
                                    )
                                elif current_network == "fyber":
                                    _process_fyber_create_app_results(
                                        current_network, network_display, form_data, results
                                    )
                                elif current_network == "admob":
                                    _process_admob_create_app_results(
                                        current_network, network_display, form_data, results
                                    )
                                elif current_network == "pangle":
                                    _process_pangle_create_app_results(
                                        current_network, network_display, form_data, results
                                    )
                                elif current_network == "vungle":
                                    _process_vungle_create_app_results(
                                        current_network, network_display, form_data, results
                                    )
                                elif current_network == "mintegral":
                                    _process_mintegral_create_app_results(
                                        current_network, network_display, form_data, results
                                    )
                    else:
                        # For other networks, use original logic
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
                                _process_create_app_result(
                                    current_network, network_display, form_data, result
                                )
                
                except Exception as e:
                    st.error(f"❌ Error creating app: {str(e)}")
                    SessionManager.log_error(current_network, str(e))
    except NameError:
        pass


def _process_create_app_result(current_network: str, network_display: str, form_data: dict, result: dict):
    """Process the result from create app API call
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        result: API response result
    """
    # Extract app code from actual API response based on network
    # result is already the normalized response from network_manager
    app_code = None
    app_id = None
    unity_game_ids = None  # Initialize for Unity
    
    if current_network == "ironsource":
        # IronSource: result contains appKey directly
        app_code = result.get("appKey")
    elif current_network == "pangle":
        # Pangle: result.data contains site_id, or result itself
        app_code = result.get("site_id") or (result.get("data", {}) if isinstance(result.get("data"), dict) else {}).get("site_id")
    elif current_network == "mintegral":
        # Mintegral: result.result contains app_id
        # Response format: {"status": 0, "code": 0, "msg": "Success", "result": {"app_id": 441875, ...}}
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else {}
        app_id = result_data.get("app_id") or result_data.get("id") or result_data.get("appId")
        # Fallback to data field if result.result doesn't have app_id
        if not app_id:
            data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
            app_id = data.get("app_id") or data.get("id") or data.get("appId")
        # Final fallback to result itself
        if not app_id:
            app_id = result.get("app_id") or result.get("id")
        app_code = str(app_id) if app_id else None
    elif current_network == "inmobi":
        # InMobi: result.data contains appId, or result itself
        # Try multiple possible field names
        data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
        app_id = data.get("appId") or data.get("id") or data.get("app_id") or result.get("appId") or result.get("id")
        app_code = str(app_id) if app_id else None
    elif current_network == "unity":
        # Unity: result.result.stores.apple.gameId and result.result.stores.google.gameId
        # Store both gameIds separately for display
        result_data = result.get("result", {})
        if not result_data:
            result_data = result  # Fallback if result structure is different
        
        stores = result_data.get("stores", {})
        apple_store = stores.get("apple", {}) if isinstance(stores.get("apple"), dict) else {}
        google_store = stores.get("google", {}) if isinstance(stores.get("google"), dict) else {}
        
        apple_game_id = apple_store.get("gameId")
        google_game_id = google_store.get("gameId")
        
        # For app_code, use first available gameId (prefer Apple, then Google)
        # This is what Unity uses as the app identifier
        if apple_game_id:
            app_code = str(apple_game_id)
        elif google_game_id:
            app_code = str(google_game_id)
        else:
            # Fallback to project id if gameIds are not available
            project_id = result_data.get("id")
            app_code = str(project_id) if project_id else None
        
        # Store gameIds separately for Unity (don't use app_id variable to avoid conflicts)
        unity_game_ids = {
            "apple_gameId": apple_game_id,
            "google_gameId": google_game_id,
            "project_id": result_data.get("id")
        }
        # For Unity, app_id should remain None (not used for Unity)
        app_id = None
    elif current_network == "fyber":
        # Fyber: result.result contains appId and platform
        # Handle both cases: result.result.appId or direct result.appId
        fyber_result = result.get("result", {})
        if not fyber_result or (isinstance(fyber_result, dict) and not fyber_result.get("appId") and not fyber_result.get("id")):
            # If result.result is empty or doesn't have appId, try result directly
            fyber_result = result
        app_id = fyber_result.get("appId") or fyber_result.get("id")
        app_code = str(app_id) if app_id else None
    else:
        # BigOAds: result.result contains appCode (from _create_bigoads_app normalization)
        # The normalized response has result.result containing the actual data
        result_data = result.get("result", {})
        app_code = result_data.get("appCode") or result.get("appCode")
    
    if not app_code:
        app_code = "N/A"
    
    app_name = form_data.get("app_name") or form_data.get("appName") or form_data.get("name", "Unknown")
    
    # For IronSource, Pangle, Mintegral, InMobi, and Fyber, we don't have platform/pkgName in the same way
    if current_network in ["ironsource", "pangle", "mintegral", "inmobi", "fyber"]:
        platform = None
        platform_str = None
        pkg_name = None
        
        # For IronSource, extract platform from form_data
        if current_network == "ironsource":
            platform_value = form_data.get("platform", "Android")
            platform_str = "android" if platform_value == "Android" else "ios"
            platform = 1 if platform_value == "Android" else 2
        elif current_network == "fyber":
            # Fyber: Extract platform from API response
            fyber_result = result.get("result", {})
            platform_value = fyber_result.get("platform", "").lower()
            if platform_value == "android":
                platform_str = "android"
                platform = 1
            elif platform_value == "ios":
                platform_str = "ios"
                platform = 2
            else:
                # Fallback to form_data if not in response
                platform_value = form_data.get("platform", 1)
                platform = platform_value if isinstance(platform_value, int) else (1 if platform_value == "Android" else 2)
                platform_str = "android" if platform == 1 else "ios"
            pkg_name = fyber_result.get("bundle", "") or form_data.get("pkgName", "")
        else:
            platform = form_data.get("platform", 1)  # 1 = Android, 2 = iOS
            platform_str = "android" if platform == 1 else "ios"
            pkg_name = form_data.get("pkgName", "")
    else:
        # For BigOAds and other networks
        platform = form_data.get("platform", 1)  # 1 = Android, 2 = iOS
        platform_str = "android" if platform == 1 else "ios"
        pkg_name = form_data.get("pkgName", "")
    
    # Save to session with full info for slot creation
    # For Unity, unity_game_ids is already set above in the Unity branch
    # For other networks, set to None
    if current_network != "unity":
        unity_game_ids = None
    
    app_data = {
        "appCode": app_code,  # For IronSource, this is actually appKey. For Unity, this is gameId.
        "appKey": app_code if current_network == "ironsource" else None,  # Store appKey separately for IronSource
        "siteId": app_code if current_network == "pangle" else None,  # Store siteId separately for Pangle
        "app_id": app_id if current_network in ["mintegral", "inmobi"] else (int(app_code) if app_code and app_code != "N/A" and str(app_code).isdigit() else None),  # Store app_id separately for Mintegral and InMobi
        "gameId": unity_game_ids if current_network == "unity" else None,  # Store gameIds separately for Unity
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
        # For Unity, display Project ID first, then gameId for each platform separately
        if current_network == "unity":
            result_data = result.get("result", {})
            if not result_data:
                result_data = result  # Fallback if result structure is different
            
            project_id = result_data.get("id")
            stores = result_data.get("stores", {})
            apple_store = stores.get("apple", {}) if isinstance(stores.get("apple"), dict) else {}
            google_store = stores.get("google", {}) if isinstance(stores.get("google"), dict) else {}
            
            apple_game_id = apple_store.get("gameId")
            google_game_id = google_store.get("gameId")
            
            if project_id:
                st.write(f"**Project ID:** {project_id}")
            
            st.write("**App Code (Game ID):**")
            if apple_game_id:
                st.write(f"  - **iOS (Apple):** {apple_game_id}")
            if google_game_id:
                st.write(f"  - **Android (Google):** {google_game_id}")
            if not apple_game_id and not google_game_id:
                st.write("  - N/A")
            
            # Display the primary app_code used
            if app_code and app_code != "N/A":
                st.write(f"**Primary App Code:** {app_code}")
        elif current_network == "fyber":
            # Fyber: Display App ID instead of App Code
            # Handle both cases: result.result.appId or direct result.appId
            fyber_result = result.get("result", {})
            if not fyber_result or (isinstance(fyber_result, dict) and not fyber_result.get("appId") and not fyber_result.get("id")):
                # If result.result is empty or doesn't have appId, try result directly
                fyber_result = result
            fyber_app_id = fyber_result.get("appId") or fyber_result.get("id") or app_code
            st.write(f"**App ID:** {fyber_app_id}")
        else:
            st.write(f"**App Code:** {result.get('appCode', app_code)}")
        with result_col2:
            st.write(f"**App Name:** {form_data.get('name', app_name)}")
            # Display platform correctly for all networks
            if current_network == "fyber":
                # Fyber: Get platform from API response
                fyber_result = result.get("result", {})
                fyber_platform = fyber_result.get("platform", "").lower()
                if fyber_platform == "android":
                    platform_display = "Android"
                elif fyber_platform == "ios":
                    platform_display = "iOS"
                else:
                    platform_display = platform_str.capitalize() if platform_str else "N/A"
                st.write(f"**Platform:** {platform_display}")
            elif current_network in ["ironsource", "pangle", "mintegral", "inmobi"]:
                # For these networks, use platform_str or platform_value
                if current_network == "ironsource":
                    platform_value = form_data.get("platform", "Android")
                    platform_display = "Android" if platform_value == "Android" else "iOS"
                else:
                    platform_display = "Android" if platform_str == "android" else "iOS"
                st.write(f"**Platform:** {platform_display}")
            elif current_network == "unity":
                # Unity supports both platforms, show both if available
                result_data = result.get("result", {})
                stores = result_data.get("stores", {})
                apple_game_id = stores.get("apple", {}).get("gameId")
                google_game_id = stores.get("google", {}).get("gameId")
                platforms = []
                if apple_game_id:
                    platforms.append("iOS")
                if google_game_id:
                    platforms.append("Android")
                if platforms:
                    st.write(f"**Platform:** {', '.join(platforms)}")
            elif form_data.get('platform'):
                # For other networks, platform is numeric (1 = Android, 2 = iOS)
                st.write(f"**Platform:** {'Android' if form_data.get('platform') == 1 else 'iOS'}")


def _process_ironsource_create_app_results(current_network: str, network_display: str, form_data: dict, results: List[Tuple[str, dict, dict]]):
    """Process IronSource create app results for multiple platforms
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        results: List of tuples (platform, result, response) for each platform created
    """
    app_name = form_data.get("appName", "Unknown")
    ios_store_url = form_data.get("iosStoreUrl", "").strip()
    android_store_url = form_data.get("androidStoreUrl", "").strip()
    
    # Store both appKeys
    android_app_key = None
    ios_app_key = None
    android_result_data = None
    ios_result_data = None
    
    for platform, result, response in results:
        app_key = result.get("appKey")
        if platform == "Android":
            android_app_key = app_key
            android_result_data = result
        elif platform == "iOS":
            ios_app_key = app_key
            ios_result_data = result
    
    # Save combined app data with both appKeys
    app_data = {
        "appCode": app_name,  # Use app name as primary identifier
        "appKey": android_app_key,  # Android appKey (primary)
        "appKeyIOS": ios_app_key,  # iOS appKey
        "name": app_name,
        "platform": "both" if android_app_key and ios_app_key else ("android" if android_app_key else "ios"),
        "platformStr": "both" if android_app_key and ios_app_key else ("android" if android_app_key else "ios"),
        "storeUrl": android_store_url if android_store_url else ios_store_url,
        "iosStoreUrl": ios_store_url,
        "androidStoreUrl": android_store_url,
        "hasAndroid": bool(android_app_key),
        "hasIOS": bool(ios_app_key)
    }
    SessionManager.add_created_app(current_network, app_data)
    
    # Add both apps to cache
    cached_apps = SessionManager.get_cached_apps(current_network)
    
    if android_app_key:
        android_app = {
            "appCode": android_app_key,
            "appKey": android_app_key,
            "name": app_name,
            "platform": "Android",
            "status": "Active",
            "storeUrl": android_store_url
        }
        if not any(app.get("appKey") == android_app_key for app in cached_apps):
            cached_apps.append(android_app)
    
    if ios_app_key:
        ios_app = {
            "appCode": ios_app_key,
            "appKey": ios_app_key,
            "name": app_name,
            "platform": "iOS",
            "status": "Active",
            "storeUrl": ios_store_url
        }
        if not any(app.get("appKey") == ios_app_key for app in cached_apps):
            cached_apps.append(ios_app)
    
    SessionManager.cache_apps(current_network, cached_apps)
    
    # Show success message
    platforms_str = " and ".join([p for p, _, _ in results])
    st.success(f"🎉 App created successfully for {platforms_str}!")
    st.balloons()
    
    # Show result details
    st.subheader("📝 Result")
    result_col1, result_col2 = st.columns(2)
    with result_col1:
        st.write(f"**Network:** {network_display}")
        st.write(f"**App Name:** {app_name}")
        st.write("**App Keys:**")
        if android_app_key:
            st.write(f"  - **Android:** {android_app_key}")
        if ios_app_key:
            st.write(f"  - **iOS:** {ios_app_key}")
    with result_col2:
        st.write(f"**Platforms:** {', '.join([p for p, _, _ in results])}")
        if android_store_url:
            st.write(f"**Android Store URL:** {android_store_url[:50]}...")
        if ios_store_url:
            st.write(f"**iOS Store URL:** {ios_store_url[:50]}...")


def _process_inmobi_create_app_results(current_network: str, network_display: str, form_data: dict, results: List[Tuple[str, dict, dict]]):
    """Process InMobi create app results for multiple platforms
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        results: List of tuples (platform, result, response) for each platform created
    """
    app_name = form_data.get("appName", "Unknown")
    ios_store_url = form_data.get("iosStoreUrl", "").strip()
    android_store_url = form_data.get("androidStoreUrl", "").strip()
    
    # Store both appIds
    android_app_id = None
    ios_app_id = None
    android_result_data = None
    ios_result_data = None
    
    for platform, result, response in results:
        # InMobi: result contains appId
        data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
        app_id = data.get("appId") or data.get("id") or data.get("app_id") or result.get("appId") or result.get("id")
        
        if platform == "Android":
            android_app_id = app_id
            android_result_data = result
        elif platform == "iOS":
            ios_app_id = app_id
            ios_result_data = result
    
    # Save combined app data with both appIds
    app_data = {
        "appCode": app_name,  # Use app name as primary identifier
        "appId": android_app_id,  # Android appId (primary)
        "appIdIOS": ios_app_id,  # iOS appId
        "name": app_name,
        "platform": "both" if android_app_id and ios_app_id else ("android" if android_app_id else "ios"),
        "platformStr": "both" if android_app_id and ios_app_id else ("android" if android_app_id else "ios"),
        "storeUrl": android_store_url if android_store_url else ios_store_url,
        "iosStoreUrl": ios_store_url,
        "androidStoreUrl": android_store_url,
        "hasAndroid": bool(android_app_id),
        "hasIOS": bool(ios_app_id)
    }
    SessionManager.add_created_app(current_network, app_data)
    
    # Add both apps to cache
    cached_apps = SessionManager.get_cached_apps(current_network)
    
    if android_app_id:
        android_app = {
            "appCode": str(android_app_id),
            "appId": android_app_id,
            "name": app_name,
            "platform": "Android",
            "status": "Active",
            "storeUrl": android_store_url
        }
        if not any(app.get("appId") == android_app_id for app in cached_apps):
            cached_apps.append(android_app)
    
    if ios_app_id:
        ios_app = {
            "appCode": str(ios_app_id),
            "appId": ios_app_id,
            "name": app_name,
            "platform": "iOS",
            "status": "Active",
            "storeUrl": ios_store_url
        }
        if not any(app.get("appId") == ios_app_id for app in cached_apps):
            cached_apps.append(ios_app)
    
    SessionManager.cache_apps(current_network, cached_apps)
    
    # Show success message
    platforms_str = " and ".join([p for p, _, _ in results])
    st.success(f"🎉 App created successfully for {platforms_str}!")
    st.balloons()
    
    # Show result details
    st.subheader("📝 Result")
    result_col1, result_col2 = st.columns(2)
    with result_col1:
        st.write(f"**Network:** {network_display}")
        st.write(f"**App Name:** {app_name}")
        st.write("**App IDs:**")
        if android_app_id:
            st.write(f"  - **Android:** {android_app_id}")
        if ios_app_id:
            st.write(f"  - **iOS:** {ios_app_id}")
    with result_col2:
        st.write(f"**Platforms:** {', '.join([p for p, _, _ in results])}")
        if android_store_url:
            st.write(f"**Android Store URL:** {android_store_url[:50]}...")
        if ios_store_url:
            st.write(f"**iOS Store URL:** {ios_store_url[:50]}...")


def _process_bigoads_create_app_results(current_network: str, network_display: str, form_data: dict, results: List[Tuple[str, dict, dict]]):
    """Process BigOAds create app results for multiple platforms
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        results: List of tuples (platform, result, response) for each platform created
    """
    app_name = form_data.get("name", "Unknown")
    ios_store_url = form_data.get("iosStoreUrl", "").strip()
    android_store_url = form_data.get("androidStoreUrl", "").strip()
    
    # Store both appCodes
    android_app_code = None
    ios_app_code = None
    android_result_data = None
    ios_result_data = None
    
    for platform, result, response in results:
        # BigOAds: result.result contains appCode
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result
        app_code = result_data.get("appCode") or result.get("appCode")
        
        if platform == "Android":
            android_app_code = app_code
            android_result_data = result
        elif platform == "iOS":
            ios_app_code = app_code
            ios_result_data = result
    
    # Save combined app data with both appCodes
    app_data = {
        "appCode": app_name,  # Use app name as primary identifier
        "appCodeAndroid": android_app_code,  # Android appCode
        "appCodeIOS": ios_app_code,  # iOS appCode
        "name": app_name,
        "platform": "both" if android_app_code and ios_app_code else ("android" if android_app_code else "ios"),
        "platformStr": "both" if android_app_code and ios_app_code else ("android" if android_app_code else "ios"),
        "storeUrl": android_store_url if android_store_url else ios_store_url,
        "iosStoreUrl": ios_store_url,
        "androidStoreUrl": android_store_url,
        "hasAndroid": bool(android_app_code),
        "hasIOS": bool(ios_app_code)
    }
    SessionManager.add_created_app(current_network, app_data)
    
    # Add both apps to cache
    cached_apps = SessionManager.get_cached_apps(current_network)
    
    if android_app_code:
        android_app = {
            "appCode": str(android_app_code),
            "name": app_name,
            "platform": "Android",
            "status": "Active",
            "storeUrl": android_store_url,
            "pkgName": form_data.get("androidPkgName", "")
        }
        if not any(app.get("appCode") == android_app_code for app in cached_apps):
            cached_apps.append(android_app)
    
    if ios_app_code:
        ios_app = {
            "appCode": str(ios_app_code),
            "name": app_name,
            "platform": "iOS",
            "status": "Active",
            "storeUrl": ios_store_url,
            "pkgName": form_data.get("iosPkgName", "")
        }
        if not any(app.get("appCode") == ios_app_code for app in cached_apps):
            cached_apps.append(ios_app)
    
    SessionManager.cache_apps(current_network, cached_apps)
    
    # Show success message
    platforms_str = " and ".join([p for p, _, _ in results])
    st.success(f"🎉 App created successfully for {platforms_str}!")
    st.balloons()
    
    # Show result details
    st.subheader("📝 Result")
    result_col1, result_col2 = st.columns(2)
    with result_col1:
        st.write(f"**Network:** {network_display}")
        st.write(f"**App Name:** {app_name}")
        st.write("**App Codes:**")
        if android_app_code:
            st.write(f"  - **Android:** {android_app_code}")
        if ios_app_code:
            st.write(f"  - **iOS:** {ios_app_code}")
    with result_col2:
        st.write(f"**Platforms:** {', '.join([p for p, _, _ in results])}")
        if android_store_url:
            st.write(f"**Android Store URL:** {android_store_url[:50]}...")
        if ios_store_url:
            st.write(f"**iOS Store URL:** {ios_store_url[:50]}...")


def _process_admob_create_app_results(current_network: str, network_display: str, form_data: dict, results: List[Tuple[str, dict, dict]]):
    """Process AdMob create app results for multiple platforms
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        results: List of tuples (platform, result, response) for each platform created
    """
    android_app_name = form_data.get("androidAppName", "").strip()
    ios_app_name = form_data.get("iosAppName", "").strip()
    android_app_store_id = form_data.get("androidAppStoreId", "").strip()
    ios_app_store_id = form_data.get("iosAppStoreId", "").strip()
    # Use first available name as primary identifier
    app_name = android_app_name or ios_app_name or "Unknown"

    # Store both appIds
    android_app_id = None
    ios_app_id = None
    android_result_data = None
    ios_result_data = None

    for platform, result, response in results:
        # AdMob: result.result contains appId (e.g., "ca-app-pub-1234567890123456~1234567890")
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result
        app_id = result_data.get("appId") or result_data.get("name") or result.get("appId") or result.get("name")

        if platform == "Android":
            android_app_id = app_id
            android_result_data = result
        elif platform == "iOS":
            ios_app_id = app_id
            ios_result_data = result

    # Save combined app data with both appIds
    app_data = {
        "appCode": app_name,  # Use app name as primary identifier
        "appId": android_app_id,  # Android appId (primary)
        "appIdIOS": ios_app_id,  # iOS appId
        "name": app_name,
        "androidAppName": android_app_name,
        "iosAppName": ios_app_name,
        "platform": "both" if android_app_id and ios_app_id else ("android" if android_app_id else "ios"),
        "platformStr": "both" if android_app_id and ios_app_id else ("android" if android_app_id else "ios"),
        "androidAppStoreId": android_app_store_id,
        "iosAppStoreId": ios_app_store_id,
        "hasAndroid": bool(android_app_id),
        "hasIOS": bool(ios_app_id)
    }
    SessionManager.add_created_app(current_network, app_data)

    # Add both apps to cache
    cached_apps = SessionManager.get_cached_apps(current_network)

    if android_app_id:
        android_app = {
            "appId": android_app_id,
            "name": android_app_name or app_name,
            "platform": "ANDROID",
            "appStoreId": android_app_store_id
        }
        if cached_apps:
            cached_apps.append(android_app)
        else:
            SessionManager.cache_apps(current_network, [android_app])

    if ios_app_id:
        ios_app = {
            "appId": ios_app_id,
            "name": ios_app_name or app_name,
            "platform": "IOS",
            "appStoreId": ios_app_store_id
        }
        if cached_apps:
            cached_apps.append(ios_app)
        else:
            if not cached_apps:
                SessionManager.cache_apps(current_network, [ios_app])
            else:
                cached_apps.append(ios_app)

    # Display results
    st.success(f"✅ {network_display} App(s) Created Successfully!")

    result_col1, result_col2 = st.columns(2)

    with result_col1:
        st.subheader("📱 App Information")
        if android_app_id:
            st.write(f"**Android App Name:** {android_app_name}")
            st.write(f"**Android App ID:** `{android_app_id}`")
        if ios_app_id:
            st.write(f"**iOS App Name:** {ios_app_name}")
            st.write(f"**iOS App ID:** `{ios_app_id}`")

    with result_col2:
        st.subheader("📊 Creation Summary")
        platforms_created = []
        if android_app_id:
            platforms_created.append("Android")
        if ios_app_id:
            platforms_created.append("iOS")
        st.write(f"**Platforms:** {', '.join(platforms_created)}")
        if android_app_store_id:
            st.write(f"**Android App Store ID:** {android_app_store_id}")
        if ios_app_store_id:
            st.write(f"**iOS App Store ID:** {ios_app_store_id}")

    # Show detailed results
    if android_result_data or ios_result_data:
        with st.expander("📋 Detailed Results"):
            if android_result_data:
                st.write("**Android:**")
                st.json(android_result_data)
            if ios_result_data:
                st.write("**iOS:**")
                st.json(ios_result_data)


def _process_fyber_create_app_results(current_network: str, network_display: str, form_data: dict, results: List[Tuple[str, dict, dict]]):
    """Process Fyber create app results for multiple platforms
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        results: List of tuples (platform, result, response) for each platform created
    """
    app_name = form_data.get("name", "Unknown")
    ios_store_url = form_data.get("iosStoreUrl", "").strip()
    android_store_url = form_data.get("androidStoreUrl", "").strip()
    
    # Store both appIds
    android_app_id = None
    ios_app_id = None
    android_result_data = None
    ios_result_data = None
    
    for platform, result, response in results:
        # Fyber: result.result contains appId
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result
        app_id = result_data.get("appId") or result_data.get("id") or result.get("appId") or result.get("id")
        
        if platform == "Android":
            android_app_id = app_id
            android_result_data = result
        elif platform == "iOS":
            ios_app_id = app_id
            ios_result_data = result
    
    # Save combined app data with both appIds
    app_data = {
        "appCode": app_name,  # Use app name as primary identifier
        "appId": android_app_id,  # Android appId (primary)
        "appIdIOS": ios_app_id,  # iOS appId
        "name": app_name,
        "platform": "both" if android_app_id and ios_app_id else ("android" if android_app_id else "ios"),
        "platformStr": "both" if android_app_id and ios_app_id else ("android" if android_app_id else "ios"),
        "storeUrl": android_store_url if android_store_url else ios_store_url,
        "iosStoreUrl": ios_store_url,
        "androidStoreUrl": android_store_url,
        "hasAndroid": bool(android_app_id),
        "hasIOS": bool(ios_app_id)
    }
    SessionManager.add_created_app(current_network, app_data)
    
    # Add both apps to cache
    cached_apps = SessionManager.get_cached_apps(current_network)
    
    if android_app_id:
        android_app = {
            "appCode": str(android_app_id),
            "appId": android_app_id,
            "name": app_name,
            "platform": "Android",
            "status": "Active",
            "storeUrl": android_store_url,
            "bundle": form_data.get("androidBundle", "")
        }
        if not any(app.get("appId") == android_app_id for app in cached_apps):
            cached_apps.append(android_app)
    
    if ios_app_id:
        ios_app = {
            "appCode": str(ios_app_id),
            "appId": ios_app_id,
            "name": app_name,
            "platform": "iOS",
            "status": "Active",
            "storeUrl": ios_store_url,
            "bundle": form_data.get("iosBundle", "")
        }
        if not any(app.get("appId") == ios_app_id for app in cached_apps):
            cached_apps.append(ios_app)
    
    SessionManager.cache_apps(current_network, cached_apps)
    
    # Show success message
    platforms_str = " and ".join([p for p, _, _ in results])
    st.success(f"🎉 App created successfully for {platforms_str}!")
    st.balloons()
    
    # Show result details (Unity-style display: Android and iOS together)
    st.subheader("📝 Result")
    result_col1, result_col2 = st.columns(2)
    with result_col1:
        st.write(f"**Network:** {network_display}")
        st.write(f"**App Name:** {app_name}")
        st.write("**App ID:**")
        if android_app_id:
            st.write(f"  - **Android:** {android_app_id}")
        if ios_app_id:
            st.write(f"  - **iOS:** {ios_app_id}")
        if not android_app_id and not ios_app_id:
            st.write(f"  N/A")
    with result_col2:
        # Display platforms
        platforms = []
        if android_app_id:
            platforms.append("Android")
        if ios_app_id:
            platforms.append("iOS")
        if platforms:
            st.write(f"**Platform:** {', '.join(platforms)}")
        else:
            st.write(f"**Platform:** N/A")
        
        # Display store URLs
        if android_store_url:
            st.write(f"**Android Store URL:** {android_store_url[:50]}...")
        if ios_store_url:
            st.write(f"**iOS Store URL:** {ios_store_url[:50]}...")


def _process_pangle_create_app_results(current_network: str, network_display: str, form_data: dict, results: List[Tuple[str, dict, dict]]):
    """Process Pangle create app results for multiple platforms
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        results: List of tuples (platform, result, response) for each platform created
    """
    app_name = form_data.get("app_name", "Unknown")
    ios_download_url = form_data.get("iosDownloadUrl", "").strip()
    android_download_url = form_data.get("androidDownloadUrl", "").strip()
    
    # Store both siteIds
    android_site_id = None
    ios_site_id = None
    android_result_data = None
    ios_result_data = None
    
    for platform, result, response in results:
        # Pangle: result contains site_id and app_id
        result_data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
        site_id = result.get("site_id") or result_data.get("site_id")
        app_id = result.get("app_id") or result_data.get("app_id") or site_id  # Fallback to site_id if app_id not found
        
        if platform == "Android":
            android_site_id = site_id
            android_app_id = app_id
            android_result_data = result
        elif platform == "iOS":
            ios_site_id = site_id
            ios_app_id = app_id
            ios_result_data = result
    
    # Save combined app data with both siteIds and appIds
    app_data = {
        "appCode": app_name,  # Use app name as primary identifier
        "siteId": android_site_id,  # Android siteId (primary)
        "siteIdIOS": ios_site_id,  # iOS siteId
        "appId": android_app_id,  # Android appId (primary)
        "appIdIOS": ios_app_id,  # iOS appId
        "name": app_name,
        "platform": "both" if android_site_id and ios_site_id else ("android" if android_site_id else "ios"),
        "platformStr": "both" if android_site_id and ios_site_id else ("android" if android_site_id else "ios"),
        "downloadUrl": android_download_url if android_download_url else ios_download_url,
        "iosDownloadUrl": ios_download_url,
        "androidDownloadUrl": android_download_url,
        "hasAndroid": bool(android_site_id),
        "hasIOS": bool(ios_site_id)
    }
    SessionManager.add_created_app(current_network, app_data)
    
    # Add both apps to cache
    cached_apps = SessionManager.get_cached_apps(current_network)
    
    if android_site_id:
        android_app = {
            "appCode": str(android_site_id),
            "siteId": str(android_site_id),
            "appId": str(android_app_id) if android_app_id else str(android_site_id),  # Use app_id if available, fallback to site_id
            "name": app_name,
            "platform": "Android",
            "status": "Active",
            "downloadUrl": android_download_url
        }
        if not any(app.get("siteId") == str(android_site_id) for app in cached_apps):
            cached_apps.append(android_app)
    
    if ios_site_id:
        ios_app = {
            "appCode": str(ios_site_id),
            "siteId": str(ios_site_id),
            "appId": str(ios_app_id) if ios_app_id else str(ios_site_id),  # Use app_id if available, fallback to site_id
            "name": app_name,
            "platform": "iOS",
            "status": "Active",
            "downloadUrl": ios_download_url
        }
        if not any(app.get("siteId") == str(ios_site_id) for app in cached_apps):
            cached_apps.append(ios_app)
    
    SessionManager.cache_apps(current_network, cached_apps)
    
    # Show success message
    platforms_str = " and ".join([p for p, _, _ in results])
    st.success(f"🎉 App created successfully for {platforms_str}!")
    st.balloons()
    
    # Show result details
    st.subheader("📝 Result")
    result_col1, result_col2 = st.columns(2)
    with result_col1:
        st.write(f"**Network:** {network_display}")
        st.write(f"**App Name:** {app_name}")
        st.write("**Site ID:**")
        if android_site_id:
            st.write(f"  - **Android:** {android_site_id}")
        if ios_site_id:
            st.write(f"  - **iOS:** {ios_site_id}")
        if not android_site_id and not ios_site_id:
            st.write(f"  N/A")
    with result_col2:
        # Display platforms
        platforms = []
        if android_site_id:
            platforms.append("Android")
        if ios_site_id:
            platforms.append("iOS")
        if platforms:
            st.write(f"**Platform:** {', '.join(platforms)}")
        else:
            st.write(f"**Platform:** N/A")
        
        # Display download URLs
        if android_download_url:
            st.write(f"**Android Download URL:** {android_download_url[:50]}...")


def _process_vungle_create_app_results(current_network: str, network_display: str, form_data: dict, results: List[Tuple[str, dict, dict]]):
    """Process Vungle create app results for multiple platforms
    
    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        results: List of tuples (platform, result, response) for each platform created
    """
    app_name = form_data.get("app_name", "Unknown")
    android_store_id = form_data.get("androidStoreId", "").strip()
    ios_store_id = form_data.get("iosStoreId", "").strip()
    
    # Store app data for each platform
    android_vungle_app_id = None
    ios_vungle_app_id = None
    android_default_placement = None
    ios_default_placement = None
    android_result_data = None
    ios_result_data = None
    
    for platform, result, response in results:
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result
        vungle_app_id = result_data.get("vungleAppId")
        default_placement = result_data.get("defaultPlacement")
        
        if platform == "Android":
            android_vungle_app_id = vungle_app_id
            android_default_placement = default_placement
            android_result_data = result_data
        elif platform == "iOS":
            ios_vungle_app_id = vungle_app_id
            ios_default_placement = default_placement
            ios_result_data = result_data
    
    # Save app data
    app_data = {
        "appCode": android_vungle_app_id or ios_vungle_app_id,  # Use first available app ID
        "vungleAppId": android_vungle_app_id or ios_vungle_app_id,
        "vungleAppIdIOS": ios_vungle_app_id,
        "defaultPlacement": android_default_placement or ios_default_placement,
        "defaultPlacementIOS": ios_default_placement,
        "name": app_name,
        "platform": "both" if android_vungle_app_id and ios_vungle_app_id else ("android" if android_vungle_app_id else "ios"),
        "platformStr": "both" if android_vungle_app_id and ios_vungle_app_id else ("android" if android_vungle_app_id else "ios"),
        "hasAndroid": bool(android_vungle_app_id),
        "hasIOS": bool(ios_vungle_app_id),
        "androidStoreId": android_store_id,  # Store Android Store ID for placement name generation
        "iosStoreId": ios_store_id,  # Store iOS Store ID for placement name generation
    }
    
    SessionManager.save_created_app(current_network, app_data)
    
    # Cache apps for app selector
    cached_apps = SessionManager.get_cached_apps(current_network) or []
    
    if android_vungle_app_id:
        android_app = {
            "appCode": str(android_vungle_app_id),
            "vungleAppId": str(android_vungle_app_id),
            "defaultPlacement": str(android_default_placement) if android_default_placement else None,
            "name": app_name,
            "platform": "Android",
            "status": "Active",
            "androidStoreId": android_store_id,  # Store Android Store ID for placement name generation
        }
        if not any(app.get("vungleAppId") == str(android_vungle_app_id) for app in cached_apps):
            cached_apps.append(android_app)
    
    if ios_vungle_app_id:
        ios_app = {
            "appCode": str(ios_vungle_app_id),
            "vungleAppId": str(ios_vungle_app_id),
            "defaultPlacement": str(ios_default_placement) if ios_default_placement else None,
            "name": app_name,
            "platform": "iOS",
            "status": "Active",
            "iosStoreId": ios_store_id,  # Store iOS Store ID for placement name generation
        }
        if not any(app.get("vungleAppId") == str(ios_vungle_app_id) for app in cached_apps):
            cached_apps.append(ios_app)
    
    SessionManager.cache_apps(current_network, cached_apps)
    
    # Show success message
    platforms_str = " and ".join([p for p, _, _ in results])
    st.success(f"🎉 App created successfully for {platforms_str}!")
    st.balloons()
    
    # Show result details
    st.subheader("📝 Result")
    result_col1, result_col2 = st.columns(2)
    with result_col1:
        st.write(f"**Network:** {network_display}")
        st.write(f"**App Name:** {app_name}")
        # Display platform and app ID clearly
        if android_vungle_app_id:
            st.write(f"**Android:** {android_vungle_app_id}")
        if ios_vungle_app_id:
            st.write(f"**iOS:** {ios_vungle_app_id}")
        if not android_vungle_app_id and not ios_vungle_app_id:
            st.write(f"**App ID:** N/A")
    with result_col2:
        # Display platforms summary
        platforms = []
        if android_vungle_app_id:
            platforms.append("Android")
        if ios_vungle_app_id:
            platforms.append("iOS")
        if platforms:
            st.write(f"**Platform:** {', '.join(platforms)}")
        else:
            st.write(f"**Platform:** N/A")
        
        # Display default placements
        st.write("**Default Placement:**")
        if android_default_placement:
            st.write(f"  - **Android:** {android_default_placement}")
        if ios_default_placement:
            st.write(f"  - **iOS:** {ios_default_placement}")
        if not android_default_placement and not ios_default_placement:
            st.write(f"  N/A")
        if ios_download_url:
            st.write(f"**iOS Download URL:** {ios_download_url[:50]}...")


def _process_mintegral_create_app_results(current_network: str, network_display: str, form_data: dict, results: List[Tuple[str, dict, dict]]):
    """Process Mintegral create app results for multiple platforms

    Args:
        current_network: Current network identifier
        network_display: Display name for the network
        form_data: Form data submitted by user
        results: List of tuples (platform, result, response) for each platform created
    """
    app_name = form_data.get("app_name", "Unknown")
    android_store_url = form_data.get("androidStoreUrl", "").strip()
    ios_store_url = form_data.get("iosStoreUrl", "").strip()

    # Store both app_ids
    android_app_id = None
    ios_app_id = None

    for platform, result, response in results:
        # Mintegral: response has {"status": 0, "code": 0, "msg": "Success", "result": {"app_id": 441875, ...}}
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else {}
        app_id = result_data.get("app_id") or result_data.get("id") or result_data.get("appId")
        if not app_id:
            data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
            app_id = data.get("app_id") or data.get("id") or data.get("appId")
        if not app_id:
            app_id = result.get("app_id") or result.get("id")

        if platform == "Android":
            android_app_id = app_id
        elif platform == "iOS":
            ios_app_id = app_id

    # Save combined app data
    app_data = {
        "appCode": app_name,
        "app_id": android_app_id,
        "app_id_ios": ios_app_id,
        "name": app_name,
        "platform": "both" if android_app_id and ios_app_id else ("android" if android_app_id else "ios"),
        "platformStr": "both" if android_app_id and ios_app_id else ("android" if android_app_id else "ios"),
        "androidStoreUrl": android_store_url,
        "iosStoreUrl": ios_store_url,
        "hasAndroid": bool(android_app_id),
        "hasIOS": bool(ios_app_id)
    }
    SessionManager.add_created_app(current_network, app_data)

    # Add both apps to cache
    cached_apps = SessionManager.get_cached_apps(current_network)

    if android_app_id:
        android_app = {
            "appCode": str(android_app_id),
            "app_id": android_app_id,
            "name": app_name,
            "platform": "Android",
            "status": "Active",
            "storeUrl": android_store_url,
            "package": form_data.get("androidPackage", "")
        }
        if not any(app.get("app_id") == android_app_id for app in cached_apps):
            cached_apps.append(android_app)

    if ios_app_id:
        ios_app = {
            "appCode": str(ios_app_id),
            "app_id": ios_app_id,
            "name": app_name,
            "platform": "iOS",
            "status": "Active",
            "storeUrl": ios_store_url,
            "package": form_data.get("iosPackage", "")
        }
        if not any(app.get("app_id") == ios_app_id for app in cached_apps):
            cached_apps.append(ios_app)

    SessionManager.cache_apps(current_network, cached_apps)

    # Show success message
    platforms_str = " and ".join([p for p, _, _ in results])
    st.success(f"🎉 App created successfully for {platforms_str}!")
    st.balloons()

    # Show result details
    st.subheader("📝 Result")
    result_col1, result_col2 = st.columns(2)
    with result_col1:
        st.write(f"**Network:** {network_display}")
        st.write(f"**App Name:** {app_name}")
        st.write("**App ID:**")
        if android_app_id:
            st.write(f"  - **Android:** {android_app_id}")
        if ios_app_id:
            st.write(f"  - **iOS:** {ios_app_id}")
        if not android_app_id and not ios_app_id:
            st.write(f"  N/A")
    with result_col2:
        platforms = []
        if android_app_id:
            platforms.append("Android")
        if ios_app_id:
            platforms.append("iOS")
        st.write(f"**Platform:** {', '.join(platforms) if platforms else 'N/A'}")
        if android_store_url:
            st.write(f"**Android Store URL:** {android_store_url[:50]}...")
        if ios_store_url:
            st.write(f"**iOS Store URL:** {ios_store_url[:50]}...")

