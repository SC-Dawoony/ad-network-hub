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
                    _render_ironsource_slot_ui(
                        slot_key, slot_config, selected_app_code, app_info_to_use,
                        app_name, network_manager, current_network
                    )
                elif current_network == "pangle":
                    _render_pangle_slot_ui(
                        slot_key, slot_config, selected_app_code, app_info_to_use,
                        app_name, network_manager, current_network
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
                    _render_fyber_slot_ui(
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
            bundle_id = app_info_to_use.get("bundleId", "")
            platform_str = app_info_to_use.get("platformStr", "android")
            app_name_for_slot = app_info_to_use.get("name", app_name)
            if bundle_id:
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
                expected_name = _generate_slot_name(bundle_id, platform_str, slot_type, "ironsource", store_url=None, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
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
    
    if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_ironsource_{slot_key}"):
        if not mediation_ad_unit_name:
            st.toast("❌ Mediation Ad Unit Name is required", icon="🚫")
        else:
            payload = {
                "mediationAdUnitName": mediation_ad_unit_name,
                "adFormat": slot_config['adFormat'],
            }
            
            if slot_key == "RV" and slot_config.get("adFormat") == "rewarded":
                reward_item_name = slot_config.get("rewardItemName", "Reward")
                reward_amount = slot_config.get("rewardAmount", 1)
                payload["reward"] = {
                    "rewardItemName": reward_item_name,
                    "rewardAmount": reward_amount
                }
            
            with st.spinner(f"Creating {slot_key} placement..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
                    response = network_manager.create_unit(current_network, payload, app_key=selected_app_code)
                    
                    if not response:
                        st.error("❌ No response from API")
                        SessionManager.log_error(current_network, "No response from API")
                    else:
                        result = handle_api_response(response)
                        
                        if result is not None and isinstance(result, dict):
                            slot_code = result.get("adUnitId") or result.get("id") or result.get("placement_id") or result.get("placementId")
                            
                            if slot_code or not result:
                                if slot_code:
                                    unit_data = {
                                        "slotCode": slot_code,
                                        "name": mediation_ad_unit_name,
                                        "appCode": selected_app_code,
                                        "slotType": slot_config['adFormat'],
                                        "adType": slot_config['adFormat'],
                                        "auctionType": "N/A"
                                    }
                                    SessionManager.add_created_unit(current_network, unit_data)
                                    
                                    cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                                    if not cached_units:
                                        cached_units = []
                                    if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                        cached_units.append(unit_data)
                                        SessionManager.cache_units(current_network, selected_app_code, cached_units)
                                
                                st.success(f"✅ {slot_key} placement created successfully!")
                                st.rerun()
                            else:
                                st.success(f"✅ {slot_key} placement created successfully!")
                                st.rerun()
                        elif result is None:
                            pass
                        else:
                            st.error(f"❌ Unexpected response format: {type(result)}")
                            SessionManager.log_error(current_network, f"Unexpected response format: {type(result)}")
                except Exception as e:
                    st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                    SessionManager.log_error(current_network, str(e))


def _render_pangle_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                            app_name, network_manager, current_network):
    """Render Pangle slot UI"""
    slot_name_key = f"pangle_slot_{slot_key}_name"
    
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
        if slot_key == "BN":
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
            orientation = st.selectbox(
                "Orientation",
                options=[("Vertical", 1), ("Horizontal", 2)],
                index=0 if slot_config["orientation"] == 1 else 1,
                key=f"{slot_key}_orientation",
                format_func=lambda x: x[0]
            )
            slot_config["orientation"] = orientation[1]
    
    if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_pangle_{slot_key}"):
        if not slot_name:
            st.toast("❌ Slot Name is required", icon="🚫")
        elif slot_key == "RV" and (not slot_config.get("reward_name") or slot_config.get("reward_count") is None):
            st.toast("❌ Reward Name and Reward Count are required for Rewarded Video", icon="🚫")
        else:
            payload = {
                "app_id": selected_app_code,
                "ad_placement_type": slot_config["ad_slot_type"],
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
            
            with st.spinner(f"Creating {slot_key} placement..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
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
                        
                        cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                        if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                            cached_units.append(unit_data)
                            SessionManager.cache_units(current_network, selected_app_code, cached_units)
                        
                        st.success(f"✅ {slot_key} placement created successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                    SessionManager.log_error(current_network, str(e))


def _render_mintegral_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                               app_name, apps, network_manager, current_network):
    """Render Mintegral slot UI"""
    placement_name_key = f"mintegral_slot_{slot_key}_name"
    
    if selected_app_code:
        pkg_name = ""
        platform_str = "android"
        app_name_for_slot = app_name
        
        if app_info_to_use:
            pkg_name = app_info_to_use.get("pkgName", "")
            platform_str = app_info_to_use.get("platformStr", "android")
            app_name_for_slot = app_info_to_use.get("name", app_name)
        
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
        
        platform_str = _normalize_platform_str(platform_str, "mintegral")
        
        if pkg_name:
            default_name = _generate_slot_name(pkg_name, platform_str, slot_key.lower(), "mintegral", network_manager=network_manager, app_name=app_name_for_slot)
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
    
    app_id_key = f"mintegral_slot_{slot_key}_app_id"
    last_app_info = SessionManager.get_last_created_app_info(current_network)
    app_id_from_app = None
    if last_app_info:
        app_id_from_app = last_app_info.get("app_id") or last_app_info.get("appId") or last_app_info.get("appCode")
    
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
            st.toast("❌ App ID is required", icon="🚫")
        else:
            payload = {
                "app_id": int(app_id),
                "placement_name": placement_name,
                "ad_type": slot_config["ad_type"],
                "integrate_type": slot_config["integrate_type"],
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
                        st.rerun()
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
                          app_name, apps, network_manager, current_network):
    """Render Fyber slot UI"""
    placement_name_key = f"fyber_slot_{slot_key}_name"
    
    if not selected_app_code:
        manual_code = st.session_state.get("manual_app_code_input", "")
        if manual_code:
            selected_app_code = manual_code.strip()
    
    app_id = None
    if selected_app_code:
        if app_info_to_use:
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
    
    if placement_name_key not in st.session_state:
        if selected_app_code and app_info_to_use:
            bundle_id = app_info_to_use.get("bundleId", "")
            pkg_name = app_info_to_use.get("pkgName", "")
            platform_str = app_info_to_use.get("platformStr", "android")
            app_name_for_slot = app_info_to_use.get("name", app_name)
            
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
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 80px; margin-bottom: 10px;">'
    settings_html += '<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Placement Type: {slot_config["placementType"]}</li>'
    settings_html += f'<li>COPPA: {"No" if not slot_config["coppa"] else "Yes"}</li>'
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    if app_id:
        st.info(f"📱 App ID: {app_id}")
    elif selected_app_code:
        st.warning(f"⚠️ App ID not found. Will use entered code: {selected_app_code}")
    
    if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_fyber_{slot_key}"):
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
            if not app_id or app_id <= 0:
                try:
                    app_id = int(code_to_parse)
                except (ValueError, TypeError):
                    numeric_match = re.search(r'\d+', str(code_to_parse))
                    if numeric_match:
                        app_id = int(numeric_match.group())
                    else:
                        app_id = None
                        st.toast("❌ Invalid App ID. Please enter a valid numeric App ID.", icon="🚫")
            
            if not app_id or app_id <= 0:
                st.toast("❌ App ID is required. Please select an app or enter a valid App ID.", icon="🚫")
            else:
                payload = {
                    "name": placement_name.strip(),
                    "appId": str(app_id),
                    "placementType": slot_config["placementType"],
                    "coppa": bool(slot_config["coppa"]),
                }
                
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
        settings_html += f'<li>Auto Refresh: {AUTO_REFRESH_MAP[slot_config["autoRefresh"]]}</li>'
        settings_html += f'<li>Banner Size: {BANNER_SIZE_MAP[slot_config["bannerSize"]]}</li>'
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
            music_display = MUSIC_SWITCH_MAP[slot_config['musicSwitch']]
            new_music = st.selectbox(
                "Music",
                options=list(MUSIC_SWITCH_MAP.values()),
                index=list(MUSIC_SWITCH_MAP.values()).index(music_display),
                key=f"{slot_key}_musicSwitch"
            )
            slot_config['musicSwitch'] = MUSIC_SWITCH_REVERSE[new_music]
    
    if st.button(f"✅ Create {slot_key} Slot", use_container_width=True, key=f"create_{slot_key}"):
        payload = {
            "appCode": selected_app_code,
            "name": slot_name,
            "adType": slot_config['adType'],
            "auctionType": slot_config['auctionType'],
        }
        
        if slot_key == "BN":
            payload["autoRefresh"] = slot_config['autoRefresh']
            payload["bannerSize"] = slot_config['bannerSize']
        else:
            payload["musicSwitch"] = slot_config['musicSwitch']
        
        with st.spinner(f"Creating {slot_key} slot..."):
            try:
                from utils.network_manager import get_network_manager
                network_manager = get_network_manager()
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
                    
                    cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                    if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                        cached_units.append(unit_data)
                        SessionManager.cache_units(current_network, selected_app_code, cached_units)
                    
                    st.success(f"✅ {slot_key} slot created successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error creating {slot_key} slot: {str(e)}")
                SessionManager.log_error(current_network, str(e))

