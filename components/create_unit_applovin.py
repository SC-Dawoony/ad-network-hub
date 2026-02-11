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

    # Ad Unit Information - per platform from store info
    st.markdown("**Ad Unit Information**")

    store_android = st.session_state.get("store_info_android")
    store_ios = st.session_state.get("store_info_ios")

    android_app_name = store_android.get("name", "") if store_android else ""
    android_package_name = store_android.get("package_name", "") if store_android else ""
    ios_app_name = store_ios.get("name", "") if store_ios else ""
    ios_bundle_id = store_ios.get("bundle_id", "") if store_ios else ""

    if store_android or store_ios:
        info_cols = st.columns(2)
        with info_cols[0]:
            st.markdown("**🤖 Android**")
            if store_android:
                st.write(f"App Name: **{android_app_name}**")
                st.write(f"Package Name: `{android_package_name}`")
            else:
                st.caption("앱 정보 없음")
        with info_cols[1]:
            st.markdown("**🍎 iOS**")
            if store_ios:
                st.write(f"App Name: **{ios_app_name}**")
                st.write(f"Bundle ID: `{ios_bundle_id}`")
            else:
                st.caption("앱 정보 없음")
    else:
        st.warning("⚠️ 위에서 '앱 정보 조회'를 먼저 실행해주세요.")

    # Get app_match_name for ad unit name generation
    app_match_name = SessionManager.get_app_match_name()
    if app_match_name:
        st.info(f"💡 Ad Unit Name 생성에 App Match Name: **{app_match_name}** 이 사용됩니다.")

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

    # Create sections for Android and iOS
    platforms = [
        ("android", "Android", android_package_name),
        ("ios", "iOS", ios_bundle_id)
    ]

    for platform, platform_display, pkg_name in platforms:
        st.subheader(f"📱 {platform_display}")

        if not pkg_name:
            st.caption(f"{platform_display} 앱 정보가 없어 Ad Unit을 생성할 수 없습니다.")
            st.divider()
            continue

        # Create 3 columns for RV, IS, BN
        col1, col2, col3 = st.columns(3)

        for idx, (slot_key, slot_config) in enumerate(slot_configs_applovin.items()):
            with [col1, col2, col3][idx]:
                with st.container():
                    st.markdown(f"### 🎯 {slot_key} ({slot_config['name']})")

                    # Slot name - generate from app_match_name
                    slot_name_key = f"applovin_slot_{platform}_{slot_key}_name"

                    # Generate default name from app_match_name
                    if app_match_name:
                        os_lower = "aos" if platform == "android" else "ios"
                        adtype_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                        adtype = adtype_map.get(slot_key, slot_key.lower())
                        default_name = f"{app_match_name}_{os_lower}_applovin_{adtype}_bidding"
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

                    # Create button for AppLovin
                    if st.button(f"✅ Create {slot_key} ({platform_display})", use_container_width=True, key=f"create_applovin_{platform}_{slot_key}"):
                        # Validate inputs
                        if not slot_name:
                            st.toast("❌ Ad Unit Name is required", icon="🚫")
                        else:
                            # Build payload
                            payload = {
                                "name": slot_name,
                                "platform": platform,
                                "package_name": pkg_name,
                                "ad_format": slot_config["ad_format"]
                            }

                            # Make API call
                            with st.spinner(f"Creating {slot_key} ad unit for {platform_display}..."):
                                try:
                                    network_manager = get_network_manager()
                                    response = network_manager.create_unit("applovin", payload)

                                    if not response:
                                        st.error("❌ No response from API")
                                        SessionManager.log_error("applovin", "No response from API")
                                    else:
                                        result = handle_api_response(response)

                                        if result is not None:
                                            unit_data = {
                                                "slotCode": result.get("id", result.get("adUnitId", "N/A")),
                                                "name": slot_name,
                                                "appCode": pkg_name,
                                                "slotType": slot_config["ad_format"],
                                                "adType": slot_config["ad_format"],
                                                "auctionType": "N/A"
                                            }
                                            SessionManager.add_created_unit("applovin", unit_data)

                                            st.success(f"✅ {slot_key} ad unit ({platform_display}) created successfully!")
                                            st.rerun()
                                        else:
                                            # handle_api_response already displayed error
                                            pass
                                except Exception as e:
                                    st.error(f"❌ Error creating {slot_key} ad unit ({platform_display}): {str(e)}")
                                    SessionManager.log_error("applovin", str(e))

        st.divider()
