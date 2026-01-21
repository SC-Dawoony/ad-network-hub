"""Unity Create Unit UI component"""
import streamlit as st
import logging
import json
from utils.session_manager import SessionManager
from utils.network_manager import get_network_manager, handle_api_response, _mask_sensitive_data

logger = logging.getLogger(__name__)


def render_unity_create_unit_ui(current_network: str):
    """Render the Unity-specific Create Unit UI
    
    Args:
        current_network: Current network identifier (should be "unity")
    """
    # Get Project ID from Create App response or manual input
    unity_response_key = f"{current_network}_last_app_response"
    unity_response = st.session_state.get(unity_response_key)
    
    project_id = None
    if unity_response and unity_response.get("status") == 0:
        result_data = unity_response.get("result", {})
        project_id = result_data.get("id")
    
    # Manual input option
    with st.expander("📝 Project ID 입력", expanded=not project_id):
        manual_project_id = st.text_input(
            "Project ID",
            value=project_id or "",
            placeholder="de39f42a-2319-4f34-a1b4-cd555f457192",
            help="Unity 프로젝트 ID를 입력하세요 (Create App response의 result.id)",
            key="unity_create_unit_project_id"
        )
        if manual_project_id:
            project_id = manual_project_id
    
    if not project_id:
        st.info("💡 Project ID를 입력하거나 Create App을 먼저 실행해주세요.")
        return
    
    # Display persisted create unit responses if exist
    for store_name in ["apple", "google"]:
        response_key = f"unity_create_unit_{store_name}_response"
        if response_key in st.session_state:
            last_response = st.session_state[response_key]
            store_display = "Apple (iOS)" if store_name == "apple" else "Google (Android)"
            with st.expander(f"📥 Last Create Unit Response - {store_display}", expanded=False):
                st.json(_mask_sensitive_data(last_response))
                if last_response.get("status") == 0:
                    result = last_response.get("result", {})
                    if result:
                        st.subheader("📝 Result Data")
                        st.json(_mask_sensitive_data(result))
            if st.button(f"🗑️ Clear {store_display} Response", key=f"clear_unity_unit_{store_name}_response"):
                del st.session_state[response_key]
                st.rerun()
    
    if any(f"unity_create_unit_{store}_response" in st.session_state for store in ["apple", "google"]):
        st.divider()
    
    # Unity Create Unit: Store별로 한 번에 3개 Ad Units 생성
    stores_to_create = ["apple", "google"]
    
    # Get project info to extract storeId for placement name generation (for addPlacements)
    project_info_for_units = None
    if project_id:
        try:
            network_manager = get_network_manager()
            all_projects = network_manager.get_apps("unity")
            for proj in all_projects:
                if proj.get("id") == project_id or str(proj.get("id")) == str(project_id):
                    project_info_for_units = proj
                    break
        except Exception as e:
            logger.warning(f"[Unity] Failed to fetch project info for units: {str(e)}")
    
    # Helper function to generate placement name (same as Create Placements)
    def _generate_unity_placement_name_for_unit(store_id: str, os: str, ad_format: str) -> str:
        """Generate Unity placement name for addPlacements in Create Unit
        
        Args:
            store_id: Store ID (e.g., "com.example.app")
            os: "ios" or "aos"
            ad_format: "rv", "is", or "bn"
        
        Returns:
            Placement name (e.g., "app aos unity rv bidding") - with spaces
        """
        # Check if app_match_name is set in session - use it instead of store_id
        app_match_name = SessionManager.get_app_match_name()
        if app_match_name and app_match_name.strip():
            last_part = app_match_name.strip().lower()
        else:
            # Get last part after last "."
            if "." in store_id:
                last_part = store_id.split(".")[-1]
            else:
                last_part = store_id
            last_part = last_part.lower()
        
        # Format: {last_part} {os} unity {ad_format} bidding (with spaces, all lowercase)
        placement_name = f"{last_part} {os} unity {ad_format} bidding"
        return placement_name
    
    # Unity ad unit configurations
    unity_slot_configs = {
        "RV": {
            "name": "Rewarded Video",
            "adFormat": "rewarded"
        },
        "IS": {
            "name": "Interstitial",
            "adFormat": "interstitial"
        },
        "BN": {
            "name": "Banner",
            "adFormat": "banner"
        }
    }
    
    # Create 2 columns for Apple and Google
    col1, col2 = st.columns(2)
    
    for idx, store_name in enumerate(stores_to_create):
        with [col1, col2][idx]:
            store_display = "Apple (iOS)" if store_name == "apple" else "Google (Android)"
            os_str = "ios" if store_name == "apple" else "aos"
            st.markdown(f"### {store_display}")
            
            # Get storeId from project info for placement name generation
            store_id_for_units = None
            if project_info_for_units:
                stores_data = project_info_for_units.get("stores") or project_info_for_units.get("stores_parsed")
                if isinstance(stores_data, str):
                    try:
                        stores_data = json.loads(stores_data)
                    except:
                        pass
                
                if isinstance(stores_data, dict):
                    # Always use Google's storeId for both Apple and Google
                    google_store_info = stores_data.get("google", {})
                    store_id_for_units = google_store_info.get("storeId", "")
            
            # Display ad units that will be created
            st.markdown("**Ad Units to create:**")
            ad_unit_names = []
            for slot_key, slot_config in unity_slot_configs.items():
                unit_name = f"AOS {slot_key} Bidding" if store_name == "google" else f"iOS {slot_key} Bidding"
                ad_unit_names.append(unit_name)
                
                # Map adFormat to short format for placement name
                ad_format_map = {
                    "rewarded": "rv",
                    "interstitial": "is",
                    "banner": "bn"
                }
                ad_format_lower = ad_format_map.get(slot_config["adFormat"], slot_config["adFormat"][:2])
                
                # Generate placement name to display
                placement_name_display = ""
                if store_id_for_units:
                    placement_name_display = _generate_unity_placement_name_for_unit(store_id_for_units, os_str, ad_format_lower)
                else:
                    placement_name_display = f"unknown {os_str} unity {ad_format_lower} bidding"
                
                st.markdown(f"- **{slot_key}**: {unit_name} ({slot_config['adFormat']})")
                st.markdown(f"  - **Placement Name**: `{placement_name_display}`")
                st.markdown(f"  - **Placement Type**: `bidding`")
            
            # Create All 3 Ad Units button
            if st.button(f"✅ Create All 3 Ad Units", use_container_width=True, type="primary", key=f"create_unity_all_{store_name}"):
                # Build payload for all 3 ad units
                payload = []
                for slot_key, slot_config in unity_slot_configs.items():
                    unit_name = f"AOS {slot_key} Bidding" if store_name == "google" else f"iOS {slot_key} Bidding"
                    
                    # Map adFormat to short format for placement name
                    ad_format_map = {
                        "rewarded": "rv",
                        "interstitial": "is",
                        "banner": "bn"
                    }
                    ad_format_lower = ad_format_map.get(slot_config["adFormat"], slot_config["adFormat"][:2])
                    
                    # Generate placement name (same format as Create Placements)
                    if store_id_for_units:
                        placement_name = _generate_unity_placement_name_for_unit(store_id_for_units, os_str, ad_format_lower)
                    else:
                        placement_name = f"unknown {os_str} unity {ad_format_lower} bidding"
                    
                    # Build ad unit payload with addPlacements
                    ad_unit_payload = {
                        "name": unit_name,
                        "adFormat": slot_config["adFormat"],
                        "addPlacements": [{
                            "name": placement_name,
                            "placementType": "bidding"
                        }]
                    }
                    payload.append(ad_unit_payload)
                
                # Make API call
                with st.spinner(f"Creating 3 ad units for {store_display}..."):
                    try:
                        network_manager = get_network_manager()
                        response = network_manager._create_unity_ad_units(project_id, store_name, payload)
                        
                        # Store response in session_state for persistence
                        response_key = f"unity_create_unit_{store_name}_response"
                        st.session_state[response_key] = response
                        
                        result = handle_api_response(response)
                        
                        if result and response.get("status") == 0:
                            # Check if msg contains "Success" (case-insensitive)
                            msg = response.get("msg", "").lower()
                            if "success" in msg:
                                st.success(f"✅ Ad Units created successfully: {', '.join(ad_unit_names)}")
                                st.balloons()
                            else:
                                st.success(f"✅ Ad Units created: {', '.join(ad_unit_names)}")
                            st.rerun()
                        # handle_api_response already displays error messages
                    except Exception as e:
                        st.error(f"❌ Error creating ad units: {str(e)}")
                        SessionManager.log_error(current_network, str(e))

