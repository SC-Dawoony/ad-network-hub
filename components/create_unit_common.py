"""Common Create Unit UI component for networks other than AppLovin and Unity"""
import streamlit as st
import logging
import re
from utils.session_manager import SessionManager
from utils.network_manager import handle_api_response
from components.create_app_helpers import (
    normalize_platform_str as _normalize_platform_str,
    generate_slot_name as _generate_slot_name,
    create_default_slot as _create_default_slot
)

logger = logging.getLogger(__name__)


def render_create_unit_common_ui(
    current_network: str,
    selected_app_code: str,
    app_name: str,
    app_info_to_use: dict,
    apps: list,
    app_info_map: dict,
    network_manager,
    config
):
    """Render common Create Unit UI for networks other than AppLovin and Unity
    
    Args:
        current_network: Current network identifier
        selected_app_code: Selected app code
        app_name: App name
        app_info_to_use: App info dict to use for slot name generation
        apps: List of apps from API
        app_info_map: Map of app codes to app info
        network_manager: Network manager instance
        config: Network config instance
    """
    # Ensure app_info_to_use is available for slot name generation
    last_app_info = SessionManager.get_last_created_app_info(current_network)
    if selected_app_code and not app_info_to_use:
        # Try to get app info again if not already set
        # For IronSource, check if selected_app_code is an app name (grouped app)
        if current_network == "ironsource" and selected_app_code in app_info_map:
            app_info_to_use = app_info_map[selected_app_code]
            # If it's a grouped app, merge with last_app_info if available
            if last_app_info and last_app_info.get("appCode") == selected_app_code:
                # Merge last_app_info data (has both appKeys)
                app_info_to_use["appKey"] = last_app_info.get("appKey", app_info_to_use.get("appKey"))
                app_info_to_use["appKeyIOS"] = last_app_info.get("appKeyIOS", app_info_to_use.get("appKeyIOS"))
                app_info_to_use["platform"] = last_app_info.get("platform", app_info_to_use.get("platform"))
                app_info_to_use["platformStr"] = last_app_info.get("platformStr", app_info_to_use.get("platformStr"))
                app_info_to_use["hasAndroid"] = last_app_info.get("hasAndroid", app_info_to_use.get("hasAndroid", False))
                app_info_to_use["hasIOS"] = last_app_info.get("hasIOS", app_info_to_use.get("hasIOS", False))
        elif last_app_info and last_app_info.get("appCode") == selected_app_code:
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
                        # Use _normalize_platform_str to handle different platform formats (e.g., "ANDROID", "IOS" for Mintegral)
                        platform_str_val = _normalize_platform_str(platform_str, current_network)
                        platform_num = 1 if platform_str_val == "android" else 2
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
        # Check if there are results from previous batch creation
        batch_results_key = f"{current_network}_batch_create_results"
        if batch_results_key in st.session_state and st.session_state[batch_results_key]:
            results = st.session_state[batch_results_key]
            st.success("🎉 Finished creating slots!")
            st.balloons()
            
            # Display created slots
            st.subheader("📋 Created Slots")
            for result in results:
                if result["status"] == "success":
                    st.success(f"✅ {result['type']} slot created successfully")
                else:
                    st.error(f"❌ {result['type']} slot failed: {result.get('error', 'Unknown error')}")
            
            # Clear results after displaying (optional - remove if you want to keep them)
            # st.session_state[batch_results_key] = None
        
        if st.button("✨ Create All 3 Slots (RV + IS + BN)", use_container_width=True, type="primary"):
            # Validate app_info_to_use before creating slots
            if not app_info_to_use:
                st.error("❌ App information is required. Please select an app first.")
                logger.error("[BigOAds] app_info_to_use is None or empty")
            elif not app_info_to_use.get("appCode") and not app_info_to_use.get("appId"):
                st.error("❌ App Code is required. Please select an app first.")
                logger.error(f"[BigOAds] app_info_to_use missing appCode: {app_info_to_use}")
            else:
                with st.spinner("Creating all 3 slots..."):
                    results = []
                    for slot_type in ["rv", "is", "bn"]:
                        try:
                            _create_default_slot(current_network, app_info_to_use, slot_type, network_manager, config)
                            results.append({"type": slot_type.upper(), "status": "success"})
                        except Exception as e:
                            error_msg = str(e)
                            logger.error(f"[BigOAds] Error creating {slot_type.upper()} slot: {error_msg}")
                            results.append({"type": slot_type.upper(), "status": "error", "error": error_msg})
                
                # Store results in session state to persist across reruns
                st.session_state[batch_results_key] = results
                
                # Show results immediately
                st.success("🎉 Finished creating slots!")
                st.balloons()
                
                # Display created slots
                st.subheader("📋 Created Slots")
                for result in results:
                    if result["status"] == "success":
                        st.success(f"✅ {result['type']} slot created successfully")
                    else:
                        st.error(f"❌ {result['type']} slot failed: {result.get('error', 'Unknown error')}")
                
                # Don't rerun - keep the results visible
                # st.rerun()
    
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
            "bannerAutoRefresh": 2,
            "bannerSizeMode": 2,
            "bannerSizeW": 250,
            "bannerSizeH": 320,
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
            "skipability": "NonSkippable",  # Default: NonSkippable for Interstitial
        },
        "BN": {
            "name": "Banner",
            "placementType": "Banner",
            "coppa": False,
        }
    }
    
    # Default slot configurations for AdMob
    slot_configs_admob = {
        "RV": {
            "name": "Rewarded",
            "format": "REWARDED",
        },
        "IS": {
            "name": "Interstitial",
            "format": "INTERSTITIAL",
        },
        "BN": {
            "name": "Banner",
            "format": "BANNER",
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
    elif current_network == "admob":
        slot_configs = slot_configs_admob
    else:
        slot_configs = slot_configs_bigoads
    
    # For IronSource, "Activate All Ad Units" button is no longer needed
    # Create Ad Unit already activates them automatically
    # The entire activate button section has been removed
    
    # For IronSource, skip RV/IS/BN sections and only show instance results
    if current_network == "ironsource":
        # IronSource Create Ad Unit section
        # Get app keys from Create App response (default) - minimize space
        ironsource_response_key = f"{current_network}_last_app_response"
        ironsource_response = st.session_state.get(ironsource_response_key)
        
        default_android_app_key = None
        default_ios_app_key = None
        default_app_name = None
        
        if ironsource_response and ironsource_response.get("status") == 0:
            result_data = ironsource_response.get("result", {})
            if isinstance(result_data, list):
                for res in result_data:
                    platform = res.get("platform", "")
                    if platform == "Android":
                        default_android_app_key = res.get("appKey")
                    elif platform == "iOS":
                        default_ios_app_key = res.get("appKey")
                    if not default_app_name:
                        default_app_name = res.get("name")
            else:
                platform = result_data.get("platform", "")
                if platform == "Android":
                    default_android_app_key = result_data.get("appKey")
                elif platform == "iOS":
                    default_ios_app_key = result_data.get("appKey")
                default_app_name = result_data.get("name")
        
        # Also check session state for app info
        last_app_info = SessionManager.get_last_created_app_info(current_network)
        if last_app_info:
            default_android_app_key = default_android_app_key or last_app_info.get("appKey")
            default_ios_app_key = default_ios_app_key or last_app_info.get("appKeyIOS")
            default_app_name = default_app_name or last_app_info.get("name")
        
        # App list 조회를 expander로 감싸기 (Deactivate Existing Ad Units처럼)
        with st.expander("📝 App List 조회", expanded=True):
            # App list API 조회 버튼과 Select App을 한 줄에 배치
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("🔍 GET App List (API 조회)", use_container_width=True, key="ironsource_fetch_app_list_for_create_unit"):
                    with st.spinner("Loading apps from API..."):
                        try:
                            api_apps = network_manager.get_apps(current_network)
                            if api_apps:
                                st.session_state["ironsource_api_apps_for_create_unit"] = api_apps
                                st.success(f"✅ Loaded {len(api_apps)} apps from API")
                            else:
                                st.warning("⚠️ No apps found")
                        except Exception as e:
                            st.error(f"❌ Failed to load apps: {str(e)}")
                            logger.exception("Error loading IronSource apps for create unit")
            
            # Display app list if available
            android_app_key = default_android_app_key
            ios_app_key = default_ios_app_key
            
            with col2:
                if "ironsource_api_apps_for_create_unit" in st.session_state:
                    api_apps = st.session_state["ironsource_api_apps_for_create_unit"]
                    if api_apps:
                        # Group apps by name (Android + iOS)
                        app_groups = {}
                        for app in api_apps:
                            app_name_group = app.get("name", "Unknown")
                            platform = app.get("platform", "").lower()
                            app_key = app.get("appKey", "")
                            
                            if app_name_group not in app_groups:
                                app_groups[app_name_group] = {"android": None, "ios": None, "android_bundle": None, "ios_bundle": None, "app_name": app_name_group}
                            
                            if platform == "android" and app_key:
                                app_groups[app_name_group]["android"] = app_key
                                app_groups[app_name_group]["android_bundle"] = app.get("bundleId", "")
                            elif platform == "ios" and app_key:
                                app_groups[app_name_group]["ios"] = app_key
                                app_groups[app_name_group]["ios_bundle"] = app.get("bundleId", "")
                        
                        # Display grouped apps
                        selected_app_name = st.selectbox(
                            "Select App",
                            options=[""] + list(app_groups.keys()),
                            format_func=lambda x: f"{x} (Android + iOS)" if x and app_groups.get(x, {}).get("android") and app_groups.get(x, {}).get("ios") else (f"{x} (Android)" if x and app_groups.get(x, {}).get("android") else (f"{x} (iOS)" if x and app_groups.get(x, {}).get("ios") else x)),
                            key="ironsource_select_app_for_create_unit"
                        )
                        
                        if selected_app_name and selected_app_name in app_groups:
                            selected_group = app_groups[selected_app_name]
                            if selected_group["android"]:
                                android_app_key = selected_group["android"]
                                st.session_state["_ironsource_selected_android_app_key"] = selected_group["android"]
                                st.session_state["_ironsource_android_bundle_id"] = selected_group["android_bundle"]
                            if selected_group["ios"]:
                                ios_app_key = selected_group["ios"]
                                st.session_state["_ironsource_selected_ios_app_key"] = selected_group["ios"]
                                st.session_state["_ironsource_ios_bundle_id"] = selected_group["ios_bundle"]
                            if selected_group["app_name"]:
                                default_app_name = selected_group["app_name"]
        
        if not android_app_key and not ios_app_key:
            st.info("💡 App Key를 입력하거나 Create App을 먼저 실행해주세요.")
        else:
            # Create Ad Units for Android
            if android_app_key:
                st.markdown("### Android")
                
                # Get bundleId and app_name from API or session state
                bundle_id = st.session_state.get("_ironsource_android_bundle_id", "")
                app_name_for_slot = default_app_name or ""
                
                # Try to get from API apps list if available
                if not bundle_id and "ironsource_api_apps_for_create_unit" in st.session_state:
                    api_apps = st.session_state["ironsource_api_apps_for_create_unit"]
                    for app in api_apps:
                        if app.get("appKey") == android_app_key and app.get("platform", "").lower() == "android":
                            bundle_id = app.get("bundleId", "")
                            app_name_for_slot = app.get("name", app_name_for_slot)
                            break
                
                # Try to get from last_app_info
                if not bundle_id and last_app_info:
                    android_app = last_app_info.get("androidApp", {})
                    bundle_id = android_app.get("bundleId") or last_app_info.get("bundleId", "")
                    app_name_for_slot = app_name_for_slot or last_app_info.get("name", "")
                
                # Check if bundleId is available before proceeding
                if not bundle_id:
                    st.warning("⚠️ Bundle ID를 찾을 수 없습니다. API에서 App을 조회해주세요.")
                    st.stop()
                
                # Generate slot names for Android
                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                ad_format_map = {"RV": "rewarded", "IS": "interstitial", "BN": "banner"}
                android_ad_units = []
                for slot_key in ["RV", "IS", "BN"]:
                    slot_type = slot_type_map.get(slot_key, slot_key.lower())
                    slot_name = _generate_slot_name("", "android", slot_type, "ironsource", store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                    android_ad_units.append({
                        "slot_key": slot_key,
                        "slot_name": slot_name,
                        "ad_format": ad_format_map[slot_key]
                    })
                    
                # Display RV, IS, BN sections (버튼 높이 맞추기)
                # 버튼 높이를 맞추기 위한 CSS (한 번만 적용)
                st.markdown("""
                <style>
                div[data-testid='column']:has(button[key*='create_android_rv_ad_unit']) > div,
                div[data-testid='column']:has(button[key*='create_android_is_ad_unit']) > div,
                div[data-testid='column']:has(button[key*='create_android_bn_ad_unit']) > div {
                    display: flex !important;
                    flex-direction: column !important;
                    height: 100% !important;
                }
                div[data-testid='column']:has(button[key*='create_android_rv_ad_unit']) button,
                div[data-testid='column']:has(button[key*='create_android_is_ad_unit']) button,
                div[data-testid='column']:has(button[key*='create_android_bn_ad_unit']) button {
                    margin-top: auto !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                slot_names = {"RV": "Reward Video", "IS": "Interstitial", "BN": "Banner"}
                
                for idx, ad_unit in enumerate(android_ad_units):
                    with [col1, col2, col3][idx]:
                        # 높이를 맞추기 위해 container 사용
                        with st.container():
                            st.markdown(f"### 🎯 {ad_unit['slot_key']} ({slot_names[ad_unit['slot_key']]})")
                            st.write(f"**Slot Name:** {ad_unit['slot_name']}")
                            st.write(f"**Ad Format:** {ad_unit['ad_format']}")
                            # Display reward settings for RV
                            if ad_unit['ad_format'] == "rewarded":
                                st.write(f"**Reward Item Name:** Reward")
                                st.write(f"**Reward Amount:** 1")
                            else:
                                # 높이 맞추기 위해 빈 공간 추가 (RV의 Reward Item Name + Reward Amount와 같은 높이)
                                st.write("")  # IS, BN의 경우 빈 줄 추가
                                st.write("")
                            
                            if st.button(f"✨ Create {ad_unit['slot_key']} Ad Unit", use_container_width=True, type="primary", key=f"create_android_{ad_unit['slot_key'].lower()}_ad_unit"):
                                with st.spinner(f"🚀 Creating Android {ad_unit['slot_key']} ad unit..."):
                                    try:
                                        payload = {
                                            "mediationAdUnitName": ad_unit['slot_name'],
                                            "adFormat": ad_unit['ad_format']
                                        }
                                        # Add reward object for rewarded ad format (required by API)
                                        if ad_unit['ad_format'] == "rewarded":
                                            payload["reward"] = {
                                                "rewardItemName": "Reward",
                                                "rewardAmount": 1
                                            }
                                        
                                        create_response = network_manager._create_ironsource_placements(android_app_key, [payload])
                                        result = handle_api_response(create_response)
                                        
                                        # Check if response indicates success (status 0 or code 0, even with empty result)
                                        if create_response.get("status") == 0 or create_response.get("code") == 0:
                                            # After creating, automatically activate it
                                            with st.spinner("✅ Activating created ad unit..."):
                                                from utils.ad_network_query import get_ironsource_units
                                                existing_units = get_ironsource_units(android_app_key)
                                                
                                                if existing_units:
                                                    for unit in existing_units:
                                                        mediation_adunit_id = unit.get("mediationAdUnitId") or unit.get("mediationAdunitId") or unit.get("id")
                                                        if mediation_adunit_id:
                                                            unit_name = unit.get("mediationAdUnitName", "")
                                                            if unit_name == ad_unit['slot_name']:
                                                                activate_payload = [{
                                                                    "mediationAdUnitId": mediation_adunit_id,
                                                                    "isPaused": False
                                                                }]
                                                                activate_response = network_manager._update_ironsource_ad_units(android_app_key, activate_payload)
                                                                if activate_response.get("status") == 0:
                                                                    st.success(f"✅ Successfully created and activated Android {ad_unit['slot_key']} ad unit!")
                                                                else:
                                                                    st.success(f"✅ Successfully created Android {ad_unit['slot_key']} ad unit!")
                                                                    st.warning("⚠️ Created but activation failed. Please activate manually.")
                                                                break
                                                else:
                                                    st.success(f"✅ Successfully created Android {ad_unit['slot_key']} ad unit!")
                                            
                                            st.balloons()
                                        else:
                                            # Error already displayed by handle_api_response
                                            pass
                                    except Exception as e:
                                        st.error(f"❌ Error creating Android {ad_unit['slot_key']} ad unit: {str(e)}")
                                        logger.exception(f"Error creating IronSource Android {ad_unit['slot_key']} ad unit")
                
                # Use unique key with app_code to avoid duplicate key errors
                button_key_android = f"create_android_ad_units_{selected_app_code}_{app_name}"
                if st.button("✨ Create All 3 Ad Units (Android: RV, IS, BN)", use_container_width=True, type="primary", key=button_key_android):
                    with st.spinner("🚀 Creating Android ad units..."):
                        try:
                            create_payloads = []
                            for ad_unit in android_ad_units:
                                payload = {
                                    "mediationAdUnitName": ad_unit['slot_name'],
                                    "adFormat": ad_unit['ad_format']
                                }
                                # Add reward object for rewarded ad format (required by API)
                                if ad_unit['ad_format'] == "rewarded":
                                    payload["reward"] = {
                                        "rewardItemName": "Reward",
                                        "rewardAmount": 1
                                    }
                                create_payloads.append(payload)
                            
                            create_response = network_manager._create_ironsource_placements(android_app_key, create_payloads)
                            result = handle_api_response(create_response)
                            
                            # Check if response indicates success (status 0 or code 0, even with empty result)
                            if create_response.get("status") == 0 or create_response.get("code") == 0:
                                # After creating, automatically activate them
                                with st.spinner("✅ Activating created ad units..."):
                                    from utils.ad_network_query import get_ironsource_units
                                    existing_units = get_ironsource_units(android_app_key)
                                    
                                    if existing_units:
                                        activate_payloads = []
                                        for unit in existing_units:
                                            # GET API returns mediationAdUnitId (uppercase U)
                                            mediation_adunit_id = unit.get("mediationAdUnitId") or unit.get("mediationAdunitId") or unit.get("id")
                                            if mediation_adunit_id:
                                                # Check if this unit matches one we just created
                                                unit_name = unit.get("mediationAdUnitName", "")
                                                if any(unit_name == ad_unit['slot_name'] for ad_unit in android_ad_units):
                                                    activate_payloads.append({
                                                        "mediationAdUnitId": mediation_adunit_id,  # uppercase U
                                                        "isPaused": False
                                                    })
                                        
                                        if activate_payloads:
                                            activate_response = network_manager._update_ironsource_ad_units(android_app_key, activate_payloads)
                                            if activate_response.get("status") == 0:
                                                st.success(f"✅ Successfully created and activated {len(create_payloads)} Android ad units!")
                                            else:
                                                st.success(f"✅ Successfully created {len(create_payloads)} Android ad units!")
                                                st.warning("⚠️ Created but activation failed. Please activate manually.")
                                        else:
                                            st.success(f"✅ Successfully created {len(create_payloads)} Android ad units!")
                                    else:
                                        st.success(f"✅ Successfully created {len(create_payloads)} Android ad units!")
                                
                                st.balloons()
                            else:
                                # Error already displayed by handle_api_response
                                pass
                        except Exception as e:
                            st.error(f"❌ Error creating Android ad units: {str(e)}")
                            logger.exception("Error creating IronSource Android ad units")
            
            # Create Ad Units for iOS
            if ios_app_key:
                st.markdown("### iOS")
                
                # Get bundleId and app_name from API or session state
                bundle_id = st.session_state.get("_ironsource_ios_bundle_id", "")
                app_name_for_slot = default_app_name or ""
                
                # Try to get from API apps list if available
                if not bundle_id and "ironsource_api_apps_for_create_unit" in st.session_state:
                    api_apps = st.session_state["ironsource_api_apps_for_create_unit"]
                    for app in api_apps:
                        if app.get("appKey") == ios_app_key and app.get("platform", "").lower() == "ios":
                            bundle_id = app.get("bundleId", "")
                            app_name_for_slot = app.get("name", app_name_for_slot)
                            break
                
                # Try to get from last_app_info
                if not bundle_id and last_app_info:
                    ios_app = last_app_info.get("iosApp", {})
                    bundle_id = ios_app.get("bundleId") or last_app_info.get("bundleIdIOS", "")
                    app_name_for_slot = app_name_for_slot or last_app_info.get("name", "")
                
                # Check if bundleId is available before proceeding
                if not bundle_id:
                    st.warning("⚠️ Bundle ID를 찾을 수 없습니다. API에서 App을 조회해주세요.")
                    st.stop()
                
                # Generate slot names for iOS
                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                ad_format_map = {"RV": "rewarded", "IS": "interstitial", "BN": "banner"}
                ios_ad_units = []
                for slot_key in ["RV", "IS", "BN"]:
                    slot_type = slot_type_map.get(slot_key, slot_key.lower())
                    slot_name = _generate_slot_name("", "ios", slot_type, "ironsource", store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                    ios_ad_units.append({
                        "slot_key": slot_key,
                        "slot_name": slot_name,
                        "ad_format": ad_format_map[slot_key]
                    })
                    
                # Display RV, IS, BN sections (버튼 높이 맞추기)
                # 버튼 높이를 맞추기 위한 CSS (한 번만 적용)
                st.markdown("""
                <style>
                div[data-testid='column']:has(button[key*='create_ios_rv_ad_unit']) > div,
                div[data-testid='column']:has(button[key*='create_ios_is_ad_unit']) > div,
                div[data-testid='column']:has(button[key*='create_ios_bn_ad_unit']) > div {
                    display: flex !important;
                    flex-direction: column !important;
                    height: 100% !important;
                }
                div[data-testid='column']:has(button[key*='create_ios_rv_ad_unit']) button,
                div[data-testid='column']:has(button[key*='create_ios_is_ad_unit']) button,
                div[data-testid='column']:has(button[key*='create_ios_bn_ad_unit']) button {
                    margin-top: auto !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                slot_names = {"RV": "Reward Video", "IS": "Interstitial", "BN": "Banner"}
                
                for idx, ad_unit in enumerate(ios_ad_units):
                    with [col1, col2, col3][idx]:
                        # 높이를 맞추기 위해 container 사용
                        with st.container():
                            st.markdown(f"### 🎯 {ad_unit['slot_key']} ({slot_names[ad_unit['slot_key']]})")
                            st.write(f"**Slot Name:** {ad_unit['slot_name']}")
                            st.write(f"**Ad Format:** {ad_unit['ad_format']}")
                            
                            # RV의 경우 Reward 정보 표시, IS/BN의 경우 빈 공간으로 높이 맞추기
                            if ad_unit['ad_format'] == "rewarded":
                                st.write(f"**Reward Item Name:** Reward")
                                st.write(f"**Reward Amount:** 1")
                            else:
                                # IS, BN의 경우 RV의 Reward Item Name + Reward Amount와 같은 높이를 위해 빈 줄 추가
                                st.write("")  # 빈 줄 1
                                st.write("")  # 빈 줄 2
                            
                            if st.button(f"✨ Create {ad_unit['slot_key']} Ad Unit", use_container_width=True, type="primary", key=f"create_ios_{ad_unit['slot_key'].lower()}_ad_unit"):
                                with st.spinner(f"🚀 Creating iOS {ad_unit['slot_key']} ad unit..."):
                                    try:
                                        payload = {
                                            "mediationAdUnitName": ad_unit['slot_name'],
                                            "adFormat": ad_unit['ad_format']
                                        }
                                        # Add reward object for rewarded ad format (required by API)
                                        if ad_unit['ad_format'] == "rewarded":
                                            payload["reward"] = {
                                                "rewardItemName": "Reward",
                                                "rewardAmount": 1
                                            }
                                        
                                        create_response = network_manager._create_ironsource_placements(ios_app_key, [payload])
                                        result = handle_api_response(create_response)
                                        
                                        # Check if response indicates success (status 0 or code 0, even with empty result)
                                        if create_response.get("status") == 0 or create_response.get("code") == 0:
                                            # After creating, automatically activate it
                                            with st.spinner("✅ Activating created ad unit..."):
                                                from utils.ad_network_query import get_ironsource_units
                                                existing_units = get_ironsource_units(ios_app_key)
                                                
                                                if existing_units:
                                                    for unit in existing_units:
                                                        mediation_adunit_id = unit.get("mediationAdUnitId") or unit.get("mediationAdunitId") or unit.get("id")
                                                        if mediation_adunit_id:
                                                            unit_name = unit.get("mediationAdUnitName", "")
                                                            if unit_name == ad_unit['slot_name']:
                                                                activate_payload = [{
                                                                    "mediationAdUnitId": mediation_adunit_id,
                                                                    "isPaused": False
                                                                }]
                                                                activate_response = network_manager._update_ironsource_ad_units(ios_app_key, activate_payload)
                                                                if activate_response.get("status") == 0:
                                                                    st.success(f"✅ Successfully created and activated iOS {ad_unit['slot_key']} ad unit!")
                                                                else:
                                                                    st.success(f"✅ Successfully created iOS {ad_unit['slot_key']} ad unit!")
                                                                    st.warning("⚠️ Created but activation failed. Please activate manually.")
                                                                break
                                                else:
                                                    st.success(f"✅ Successfully created iOS {ad_unit['slot_key']} ad unit!")
                                            
                                            st.balloons()
                                        else:
                                            # Error already displayed by handle_api_response
                                            pass
                                    except Exception as e:
                                        st.error(f"❌ Error creating iOS {ad_unit['slot_key']} ad unit: {str(e)}")
                                        logger.exception(f"Error creating IronSource iOS {ad_unit['slot_key']} ad unit")
                
                # Use unique key with app_code to avoid duplicate key errors
                button_key_ios = f"create_ios_ad_units_{selected_app_code}_{app_name}"
                if st.button("✨ Create All 3 Ad Units (iOS: RV, IS, BN)", use_container_width=True, type="primary", key=button_key_ios):
                    with st.spinner("🚀 Creating iOS ad units..."):
                        try:
                            create_payloads = []
                            for ad_unit in ios_ad_units:
                                payload = {
                                    "mediationAdUnitName": ad_unit['slot_name'],
                                    "adFormat": ad_unit['ad_format']
                                }
                                # Add reward object for rewarded ad format (required by API)
                                if ad_unit['ad_format'] == "rewarded":
                                    payload["reward"] = {
                                        "rewardItemName": "Reward",
                                        "rewardAmount": 1
                                    }
                                create_payloads.append(payload)
                            
                            create_response = network_manager._create_ironsource_placements(ios_app_key, create_payloads)
                            result = handle_api_response(create_response)
                            
                            # Check if response indicates success (status 0 or code 0, even with empty result)
                            if create_response.get("status") == 0 or create_response.get("code") == 0:
                                # After creating, automatically activate them
                                with st.spinner("✅ Activating created ad units..."):
                                    from utils.ad_network_query import get_ironsource_units
                                    existing_units = get_ironsource_units(ios_app_key)
                                    
                                    if existing_units:
                                        activate_payloads = []
                                        for unit in existing_units:
                                            # GET API returns mediationAdUnitId (uppercase U)
                                            mediation_adunit_id = unit.get("mediationAdUnitId") or unit.get("mediationAdunitId") or unit.get("id")
                                            if mediation_adunit_id:
                                                # Check if this unit matches one we just created
                                                unit_name = unit.get("mediationAdUnitName", "")
                                                if any(unit_name == ad_unit['slot_name'] for ad_unit in ios_ad_units):
                                                    activate_payloads.append({
                                                        "mediationAdUnitId": mediation_adunit_id,  # uppercase U
                                                        "isPaused": False
                                                    })
                                        
                                        if activate_payloads:
                                            activate_response = network_manager._update_ironsource_ad_units(ios_app_key, activate_payloads)
                                            if activate_response.get("status") == 0:
                                                st.success(f"✅ Successfully created and activated {len(create_payloads)} iOS ad units!")
                                            else:
                                                st.success(f"✅ Successfully created {len(create_payloads)} iOS ad units!")
                                                st.warning("⚠️ Created but activation failed. Please activate manually.")
                                        else:
                                            st.success(f"✅ Successfully created {len(create_payloads)} iOS ad units!")
                                    else:
                                        st.success(f"✅ Successfully created {len(create_payloads)} iOS ad units!")
                                
                                st.balloons()
                            else:
                                # Error already displayed by handle_api_response
                                pass
                        except Exception as e:
                            st.error(f"❌ Error creating iOS ad units: {str(e)}")
                            logger.exception("Error creating IronSource iOS ad units")
    else:
        st.divider()
        
        # For InMobi, add "Create All 3 Placements" button
        if current_network == "inmobi":
            # Get app info for InMobi
            app_id = None
            bundle_id = ""
            pkg_name = ""
            platform_str = "android"
            app_name_for_slot = app_name
            
            if selected_app_code:
                if app_info_to_use:
                    app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId")
                    bundle_id = app_info_to_use.get("bundleId", "")
                    pkg_name = app_info_to_use.get("pkgName", "")
                    platform_str = _normalize_platform_str(app_info_to_use.get("platformStr", "android"), "inmobi")
                    app_name_for_slot = app_info_to_use.get("name", app_name)
                
                if not app_id:
                    try:
                        app_id = int(selected_app_code)
                    except (ValueError, TypeError):
                        app_id = None
                
                if not app_id or not bundle_id:
                    for app in apps:
                        app_identifier = app.get("appId") or app.get("appCode")
                        if str(app_identifier) == str(selected_app_code):
                            if not app_id:
                                app_id = app.get("appId") or app.get("app_id")
                                if not app_id:
                                    try:
                                        app_id = int(app_identifier)
                                    except (ValueError, TypeError):
                                        app_id = None
                            if not bundle_id:
                                bundle_id = app.get("bundleId", "")
                                pkg_name = app.get("pkgName", "")
                                platform_from_app = app.get("platform", "")
                                platform_str = _normalize_platform_str(platform_from_app, "inmobi")
                                app_name_for_slot = app.get("name", app_name)
                            break
            
            # Create All 3 Placements button
            if st.button("✨ Create All 3 Placements (RV + IS + BN)", use_container_width=True, type="primary", key="create_all_inmobi_placements"):
                if not selected_app_code:
                    st.toast("❌ Please select an App Code", icon="🚫")
                else:
                    # Ensure app_id is a valid integer
                    try:
                        app_id_int = int(app_id) if app_id else None
                        if not app_id_int or app_id_int <= 0:
                            st.toast("❌ App ID is required. Please select an App Code.", icon="🚫")
                        else:
                            app_id = app_id_int  # Use the integer version
                            source_pkg = bundle_id if bundle_id else pkg_name
                            if not source_pkg:
                                st.toast("❌ Package name or bundle ID is required", icon="🚫")
                            else:
                                with st.spinner("🚀 Creating all 3 placements..."):
                                    try:
                                        from utils.network_manager import get_network_manager
                                        network_manager = get_network_manager()
                                        
                                        slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                                        create_payloads = []
                                        placement_names = []
                                        
                                        for slot_key in ["RV", "IS", "BN"]:
                                            slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                            slot_config = slot_configs.get(slot_key, {})
                                            placement_name = _generate_slot_name(source_pkg, platform_str, slot_type, "inmobi", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                                            placement_names.append((slot_key, placement_name))
                                            
                                            payload = {
                                                "appId": int(app_id),
                                                "placementName": placement_name,
                                                "placementType": slot_config["placementType"],
                                                "isAudienceBiddingEnabled": slot_config["isAudienceBiddingEnabled"],
                                            }
                                            
                                            if slot_config["isAudienceBiddingEnabled"]:
                                                payload["audienceBiddingPartner"] = slot_config["audienceBiddingPartner"]
                                            
                                            create_payloads.append((slot_key, slot_config, payload))
                                        
                                        # Create placements sequentially
                                        results = []
                                        for slot_key, slot_config, payload in create_payloads:
                                            response = network_manager.create_unit(current_network, payload)
                                            result = handle_api_response(response)
                                            results.append((slot_key, response, result))
                                        
                                        # Process results
                                        success_count = 0
                                        failed_count = 0
                                        
                                        for slot_key, response, result in results:
                                            if response.get("status") == 0 or response.get("code") == 0:
                                                success_count += 1
                                                if result:
                                                    placement_name = next((name for sk, name in placement_names if sk == slot_key), "")
                                                    unit_data = {
                                                        "slotCode": result.get("placementId", result.get("id", "N/A")),
                                                        "name": placement_name,
                                                        "appCode": str(app_id),
                                                        "slotType": slot_config["placementType"],
                                                        "adType": slot_config["placementType"],
                                                        "auctionType": "N/A"
                                                    }
                                                    SessionManager.add_created_unit(current_network, unit_data)
                                                    
                                                    cached_units = SessionManager.get_cached_units(current_network, str(app_id))
                                                    if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                        cached_units.append(unit_data)
                                                        SessionManager.cache_units(current_network, str(app_id), cached_units)
                                            else:
                                                failed_count += 1
                                        
                                        # Display summary
                                        if success_count == 3:
                                            st.success(f"✅ Successfully created all 3 placements!")
                                            st.balloons()
                                        elif success_count > 0:
                                            st.warning(f"⚠️ Created {success_count} placements, {failed_count} failed")
                                        else:
                                            st.error(f"❌ Failed to create placements")
                                        
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error creating placements: {str(e)}")
                                        logger.exception("Error creating InMobi placements")
                    except (ValueError, TypeError) as e:
                        st.toast(f"❌ Invalid App ID: {app_id}", icon="🚫")
                        logger.exception(f"Invalid App ID for InMobi: {app_id}")
        
        # For AdMob, add "Create All 3 Ad Units" button
        if current_network == "admob":
            # Get app info for AdMob
            app_id = None
            app_store_id = None
            pkg_name = ""
            platform_str = "android"
            app_name_for_slot = app_name
            
            if selected_app_code:
                if app_info_to_use:
                    app_id = app_info_to_use.get("appId") or app_info_to_use.get("appIdAndroid") or app_info_to_use.get("appIdIOS")
                    app_store_id = app_info_to_use.get("androidAppStoreId") or app_info_to_use.get("iosAppStoreId")
                    # For AdMob, get appStoreId from linkedAppInfo
                    linked_info = app_info_to_use.get("linkedAppInfo", {})
                    if linked_info:
                        app_store_id = linked_info.get("appStoreId") or app_store_id
                    pkg_name = app_store_id or app_info_to_use.get("pkgName", "")
                    platform_str = app_info_to_use.get("platformStr", "android")
                    app_name_for_slot = app_info_to_use.get("name", app_name)
                    
                    if platform_str == "both":
                        platform_str = "android"
                        if not pkg_name:
                            # For AdMob, try to get from linkedAppInfo
                            android_linked_info = app_info_to_use.get("linkedAppInfo", {})
                            if android_linked_info:
                                pkg_name = android_linked_info.get("appStoreId") or app_info_to_use.get("androidAppStoreId")
                            else:
                                pkg_name = app_info_to_use.get("androidAppStoreId")
                
                if not app_id and not app_store_id:
                    for app in apps:
                        app_identifier = app.get("appId") or app.get("appCode")
                        if str(app_identifier) == str(selected_app_code):
                            app_id = app.get("appId")
                            # For AdMob, get appStoreId from linkedAppInfo
                            linked_info = app.get("linkedAppInfo", {})
                            app_store_id = linked_info.get("appStoreId") if linked_info else app.get("appStoreId")
                            pkg_name = app_store_id or app.get("pkgName", "")
                            platform_str_val = app.get("platform", "")
                            platform_str = "android" if platform_str_val == "ANDROID" else ("ios" if platform_str_val == "IOS" else "android")
                            app_name_for_slot = app.get("name", app_name)
                            break
            
            # Create All 3 Ad Units button
            if st.button("✨ Create All 3 Ad Units (RV + IS + BN)", use_container_width=True, type="primary", key="create_all_admob_ad_units"):
                if not selected_app_code:
                    st.toast("❌ Please select an App Code", icon="🚫")
                elif not app_id and not app_store_id:
                    st.toast("❌ App ID or App Store ID is required. Please select an App Code.", icon="🚫")
                elif not pkg_name:
                    st.toast("❌ Package name or App Store ID is required", icon="🚫")
                else:
                    with st.spinner("🚀 Creating all 3 ad units..."):
                        try:
                            from utils.network_manager import get_network_manager
                            network_manager = get_network_manager()
                            
                            slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                            format_map = {
                                "RV": "REWARDED",
                                "IS": "INTERSTITIAL",
                                "BN": "BANNER"
                            }
                            create_payloads = []
                            display_names = []
                            
                            for slot_key in ["RV", "IS", "BN"]:
                                slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                ad_format = format_map.get(slot_key, "REWARDED")
                                
                                # For AdMob, use linkedAppInfo.appStoreId's last part after "."
                                # If iOS and appStoreId is numeric only, find Android app with same name
                                display_name_pkg = pkg_name
                                
                                # Check if iOS and appStoreId is numeric only (iTunes ID)
                                if platform_str == "ios" and app_store_id and app_store_id.strip().isdigit():
                                    # Find Android app with same name
                                    logger.info(f"[AdMob] iOS appStoreId is numeric ({app_store_id}), searching for Android app with same name: {app_name_for_slot}")
                                    for app in apps:
                                        app_name_match = app.get("name", "")
                                        app_platform = app.get("platform", "")
                                        if app_name_match == app_name_for_slot and app_platform == "ANDROID":
                                            # Use Android app's linkedAppInfo.appStoreId
                                            android_linked_info = app.get("linkedAppInfo", {})
                                            android_app_store_id = android_linked_info.get("appStoreId") if android_linked_info else app.get("appStoreId")
                                            if android_app_store_id:
                                                display_name_pkg = android_app_store_id
                                                logger.info(f"[AdMob] Found Android app with same name, using appStoreId: {android_app_store_id}")
                                                break
                                
                                # Extract last part after "." for display name
                                if display_name_pkg and "." in display_name_pkg:
                                    last_part = display_name_pkg.split(".")[-1]
                                else:
                                    last_part = display_name_pkg if display_name_pkg else "app"
                                
                                # Format: {last_part}_{os}_admob_{adtype}_bidding
                                os_str = "aos" if platform_str == "android" else "ios"
                                display_name = f"{last_part}_{os_str}_admob_{slot_type}_bidding"
                                
                                display_names.append((slot_key, display_name))
                                
                                payload = {
                                    "displayName": display_name,
                                    "format": ad_format
                                }
                                
                                if app_id:
                                    payload["appId"] = app_id
                                elif app_store_id:
                                    payload["appStoreId"] = app_store_id
                                
                                create_payloads.append((slot_key, payload))
                            
                            # Create ad units sequentially
                            results = []
                            for slot_key, payload in create_payloads:
                                response = network_manager.create_unit(current_network, payload)
                                result = handle_api_response(response)
                                results.append((slot_key, response, result))
                            
                            # Process results
                            success_count = 0
                            failed_count = 0
                            
                            for slot_key, response, result in results:
                                if response.get("status") == 0 or response.get("code") == 0:
                                    success_count += 1
                                    if result:
                                        display_name = next((name for sk, name in display_names if sk == slot_key), "")
                                        result_data = result.get("result", {})
                                        if isinstance(result_data, dict):
                                            unit_id = result_data.get("name") or result_data.get("adUnitId") or result_data.get("id")
                                            unit_data = {
                                                "slotCode": unit_id or "N/A",
                                                "name": display_name,
                                                "appCode": app_id or app_store_id or selected_app_code,
                                                "slotType": format_map.get(slot_key, ""),
                                                "adType": format_map.get(slot_key, ""),
                                                "auctionType": "N/A"
                                            }
                                            SessionManager.add_created_unit(current_network, unit_data)
                                            
                                            cached_units = SessionManager.get_cached_units(current_network, str(app_id or app_store_id or selected_app_code))
                                            if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                cached_units.append(unit_data)
                                                SessionManager.cache_units(current_network, str(app_id or app_store_id or selected_app_code), cached_units)
                                else:
                                    failed_count += 1
                            
                            # Display summary
                            if success_count == 3:
                                st.success(f"✅ Successfully created all 3 ad units!")
                                st.balloons()
                            elif success_count > 0:
                                st.warning(f"⚠️ Created {success_count} ad units, {failed_count} failed")
                            else:
                                st.error(f"❌ Failed to create ad units")
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error creating ad units: {str(e)}")
                            logger.exception("Error creating AdMob ad units")
        
        # For Fyber, add "Create All 3 Placements" button
        if current_network == "fyber":
            # Get app info for Fyber
            app_id = None
            bundle_id = ""
            pkg_name = ""
            platform_str = "android"
            app_name_for_slot = app_name
            
            if selected_app_code:
                if app_info_to_use:
                    app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId")
                    bundle_id = app_info_to_use.get("bundleId") or app_info_to_use.get("bundle", "")
                    pkg_name = app_info_to_use.get("pkgName", "")
                    platform_str = _normalize_platform_str(app_info_to_use.get("platformStr", "android"), "fyber")
                    app_name_for_slot = app_info_to_use.get("name", app_name)
                
                if not app_id:
                    try:
                        app_id = int(selected_app_code)
                    except (ValueError, TypeError):
                        import re
                        numeric_match = re.search(r'\d+', str(selected_app_code))
                        if numeric_match:
                            app_id = int(numeric_match.group())
                
                if not app_id or not bundle_id:
                    for app in apps:
                        app_identifier = app.get("appId") or app.get("appCode") or app.get("id")
                        if str(app_identifier) == str(selected_app_code):
                            if not app_id:
                                app_id = app.get("appId") or app.get("app_id")
                                if not app_id:
                                    try:
                                        app_id = int(app_identifier)
                                    except (ValueError, TypeError):
                                        app_id = None
                            if not bundle_id:
                                bundle_id = app.get("bundle") or app.get("bundleId", "")
                                pkg_name = app.get("pkgName", "")
                                platform_from_app = app.get("platform", "")
                                platform_str = _normalize_platform_str(platform_from_app, "fyber")
                                app_name_for_slot = app.get("name", app_name)
                            break
            
            # Create All 3 Placements button
            if st.button("✨ Create All 3 Placements (RV + IS + BN)", use_container_width=True, type="primary", key="create_all_fyber_placements"):
                if not selected_app_code:
                    st.toast("❌ Please select an App Code", icon="🚫")
                elif not app_id:
                    st.toast("❌ App ID is required. Please select an App Code.", icon="🚫")
                else:
                    source_pkg = bundle_id if bundle_id else pkg_name
                    if not source_pkg:
                        st.toast("❌ Package name or bundle ID is required", icon="🚫")
                    else:
                        with st.spinner("🚀 Creating all 3 placements..."):
                            try:
                                from utils.network_manager import get_network_manager
                                network_manager = get_network_manager()
                                
                                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                                create_payloads = []
                                placement_names = []
                                
                                for slot_key in ["RV", "IS", "BN"]:
                                    slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                    slot_config = slot_configs.get(slot_key, {})
                                    placement_name = _generate_slot_name(source_pkg, platform_str, slot_type, "fyber", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                                    placement_names.append((slot_key, placement_name))
                                    
                                    payload = {
                                        "name": placement_name.strip(),  # Fyber uses "name" field, not "placementName"
                                        "appId": str(app_id),  # Fyber requires appId as string
                                        "placementType": slot_config["placementType"],
                                        "coppa": bool(slot_config["coppa"]),
                                    }
                                    
                                    # Add skipability for Interstitial placement (default: NonSkippable)
                                    if slot_key == "IS" and slot_config.get("skipability"):
                                        payload["skipability"] = slot_config["skipability"]
                                    
                                    create_payloads.append((slot_key, slot_config, payload))
                                
                                # Create placements sequentially
                                results = []
                                for slot_key, slot_config, payload in create_payloads:
                                    response = network_manager.create_unit(current_network, payload)
                                    result = handle_api_response(response)
                                    results.append((slot_key, response, result))
                                
                                # Process results
                                success_count = 0
                                failed_count = 0
                                
                                for slot_key, response, result in results:
                                    if response.get("status") == 0 or response.get("code") == 0:
                                        success_count += 1
                                        if result:
                                            placement_name = next((name for sk, name in placement_names if sk == slot_key), "")
                                            unit_data = {
                                                "slotCode": result.get("placementId", result.get("id", "N/A")),
                                                "name": placement_name,
                                                "appCode": str(app_id),
                                                "slotType": slot_config["placementType"],
                                                "adType": slot_config["placementType"],
                                                "auctionType": "N/A"
                                            }
                                            SessionManager.add_created_unit(current_network, unit_data)
                                            
                                            cached_units = SessionManager.get_cached_units(current_network, str(app_id))
                                            if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                cached_units.append(unit_data)
                                                SessionManager.cache_units(current_network, str(app_id), cached_units)
                                    else:
                                        failed_count += 1
                                
                                # Display summary
                                if success_count == 3:
                                    st.success(f"✅ Successfully created all 3 placements!")
                                    st.balloons()
                                elif success_count > 0:
                                    st.warning(f"⚠️ Created {success_count} placements, {failed_count} failed")
                                else:
                                    st.error(f"❌ Failed to create placements")
                                
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error creating placements: {str(e)}")
                                logger.exception("Error creating Fyber placements")
        
        # For Pangle, add "Create All 6 Placements (Android + iOS)" button
        if current_network == "pangle":
            # Get selected app info
            selected_app_info = None
            selected_platform = None
            selected_app_name = None
            selected_pkg_name = None
            
            if selected_app_code:
                # Find selected app in apps list
                for app in apps:
                    app_identifier = app.get("siteId") or app.get("appCode")
                    if str(app_identifier) == str(selected_app_code):
                        selected_app_info = app
                        selected_platform = app.get("platform", "") or app.get("osType", "")
                        selected_platform = "android" if selected_platform.lower() == "android" else ("ios" if selected_platform.lower() == "ios" else None)
                        selected_app_name = app.get("name", "")
                        
                        # Get package name
                        download_url = app.get("downloadUrl", "")
                        if download_url:
                            import re
                            if "play.google.com" in download_url:
                                match = re.search(r'[?&]id=([^&]+)', download_url)
                                if match:
                                    selected_pkg_name = match.group(1)
                            elif "apps.apple.com" in download_url or "itunes.apple.com" in download_url:
                                match = re.search(r'/id(\d+)', download_url) or re.search(r'[?&]id=(\d+)', download_url)
                                if match:
                                    selected_pkg_name = match.group(1)
                        
                        if not selected_pkg_name:
                            selected_pkg_name = app.get("pkgName", "")
                        break
            
            # Find matching iOS app if Android is selected
            ios_app_info = None
            if selected_app_info and selected_platform == "android":
                # Search for iOS app with same app_name or package_name
                for app in apps:
                    app_platform = app.get("platform", "") or app.get("osType", "")
                    app_platform_normalized = "android" if app_platform.lower() == "android" else ("ios" if app_platform.lower() == "ios" else "")
                    
                    if app_platform_normalized == "ios":
                        app_name_from_list = app.get("name", "")
                        
                        # Get package name from iOS app
                        app_pkg_name = ""
                        download_url = app.get("downloadUrl", "")
                        if download_url:
                            import re
                            if "play.google.com" in download_url:
                                match = re.search(r'[?&]id=([^&]+)', download_url)
                                if match:
                                    app_pkg_name = match.group(1)
                            elif "apps.apple.com" in download_url or "itunes.apple.com" in download_url:
                                match = re.search(r'/id(\d+)', download_url) or re.search(r'[?&]id=(\d+)', download_url)
                                if match:
                                    app_pkg_name = match.group(1)
                        
                        if not app_pkg_name:
                            app_pkg_name = app.get("pkgName", "")
                        
                        # Check if app_name or package_name matches
                        if (app_name_from_list == selected_app_name) or (app_pkg_name and selected_pkg_name and app_pkg_name == selected_pkg_name):
                            ios_app_info = app
                            logger.info(f"[Pangle] Found matching iOS app: name={app_name_from_list}, pkg={app_pkg_name}, siteId={app.get('siteId')}")
                            break
                
                # If not found in apps list, try fetching all apps from API
                if not ios_app_info:
                    logger.info(f"[Pangle] iOS app not found in apps list, fetching all apps from API")
                    try:
                        all_apps = network_manager.get_apps(current_network)
                        if all_apps:
                            for app in all_apps:
                                app_platform = app.get("platform", "") or app.get("osType", "")
                                app_platform_normalized = "android" if app_platform.lower() == "android" else ("ios" if app_platform.lower() == "ios" else "")
                                
                                if app_platform_normalized == "ios":
                                    app_name_from_list = app.get("name", "")
                                    
                                    # Get package name from iOS app
                                    app_pkg_name = ""
                                    download_url = app.get("downloadUrl", "")
                                    if download_url:
                                        import re
                                        if "play.google.com" in download_url:
                                            match = re.search(r'[?&]id=([^&]+)', download_url)
                                            if match:
                                                app_pkg_name = match.group(1)
                                        elif "apps.apple.com" in download_url or "itunes.apple.com" in download_url:
                                            match = re.search(r'/id(\d+)', download_url) or re.search(r'[?&]id=(\d+)', download_url)
                                            if match:
                                                app_pkg_name = match.group(1)
                                    
                                    if not app_pkg_name:
                                        app_pkg_name = app.get("pkgName", "")
                                    
                                    # Check if app_name or package_name matches
                                    if (app_name_from_list == selected_app_name) or (app_pkg_name and selected_pkg_name and app_pkg_name == selected_pkg_name):
                                        ios_app_info = app
                                        logger.info(f"[Pangle] Found matching iOS app in full apps list: name={app_name_from_list}, pkg={app_pkg_name}, siteId={app.get('siteId')}")
                                        break
                    except Exception as e:
                        logger.warning(f"[Pangle] Failed to fetch all apps from API: {str(e)}")
            
            # Create All 6 Placements (Android + iOS) button
            if selected_platform == "android" and ios_app_info:
                if st.button("✨ Create All 6 Placements (Android + iOS: RV + IS + BN)", use_container_width=True, type="primary", key="create_all_6_pangle_placements"):
                    with st.spinner("🚀 Creating all 6 placements (Android + iOS)..."):
                        try:
                            from utils.network_manager import get_network_manager
                            network_manager = get_network_manager()
                            
                            android_site_id = selected_app_code
                            ios_site_id = ios_app_info.get("siteId") or ios_app_info.get("appCode")
                            
                            # Get package names for name generation
                            android_pkg_name = selected_pkg_name
                            ios_pkg_name = ""
                            ios_download_url = ios_app_info.get("downloadUrl", "")
                            if ios_download_url:
                                import re
                                if "play.google.com" in ios_download_url:
                                    match = re.search(r'[?&]id=([^&]+)', ios_download_url)
                                    if match:
                                        ios_pkg_name = match.group(1)
                                elif "apps.apple.com" in ios_download_url or "itunes.apple.com" in ios_download_url:
                                    match = re.search(r'/id(\d+)', ios_download_url) or re.search(r'[?&]id=(\d+)', ios_download_url)
                                    if match:
                                        ios_pkg_name = match.group(1)
                            
                            if not ios_pkg_name:
                                ios_pkg_name = ios_app_info.get("pkgName", "")
                            
                            # If iOS pkg_name is iTunes ID, use Android pkg_name for iOS placement name generation
                            if ios_pkg_name and ios_pkg_name.strip().isdigit():
                                ios_pkg_name_for_name = android_pkg_name
                            else:
                                ios_pkg_name_for_name = ios_pkg_name
                            
                            create_payloads = []
                            
                            # Get Android app_id
                            android_app_id = None
                            if selected_app_info:
                                android_app_id = selected_app_info.get("appId") or selected_app_info.get("siteId")
                            if not android_app_id:
                                android_app_id = android_site_id
                            
                            # Ensure Android app_id is valid
                            if not android_app_id or android_app_id == "":
                                st.error(f"❌ Android App ID is required but not found. siteId: {android_site_id}")
                                logger.error(f"[Pangle] Android App ID validation failed - siteId: {android_site_id}")
                                return
                            
                            # Convert to string if needed
                            if isinstance(android_app_id, (int, float)):
                                android_app_id = str(int(android_app_id))
                            else:
                                android_app_id = str(android_app_id) if android_app_id else None
                            
                            if not android_app_id or android_app_id == "":
                                st.error(f"❌ Android App ID is required but is empty after conversion. siteId: {android_site_id}")
                                logger.error(f"[Pangle] Android App ID conversion failed - siteId: {android_site_id}")
                                return
                            
                            # Get iOS app_id
                            ios_app_id = None
                            if ios_app_info:
                                ios_app_id = ios_app_info.get("appId") or ios_app_info.get("siteId")
                            if not ios_app_id:
                                ios_app_id = ios_site_id
                            
                            # Ensure iOS app_id is valid
                            if not ios_app_id or ios_app_id == "":
                                st.error(f"❌ iOS App ID is required but not found. siteId: {ios_site_id}")
                                logger.error(f"[Pangle] iOS App ID validation failed - siteId: {ios_site_id}")
                                return
                            
                            # Convert to string if needed
                            if isinstance(ios_app_id, (int, float)):
                                ios_app_id = str(int(ios_app_id))
                            else:
                                ios_app_id = str(ios_app_id) if ios_app_id else None
                            
                            if not ios_app_id or ios_app_id == "":
                                st.error(f"❌ iOS App ID is required but is empty after conversion. siteId: {ios_site_id}")
                                logger.error(f"[Pangle] iOS App ID conversion failed - siteId: {ios_site_id}")
                                return
                            
                            logger.info(f"[Pangle] Create All 6 - Android: site_id={android_site_id}, app_id={android_app_id}, iOS: site_id={ios_site_id}, app_id={ios_app_id}")
                            
                            # Create Android placements
                            for slot_key in ["RV", "IS", "BN"]:
                                slot_config = slot_configs.get(slot_key, {})
                                
                                # Generate slot name for Android
                                slot_name = _generate_slot_name(android_pkg_name, "android", slot_key.lower(), "pangle", network_manager=network_manager, app_name=selected_app_name)
                                if not slot_name:
                                    slot_name = f"{slot_key.lower()}_placement"
                                
                                # Convert app_id to int (Pangle API expects int)
                                try:
                                    android_app_id_int = int(android_app_id) if android_app_id else None
                                except (ValueError, TypeError):
                                    logger.error(f"[Pangle] Android App ID conversion failed - app_id: {android_app_id}")
                                    st.error(f"❌ Android App ID must be a valid integer. Current value: {android_app_id}")
                                    return
                                
                                if not android_app_id_int:
                                    logger.error(f"[Pangle] Android App ID is None or empty")
                                    st.error(f"❌ Android App ID is required but is empty after conversion.")
                                    return
                                
                                payload = {
                                    "app_id": android_app_id_int,  # Required field - must be int
                                    "ad_placement_type": slot_config["ad_slot_type"],
                                    "ad_slot_name": slot_name.strip(),  # User-selected name
                                    "bidding_type": 1,
                                }
                                
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
                                        "reward_name": slot_config.get("reward_name", "Reward"),
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
                                
                                create_payloads.append(("Android", slot_key, slot_config, payload, slot_name, android_site_id))
                            
                            # Create iOS placements
                            for slot_key in ["RV", "IS", "BN"]:
                                slot_config = slot_configs.get(slot_key, {})
                                
                                # Generate slot name for iOS
                                slot_name = _generate_slot_name(ios_pkg_name_for_name, "ios", slot_key.lower(), "pangle", network_manager=network_manager, app_name=selected_app_name)
                                if not slot_name:
                                    slot_name = f"{slot_key.lower()}_placement"
                                
                                # Convert app_id to int (Pangle API expects int)
                                try:
                                    ios_app_id_int = int(ios_app_id) if ios_app_id else None
                                except (ValueError, TypeError):
                                    logger.error(f"[Pangle] iOS App ID conversion failed - app_id: {ios_app_id}")
                                    st.error(f"❌ iOS App ID must be a valid integer. Current value: {ios_app_id}")
                                    return
                                
                                if not ios_app_id_int:
                                    logger.error(f"[Pangle] iOS App ID is None or empty")
                                    st.error(f"❌ iOS App ID is required but is empty after conversion.")
                                    return
                                
                                payload = {
                                    "app_id": ios_app_id_int,  # Required field - must be int
                                    "ad_placement_type": slot_config["ad_slot_type"],
                                    "ad_slot_name": slot_name.strip(),  # User-selected name
                                    "bidding_type": 1,
                                }
                                
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
                                        "reward_name": slot_config.get("reward_name", "Reward"),
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
                                
                                create_payloads.append(("iOS", slot_key, slot_config, payload, slot_name, ios_site_id))
                            
                            # Create placements sequentially
                            results = []
                            for platform, slot_key, slot_config, payload, slot_name, site_id in create_payloads:
                                # Display payload before API call
                                st.markdown(f"#### 📤 Request Payload ({platform} - {slot_key})")
                                st.json(payload)
                                
                                response = network_manager.create_unit(current_network, payload)
                                
                                # Display response
                                st.markdown(f"#### 📥 Response ({platform} - {slot_key})")
                                st.json(response)
                                
                                result = handle_api_response(response)
                                results.append((platform, slot_key, response, result, slot_name, site_id, slot_config))
                            
                            # Process results
                            success_count = 0
                            failed_count = 0
                            
                            for platform, slot_key, response, result, slot_name, site_id, slot_config in results:
                                if response.get("status") == 0 or response.get("code") == 0:
                                    success_count += 1
                                    if result:
                                        unit_data = {
                                            "slotCode": result.get("code_id", result.get("ad_unit_id", "N/A")),
                                            "name": slot_name,
                                            "appCode": site_id,
                                            "slotType": slot_config["ad_slot_type"],
                                            "adType": f"Type {slot_config['ad_slot_type']}",
                                            "auctionType": "N/A"
                                        }
                                        SessionManager.add_created_unit(current_network, unit_data)
                                        
                                        cached_units = SessionManager.get_cached_units(current_network, site_id)
                                        if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                            cached_units.append(unit_data)
                                            SessionManager.cache_units(current_network, site_id, cached_units)
                                else:
                                    failed_count += 1
                            
                            # Display summary
                            if success_count == 6:
                                st.success(f"✅ Successfully created all 6 placements (Android + iOS)!")
                                st.balloons()
                            elif success_count > 0:
                                st.warning(f"⚠️ Created {success_count} placements, {failed_count} failed")
                            else:
                                st.error(f"❌ Failed to create placements")
                            
                            # Don't rerun - keep the response visible
                        except Exception as e:
                            st.error(f"❌ Error creating placements: {str(e)}")
                            logger.exception("Error creating Pangle placements")
            
            # Create All 3 Placements button (for single platform or when iOS app not found)
            if st.button("✨ Create All 3 Placements (RV + IS + BN)", use_container_width=True, type="secondary", key="create_all_3_pangle_placements"):
                if not selected_app_code:
                    st.toast("❌ Please select an App Code", icon="🚫")
                else:
                    # Get package name for name generation
                    pkg_name = selected_pkg_name
                    platform_str = selected_platform or "android"
                    app_name_for_slot = selected_app_name or app_name
                    
                    if not pkg_name or pkg_name.strip().isdigit():
                        st.toast("❌ Package name is required and must be valid (not iTunes ID). Please select an app.", icon="🚫")
                    else:
                        with st.spinner("🚀 Creating all 3 placements..."):
                            try:
                                from utils.network_manager import get_network_manager
                                network_manager = get_network_manager()
                                
                                create_payloads = []
                                
                                for slot_key in ["RV", "IS", "BN"]:
                                    slot_config = slot_configs.get(slot_key, {})
                                    
                                    # Generate slot name
                                    slot_name = _generate_slot_name(pkg_name, platform_str, slot_key.lower(), "pangle", network_manager=network_manager, app_name=app_name_for_slot)
                                    if not slot_name:
                                        slot_name = f"{slot_key.lower()}_placement"
                                    
                                    # Get app_id and site_id for Pangle
                                    site_id = selected_app_code
                                    app_id = None
                                    
                                    # Try to get from app_info_to_use or apps list
                                    if app_info_to_use:
                                        site_id = app_info_to_use.get("siteId") or selected_app_code
                                        app_id = app_info_to_use.get("appId") or app_info_to_use.get("siteId")
                                    
                                    if not app_id:
                                        for app in apps:
                                            app_identifier = app.get("siteId") or app.get("appCode")
                                            if str(app_identifier) == str(selected_app_code):
                                                site_id = app.get("siteId") or selected_app_code
                                                app_id = app.get("appId") or app.get("siteId")
                                                break
                                    
                                    # Fallback to site_id if app_id not found
                                    if not app_id:
                                        app_id = site_id
                                    
                                    # Ensure app_id is not None or empty
                                    if not app_id or app_id == "":
                                        logger.error(f"[Pangle] App ID validation failed for Create All 3 - siteId: {site_id}, appId: {app_id}")
                                        st.error(f"❌ App ID is required but not found. siteId: {site_id}")
                                        return
                                    
                                    # Convert to int (Pangle API expects int)
                                    try:
                                        app_id_int = int(app_id) if app_id else None
                                    except (ValueError, TypeError):
                                        logger.error(f"[Pangle] App ID conversion failed for Create All 3 - app_id: {app_id}")
                                        st.error(f"❌ App ID must be a valid integer. Current value: {app_id}")
                                        return
                                    
                                    if not app_id_int:
                                        logger.error(f"[Pangle] App ID is None or empty for Create All 3")
                                        st.error(f"❌ App ID is required but is empty after conversion.")
                                        return
                                    
                                    payload = {
                                        "app_id": app_id_int,  # Required field - must be int
                                        "ad_placement_type": slot_config["ad_slot_type"],
                                        "ad_slot_name": slot_name.strip(),  # User-selected name
                                        "bidding_type": 1,
                                    }
                                    
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
                                            "reward_name": slot_config.get("reward_name", "Reward"),
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
                                    
                                    create_payloads.append((slot_key, slot_config, payload, slot_name))
                                
                                # Create placements sequentially
                                results = []
                                for slot_key, slot_config, payload, slot_name in create_payloads:
                                    # Display payload before API call
                                    st.markdown(f"#### 📤 Request Payload ({slot_key})")
                                    st.json(payload)
                                    
                                    response = network_manager.create_unit(current_network, payload)
                                    
                                    # Display response
                                    st.markdown(f"#### 📥 Response ({slot_key})")
                                    st.json(response)
                                    
                                    result = handle_api_response(response)
                                    results.append((slot_key, response, result, slot_name, slot_config))
                                
                                # Process results
                                success_count = 0
                                failed_count = 0
                                
                                for slot_key, response, result, slot_name, slot_config in results:
                                    if response.get("status") == 0 or response.get("code") == 0:
                                        success_count += 1
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
                                            
                                            cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                                            if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                cached_units.append(unit_data)
                                                SessionManager.cache_units(current_network, selected_app_code, cached_units)
                                    else:
                                        failed_count += 1
                                
                                # Display summary
                                if success_count == 3:
                                    st.success(f"✅ Successfully created all 3 placements!")
                                    st.balloons()
                                elif success_count > 0:
                                    st.warning(f"⚠️ Created {success_count} placements, {failed_count} failed")
                                else:
                                    st.error(f"❌ Failed to create placements")
                                
                                # Don't rerun - keep the response visible
                            except Exception as e:
                                st.error(f"❌ Error creating placements: {str(e)}")
                                logger.exception("Error creating Pangle placements")
        
        # For Mintegral, add "Create All 3 Placements" button
        if current_network == "mintegral":
            # Get app info for Mintegral
            app_id = None
            pkg_name = ""
            platform_str = "android"
            app_name_for_slot = app_name
            
            if selected_app_code:
                if app_info_to_use:
                    app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId") or app_info_to_use.get("appCode")
                    pkg_name = app_info_to_use.get("pkgName", "")
                    platform_str = _normalize_platform_str(app_info_to_use.get("platformStr", "android"), "mintegral")
                    app_name_for_slot = app_info_to_use.get("name", app_name)
                
                if not app_id or not pkg_name:
                    for app in apps:
                        app_identifier = app.get("appCode")
                        if str(app_identifier) == str(selected_app_code) or app_identifier == selected_app_code:
                            if not app_id:
                                app_id = app.get("app_id") or app.get("appId") or app.get("appCode")
                            if not pkg_name:
                                pkg_name = app.get("pkgName", "")
                                platform_from_app = app.get("platform", "")
                                platform_str = _normalize_platform_str(platform_from_app, "mintegral")
                                app_name_for_slot = app.get("name", app_name)
                            break
                
                # For iOS apps, if pkg_name is iTunes ID, try to find Android version
                platform_str = _normalize_platform_str(platform_str, "mintegral")
                if platform_str == "ios" and pkg_name and pkg_name.startswith("id") and pkg_name[2:].isdigit():
                    # Search for Android app with same app_name
                    for app in apps:
                        app_platform = app.get("platform", "")
                        app_platform_normalized = _normalize_platform_str(app_platform, "mintegral")
                        app_name_from_list = app.get("name", "")
                        
                        if app_platform_normalized == "android" and app_name_from_list == app_name_for_slot:
                            android_pkg_name = app.get("pkgName", "")
                            if android_pkg_name and not android_pkg_name.startswith("id"):
                                pkg_name = android_pkg_name
                                break
                    
                    # If not found in apps list, try fetching all apps from API
                    if pkg_name.startswith("id") and pkg_name[2:].isdigit():
                        try:
                            all_apps = network_manager.get_apps(current_network)
                            if all_apps:
                                for app in all_apps:
                                    app_platform = app.get("platform", "")
                                    app_platform_normalized = _normalize_platform_str(app_platform, "mintegral")
                                    app_name_from_list = app.get("name", "")
                                    
                                    if app_platform_normalized == "android" and app_name_from_list == app_name_for_slot:
                                        android_pkg_name = app.get("pkgName", "")
                                        if android_pkg_name and not android_pkg_name.startswith("id"):
                                            pkg_name = android_pkg_name
                                            break
                        except Exception as e:
                            logger.warning(f"[Mintegral] Failed to fetch all apps from API: {str(e)}")
            
            # Create All 3 Placements button
            if st.button("✨ Create All 3 Placements (RV + IS + BN)", use_container_width=True, type="primary", key="create_all_mintegral_placements"):
                if not selected_app_code:
                    st.toast("❌ Please select an App Code", icon="🚫")
                else:
                    # Ensure app_id is a valid integer
                    try:
                        app_id_int = int(app_id) if app_id else None
                        if not app_id_int or app_id_int <= 0:
                            st.toast("❌ App ID is required. Please select an App Code.", icon="🚫")
                        else:
                            if not pkg_name or (pkg_name.startswith("id") and pkg_name[2:].isdigit()):
                                st.toast("❌ Package name is required and must be valid (not iTunes ID). Please select an app.", icon="🚫")
                            else:
                                with st.spinner("🚀 Creating all 3 placements..."):
                                    try:
                                        from utils.network_manager import get_network_manager
                                        network_manager = get_network_manager()
                                        
                                        slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                                        create_payloads = []
                                        placement_names = []
                                        
                                        for slot_key in ["RV", "IS", "BN"]:
                                            slot_type = slot_type_map.get(slot_key, slot_key.lower())
                                            slot_config = slot_configs.get(slot_key, {})
                                            
                                            # Generate placement name
                                            placement_name = _generate_slot_name(pkg_name, platform_str, slot_type, "mintegral", network_manager=network_manager, app_name=app_name_for_slot)
                                            if not placement_name:
                                                placement_name = f"{slot_key.lower()}_placement"
                                            placement_names.append((slot_key, placement_name))
                                            
                                            payload = {
                                                "app_id": app_id_int,
                                                "placement_name": placement_name,
                                                "ad_type": slot_config["ad_type"],
                                                "integrate_type": slot_config.get("integrate_type", "sdk"),
                                                "hb_unit_name": placement_name,
                                            }
                                            
                                            if slot_key == "RV":
                                                payload["skip_time"] = slot_config.get("skip_time", -1)
                                            elif slot_key == "IS":
                                                payload["content_type"] = slot_config.get("content_type", "both")
                                                payload["ad_space_type"] = slot_config.get("ad_space_type", 1)
                                                payload["skip_time"] = slot_config.get("skip_time", -1)
                                            elif slot_key == "BN":
                                                payload["show_close_button"] = slot_config.get("show_close_button", 0)
                                                payload["auto_fresh"] = slot_config.get("auto_fresh", 0)
                                            
                                            create_payloads.append((slot_key, slot_config, payload, placement_name))
                                        
                                        # Create placements sequentially
                                        results = []
                                        for slot_key, slot_config, payload, placement_name in create_payloads:
                                            # Display payload before API call
                                            st.markdown(f"#### 📤 Request Payload ({slot_key})")
                                            st.json(payload)
                                            
                                            response = network_manager.create_unit(current_network, payload)
                                            
                                            # Display response
                                            st.markdown(f"#### 📥 Response ({slot_key})")
                                            st.json(response)
                                            
                                            result = handle_api_response(response)
                                            results.append((slot_key, response, result, placement_name, slot_config))
                                        
                                        # Process results
                                        success_count = 0
                                        failed_count = 0
                                        
                                        for slot_key, response, result, placement_name, slot_config in results:
                                            if response.get("status") == 0 or response.get("code") == 0:
                                                success_count += 1
                                                if result:
                                                    unit_data = {
                                                        "slotCode": result.get("placement_id", result.get("id", "N/A")),
                                                        "name": placement_name,
                                                        "appCode": str(app_id_int),
                                                        "slotType": slot_config["ad_type"],
                                                        "adType": slot_config["ad_type"],
                                                        "auctionType": "N/A"
                                                    }
                                                    SessionManager.add_created_unit(current_network, unit_data)
                                                    
                                                    cached_units = SessionManager.get_cached_units(current_network, str(app_id_int))
                                                    if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                                        cached_units.append(unit_data)
                                                        SessionManager.cache_units(current_network, str(app_id_int), cached_units)
                                            else:
                                                failed_count += 1
                                        
                                        # Display summary
                                        if success_count == 3:
                                            st.success(f"✅ Successfully created all 3 placements!")
                                            st.balloons()
                                        elif success_count > 0:
                                            st.warning(f"⚠️ Created {success_count} placements, {failed_count} failed")
                                        else:
                                            st.error(f"❌ Failed to create placements")
                                        
                                        # Don't rerun - keep the response visible
                                    except Exception as e:
                                        st.error(f"❌ Error creating placements: {str(e)}")
                                        logger.exception("Error creating Mintegral placements")
                    except (ValueError, TypeError) as e:
                        st.toast(f"❌ Invalid App ID: {app_id}", icon="🚫")
                        logger.exception(f"Invalid App ID for Mintegral: {app_id}")
        
        # Create 3 columns for RV, IS, BN
        col1, col2, col3 = st.columns(3)
        
        for idx, (slot_key, slot_config) in enumerate(slot_configs.items()):
            with [col1, col2, col3][idx]:
                with st.container():
                    st.markdown(f"### 🎯 {slot_key} ({slot_config['name']})")
                    
                    if current_network == "pangle":
                        # Check if Android app is selected and matching iOS app exists
                        has_android = selected_app_info and selected_platform == "android"
                        has_ios = ios_app_info is not None
                        
                        if has_android and has_ios:
                            # Display Android and iOS sections separately (like AppLovin/Fyber)
                            st.markdown(f"#### Android")
                            _render_pangle_slot_ui(
                                slot_key, slot_config, selected_app_code, app_info_to_use,
                                app_name, apps, network_manager, current_network, platform="android"
                            )
                            st.markdown("---")
                            st.markdown(f"#### iOS")
                            ios_site_id = ios_app_info.get("siteId") or ios_app_info.get("appCode")
                            _render_pangle_slot_ui(
                                slot_key, slot_config, ios_site_id, ios_app_info,
                                app_name, apps, network_manager, current_network, platform="ios"
                            )
                        else:
                            # Single platform (backward compatibility)
                            _render_pangle_slot_ui(
                                slot_key, slot_config, selected_app_code, app_info_to_use,
                                app_name, apps, network_manager, current_network
                            )
                    elif current_network == "mintegral":
                        _render_mintegral_slot_ui(
                            slot_key, slot_config, selected_app_code, app_info_to_use,
                            app_name, apps, network_manager, current_network
                        )
                    elif current_network == "inmobi":
                        _render_inmobi_slot_ui(
                            slot_key, slot_config, selected_app_code, app_info_to_use,
                            app_name, apps, network_manager, current_network
                        )
                    elif current_network == "fyber":
                        # Check if app_info_to_use has both Android and iOS (from Create App)
                        has_android = app_info_to_use and (app_info_to_use.get("appId") or app_info_to_use.get("app_id"))
                        has_ios = app_info_to_use and app_info_to_use.get("appIdIOS")
                        
                        if has_android and has_ios:
                            # Display Android and iOS sections separately (like AppLovin)
                            st.markdown(f"#### Android")
                            _render_fyber_slot_ui(
                                slot_key, slot_config, selected_app_code, app_info_to_use,
                                app_name, apps, network_manager, current_network, platform="android"
                            )
                            st.markdown("---")
                            st.markdown(f"#### iOS")
                            _render_fyber_slot_ui(
                                slot_key, slot_config, selected_app_code, app_info_to_use,
                                app_name, apps, network_manager, current_network, platform="ios"
                            )
                        else:
                            # Single platform (backward compatibility)
                            _render_fyber_slot_ui(
                                slot_key, slot_config, selected_app_code, app_info_to_use,
                                app_name, apps, network_manager, current_network
                            )
                    elif current_network == "admob":
                        _render_admob_slot_ui(
                            slot_key, slot_config, selected_app_code, app_info_to_use,
                            app_name, apps, network_manager, current_network
                        )
                    else:
                        # BigOAds and other networks
                        _render_bigoads_slot_ui(
                            slot_key, slot_config, selected_app_code, app_info_to_use,
                            app_name, apps, network_manager, current_network,
                            AD_TYPE_MAP, AUCTION_TYPE_MAP, MUSIC_SWITCH_MAP,
                            AUTO_REFRESH_MAP, BANNER_SIZE_MAP,
                            AD_TYPE_REVERSE, AUCTION_TYPE_REVERSE,
                            MUSIC_SWITCH_REVERSE, AUTO_REFRESH_REVERSE,
                            BANNER_SIZE_REVERSE
                        )


def _render_ironsource_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                                app_name, network_manager, current_network):
    """Render IronSource slot UI"""
    slot_name_key = f"ironsource_slot_{slot_key}_name"
    auto_gen_flag_key = f"{slot_name_key}_auto_generated"
    
    if selected_app_code and app_info_to_use:
        if slot_name_key not in st.session_state or st.session_state.get(auto_gen_flag_key, False):
            # For IronSource, determine which platform to use
            has_android = app_info_to_use.get("hasAndroid", False)
            has_ios = app_info_to_use.get("hasIOS", False)
            platform = app_info_to_use.get("platform", "")
            
            # Use Android bundleId by default if both platforms available
            if platform == "both" or (has_android and has_ios):
                bundle_id = app_info_to_use.get("bundleId", "")  # Android bundleId
                platform_str = "android"
            elif has_android:
                bundle_id = app_info_to_use.get("bundleId", "")  # Android bundleId
                platform_str = "android"
            elif has_ios:
                bundle_id = app_info_to_use.get("bundleIdIOS", "")  # iOS bundleId
                platform_str = "ios"
            else:
                bundle_id = app_info_to_use.get("bundleId", "") or app_info_to_use.get("bundleIdIOS", "")
                platform_str = app_info_to_use.get("platformStr", "android")
            
            app_name_for_slot = app_info_to_use.get("name", app_name)
            if bundle_id:
                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                slot_type = slot_type_map.get(slot_key, slot_key.lower())
                # pkg_name is first param, bundle_id is separate param
                default_name = _generate_slot_name("", platform_str, slot_type, "ironsource", store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
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
    
    mediation_ad_unit_name = st.text_input(
        "Mediation Ad Unit Name*",
        value=st.session_state.get(slot_name_key, ""),
        key=slot_name_key,
        help=f"Name for {slot_config['name']} placement"
    )
    
    if mediation_ad_unit_name:
        if selected_app_code and app_info_to_use:
            bundle_id = app_info_to_use.get("bundleId", "")
            if bundle_id:
                platform_str = app_info_to_use.get("platformStr", "android")
                app_name_for_slot = app_info_to_use.get("name", app_name)
                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                slot_type = slot_type_map.get(slot_key, slot_key.lower())
                # pkg_name is first param, bundle_id is separate param
                expected_name = _generate_slot_name("", platform_str, slot_type, "ironsource", store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                if mediation_ad_unit_name != expected_name:
                    st.session_state[auto_gen_flag_key] = False
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 120px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Ad Format: {slot_config["adFormat"].title()}</li>'
    
    if slot_key == "RV" and slot_config.get("adFormat") == "rewarded":
        reward_item_name = slot_config.get("rewardItemName", "Reward")
        reward_amount = slot_config.get("rewardAmount", 1)
        settings_html += f'<li>Reward Item Name: {reward_item_name}</li>'
        settings_html += f'<li>Reward Amount: {reward_amount}</li>'
    
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    if st.button(f"✅ Activate {slot_key} Ad Unit", use_container_width=True, key=f"activate_ironsource_{slot_key}"):
        with st.spinner(f"Activating {slot_key} ad unit..."):
            try:
                from utils.network_manager import get_network_manager
                from utils.ad_network_query import get_ironsource_units
                network_manager = get_network_manager()
                
                # For IronSource, determine which appKey to use based on selected app
                app_key_to_use = selected_app_code
                if current_network == "ironsource" and app_info_to_use:
                    has_android = app_info_to_use.get("hasAndroid", False)
                    has_ios = app_info_to_use.get("hasIOS", False)
                    platform = app_info_to_use.get("platform", "")
                    
                    # If both platforms available, use Android by default
                    if platform == "both" or (has_android and has_ios):
                        app_key_to_use = app_info_to_use.get("appKey")  # Android appKey
                    elif has_android:
                        app_key_to_use = app_info_to_use.get("appKey")  # Android appKey
                    elif has_ios:
                        app_key_to_use = app_info_to_use.get("appKeyIOS")  # iOS appKey
                
                # Fallback to selected_app_code if app_key_to_use is not determined
                if not app_key_to_use:
                    app_key_to_use = selected_app_code
                
                # Step 1: Get existing ad units
                existing_units = get_ironsource_units(app_key_to_use)
                
                if not existing_units:
                    st.error("❌ No existing ad units found. Please create ad units first in IronSource dashboard.")
                    SessionManager.log_error(current_network, "No existing ad units found")
                else:
                    # Step 2: Find matching ad unit by adFormat
                    ad_format = slot_config['adFormat']
                    matching_unit = None
                    for unit in existing_units:
                        if unit.get("adFormat") == ad_format:
                            matching_unit = unit
                            break
                    
                    if not matching_unit:
                        st.error(f"❌ No ad unit found for adFormat: {ad_format}")
                        SessionManager.log_error(current_network, f"No ad unit found for adFormat: {ad_format}")
                    else:
                        mediation_adunit_id = matching_unit.get("mediationAdunitId") or matching_unit.get("id")
                        
                        if not mediation_adunit_id:
                            st.error("❌ mediationAdunitId not found in ad unit")
                            SessionManager.log_error(current_network, "mediationAdunitId not found")
                        else:
                            # Step 3: Update (activate) ad unit
                            update_payload = {
                                "mediationAdunitId": mediation_adunit_id,
                                "isPaused": False  # Activate
                            }
                            
                            update_response = network_manager._update_ironsource_ad_units(app_key_to_use, [update_payload])
                            update_result = handle_api_response(update_response)
                            
                            if update_result:
                                # Step 4: Get instances
                                instances_response = network_manager._get_ironsource_instances(app_key_to_use)
                                
                                if instances_response.get("status") == 0:
                                    instances = instances_response.get("result", [])
                                    
                                    # Filter instances by adFormat
                                    matching_instances = [inst for inst in instances if inst.get("adFormat") == ad_format]
                                    
                                    st.success(f"✅ {slot_key} ad unit activated successfully!")
                                    
                                    if matching_instances:
                                        st.subheader("📡 Instances")
                                        for inst in matching_instances:
                                            instance_id = inst.get("instanceId", "N/A")
                                            ad_format_display = inst.get("adFormat", "N/A")
                                            network_name = inst.get("networkName", "N/A")
                                            instance_name = inst.get("instanceName", "")
                                            is_bidder = inst.get("isBidder", False)
                                            is_live = inst.get("isLive", False)
                                            
                                            st.write(f"**Instance ID:** {instance_id} | **Ad Format:** {ad_format_display}")
                                            st.write(f"  - Network: {network_name} | Instance Name: {instance_name or 'N/A'}")
                                            st.write(f"  - Is Bidder: {is_bidder} | Is Live: {is_live}")
                                            st.divider()
                                else:
                                    st.warning("⚠️ Ad unit activated but failed to fetch instances")
                                
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to activate {slot_key} ad unit")
                                SessionManager.log_error(current_network, f"Failed to activate {slot_key} ad unit")
            except Exception as e:
                st.error(f"❌ Error activating {slot_key} ad unit: {str(e)}")
                SessionManager.log_error(current_network, str(e))


def _render_pangle_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                            app_name, apps, network_manager, current_network, platform=None):
    """Render Pangle slot UI
    
    Args:
        platform: "android" or "ios" to specify which platform to render (for dual-platform display)
    """
    # Use platform-specific key for slot name if platform is specified
    if platform:
        slot_name_key = f"pangle_slot_{slot_key}_{platform}_name"
    else:
        slot_name_key = f"pangle_slot_{slot_key}_name"
    
    # Track last selected app code to detect changes
    if platform:
        last_app_code_key = f"pangle_last_app_code_{slot_key}_{platform}"
    else:
        last_app_code_key = f"pangle_last_app_code_{slot_key}"
    last_app_code = st.session_state.get(last_app_code_key, "")
    
    # Auto-generate slot name if not set or if app selection changed
    app_selection_changed = selected_app_code and selected_app_code != last_app_code
    should_regenerate = (
        slot_name_key not in st.session_state or 
        app_selection_changed
    )
    
    if selected_app_code and should_regenerate:
        pkg_name = ""
        # Use platform parameter if provided, otherwise detect from app info
        if platform:
            platform_str = platform
        else:
            platform_str = "android"
        app_name_for_slot = app_name
        
        if app_info_to_use:
            # First, try to get pkgName directly (most reliable)
            pkg_name_from_field = app_info_to_use.get("pkgName", "")
            
            # Check if pkgName is a valid package name (not iTunes ID)
            # Valid package name should contain at least one dot and not be purely numeric
            is_valid_pkg_name = pkg_name_from_field and "." in pkg_name_from_field and not pkg_name_from_field.strip().isdigit()
            
            if is_valid_pkg_name:
                # Use pkgName directly if it's a valid package name
                pkg_name = pkg_name_from_field
                logger.info(f"[Pangle] Using pkgName from field: {pkg_name}")
            else:
                # If pkgName is not valid (empty or iTunes ID), try to extract from downloadUrl
                download_url = app_info_to_use.get("downloadUrl", "")
                if download_url:
                    # Extract package name from download URL
                    if "play.google.com" in download_url:
                        # Android: extract from ?id=package_name
                        import re
                        match = re.search(r'[?&]id=([^&]+)', download_url)
                        if match:
                            pkg_name = match.group(1)
                        platform_str = "android"
                    elif "apps.apple.com" in download_url or "itunes.apple.com" in download_url:
                        # iOS: extract from /id{numbers} or ?id={numbers}
                        import re
                        match = re.search(r'/id(\d+)', download_url) or re.search(r'[?&]id=(\d+)', download_url)
                        if match:
                            # For iOS, this is iTunes ID (numeric)
                            pkg_name = match.group(1)
                        platform_str = "ios"
                
                # Fallback to pkgName if downloadUrl extraction failed
                if not pkg_name:
                    pkg_name = pkg_name_from_field
            
            # Use platform parameter if provided, otherwise use from app_info_to_use
            if not platform:
                platform_str = app_info_to_use.get("platformStr", platform_str)
            app_name_for_slot = app_info_to_use.get("name", app_name)
        
        # If not found in app_info_to_use, try apps list
        if not pkg_name and selected_app_code:
            for app in apps:
                app_identifier = app.get("siteId") or app.get("appCode")
                if str(app_identifier) == str(selected_app_code):
                    # First, try to get pkgName directly (most reliable)
                    pkg_name_from_field = app.get("pkgName", "")
                    
                    # Check if pkgName is a valid package name (not iTunes ID)
                    # Valid package name should contain at least one dot and not be purely numeric
                    is_valid_pkg_name = pkg_name_from_field and "." in pkg_name_from_field and not pkg_name_from_field.strip().isdigit()
                    
                    if is_valid_pkg_name:
                        # Use pkgName directly if it's a valid package name
                        pkg_name = pkg_name_from_field
                        logger.info(f"[Pangle] Using pkgName from apps list: {pkg_name}")
                    else:
                        # If pkgName is not valid (empty or iTunes ID), try to extract from downloadUrl
                        download_url = app.get("downloadUrl", "")
                        if download_url:
                            # Extract package name from download URL
                            if "play.google.com" in download_url:
                                import re
                                match = re.search(r'[?&]id=([^&]+)', download_url)
                                if match:
                                    pkg_name = match.group(1)
                                if not platform:
                                    platform_str = "android"
                            elif "apps.apple.com" in download_url or "itunes.apple.com" in download_url:
                                import re
                                match = re.search(r'/id(\d+)', download_url) or re.search(r'[?&]id=(\d+)', download_url)
                                if match:
                                    # For iOS, this is iTunes ID (numeric)
                                    pkg_name = match.group(1)
                                if not platform:
                                    platform_str = "ios"
                        
                        # Fallback to pkgName if downloadUrl extraction failed
                        if not pkg_name:
                            pkg_name = pkg_name_from_field
                    
                    # Use platform parameter if provided, otherwise detect from app
                    if not platform:
                        platform_str_val = app.get("platform", "") or app.get("osType", "")
                        if platform_str_val:
                            platform_str = "android" if platform_str_val.lower() == "android" else ("ios" if platform_str_val.lower() == "ios" else platform_str)
                    
                    app_name_for_slot = app.get("name", app_name)
                    break
        
        # For Pangle, handle iOS apps specially:
        # 1. If iOS app's pkg_name is iTunes ID (numeric only), find Android app with same app_name
        # 2. If iOS app's pkg_name is actual package name, check for Android app with same package_name
        # 3. If Android app not found, remove trailing digits from package_name
        import re
        current_pkg_name = pkg_name
        # Use platform parameter if provided, otherwise use platform_str
        current_platform = platform if platform else platform_str
        is_ios_itunes_id = current_platform == "ios" and current_pkg_name and current_pkg_name.strip().isdigit()
        
        # Update platform_str to match current_platform for consistency
        platform_str = current_platform
        
        android_found = False
        
        if is_ios_itunes_id:
            # iOS app with iTunes ID: find Android app with same app_name
            logger.info(f"[Pangle] iOS app with iTunes ID: {current_pkg_name}, searching for Android app with same app_name: {app_name_for_slot}")
            for app in apps:
                app_platform = app.get("platform", "") or app.get("osType", "")
                app_platform_normalized = "android" if app_platform.lower() == "android" else ("ios" if app_platform.lower() == "ios" else "")
                app_name_from_list = app.get("name", "")
                
                if app_platform_normalized == "android" and app_name_from_list == app_name_for_slot:
                    # Get package name from Android app
                    app_pkg_name = ""
                    download_url = app.get("downloadUrl", "")
                    if download_url and "play.google.com" in download_url:
                        match = re.search(r'[?&]id=([^&]+)', download_url)
                        if match:
                            app_pkg_name = match.group(1)
                    else:
                        app_pkg_name = app.get("pkgName", "")
                    
                    if app_pkg_name and not app_pkg_name.strip().isdigit():
                        logger.info(f"[Pangle] Found Android app with same name, using package: {app_pkg_name}")
                        pkg_name = app_pkg_name
                        android_found = True
                        break
            
            # If not found in apps list, try fetching all apps from API
            if not android_found:
                logger.info(f"[Pangle] Android app with name '{app_name_for_slot}' not found in apps list, fetching all apps from API")
                try:
                    all_apps = network_manager.get_apps(current_network)
                    if all_apps:
                        for app in all_apps:
                            app_platform = app.get("platform", "") or app.get("osType", "")
                            app_platform_normalized = "android" if app_platform.lower() == "android" else ("ios" if app_platform.lower() == "ios" else "")
                            app_name_from_list = app.get("name", "")
                            
                            if app_platform_normalized == "android" and app_name_from_list == app_name_for_slot:
                                app_pkg_name = ""
                                download_url = app.get("downloadUrl", "")
                                if download_url and "play.google.com" in download_url:
                                    match = re.search(r'[?&]id=([^&]+)', download_url)
                                    if match:
                                        app_pkg_name = match.group(1)
                                else:
                                    app_pkg_name = app.get("pkgName", "")
                                
                                if app_pkg_name and not app_pkg_name.strip().isdigit():
                                    logger.info(f"[Pangle] Found Android app with same name in full apps list, using package: {app_pkg_name}")
                                    pkg_name = app_pkg_name
                                    android_found = True
                                    break
                except Exception as e:
                    logger.warning(f"[Pangle] Failed to fetch all apps from API: {str(e)}")
        elif current_pkg_name:
            # iOS or Android app with actual package name: check for Android app with same package_name
            logger.info(f"[Pangle] Checking for Android app with same package_name: {current_pkg_name}")
            for app in apps:
                app_platform = app.get("platform", "") or app.get("osType", "")
                app_platform_normalized = "android" if app_platform.lower() == "android" else ("ios" if app_platform.lower() == "ios" else "")
                
                if app_platform_normalized == "android":
                    # Get package name from app
                    app_pkg_name = ""
                    download_url = app.get("downloadUrl", "")
                    if download_url and "play.google.com" in download_url:
                        match = re.search(r'[?&]id=([^&]+)', download_url)
                        if match:
                            app_pkg_name = match.group(1)
                    else:
                        app_pkg_name = app.get("pkgName", "")
                    
                    # Check if package names match
                    if app_pkg_name and current_pkg_name and app_pkg_name == current_pkg_name:
                        logger.info(f"[Pangle] Found Android app with same package_name: {app_pkg_name}")
                        pkg_name = app_pkg_name
                        android_found = True
                        break
            
            # If not found in apps list, try fetching all apps from API
            if not android_found and current_pkg_name:
                logger.info(f"[Pangle] Android app with package_name '{current_pkg_name}' not found in apps list, fetching all apps from API")
                try:
                    all_apps = network_manager.get_apps(current_network)
                    if all_apps:
                        for app in all_apps:
                            app_platform = app.get("platform", "") or app.get("osType", "")
                            app_platform_normalized = "android" if app_platform.lower() == "android" else ("ios" if app_platform.lower() == "ios" else "")
                            
                            if app_platform_normalized == "android":
                                app_pkg_name = ""
                                download_url = app.get("downloadUrl", "")
                                if download_url and "play.google.com" in download_url:
                                    match = re.search(r'[?&]id=([^&]+)', download_url)
                                    if match:
                                        app_pkg_name = match.group(1)
                                else:
                                    app_pkg_name = app.get("pkgName", "")
                                
                                if app_pkg_name and current_pkg_name and app_pkg_name == current_pkg_name:
                                    logger.info(f"[Pangle] Found Android app with same package_name in full apps list: {app_pkg_name}")
                                    pkg_name = app_pkg_name
                                    android_found = True
                                    break
                except Exception as e:
                    logger.warning(f"[Pangle] Failed to fetch all apps from API: {str(e)}")
            
            # If Android app with same package_name not found, remove trailing digits
            if not android_found and current_pkg_name:
                # Remove trailing digits from package_name
                pkg_name_cleaned = re.sub(r'\d+$', '', current_pkg_name).rstrip('_').rstrip('-')
                if pkg_name_cleaned and pkg_name_cleaned != current_pkg_name:
                    logger.info(f"[Pangle] Android app with package_name '{current_pkg_name}' not found, removing trailing digits: {pkg_name_cleaned}")
                    pkg_name = pkg_name_cleaned
                else:
                    pkg_name = current_pkg_name
        
        # Generate slot name if we have a valid package name (not iTunes ID)
        # Use current_platform (from platform parameter or detected) for name generation
        if pkg_name and not (pkg_name.strip().isdigit()):
            default_name = _generate_slot_name(pkg_name, current_platform, slot_key.lower(), "pangle", network_manager=network_manager, app_name=app_name_for_slot)
            if default_name:
                st.session_state[slot_name_key] = default_name
            else:
                # generate_slot_name returned empty, use fallback
                default_name = f"{slot_key.lower()}_placement"
                st.session_state[slot_name_key] = default_name
        else:
            # No valid package name found, use fallback
            default_name = f"{slot_key.lower()}_placement"
            st.session_state[slot_name_key] = default_name
        
        # Update last app code
        st.session_state[last_app_code_key] = selected_app_code
    elif slot_name_key not in st.session_state:
        default_name = f"{slot_key.lower()}_placement"
        st.session_state[slot_name_key] = default_name
    
    slot_name = st.text_input(
        "Slot Name*",
        value=st.session_state[slot_name_key],
        key=slot_name_key,
        help=f"Name for {slot_config['name']} ad placement"
    )
    
    # Display site_id (app_id) for Pangle
    # Get actual site_id from app_info_to_use or apps list
    display_site_id = None
    if app_info_to_use:
        display_site_id = app_info_to_use.get("siteId")
    
    if not display_site_id and selected_app_code:
        # Try to get from apps list
        for app in apps:
            app_identifier = app.get("siteId") or app.get("appCode")
            if str(app_identifier) == str(selected_app_code):
                display_site_id = app.get("siteId")
                break
    
    # Fallback to selected_app_code
    if not display_site_id:
        display_site_id = selected_app_code
    
    if display_site_id:
        platform_display = "iOS" if platform == "ios" else "Android" if platform else ""
        if platform_display:
            st.info(f"📱 {platform_display} Site ID: {display_site_id}")
        else:
            st.info(f"📱 Site ID: {display_site_id}")
    
    st.info(f"**API Version:** 1.1.13 (auto-generated)")
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 180px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Ad Slot Type: {slot_config["name"]}</li>'
    settings_html += f'<li>Render Type: Template Render</li>'
    
    if slot_key == "BN":
        slide_banner_text = "No" if slot_config["slide_banner"] == 1 else "Yes"
        settings_html += f'<li>Slide Banner: {slide_banner_text}</li>'
        settings_html += f'<li>Size: {slot_config["width"]}x{slot_config["height"]}px</li>'
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
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
    
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    with st.expander("⚙️ Edit Settings"):
        # Add platform suffix to all widget keys to avoid duplicates
        key_suffix = f"_{platform}" if platform else ""
        
        if slot_key == "BN":
            slide_banner = st.selectbox(
                "Slide Banner",
                options=[("No", 1), ("Yes", 2)],
                index=0 if slot_config["slide_banner"] == 1 else 1,
                key=f"{slot_key}_slide_banner{key_suffix}",
                format_func=lambda x: x[0]
            )
            slot_config["slide_banner"] = slide_banner[1]
            
            banner_size = st.selectbox(
                "Banner Size",
                options=[("640x100 (320*50)", (640, 100)), ("600x500 (300*250)", (600, 500))],
                index=0 if (slot_config["width"], slot_config["height"]) == (640, 100) else 1,
                key=f"{slot_key}_banner_size{key_suffix}",
                format_func=lambda x: x[0]
            )
            slot_config["width"] = banner_size[1][0]
            slot_config["height"] = banner_size[1][1]
        elif slot_key == "RV":
            orientation = st.selectbox(
                "Orientation",
                options=[("Vertical", 1), ("Horizontal", 2)],
                index=0 if slot_config["orientation"] == 1 else 1,
                key=f"{slot_key}_orientation{key_suffix}",
                format_func=lambda x: x[0]
            )
            slot_config["orientation"] = orientation[1]
            
            reward_name = st.text_input(
                "Reward Name*",
                value=st.session_state.get(f"{slot_key}_reward_name{key_suffix}", slot_config.get("reward_name", "Reward")),
                key=f"{slot_key}_reward_name{key_suffix}",
                help="Reward name (1-60 characters)"
            )
            slot_config["reward_name"] = reward_name
            
            reward_count = st.number_input(
                "Reward Count*",
                min_value=0,
                max_value=9007199254740991,
                value=st.session_state.get(f"{slot_key}_reward_count{key_suffix}", slot_config.get("reward_count", 1)),
                key=f"{slot_key}_reward_count{key_suffix}"
            )
            slot_config["reward_count"] = reward_count
            
            reward_is_callback = st.selectbox(
                "Reward Callback",
                options=[("No Server Callback", 0), ("Server Callback", 1)],
                index=0 if slot_config["reward_is_callback"] == 0 else 1,
                key=f"{slot_key}_reward_is_callback{key_suffix}",
                format_func=lambda x: x[0]
            )
            slot_config["reward_is_callback"] = reward_is_callback[1]
            
            if reward_is_callback[1] == 1:
                reward_callback_url = st.text_input(
                    "Reward Callback URL*",
                    value=st.session_state.get(f"{slot_key}_reward_callback_url{key_suffix}", ""),
                    key=f"{slot_key}_reward_callback_url{key_suffix}",
                    help="Required when server callback is enabled"
                )
                slot_config["reward_callback_url"] = reward_callback_url
        elif slot_key == "IS":
            orientation = st.selectbox(
                "Orientation",
                options=[("Vertical", 1), ("Horizontal", 2)],
                index=0 if slot_config["orientation"] == 1 else 1,
                key=f"{slot_key}_orientation{key_suffix}",
                format_func=lambda x: x[0]
            )
            slot_config["orientation"] = orientation[1]
    
    button_key = f"create_pangle_{slot_key}_{platform}" if platform else f"create_pangle_{slot_key}"
    button_label = f"✅ Create {slot_key} Placement ({platform.upper()})" if platform else f"✅ Create {slot_key} Placement"
    if st.button(button_label, use_container_width=True, key=button_key):
        if not slot_name:
            st.toast("❌ Slot Name is required", icon="🚫")
        elif slot_key == "RV" and (not slot_config.get("reward_name") or slot_config.get("reward_count") is None):
            st.toast("❌ Reward Name and Reward Count are required for Rewarded Video", icon="🚫")
        else:
            # For Pangle, use both app_id and site_id
            # Priority: 1) app_info_to_use, 2) apps list, 3) selected_app_code
            site_id = None
            app_id = None
            
            if app_info_to_use:
                site_id = app_info_to_use.get("siteId")
                app_id = app_info_to_use.get("appId") or app_info_to_use.get("siteId")  # Fallback to site_id if app_id not found
                logger.info(f"[Pangle] From app_info_to_use: siteId={site_id}, appId={app_id}, keys: {list(app_info_to_use.keys())}")
            
            if not site_id or not app_id:
                # Try to get from apps list
                for app in apps:
                    app_identifier = app.get("siteId") or app.get("appCode")
                    if str(app_identifier) == str(selected_app_code):
                        if not site_id:
                            site_id = app.get("siteId")
                        if not app_id:
                            app_id = app.get("appId") or app.get("siteId")  # Fallback to site_id if app_id not found
                        logger.info(f"[Pangle] Found from apps list: siteId={site_id}, appId={app_id}")
                        break
            
            # Fallback to selected_app_code if not found
            if not site_id:
                site_id = selected_app_code
                logger.warning(f"[Pangle] siteId not found, using selected_app_code: {site_id}")
            if not app_id or app_id == "" or app_id is None:
                app_id = site_id  # Use site_id as fallback for app_id
                logger.warning(f"[Pangle] appId not found or empty, using site_id: {app_id}")
            
            # Ensure app_id is not None or empty string
            if not app_id or app_id == "":
                st.error(f"❌ App ID is required but not found. siteId: {site_id}, selected_app_code: {selected_app_code}")
                logger.error(f"[Pangle] App ID validation failed - siteId: {site_id}, appId: {app_id}, selected_app_code: {selected_app_code}")
                return
            
            # Convert to string if needed (Pangle API expects string or int)
            if isinstance(app_id, (int, float)):
                app_id = str(int(app_id))
            else:
                app_id = str(app_id) if app_id else None
            
            if not app_id or app_id == "":
                st.error(f"❌ App ID is required but is empty after conversion. siteId: {site_id}")
                logger.error(f"[Pangle] App ID conversion failed - siteId: {site_id}, appId after conversion: {app_id}")
                return
            
            platform_display = platform.upper() if platform else ""
            logger.info(f"[Pangle] Creating {slot_key} placement - platform: {platform_display}, app_id: {app_id} (type: {type(app_id)})")
            
            # Convert app_id to int (Pangle API expects int)
            try:
                app_id_int = int(app_id) if app_id else None
            except (ValueError, TypeError):
                st.error(f"❌ App ID must be a valid integer. Current value: {app_id}")
                logger.error(f"[Pangle] App ID conversion failed - app_id: {app_id}")
                return
            
            payload = {
                "app_id": app_id_int,  # Required field - must be int
                "ad_placement_type": slot_config["ad_slot_type"],
                "ad_slot_name": slot_name.strip(),  # User-selected name
                "bidding_type": 1,
            }
            
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
            
            # Log and display final payload
            import json as json_module
            logger.info(f"[Pangle] Final payload: {json_module.dumps(payload, indent=2)}")
            st.markdown("#### 📤 Request Payload")
            st.json(payload)
            
            with st.spinner(f"Creating {slot_key} placement..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
                    response = network_manager.create_unit(current_network, payload)
                    
                    # Display full response
                    st.markdown("#### 📥 Response")
                    st.json(response)
                    
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
                        
                        cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                        if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                            cached_units.append(unit_data)
                            SessionManager.cache_units(current_network, selected_app_code, cached_units)
                        
                        st.success(f"✅ {slot_key} placement created successfully!")
                        # Don't rerun - keep the response visible
                    else:
                        st.error(f"❌ Failed to create {slot_key} placement. Check response above.")
                except Exception as e:
                    st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                    SessionManager.log_error(current_network, str(e))
                    import traceback
                    st.code(traceback.format_exc())


def _render_mintegral_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                               app_name, apps, network_manager, current_network):
    """Render Mintegral slot UI"""
    placement_name_key = f"mintegral_slot_{slot_key}_name"
    
    # Track last selected app code to detect changes (shared across all slots)
    # Use a shared key to ensure all slots regenerate when app changes
    shared_last_app_code_key = "mintegral_last_app_code_shared"
    last_app_code = st.session_state.get(shared_last_app_code_key, "")
    
    # Auto-generate placement name if not set or if app selection changed
    app_selection_changed = selected_app_code and selected_app_code != last_app_code
    
    # Force regeneration if app selection changed (for all slots)
    # This ensures RV, IS, BN all regenerate when iOS app is selected
    if app_selection_changed:
        # Clear placement name to force regeneration
        if placement_name_key in st.session_state:
            del st.session_state[placement_name_key]
        logger.info(f"[Mintegral] App selection changed from '{last_app_code}' to '{selected_app_code}', clearing placement name for {slot_key}")
    
    should_regenerate = (
        placement_name_key not in st.session_state or 
        app_selection_changed
    )
    
    if selected_app_code and should_regenerate:
        logger.info(f"[Mintegral] Regenerating placement name. selected_app_code: {selected_app_code} (type: {type(selected_app_code).__name__}), last_app_code: {last_app_code}, app_selection_changed: {app_selection_changed}")
        logger.info(f"[Mintegral] apps list length: {len(apps)}, app_info_to_use: {app_info_to_use is not None}")
        pkg_name = ""
        platform_str = "android"
        app_name_for_slot = app_name
        
        if app_info_to_use:
            pkg_name = app_info_to_use.get("pkgName", "")
            platform_str = app_info_to_use.get("platformStr", "android")
            app_name_for_slot = app_info_to_use.get("name", app_name)
            logger.info(f"[Mintegral] From app_info_to_use: name={app_name_for_slot}, pkg={pkg_name}, platform={platform_str}")
        
        # Always try to get from apps list first (more reliable)
        found_in_apps = False
        for app in apps:
            app_identifier = app.get("appCode")
            # Try both string and int comparison
            if str(app_identifier) == str(selected_app_code) or app_identifier == selected_app_code:
                found_in_apps = True
                # Always update from apps list when app selection changes
                if app_selection_changed or not pkg_name:
                    pkg_name = app.get("pkgName", "")
                if app_selection_changed or not platform_str or platform_str == "unknown":
                    platform_from_app = app.get("platform", "")
                    platform_str = _normalize_platform_str(platform_from_app, "mintegral")
                if app_selection_changed or not app_name_for_slot or app_name_for_slot == app_name:
                    app_name_for_slot = app.get("name", app_name)
                logger.info(f"[Mintegral] Found app in apps list: name={app_name_for_slot}, pkg={pkg_name}, platform={platform_str}, appCode={app_identifier}")
                break
        
        if not found_in_apps:
            logger.warning(f"[Mintegral] App {selected_app_code} not found in apps list. Available appCodes: {[app.get('appCode') for app in apps[:5]]}")
        
        platform_str = _normalize_platform_str(platform_str, "mintegral")
        
        # For iOS apps, if pkg_name is iTunes ID (starts with "id" followed by numbers),
        # try to find Android version of the same app by matching app_name
        if platform_str == "ios" and pkg_name and pkg_name.startswith("id") and pkg_name[2:].isdigit():
            logger.info(f"[Mintegral] iOS app with iTunes ID: {pkg_name}, searching for Android version with app_name: {app_name_for_slot}")
            logger.info(f"[Mintegral] Searching in {len(apps)} apps for Android version")
            # Search for Android app with same app_name in apps list first
            android_found = False
            for app in apps:
                app_platform = app.get("platform", "")
                app_platform_normalized = _normalize_platform_str(app_platform, "mintegral")
                app_name_from_list = app.get("name", "")
                
                logger.debug(f"[Mintegral] Checking app: name={app_name_from_list}, platform={app_platform} (normalized: {app_platform_normalized})")
                
                if app_platform_normalized == "android" and app_name_from_list == app_name_for_slot:
                    android_pkg_name = app.get("pkgName", "")
                    if android_pkg_name and not android_pkg_name.startswith("id"):
                        logger.info(f"[Mintegral] Found Android app with same name in apps list, using package: {android_pkg_name}")
                        pkg_name = android_pkg_name
                        android_found = True
                        break
            
            # If not found in apps list, try fetching all apps from API
            if not android_found:
                logger.info(f"[Mintegral] Android app not found in apps list ({len(apps)} apps), fetching all apps from API")
                try:
                    all_apps = network_manager.get_apps(current_network)
                    if all_apps:
                        logger.info(f"[Mintegral] Fetched {len(all_apps)} apps from API, searching for Android version")
                        for app in all_apps:
                            app_platform = app.get("platform", "")
                            app_platform_normalized = _normalize_platform_str(app_platform, "mintegral")
                            app_name_from_list = app.get("name", "")
                            
                            if app_platform_normalized == "android" and app_name_from_list == app_name_for_slot:
                                android_pkg_name = app.get("pkgName", "")
                                if android_pkg_name and not android_pkg_name.startswith("id"):
                                    logger.info(f"[Mintegral] Found Android app with same name in full apps list, using package: {android_pkg_name}")
                                    pkg_name = android_pkg_name
                                    android_found = True
                                    break
                except Exception as e:
                    logger.warning(f"[Mintegral] Failed to fetch all apps from API: {str(e)}")
            
            if not android_found:
                logger.warning(f"[Mintegral] Could not find Android app with name '{app_name_for_slot}' in apps list. Available apps: {[(app.get('name'), app.get('platform')) for app in apps]}")
        
        # Generate placement name if we have a valid package name (not iTunes ID)
        logger.info(f"[Mintegral] Before generating: pkg_name={pkg_name}, platform_str={platform_str}, app_name_for_slot={app_name_for_slot}")
        if pkg_name and not (pkg_name.startswith("id") and pkg_name[2:].isdigit()):
            default_name = _generate_slot_name(pkg_name, platform_str, slot_key.lower(), "mintegral", network_manager=network_manager, app_name=app_name_for_slot)
            logger.info(f"[Mintegral] Generated placement name: {default_name} for app: {app_name_for_slot}, pkg: {pkg_name}")
            if default_name:
                st.session_state[placement_name_key] = default_name
            else:
                # generate_slot_name returned empty, use fallback
                logger.warning(f"[Mintegral] generate_slot_name returned empty, using fallback")
                default_name = f"{slot_key.lower()}_placement"
                st.session_state[placement_name_key] = default_name
        else:
            # No valid package name found, use fallback
            logger.warning(f"[Mintegral] No valid package name found (pkg_name: {pkg_name}), using fallback")
            default_name = f"{slot_key.lower()}_placement"
            st.session_state[placement_name_key] = default_name
        
        # Update last app code (shared across all slots)
        st.session_state[shared_last_app_code_key] = selected_app_code
    elif placement_name_key not in st.session_state:
        default_name = f"{slot_key.lower()}_placement"
        st.session_state[placement_name_key] = default_name
    
    placement_name = st.text_input(
        "Placement Name*",
        value=st.session_state[placement_name_key],
        key=placement_name_key,
        help=f"Name for {slot_config['name']} placement"
    )
    
    app_id_key = f"mintegral_slot_{slot_key}_app_id"
    
    # Priority: 1) app_info_to_use, 2) last_app_info, 3) apps list, 4) session_state
    app_id_from_app = None
    
    # First, try to get app_id from app_info_to_use (from selected app)
    if app_info_to_use:
        app_id_from_app = app_info_to_use.get("app_id") or app_info_to_use.get("appId") or app_info_to_use.get("appCode")
        logger.info(f"[Mintegral] app_info_to_use app_id: {app_id_from_app}, keys: {list(app_info_to_use.keys())}")
    
    # If not found, try last_app_info (from Create App response)
    if not app_id_from_app:
        last_app_info = SessionManager.get_last_created_app_info(current_network)
        if last_app_info:
            app_id_from_app = last_app_info.get("app_id") or last_app_info.get("appId") or last_app_info.get("appCode")
            logger.info(f"[Mintegral] last_app_info app_id: {app_id_from_app}, keys: {list(last_app_info.keys()) if last_app_info else []}")
    
    # If still not found, try to get from apps list using selected_app_code
    if not app_id_from_app and selected_app_code:
        for app in apps:
            app_identifier = app.get("appCode") or app.get("app_id") or app.get("appId") or app.get("id")
            if app_identifier == selected_app_code or str(app_identifier) == str(selected_app_code):
                app_id_from_app = app.get("app_id") or app.get("appId") or app.get("id")
                logger.info(f"[Mintegral] Found app_id from apps list: {app_id_from_app}")
                break
    
    # Calculate default_app_id
    if app_id_from_app:
        try:
            default_app_id = max(1, int(app_id_from_app)) if app_id_from_app else 1
            logger.info(f"[Mintegral] Using app_id_from_app: {app_id_from_app} -> default_app_id: {default_app_id}")
        except (ValueError, TypeError) as e:
            logger.warning(f"[Mintegral] Failed to convert app_id_from_app to int: {app_id_from_app}, error: {e}")
            default_app_id = 1
    else:
        # Check session_state, but prefer app_id_from_app if available
        default_app_id = st.session_state.get(app_id_key, 1)
        if default_app_id < 1:
            default_app_id = 1
        logger.info(f"[Mintegral] No app_id found, using session_state: {default_app_id}")
    
    # Only update session_state if we have a valid app_id_from_app
    if app_id_from_app and default_app_id > 1:
        st.session_state[app_id_key] = default_app_id
    
    app_id = st.number_input(
        "App ID*",
        value=default_app_id,
        min_value=1,
        key=app_id_key,
        help="Media ID from created app or enter manually"
    )
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 180px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Ad Type: {slot_config["ad_type"].replace("_", " ").title()}</li>'
    settings_html += f'<li>Integration Type: SDK</li>'
    
    if slot_key == "RV":
        skip_time_text = "Non Skippable" if slot_config["skip_time"] == -1 else f"{slot_config['skip_time']} seconds"
        settings_html += f'<li>Skip Time: {skip_time_text}</li>'
        settings_html += f'<li>HB Unit Name: {placement_name if placement_name else "(same as Placement Name)"}</li>'
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
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
    
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    with st.expander("⚙️ Edit Settings"):
        if slot_key == "RV":
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
    
    if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_mintegral_{slot_key}"):
        if not placement_name:
            st.toast("❌ Placement Name is required", icon="🚫")
        elif not app_id or app_id <= 0:
            st.error(f"❌ App ID is required and must be greater than 0. Current value: {app_id}")
            st.write(f"**Debug Info:**")
            st.write(f"- app_info_to_use: {app_info_to_use}")
            st.write(f"- selected_app_code: {selected_app_code}")
            st.write(f"- last_app_info: {SessionManager.get_last_created_app_info(current_network)}")
        else:
            # Ensure app_id is a valid integer
            try:
                app_id_int = int(app_id)
                if app_id_int <= 0:
                    st.error(f"❌ App ID must be greater than 0. Current value: {app_id_int}")
                    st.stop()
            except (ValueError, TypeError):
                st.error(f"❌ App ID must be a valid integer. Current value: {app_id} (type: {type(app_id)})")
                st.stop()
            
            payload = {
                "app_id": app_id_int,
                "placement_name": placement_name,
                "ad_type": slot_config["ad_type"],
                "integrate_type": slot_config.get("integrate_type", "sdk"),
                "hb_unit_name": placement_name,
            }
            
            if slot_key == "RV":
                payload["skip_time"] = slot_config.get("skip_time", -1)
            elif slot_key == "IS":
                payload["content_type"] = slot_config.get("content_type", "both")
                payload["ad_space_type"] = slot_config.get("ad_space_type", 1)
                payload["skip_time"] = slot_config.get("skip_time", -1)
            elif slot_key == "BN":
                payload["show_close_button"] = slot_config.get("show_close_button", 0)
                payload["auto_fresh"] = slot_config.get("auto_fresh", 0)
            
            # Log payload for debugging
            logger.info(f"[Mintegral] Create Unit Payload: {payload}")
            logger.info(f"[Mintegral] Payload keys: {list(payload.keys())}")
            logger.info(f"[Mintegral] app_id type: {type(payload['app_id'])}, value: {payload['app_id']}")
            logger.info(f"[Mintegral] placement_name: {payload['placement_name']}")
            logger.info(f"[Mintegral] ad_type: {payload['ad_type']}")
            logger.info(f"[Mintegral] integrate_type: {payload['integrate_type']}")
            logger.info(f"[Mintegral] hb_unit_name: {payload['hb_unit_name']}")
            
            with st.spinner(f"Creating {slot_key} placement..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
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
                        
                        cached_units = SessionManager.get_cached_units(current_network, str(app_id))
                        if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                            cached_units.append(unit_data)
                            SessionManager.cache_units(current_network, str(app_id), cached_units)
                        
                        st.success(f"✅ {slot_key} placement created successfully!")
                        # Display payload and response
                        st.markdown("#### 📤 Request Payload")
                        st.json(payload)
                        st.markdown("#### 📥 Response")
                        st.json(response)
                        # Don't rerun - keep the response visible
                except Exception as e:
                    st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                    SessionManager.log_error(current_network, str(e))


def _render_inmobi_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                            app_name, apps, network_manager, current_network):
    """Render InMobi slot UI"""
    placement_name_key = f"inmobi_slot_{slot_key}_name"
    
    app_id = None
    if selected_app_code:
        if app_info_to_use:
            app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId")
        
        if not app_id:
            try:
                app_id = int(selected_app_code)
            except (ValueError, TypeError):
                app_id = None
        
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
    
    if selected_app_code:
        bundle_id = ""
        pkg_name = ""
        platform_str = "android"
        app_name_for_slot = app_name
        
        for app in apps:
            app_identifier = app.get("appId") or app.get("appCode")
            if str(app_identifier) == str(selected_app_code):
                bundle_id = app.get("bundleId", "")
                pkg_name = app.get("pkgName", "")
                platform_from_app = app.get("platform", "")
                platform_str = _normalize_platform_str(platform_from_app, "inmobi")
                app_name_for_slot = app.get("name", app_name)
                break
        
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
        
        platform_str = _normalize_platform_str(platform_str, "inmobi")
        source_pkg = bundle_id if bundle_id else pkg_name
        
        if source_pkg:
            slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
            slot_type = slot_type_map.get(slot_key, slot_key.lower())
            default_name = _generate_slot_name(source_pkg, platform_str, slot_type, "inmobi", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
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
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 120px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Placement Type: {slot_config["placementType"].replace("_", " ").title()}</li>'
    settings_html += f'<li>Audience Bidding: {"Enabled" if slot_config["isAudienceBiddingEnabled"] else "Disabled"}</li>'
    if slot_config["isAudienceBiddingEnabled"]:
        settings_html += f'<li>Audience Bidding Partner: {slot_config["audienceBiddingPartner"]}</li>'
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_inmobi_{slot_key}"):
        if not selected_app_code:
            st.toast("❌ Please select an App Code", icon="🚫")
        elif not app_id or app_id <= 0:
            st.toast("❌ App ID is required. Please select an App Code.", icon="🚫")
        elif not placement_name:
            st.toast("❌ Placement Name is required", icon="🚫")
        else:
            payload = {
                "appId": int(app_id),
                "placementName": placement_name,
                "placementType": slot_config["placementType"],
                "isAudienceBiddingEnabled": slot_config["isAudienceBiddingEnabled"],
            }
            
            if slot_config["isAudienceBiddingEnabled"]:
                payload["audienceBiddingPartner"] = slot_config["audienceBiddingPartner"]
            
            with st.spinner(f"Creating {slot_key} placement..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
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
                        
                        cached_units = SessionManager.get_cached_units(current_network, str(app_id))
                        if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                            cached_units.append(unit_data)
                            SessionManager.cache_units(current_network, str(app_id), cached_units)
                        
                        st.success(f"✅ {slot_key} placement created successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                    SessionManager.log_error(current_network, str(e))


def _render_fyber_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                          app_name, apps, network_manager, current_network, platform=None):
    """Render Fyber slot UI
    
    Args:
        platform: "android" or "ios" to specify which platform to render (for dual-platform display)
    """
    # Use platform-specific key for placement name if platform is specified
    if platform:
        placement_name_key = f"fyber_slot_{slot_key}_{platform}_name"
    else:
        placement_name_key = f"fyber_slot_{slot_key}_name"
    
    if not selected_app_code:
        manual_code = st.session_state.get("manual_app_code_input", "")
        if manual_code:
            selected_app_code = manual_code.strip()
    
    # Get app_id based on platform
    app_id = None
    if selected_app_code:
        if app_info_to_use:
            if platform == "ios":
                # For iOS, use appIdIOS if available
                app_id = app_info_to_use.get("appIdIOS")
            else:
                # For Android or no platform specified, use appId
                app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId")
        
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
        
        if not app_id:
            try:
                app_id = int(selected_app_code)
            except (ValueError, TypeError):
                numeric_match = re.search(r'\d+', str(selected_app_code))
                if numeric_match:
                    app_id = int(numeric_match.group())
                else:
                    app_id = None
    
    # Auto-generate placement name if not set or if app info is available
    if placement_name_key not in st.session_state or (selected_app_code and app_info_to_use):
        if selected_app_code and app_info_to_use:
            # Get bundle_id and platform_str based on platform parameter or app_info_to_use
            # If platform parameter is provided, use it; otherwise, determine from app_info_to_use
            if platform:
                # Use platform parameter if provided
                if platform == "ios":
                    bundle_id = app_info_to_use.get("iosBundle") or app_info_to_use.get("bundleId") or app_info_to_use.get("bundle") or app_info_to_use.get("pkgName", "")
                    platform_str = "ios"
                else:
                    bundle_id = app_info_to_use.get("androidBundle") or app_info_to_use.get("bundleId") or app_info_to_use.get("bundle") or app_info_to_use.get("pkgName", "")
                    platform_str = "android"
            else:
                # No platform parameter, determine from app_info_to_use or apps list
                # Check if app_info_to_use has platform info (prefer platformStr, then platform)
                platform_str_from_info = app_info_to_use.get("platformStr", "")
                if not platform_str_from_info:
                    app_platform_raw = app_info_to_use.get("platform", "")
                    if app_platform_raw:
                        # Normalize platform using helper function
                        platform_str_from_info = _normalize_platform_str(str(app_platform_raw), "fyber")
                
                if platform_str_from_info == "ios":
                    bundle_id = app_info_to_use.get("iosBundle") or app_info_to_use.get("bundleId") or app_info_to_use.get("bundle") or app_info_to_use.get("pkgName", "")
                    platform_str = "ios"
                else:
                    # Default to Android or check apps list
                    bundle_id = app_info_to_use.get("androidBundle") or app_info_to_use.get("bundleId") or app_info_to_use.get("bundle") or app_info_to_use.get("pkgName", "")
                    platform_str = "android"
            
            pkg_name = app_info_to_use.get("pkgName", "")
            app_name_for_slot = app_info_to_use.get("name", app_name)
            
            source_pkg = bundle_id if bundle_id else pkg_name
            
            if source_pkg:
                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                slot_type = slot_type_map.get(slot_key, slot_key.lower())
                default_name = _generate_slot_name(source_pkg, platform_str, slot_type, "fyber", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                st.session_state[placement_name_key] = default_name
        elif selected_app_code and app_id:
            # If app_id is available but app_info_to_use is not, try to get bundleId from apps list
            bundle_id = ""
            pkg_name = ""
            platform_str = "android"  # Default, will be updated from app info
            app_name_for_slot = app_name
            
            for app in apps:
                app_identifier = app.get("appId") or app.get("appCode") or app.get("id")
                if str(app_identifier) == str(selected_app_code) or str(app_identifier) == str(app_id):
                    bundle_id = app.get("bundleId") or app.get("bundle", "")
                    pkg_name = app.get("pkgName", "")
                    platform_from_app = app.get("platform", "")
                    platform_str = _normalize_platform_str(platform_from_app, "fyber")
                    app_name_for_slot = app.get("name", app_name)
                    break
            
            # If platform parameter is provided, use it (overrides app's platform)
            if platform:
                platform_str = platform
            
            source_pkg = bundle_id if bundle_id else pkg_name
            
            if source_pkg:
                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                slot_type = slot_type_map.get(slot_key, slot_key.lower())
                default_name = _generate_slot_name(source_pkg, platform_str, slot_type, "fyber", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                st.session_state[placement_name_key] = default_name
            else:
                default_name = f"{slot_key.lower()}_placement"
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
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 80px; margin-bottom: 10px;">'
    settings_html += '<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Placement Type: {slot_config["placementType"]}</li>'
    settings_html += f'<li>COPPA: {"No" if not slot_config["coppa"] else "Yes"}</li>'
    # Add skipability display for Interstitial
    if slot_key == "IS" and slot_config.get("skipability"):
        settings_html += f'<li>Skipability: {slot_config["skipability"]}</li>'
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    if app_id:
        platform_display = "iOS" if platform == "ios" else "Android" if platform else ""
        if platform_display:
            st.info(f"📱 {platform_display} App ID: {app_id}")
        else:
            st.info(f"📱 App ID: {app_id}")
    elif selected_app_code:
        st.warning(f"⚠️ App ID not found. Will use entered code: {selected_app_code}")
    
    button_key = f"create_fyber_{slot_key}_{platform}" if platform else f"create_fyber_{slot_key}"
    button_label = f"✅ Create {slot_key} Placement ({platform.upper()})" if platform else f"✅ Create {slot_key} Placement"
    if st.button(button_label, use_container_width=True, key=button_key):
        current_app_code = selected_app_code
        if not current_app_code:
            manual_code = st.session_state.get("manual_app_code_input", "")
            if manual_code:
                current_app_code = manual_code.strip()
        
        if not placement_name:
            st.toast("❌ Placement Name is required", icon="🚫")
        elif not current_app_code:
            st.toast("❌ App Code is required. Please select an app or enter manually.", icon="🚫")
        else:
            if not selected_app_code:
                selected_app_code = current_app_code
            
            code_to_parse = current_app_code if current_app_code else selected_app_code
            # Convert app_id to int if it's a string, then check
            app_id_int = None
            if app_id:
                try:
                    app_id_int = int(app_id) if isinstance(app_id, (int, str)) else None
                except (ValueError, TypeError):
                    app_id_int = None
            
            if not app_id_int or app_id_int <= 0:
                try:
                    app_id_int = int(code_to_parse)
                except (ValueError, TypeError):
                    numeric_match = re.search(r'\d+', str(code_to_parse))
                    if numeric_match:
                        app_id_int = int(numeric_match.group())
                else:
                    app_id_int = None
                    st.toast("❌ Invalid App ID. Please enter a valid numeric App ID.", icon="🚫")
                app_id = app_id_int
            else:
                app_id = app_id_int
            
            # Ensure app_id is an integer before comparison
            if app_id and not isinstance(app_id, int):
                try:
                    app_id = int(app_id)
                except (ValueError, TypeError):
                    app_id = None
            
            if not app_id or app_id <= 0:
                st.toast("❌ App ID is required. Please select an app or enter a valid App ID.", icon="🚫")
            else:
                payload = {
                    "name": placement_name.strip(),
                    "appId": str(app_id),
                    "placementType": slot_config["placementType"],
                    "coppa": bool(slot_config["coppa"]),
                }
                
                # Add skipability for Interstitial placement (default: NonSkippable)
                if slot_key == "IS" and slot_config.get("skipability"):
                    payload["skipability"] = slot_config["skipability"]
                
                import json as json_module
                logger.info(f"[Fyber] Creating placement - selected_app_code: {selected_app_code}, appId: {app_id}, payload: {json_module.dumps(payload)}")
                
                with st.spinner(f"Creating {slot_key} placement..."):
                    try:
                        from utils.network_manager import get_network_manager
                        network_manager = get_network_manager()
                        response = network_manager.create_unit(current_network, payload)
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
                            
                            cached_units = SessionManager.get_cached_units(current_network, str(app_id))
                            if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                cached_units.append(unit_data)
                                SessionManager.cache_units(current_network, str(app_id), cached_units)
                            
                            if st.button("🔄 Refresh Page", key=f"refresh_after_{slot_key}", use_container_width=True):
                                st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                        SessionManager.log_error(current_network, str(e))


def _render_admob_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                          app_name, apps, network_manager, current_network):
    """Render AdMob Google Bidding Ad Unit creation UI (similar to InMobi)
    
    Args:
        slot_key: Slot key (RV, IS, BN)
        slot_config: Slot configuration
        selected_app_code: Selected app code
        app_info_to_use: App info dict
        app_name: App name
        apps: List of apps
        network_manager: Network manager instance
        current_network: Current network identifier
    """
    display_name_key = f"admob_slot_{slot_key}_name"
    
    # Map slot_key to format
    format_map = {
        "RV": "REWARDED",
        "IS": "INTERSTITIAL",
        "BN": "BANNER"
    }
    ad_format = format_map.get(slot_key, "REWARDED")
    
    # Get app info
    app_id = None
    app_store_id = None
    pkg_name = ""
    platform_str = "android"
    app_name_for_slot = app_name
    
    if selected_app_code:
        if app_info_to_use:
            # For AdMob, use appId and appStoreId directly
            app_id = app_info_to_use.get("appId")
            app_store_id = app_info_to_use.get("appStoreId")
            # For AdMob display name, use linkedAppInfo.appStoreId
            linked_info = app_info_to_use.get("linkedAppInfo", {})
            if linked_info:
                app_store_id = linked_info.get("appStoreId") or app_store_id
            pkg_name = app_store_id or app_info_to_use.get("pkgName", "")
            platform_str = app_info_to_use.get("platformStr", "android")
            app_name_for_slot = app_info_to_use.get("name", app_name)
        
        if not app_id and not app_store_id:
            for app in apps:
                app_identifier = app.get("appId") or app.get("appCode")
                if str(app_identifier) == str(selected_app_code):
                    app_id = app.get("appId")
                    # For AdMob, get appStoreId from linkedAppInfo
                    linked_info = app.get("linkedAppInfo", {})
                    app_store_id = linked_info.get("appStoreId") if linked_info else app.get("appStoreId")
                    pkg_name = app_store_id or app.get("pkgName", "")
                    platform_str_val = app.get("platform", "")
                    platform_str = "android" if platform_str_val == "ANDROID" else ("ios" if platform_str_val == "IOS" else "android")
                    app_name_for_slot = app.get("name", app_name)
                    break
    
    # Auto-generate display name if not set or if app info is available
    should_regenerate = (
        display_name_key not in st.session_state or 
        (selected_app_code and (app_info_to_use or apps))
    )
    
    if should_regenerate and selected_app_code:
        # Try to get appStoreId from linkedAppInfo if not already set
        if not app_store_id or not pkg_name:
            # Try to get from apps list
            for app in apps:
                app_identifier = app.get("appId") or app.get("appCode")
                if str(app_identifier) == str(selected_app_code):
                    if not app_id:
                        app_id = app.get("appId")
                    # For AdMob, get appStoreId from linkedAppInfo
                    linked_info = app.get("linkedAppInfo", {})
                    if linked_info:
                        app_store_id = linked_info.get("appStoreId") or app_store_id
                        pkg_name = app_store_id or pkg_name
                    else:
                        app_store_id = app.get("appStoreId") or app_store_id
                        pkg_name = app_store_id or app.get("pkgName", "") or pkg_name
                    
                    if not platform_str or platform_str == "android":
                        platform_str_val = app.get("platform", "")
                        platform_str = "android" if platform_str_val == "ANDROID" else ("ios" if platform_str_val == "IOS" else "android")
                    if not app_name_for_slot or app_name_for_slot == app_name:
                        app_name_for_slot = app.get("name", app_name)
                    break
        
        # Log for debugging
        logger.info(f"[AdMob] Display name generation - selected_app_code: {selected_app_code}, pkg_name: {pkg_name}, app_store_id: {app_store_id}, platform_str: {platform_str}, app_name: {app_name_for_slot}")
        
        if pkg_name or app_store_id:
            # For AdMob, use linkedAppInfo.appStoreId's last part after "."
            # If iOS and appStoreId is numeric only, find Android app with same name
            display_name_pkg = pkg_name or app_store_id
            
            # Check if iOS and appStoreId is numeric only (iTunes ID)
            if platform_str == "ios" and app_store_id and app_store_id.strip().isdigit():
                # Find Android app with same name
                logger.info(f"[AdMob] iOS appStoreId is numeric ({app_store_id}), searching for Android app with same name: {app_name_for_slot}")
                for app in apps:
                    app_name_match = app.get("name", "")
                    app_platform = app.get("platform", "")
                    if app_name_match == app_name_for_slot and app_platform == "ANDROID":
                        # Use Android app's linkedAppInfo.appStoreId
                        android_linked_info = app.get("linkedAppInfo", {})
                        android_app_store_id = android_linked_info.get("appStoreId") if android_linked_info else app.get("appStoreId")
                        if android_app_store_id:
                            display_name_pkg = android_app_store_id
                            logger.info(f"[AdMob] Found Android app with same name, using appStoreId: {android_app_store_id}")
                            break
            
            # Extract last part after "." for display name
            if display_name_pkg and "." in display_name_pkg:
                last_part = display_name_pkg.split(".")[-1]
            else:
                last_part = display_name_pkg if display_name_pkg else "app"
            
            slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
            slot_type = slot_type_map.get(slot_key, slot_key.lower())
            # Format: {last_part}_{os}_admob_{adtype}_bidding
            os_str = "aos" if platform_str == "android" else "ios"
            default_name = f"{last_part}_{os_str}_admob_{slot_type}_bidding"
            
            logger.info(f"[AdMob] Generated display name: {default_name} (from pkg: {display_name_pkg}, last_part: {last_part})")
            st.session_state[display_name_key] = default_name
        elif display_name_key not in st.session_state:
            # Fallback: use slot_type (rv, is, bn)
            slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
            slot_type = slot_type_map.get(slot_key, slot_key.lower())
            default_name = f"{slot_key.lower()}_admob_{slot_type}_bidding"
            logger.warning(f"[AdMob] Using fallback display name: {default_name} (pkg_name and app_store_id not found)")
            st.session_state[display_name_key] = default_name
    elif display_name_key not in st.session_state:
        # Fallback: use slot_type (rv, is, bn)
        slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
        slot_type = slot_type_map.get(slot_key, slot_key.lower())
        default_name = f"{slot_key.lower()}_admob_{slot_type}_bidding"
        st.session_state[display_name_key] = default_name
    
    display_name = st.text_input(
        "Display Name*",
        value=st.session_state.get(display_name_key, ""),
        key=display_name_key,
        help=f"Name for {slot_config.get('name', slot_key)} ad unit"
    )
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 80px; margin-bottom: 10px;">'
    settings_html += '<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Format: {ad_format}</li>'
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    # App ID / App Store ID display
    if app_id:
        st.info(f"📱 App ID: {app_id}")
    elif app_store_id:
        st.info(f"📱 App Store ID: {app_store_id}")
    elif selected_app_code:
        st.warning(f"⚠️ App ID/App Store ID not found. Will use entered code: {selected_app_code}")
    
    if st.button(f"✅ Create {slot_key} Ad Unit", use_container_width=True, key=f"create_admob_{slot_key}"):
        if not selected_app_code:
            st.toast("❌ Please select an App Code", icon="🚫")
        elif not display_name:
            st.toast("❌ Display Name is required", icon="🚫")
        elif not app_id and not app_store_id:
            st.toast("❌ App ID or App Store ID is required. Please select an App Code.", icon="🚫")
        else:
            payload = {
                "displayName": display_name.strip(),
                "format": ad_format
            }
            
            if app_id:
                payload["appId"] = app_id
            elif app_store_id:
                payload["appStoreId"] = app_store_id
            
            with st.spinner(f"Creating {slot_key} ad unit..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
                    response = network_manager.create_unit(current_network, payload)
                    result = handle_api_response(response)
                    
                    if result:
                        result_data = result.get("result", {})
                        if isinstance(result_data, dict):
                            unit_id = result_data.get("name") or result_data.get("adUnitId") or result_data.get("id")
                            unit_data = {
                                "slotCode": unit_id or "N/A",
                                "name": display_name,
                                "appCode": app_id or app_store_id or selected_app_code,
                                "slotType": ad_format,
                                "adType": ad_format,
                                "auctionType": "N/A"
                            }
                            SessionManager.add_created_unit(current_network, unit_data)
                            
                            cached_units = SessionManager.get_cached_units(current_network, str(app_id or app_store_id or selected_app_code))
                            if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                cached_units.append(unit_data)
                                SessionManager.cache_units(current_network, str(app_id or app_store_id or selected_app_code), cached_units)
                        
                        st.success(f"✅ {slot_key} ad unit created successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating {slot_key} ad unit: {str(e)}")
                    SessionManager.log_error(current_network, str(e))


def _render_bigoads_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                             app_name, apps, network_manager, current_network,
                             AD_TYPE_MAP, AUCTION_TYPE_MAP, MUSIC_SWITCH_MAP,
                             AUTO_REFRESH_MAP, BANNER_SIZE_MAP,
                             AD_TYPE_REVERSE, AUCTION_TYPE_REVERSE,
                             MUSIC_SWITCH_REVERSE, AUTO_REFRESH_REVERSE,
                             BANNER_SIZE_REVERSE):
    """Render BigOAds slot UI"""
    slot_name_key = f"custom_slot_{slot_key}_name"
    
    pkg_name = ""
    platform_str = "android"
    
    if selected_app_code and app_info_to_use:
        if current_network == "bigoads":
            pkg_name = app_info_to_use.get("pkgNameDisplay", app_info_to_use.get("pkgName", ""))
        else:
            pkg_name = app_info_to_use.get("pkgName", "")
        platform_str = app_info_to_use.get("platformStr", "android")
    elif selected_app_code:
        for app in apps:
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
    
    if selected_app_code and pkg_name:
        bundle_id = app_info_to_use.get("bundleId", "") if app_info_to_use else ""
        app_name_for_slot = app_info_to_use.get("name", app_name) if app_info_to_use else app_name
        default_name = _generate_slot_name(pkg_name, platform_str, slot_key.lower(), current_network, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
        st.session_state[slot_name_key] = default_name
    elif slot_name_key not in st.session_state:
        default_name = f"slot_{slot_key.lower()}"
        st.session_state[slot_name_key] = default_name
    
    slot_name = st.text_input(
        "Slot Name*",
        value=st.session_state[slot_name_key],
        key=slot_name_key,
        help=f"Name for {slot_config['name']} slot"
    )
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 120px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Ad Type: {AD_TYPE_MAP[slot_config["adType"]]}</li>'
    settings_html += f'<li>Auction Type: {AUCTION_TYPE_MAP[slot_config["auctionType"]]}</li>'
    
    if slot_key == "BN":
        # Get bannerAutoRefresh, fallback to autoRefresh for backward compatibility
        banner_auto_refresh = slot_config.get('bannerAutoRefresh', slot_config.get('autoRefresh', 2))
        settings_html += f'<li>Auto Refresh: {AUTO_REFRESH_MAP.get(banner_auto_refresh, "No")}</li>'
        banner_size_w = slot_config.get('bannerSizeW', 250)
        banner_size_h = slot_config.get('bannerSizeH', 320)
        settings_html += f'<li>Banner Size: {banner_size_w}x{banner_size_h}</li>'
    else:
        settings_html += f'<li>Music: {MUSIC_SWITCH_MAP[slot_config["musicSwitch"]]}</li>'
    
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    with st.expander("⚙️ Edit Settings"):
        st.selectbox(
            "Ad Type",
            options=[AD_TYPE_MAP[slot_config['adType']]],
            key=f"{slot_key}_adType_display",
            disabled=True
        )
        
        auction_type_display = AUCTION_TYPE_MAP[slot_config['auctionType']]
        new_auction_type = st.selectbox(
            "Auction Type",
            options=list(AUCTION_TYPE_MAP.values()),
            index=list(AUCTION_TYPE_MAP.values()).index(auction_type_display),
            key=f"{slot_key}_auctionType"
        )
        slot_config['auctionType'] = AUCTION_TYPE_REVERSE[new_auction_type]
        
        if slot_key == "BN":
            # Get bannerAutoRefresh, fallback to autoRefresh for backward compatibility
            current_auto_refresh = slot_config.get('bannerAutoRefresh', slot_config.get('autoRefresh', 2))
            auto_refresh_display = AUTO_REFRESH_MAP.get(current_auto_refresh, "No")
            new_auto_refresh = st.selectbox(
                "Auto Refresh",
                options=list(AUTO_REFRESH_MAP.values()),
                index=list(AUTO_REFRESH_MAP.values()).index(auto_refresh_display) if auto_refresh_display in AUTO_REFRESH_MAP.values() else 0,
                key=f"{slot_key}_autoRefresh"
            )
            auto_refresh_value = AUTO_REFRESH_REVERSE[new_auto_refresh]
            slot_config['autoRefresh'] = auto_refresh_value  # Keep for backward compatibility
            slot_config['bannerAutoRefresh'] = auto_refresh_value  # Set bannerAutoRefresh for API
            
            # Banner size is now fixed: 250x320 (bannerSizeMode=2, bannerSizeW=250, bannerSizeH=320)
            # Display current banner size
            banner_size_w = slot_config.get('bannerSizeW', 250)
            banner_size_h = slot_config.get('bannerSizeH', 320)
            st.info(f"Banner Size: {banner_size_w}x{banner_size_h} (Fixed)")
            # Keep values in slot_config
            slot_config['bannerSizeMode'] = slot_config.get('bannerSizeMode', 2)
            slot_config['bannerSizeW'] = banner_size_w
            slot_config['bannerSizeH'] = banner_size_h
        else:
            music_display = MUSIC_SWITCH_MAP[slot_config['musicSwitch']]
            new_music = st.selectbox(
                "Music",
                options=list(MUSIC_SWITCH_MAP.values()),
                index=list(MUSIC_SWITCH_MAP.values()).index(music_display),
                key=f"{slot_key}_musicSwitch"
            )
            slot_config['musicSwitch'] = MUSIC_SWITCH_REVERSE[new_music]
    
    if st.button(f"✅ Create {slot_key} Slot", use_container_width=True, key=f"create_{slot_key}"):
        # Log selected_app_code and slot_name for debugging
        logger.info(f"[BigOAds] Creating {slot_key} slot with appCode: {selected_app_code}, name: {slot_name}")
        logger.info(f"[BigOAds] selected_app_code type: {type(selected_app_code)}, value: {selected_app_code}")
        logger.info(f"[BigOAds] slot_name type: {type(slot_name)}, value: {slot_name}")
        
        # Validate appCode
        if not selected_app_code or (isinstance(selected_app_code, str) and not selected_app_code.strip()):
            st.error("❌ App Code is required. Please select an app or enter manually.")
            logger.error(f"[BigOAds] Invalid appCode: '{selected_app_code}'")
            return
        
        # Validate slot name
        if not slot_name or (isinstance(slot_name, str) and not slot_name.strip()):
            st.error("❌ Slot Name is required. Please enter a slot name.")
            logger.error(f"[BigOAds] Invalid slot_name: '{slot_name}'")
            return
        
        # Ensure appCode and name are strings (not None)
        app_code_str = str(selected_app_code).strip()
        slot_name_str = str(slot_name).strip()
        
        payload = {
            "appCode": app_code_str,
            "name": slot_name_str,
            "adType": slot_config['adType'],
            "auctionType": slot_config['auctionType'],
        }
        
        if slot_key == "BN":
            payload["bannerAutoRefresh"] = slot_config.get('bannerAutoRefresh', slot_config.get('autoRefresh', 2))
            # API requires bannerSize field as array - always set to [2]
            payload["bannerSize"] = [2]
        else:
            payload["musicSwitch"] = slot_config['musicSwitch']
        
        # Log and display final payload
        logger.info(f"[BigOAds] Final payload: {payload}")
        st.markdown("#### 📤 Request Payload")
        st.json(payload)
        
        with st.spinner(f"Creating {slot_key} slot..."):
            try:
                from utils.network_manager import get_network_manager
                network_manager = get_network_manager()
                response = network_manager.create_unit(current_network, payload)
                
                # Display full response
                st.markdown("#### 📥 Response")
                st.json(response)
                
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
                    
                    cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                    if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                        cached_units.append(unit_data)
                        SessionManager.cache_units(current_network, selected_app_code, cached_units)
                    
                    st.success(f"✅ {slot_key} slot created successfully!")
                    # Don't rerun - keep the response visible
                else:
                    st.error(f"❌ Failed to create {slot_key} slot. Check response above.")
            except Exception as e:
                st.error(f"❌ Error creating {slot_key} slot: {str(e)}")
                SessionManager.log_error(current_network, str(e))
                import traceback
                st.code(traceback.format_exc())

