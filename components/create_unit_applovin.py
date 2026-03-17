"""AppLovin Create Unit UI component"""
import streamlit as st
from utils.session_manager import SessionManager
from utils.network_manager import get_network_manager, handle_api_response


def render_applovin_create_unit_ui():
    """Render the AppLovin-specific Create Unit UI"""
    st.info("""
    ⚠️ **주의사항:**

    이미 활성화된 앱/플랫폼/광고 형식 조합에 대해서는 이 API를 통해 추가 Ad Unit을 생성할 수 없습니다.
    추가 생성은 대시보드에서 직접 진행해주세요.
    """)

    st.divider()

    # Ad Unit Information - per platform (manual input with store info pre-fill)
    st.markdown("**Ad Unit Information**")

    store_android = st.session_state.get("store_info_android")
    store_ios = st.session_state.get("store_info_ios")

    android_app_name = store_android.get("name", "") if store_android else ""
    ios_app_name = store_ios.get("name", "") if store_ios else ""

    info_cols = st.columns(2)
    with info_cols[0]:
        st.markdown("**🤖 Android**")
        android_package_name = st.text_input(
            "Package Name",
            value=store_android.get("package_name", "") if store_android else "",
            placeholder="com.example.app",
            key="applovin_android_package_name"
        )
    with info_cols[1]:
        st.markdown("**🍎 iOS**")
        ios_bundle_id = st.text_input(
            "Bundle ID",
            value=store_ios.get("bundle_id", "") if store_ios else "",
            placeholder="com.example.app",
            key="applovin_ios_bundle_id"
        )

    # App Name for ad unit name generation (pre-fill from store info)
    default_app_name = android_app_name or ios_app_name
    # Extract name before colon (e.g., "My Supermarket: Shop Rush" → "My Supermarket")
    if default_app_name and ":" in default_app_name:
        default_app_name = default_app_name.split(":")[0].strip()

    if default_app_name and not st.session_state.get("applovin_app_name"):
        st.session_state["applovin_app_name"] = default_app_name

    app_name = st.text_input(
        "App Name",
        placeholder="Glamour Boutique",
        help="App name (optional, used for Ad Unit Name generation)",
        key="applovin_app_name"
    )

    st.divider()

    # AppLovin slot configs
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

    # Create sections for Android and iOS (use store info package_name per platform)
    platforms = [
        ("android", "Android", "AOS", android_package_name),
        ("ios", "iOS", "iOS", ios_bundle_id)
    ]

    for platform, platform_display, os_str, pkg_name in platforms:
        st.subheader(f"📱 {platform_display}")

        # Create 3 columns for RV, IS, BN
        col1, col2, col3 = st.columns(3)

        for idx, (slot_key, slot_config) in enumerate(slot_configs_applovin.items()):
            with [col1, col2, col3][idx]:
                with st.container():
                    st.markdown(f"### 🎯 {slot_key} ({slot_config['name']})")

                    # Slot name input
                    slot_name_key = f"applovin_slot_{platform}_{slot_key}_name"

                    # Generate default name based on app_name or package_name
                    if app_name:
                        # Use app_name: {app_name} {os} {adformat}
                        adformat_map = {"RV": "RV", "IS": "IS", "BN": "BN"}
                        adformat = adformat_map.get(slot_key, slot_key)
                        default_name = f"{app_name} {os_str} {adformat}"
                        st.session_state[slot_name_key] = default_name
                    elif pkg_name:
                        # Fallback to package name format
                        pkg_last_part = pkg_name.split(".")[-1] if "." in pkg_name else pkg_name
                        os_lower = "aos" if platform == "android" else "ios"
                        adtype_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                        adtype = adtype_map.get(slot_key, slot_key.lower())
                        default_name = f"{pkg_last_part}_{os_lower}_applovin_{adtype}_bidding"
                        st.session_state[slot_name_key] = default_name
                    elif slot_name_key not in st.session_state:
                        default_name = f"{slot_key.lower()}_{platform}_ad_unit"
                        st.session_state[slot_name_key] = default_name

                    slot_name = st.text_input(
                        "Ad Unit Name*",
                        value=st.session_state.get(slot_name_key, ""),
                        key=slot_name_key,
                        help=f"Name for {slot_config['name']} ad unit ({platform_display})"
                    )

                    # Display current settings
                    st.markdown("**Current Settings:**")
                    settings_html = '<div style="min-height: 80px; margin-bottom: 10px;">'
                    settings_html += '<ul style="margin: 0; padding-left: 20px;">'
                    settings_html += f'<li>Ad Format: {slot_config["ad_format"]}</li>'
                    settings_html += f'<li>Platform: {platform_display}</li>'
                    settings_html += f'<li>Package Name: {pkg_name}</li>'
                    settings_html += '</ul></div>'
                    st.markdown(settings_html, unsafe_allow_html=True)

                    # Banner refresh interval (BN only)
                    if slot_key == "BN":
                        refresh_options = [0, 10, 15, 20, 30, 45, 60, 300]
                        refresh_labels = {
                            0: "0 (MAX 기본값)",
                            10: "10초", 15: "15초", 20: "20초",
                            30: "30초", 45: "45초", 60: "60초",
                            300: "300초 (5분)"
                        }
                        st.selectbox(
                            "Banner Refresh Interval",
                            options=refresh_options,
                            format_func=lambda x: refresh_labels.get(x, f"{x}초"),
                            index=4,  # 기본값: 30초
                            key=f"applovin_banner_refresh_{platform}_{slot_key}"
                        )

        # Create All button per platform
        if st.button(f"✅ Create All ({platform_display})", use_container_width=True, key=f"create_applovin_all_{platform}"):
            if not pkg_name:
                st.toast(f"❌ {'Package Name' if platform == 'android' else 'Bundle ID'} is required", icon="🚫")
            else:
                # Collect all slot names and validate
                slots_to_create = []
                has_error = False
                for slot_key, slot_config in slot_configs_applovin.items():
                    slot_name_key = f"applovin_slot_{platform}_{slot_key}_name"
                    slot_name = st.session_state.get(slot_name_key, "")
                    if not slot_name:
                        st.toast(f"❌ {slot_key} Ad Unit Name is required", icon="🚫")
                        has_error = True
                        break
                    slots_to_create.append((slot_key, slot_config, slot_name))

                if not has_error:
                    network_manager = get_network_manager()
                    success_count = 0
                    for slot_key, slot_config, slot_name in slots_to_create:
                        with st.spinner(f"Creating {slot_key} ad unit for {platform_display}..."):
                            try:
                                payload = {
                                    "name": slot_name,
                                    "platform": platform,
                                    "package_name": pkg_name,
                                    "ad_format": slot_config["ad_format"]
                                }
                                response = network_manager.create_unit("applovin", payload)

                                if not response:
                                    st.error(f"❌ {slot_key}: No response from API")
                                    SessionManager.log_error("applovin", f"{slot_key}: No response from API")
                                else:
                                    result = handle_api_response(response)
                                    if result is not None:
                                        ad_unit_id = result.get("id", result.get("adUnitId"))

                                        # Banner refresh settings (BN only)
                                        if slot_key == "BN" and ad_unit_id:
                                            banner_refresh = st.session_state.get(f"applovin_banner_refresh_{platform}_BN")
                                            if banner_refresh is not None:
                                                from utils.applovin_manager import update_banner_refresh_settings, get_applovin_api_key
                                                api_key = get_applovin_api_key()
                                                if api_key:
                                                    success, refresh_result = update_banner_refresh_settings(api_key, ad_unit_id, banner_refresh)
                                                    if success:
                                                        st.success(f"✅ Banner refresh interval: {banner_refresh}초 설정 완료")
                                                    else:
                                                        st.warning(f"⚠️ Banner refresh 설정 실패: {refresh_result}")

                                        unit_data = {
                                            "slotCode": ad_unit_id or "N/A",
                                            "name": slot_name,
                                            "appCode": pkg_name,
                                            "slotType": slot_config["ad_format"],
                                            "adType": slot_config["ad_format"],
                                            "auctionType": "N/A"
                                        }
                                        SessionManager.add_created_unit("applovin", unit_data)
                                        st.success(f"✅ {slot_key} ad unit ({platform_display}) created successfully!")
                                        success_count += 1
                            except Exception as e:
                                st.error(f"❌ Error creating {slot_key} ad unit ({platform_display}): {str(e)}")
                                SessionManager.log_error("applovin", str(e))

                    if success_count > 0:
                        st.rerun()

        st.divider()
