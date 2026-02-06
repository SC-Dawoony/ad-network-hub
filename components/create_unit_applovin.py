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
    
    # Create All Ad Units button
    # if st.button("✨ Create All 6 Ad Units (Android + iOS: RV, IS, BN)", use_container_width=True, type="primary", key="create_all_applovin_units"):
    #     if not package_name:
    #         st.error("❌ Package Name is required")
    #     else:
    #         # Prepare all ad units to create
    #         ad_units_to_create = []
    #         platforms = [
    #             ("android", "Android", "AOS"),
    #             ("ios", "iOS", "iOS")
    #         ]
    #         slot_configs_applovin = {
    #             "RV": {"name": "Rewarded Video", "ad_format": "REWARD"},
    #             "IS": {"name": "Interstitial", "ad_format": "INTER"},
    #             "BN": {"name": "Banner", "ad_format": "BANNER"}
    #         }
            
    #         for platform, platform_display, os_str in platforms:
    #             for slot_key, slot_config in slot_configs_applovin.items():
    #                 slot_name_key = f"applovin_slot_{platform}_{slot_key}_name"
    #                 slot_name = st.session_state.get(slot_name_key, "")
                    
    #                 if not slot_name:
    #                     # Generate name if not set
    #                     if app_name:
    #                         adformat_map = {"RV": "RV", "IS": "IS", "BN": "BN"}
    #                         adformat = adformat_map.get(slot_key, slot_key)
    #                         slot_name = f"{app_name} {os_str} {adformat}"
    #                     elif package_name:
    #                         pkg_last_part = package_name.split(".")[-1] if "." in package_name else package_name
    #                         os_lower = "aos" if platform == "android" else "ios"
    #                         adtype_map = {"RV": "rv", "IS": "is", "BN": "bn"}
    #                         adtype = adtype_map.get(slot_key, slot_key.lower())
    #                         slot_name = f"{pkg_last_part}_{os_lower}_applovin_{adtype}_bidding"
    #                     else:
    #                         slot_name = f"{slot_key.lower()}_{platform}_ad_unit"
                    
    #                 ad_units_to_create.append({
    #                     "platform": platform,
    #                     "platform_display": platform_display,
    #                     "slot_key": slot_key,
    #                     "slot_name": slot_name,
    #                     "slot_config": slot_config
    #                 })
            
    #         # Create all ad units sequentially
    #         import time
    #         results = []
    #         total = len(ad_units_to_create)
            
    #         # Create progress container
    #         progress_container = st.container()
    #         with progress_container:
    #             st.info(f"🚀 Creating {total} Ad Units...")
    #             progress_bar = st.progress(0)
    #             status_text = st.empty()
                
    #             network_manager = get_network_manager()
                
    #             for idx, unit_info in enumerate(ad_units_to_create, 1):
    #                 platform = unit_info["platform"]
    #                 platform_display = unit_info["platform_display"]
    #                 slot_key = unit_info["slot_key"]
    #                 slot_name = unit_info["slot_name"]
    #                 slot_config = unit_info["slot_config"]
                    
    #                 # Update progress
    #                 progress = idx / total
    #                 progress_bar.progress(progress)
    #                 status_text.text(f"📝 [{idx}/{total}] Creating {slot_key} ({platform_display}): {slot_name}")
                    
    #                 # Build payload
    #                 payload = {
    #                     "name": slot_name,
    #                     "platform": platform,
    #                     "package_name": package_name,
    #                     "ad_format": slot_config["ad_format"]
    #                 }
                    
    #                 # Make API call
    #                 try:
    #                     response = network_manager.create_unit("applovin", payload)
                        
    #                     if not response:
    #                         results.append({
    #                             "platform": platform_display,
    #                             "slot_key": slot_key,
    #                             "slot_name": slot_name,
    #                             "status": "error",
    #                             "error": "No response from API"
    #                         })
    #                     else:
    #                         result = handle_api_response(response)
                            
    #                         if result is not None:
    #                             unit_data = {
    #                                 "slotCode": result.get("id", result.get("adUnitId", "N/A")),
    #                                 "name": slot_name,
    #                                 "appCode": package_name,
    #                                 "slotType": slot_config["ad_format"],
    #                                 "adType": slot_config["ad_format"],
    #                                 "auctionType": "N/A"
    #                             }
    #                             SessionManager.add_created_unit("applovin", unit_data)
                                
    #                             results.append({
    #                                 "platform": platform_display,
    #                                 "slot_key": slot_key,
    #                                 "slot_name": slot_name,
    #                                 "status": "success",
    #                                 "unit_id": result.get("id", result.get("adUnitId", "N/A"))
    #                             })
    #                         else:
    #                             # Extract error message from response if available
    #                             error_msg = "Unknown error"
    #                             if isinstance(response, dict):
    #                                 error_msg = response.get("msg", response.get("error", "Unknown error"))
                                
    #                             results.append({
    #                                 "platform": platform_display,
    #                                 "slot_key": slot_key,
    #                                 "slot_name": slot_name,
    #                                 "status": "error",
    #                                 "error": error_msg
    #                             })
    #                 except Exception as e:
    #                     results.append({
    #                         "platform": platform_display,
    #                         "slot_key": slot_key,
    #                         "slot_name": slot_name,
    #                         "status": "error",
    #                         "error": str(e)
    #                     })
    #                     SessionManager.log_error("applovin", str(e))
                    
    #                 # Add small delay to avoid rate limiting (0.5 seconds between requests)
    #                 if idx < total:
    #                     time.sleep(0.5)
                
    #             # Clear progress indicators
    #             progress_bar.empty()
    #             status_text.empty()
            
    #         # Display results summary
    #         st.divider()
    #         st.subheader("📋 Creation Results")
            
    #         success_count = sum(1 for r in results if r["status"] == "success")
    #         error_count = sum(1 for r in results if r["status"] == "error")
            
    #         if success_count > 0:
    #             st.success(f"✅ {success_count} Ad Units created successfully!")
    #         if error_count > 0:
    #             st.error(f"❌ {error_count} Ad Units failed")
            
    #         # Display detailed results
    #         with st.expander("📊 Detailed Results", expanded=True):
    #             for result in results:
    #                 if result["status"] == "success":
    #                     st.success(f"✅ {result['slot_key']} ({result['platform']}): {result['slot_name']} [ID: {result.get('unit_id', 'N/A')}]")
    #                 else:
    #                     st.error(f"❌ {result['slot_key']} ({result['platform']}): {result['slot_name']} - {result.get('error', 'Unknown error')}")
            
    #         # Show balloons if all succeeded
    #         if error_count == 0 and success_count == total:
    #             st.balloons()
            
    #         st.rerun()
    
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
                    
                    # Update slot name if app_name or package_name changes
                    if app_name:
                        # Priority: app_name format
                        adformat_map = {"RV": "RV", "IS": "IS", "BN": "BN"}
                        adformat = adformat_map.get(slot_key, slot_key)
                        default_name = f"{app_name} {os_str} {adformat}"
                        st.session_state[slot_name_key] = default_name
                    elif package_name:
                        # Fallback to package name format
                        pkg_last_part = package_name.split(".")[-1] if "." in package_name else package_name
                        os_lower = "aos" if platform == "android" else "ios"
                        adtype_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                        adtype = adtype_map.get(slot_key, slot_key.lower())
                        default_name = f"{pkg_last_part}_{os_lower}_applovin_{adtype}_bidding"
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

