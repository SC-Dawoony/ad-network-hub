"""IronSource Deactivate Ad-Units Component

This component handles the IronSource-specific workflow of deactivating (pausing) existing ad units
after creating an app, before creating new units.
"""
import streamlit as st
from utils.network_manager import get_network_manager, handle_api_response
from utils.ad_network_query import get_ironsource_units


def render_ironsource_deactivate_ad_units(current_network: str):
    """Render IronSource Deactivate Ad-Units section
    
    Args:
        current_network: Current network name (should be "ironsource")
    """
    if current_network != "ironsource":
        return
    
    st.divider()
    st.subheader("⏸️ Deactivate Existing Ad Units (IronSource)")
    st.info("💡 IronSource App 생성 시 기존 Ad Units가 있을 수 있습니다. Create Unit 전에 기존 Ad Units를 deactivate (isPaused: true) 해야 합니다.")
    
    # Get IronSource Create App response from cache
    ironsource_response_key = f"{current_network}_last_app_response"
    ironsource_response = st.session_state.get(ironsource_response_key)
    
    android_app_key = None
    ios_app_key = None
    app_name = None
    
    if ironsource_response and ironsource_response.get("status") == 0:
        # IronSource response structure: {"status": 0, "result": {"appKey": "...", ...}}
        result_data = ironsource_response.get("result", {})
        # For IronSource, we might have multiple results (Android + iOS)
        # Check if it's a list or dict
        if isinstance(result_data, list):
            # Multiple results (Android + iOS)
            for res in result_data:
                platform = res.get("platform", "")
                if platform == "Android":
                    android_app_key = res.get("appKey")
                elif platform == "iOS":
                    ios_app_key = res.get("appKey")
        else:
            # Single result
            platform = result_data.get("platform", "")
            if platform == "Android":
                android_app_key = result_data.get("appKey")
            elif platform == "iOS":
                ios_app_key = result_data.get("appKey")
    
    # Also check session state for app info
    from utils.session_manager import SessionManager
    last_app_info = SessionManager.get_last_created_app_info(current_network)
    if last_app_info:
        android_app_key = android_app_key or last_app_info.get("appKey")
        ios_app_key = ios_app_key or last_app_info.get("appKeyIOS")
        app_name = last_app_info.get("name")
    
    # Manual input option
    with st.expander("📝 App Key 입력 (수동)", expanded=not (android_app_key or ios_app_key)):
        col1, col2 = st.columns(2)
        with col1:
            manual_android_app_key = st.text_input(
                "Android App Key",
                value=android_app_key or "",
                placeholder="Enter Android App Key",
                help="IronSource Android App Key를 입력하세요",
                key="ironsource_manual_android_app_key"
            )
            if manual_android_app_key:
                android_app_key = manual_android_app_key
        
        with col2:
            manual_ios_app_key = st.text_input(
                "iOS App Key",
                value=ios_app_key or "",
                placeholder="Enter iOS App Key",
                help="IronSource iOS App Key를 입력하세요",
                key="ironsource_manual_ios_app_key"
            )
            if manual_ios_app_key:
                ios_app_key = manual_ios_app_key
    
    if not android_app_key and not ios_app_key:
        st.info("💡 App Key를 입력하거나 Create App을 먼저 실행해주세요.")
        return
    
    network_manager = get_network_manager()
    
    # Deactivate Android ad units
    if android_app_key:
        st.markdown("### Android")
        
        if st.button("⏸️ Deactivate All Android Ad Units", key="deactivate_ironsource_android"):
            with st.spinner("⏸️ Deactivating Android ad units..."):
                try:
                    existing_units = get_ironsource_units(android_app_key)
                    
                    if existing_units:
                        deactivate_payloads = []
                        missing_ids = []
                        
                        for idx, unit in enumerate(existing_units):
                            # Try both lowercase and uppercase versions (API returns mediationAdUnitId with uppercase U)
                            # Also check for empty strings
                            mediation_adunit_id = None
                            
                            # Check uppercase U first (correct format from GET API)
                            temp_id = unit.get("mediationAdUnitId")
                            if temp_id is not None and str(temp_id).strip():
                                mediation_adunit_id = str(temp_id).strip()
                            
                            # Fallback to lowercase u
                            if not mediation_adunit_id:
                                temp_id = unit.get("mediationAdunitId")
                                if temp_id is not None and str(temp_id).strip():
                                    mediation_adunit_id = str(temp_id).strip()
                            
                            # Fallback to id
                            if not mediation_adunit_id:
                                temp_id = unit.get("id")
                                if temp_id is not None and str(temp_id).strip():
                                    mediation_adunit_id = str(temp_id).strip()
                            
                            if mediation_adunit_id:
                                # Update API requires mediationAdUnitId (uppercase U) - same as GET API response
                                deactivate_payloads.append({
                                    "mediationAdUnitId": mediation_adunit_id,  # uppercase U
                                    "isPaused": True
                                })
                            else:
                                # Track units without ID
                                unit_name = unit.get("mediationAdUnitName") or unit.get("mediationAdunitName") or f"Unit {idx}"
                                missing_ids.append(unit_name)
                        
                        # Show summary if some units are missing IDs
                        if missing_ids:
                            st.error(f"❌ {len(missing_ids)} ad units are missing valid mediationAdUnitId: {', '.join(missing_ids)}")
                        
                        if deactivate_payloads:
                            deactivate_response = network_manager._update_ironsource_ad_units(android_app_key, deactivate_payloads)
                            
                            # Check if response is successful (status == 0 means success)
                            if deactivate_response.get("status") == 0:
                                st.success(f"✅ Successfully deactivated {len(deactivate_payloads)} Android ad units!")
                                unit_names = [unit.get("mediationAdUnitName", "N/A") for unit in existing_units]
                                st.write(f"**Deactivated Ad Units:** {', '.join(unit_names)}")
                                # Display response if available
                                handle_api_response(deactivate_response)
                            else:
                                st.error("❌ Failed to deactivate Android ad units")
                                handle_api_response(deactivate_response)
                        else:
                            st.warning("⚠️ No ad units found to deactivate")
                    else:
                        st.info("ℹ️ No existing ad units found for Android app")
                except Exception as e:
                    st.error(f"❌ Error deactivating Android ad units: {str(e)}")
                    import traceback
                    st.exception(e)
        
        st.divider()
    
    # Deactivate iOS ad units
    if ios_app_key:
        st.markdown("### iOS")
        
        if st.button("⏸️ Deactivate All iOS Ad Units", key="deactivate_ironsource_ios"):
            with st.spinner("⏸️ Deactivating iOS ad units..."):
                try:
                    existing_units = get_ironsource_units(ios_app_key)
                    
                    if existing_units:
                        deactivate_payloads = []
                        missing_ids = []
                        
                        for idx, unit in enumerate(existing_units):
                            # Try both lowercase and uppercase versions (API returns mediationAdUnitId with uppercase U)
                            # Also check for empty strings
                            mediation_adunit_id = None
                            
                            # Check uppercase U first (correct format from GET API)
                            temp_id = unit.get("mediationAdUnitId")
                            if temp_id is not None and str(temp_id).strip():
                                mediation_adunit_id = str(temp_id).strip()
                            
                            # Fallback to lowercase u
                            if not mediation_adunit_id:
                                temp_id = unit.get("mediationAdunitId")
                                if temp_id is not None and str(temp_id).strip():
                                    mediation_adunit_id = str(temp_id).strip()
                            
                            # Fallback to id
                            if not mediation_adunit_id:
                                temp_id = unit.get("id")
                                if temp_id is not None and str(temp_id).strip():
                                    mediation_adunit_id = str(temp_id).strip()
                            
                            if mediation_adunit_id:
                                # Update API requires mediationAdUnitId (uppercase U) - same as GET API response
                                deactivate_payloads.append({
                                    "mediationAdUnitId": mediation_adunit_id,  # uppercase U
                                    "isPaused": True
                                })
                            else:
                                # Track units without ID
                                unit_name = unit.get("mediationAdUnitName") or unit.get("mediationAdunitName") or f"Unit {idx}"
                                missing_ids.append(unit_name)
                        
                        # Show summary if some units are missing IDs
                        if missing_ids:
                            st.error(f"❌ {len(missing_ids)} ad units are missing valid mediationAdUnitId: {', '.join(missing_ids)}")
                        
                        if deactivate_payloads:
                            deactivate_response = network_manager._update_ironsource_ad_units(ios_app_key, deactivate_payloads)
                            
                            # Check if response is successful (status == 0 means success)
                            if deactivate_response.get("status") == 0:
                                st.success(f"✅ Successfully deactivated {len(deactivate_payloads)} iOS ad units!")
                                unit_names = [unit.get("mediationAdUnitName", "N/A") for unit in existing_units]
                                st.write(f"**Deactivated Ad Units:** {', '.join(unit_names)}")
                                # Display response if available
                                handle_api_response(deactivate_response)
                            else:
                                st.error("❌ Failed to deactivate iOS ad units")
                                handle_api_response(deactivate_response)
                        else:
                            st.warning("⚠️ No ad units found to deactivate")
                    else:
                        st.info("ℹ️ No existing ad units found for iOS app")
                except Exception as e:
                    st.error(f"❌ Error deactivating iOS ad units: {str(e)}")
                    import traceback
                    st.exception(e)

