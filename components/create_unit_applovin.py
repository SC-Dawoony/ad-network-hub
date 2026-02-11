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

    # Common input fields (outside form, shared by all ad formats)
    st.markdown("**Ad Unit Information**")

    # Pre-fill from store info if available (only when widget is empty/unset)
    store_android = st.session_state.get("store_info_android")
    store_ios = st.session_state.get("store_info_ios")

    # Show per-platform store info
    if store_android or store_ios:
        info_cols = st.columns(2)
        with info_cols[0]:
            st.markdown("**🤖 Android**")
            if store_android:
                st.write(f"App Name: **{store_android.get('name', '')}**")
                st.write(f"Package Name: `{store_android.get('package_name', '')}`")
            else:
                st.caption("앱 정보 없음")
        with info_cols[1]:
            st.markdown("**🍎 iOS**")
            if store_ios:
                st.write(f"App Name: **{store_ios.get('name', '')}**")
                st.write(f"Bundle ID: `{store_ios.get('bundle_id', '')}`")
            else:
                st.caption("앱 정보 없음")
    else:
        st.warning("⚠️ 위에서 '앱 정보 조회'를 먼저 실행해주세요.")

    default_app_name = ""
    default_package_name = ""
    if store_android:
        default_app_name = store_android.get("name", "")
        default_package_name = store_android.get("package_name", "")
    elif store_ios:
        default_app_name = store_ios.get("name", "")
        default_package_name = store_ios.get("bundle_id", "")

    # Extract name before colon (e.g., "My Supermarket: Shop Rush" → "My Supermarket")
    if default_app_name and ":" in default_app_name:
        default_app_name = default_app_name.split(":")[0].strip()

    if default_app_name and not st.session_state.get("applovin_app_name"):
        st.session_state["applovin_app_name"] = default_app_name
    if default_package_name and not st.session_state.get("applovin_package_name"):
        st.session_state["applovin_package_name"] = default_package_name

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
        help="Package name (Android) or Bundle ID (iOS). Ad Units will be created for both Android and iOS.",
        key="applovin_package_name"
    )

    st.info("💡 **Note:** Ad Units will be created for both Android and iOS platforms automatically.")

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
        ("android", "Android", "AOS"),
        ("ios", "iOS", "iOS")
    ]

    for platform, platform_display, os_str in platforms:
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
                    elif package_name:
                        # Fallback to package name format if app_name is not provided
                        pkg_last_part = package_name.split(".")[-1] if "." in package_name else package_name
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
                    settings_html += f'<li>Package Name: {package_name if package_name else "Not set"}</li>'
                    settings_html += '</ul></div>'
                    st.markdown(settings_html, unsafe_allow_html=True)

                    # Create button for AppLovin
                    if st.button(f"✅ Create {slot_key} ({platform_display})", use_container_width=True, key=f"create_applovin_{platform}_{slot_key}"):
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
                                                "appCode": package_name,
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
