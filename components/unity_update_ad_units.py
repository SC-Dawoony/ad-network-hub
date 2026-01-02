"""Unity Update Ad-Units Component

This component handles the Unity-specific workflow of archiving existing ad units
after creating a Unity project, before creating new units.
"""
import streamlit as st
from utils.network_manager import get_network_manager, handle_api_response


def render_unity_update_ad_units(current_network: str):
    """Render Unity Update Ad-Units section
    
    Args:
        current_network: Current network name (should be "unity")
    """
    if current_network != "unity":
        return
    
    st.divider()
    st.subheader("📦 Archive Existing Ad Units (Unity)")
    st.info("💡 Unity 프로젝트 생성 시 기본 Ad Units가 자동으로 생성됩니다. Create Unit 전에 기존 Ad Units를 archive해야 합니다.")
    
    # Get Unity Create App response from cache
    unity_response_key = f"{current_network}_last_app_response"
    unity_response = st.session_state.get(unity_response_key)
    
    project_id = None
    stores_data = {}
    
    if unity_response and unity_response.get("status") == 0:
        result_data = unity_response.get("result", {})
        project_id = result_data.get("id")
        stores_data = result_data.get("stores", {})
    
    # Manual input option
    with st.expander("📝 Project ID 입력 (수동)", expanded=not project_id):
        manual_project_id = st.text_input(
            "Project ID",
            value=project_id or "",
            placeholder="de39f42a-2319-4f34-a1b4-cd555f457192",
            help="Unity 프로젝트 ID를 입력하세요 (Create App response의 result.id)",
            key="unity_manual_project_id"
        )
        if manual_project_id:
            project_id = manual_project_id
    
    if project_id:
        # If stores_data is empty (manual input or Create App response doesn't have stores), fetch ad units from API
        if not stores_data or not any(stores_data.get(platform, {}).get("adUnits") for platform in ["apple", "google"]):
            # Directly fetch ad units from Unity API
            try:
                with st.spinner("🔄 Ad Units 정보를 조회하는 중..."):
                    network_manager = get_network_manager()
                    ad_units_dict = network_manager._get_unity_ad_units(project_id)
                    
                    if ad_units_dict:
                        # ad_units_dict structure: {"apple": {"Interstitial_iOS": {...}, ...}, "google": {...}}
                        # Construct stores structure from ad units
                        for platform in ["apple", "google"]:
                            if platform in ad_units_dict and ad_units_dict[platform]:
                                # Ensure platform entry exists in stores_data
                                if platform not in stores_data:
                                    stores_data[platform] = {}
                                # Set adUnits from API response
                                stores_data[platform]["adUnits"] = ad_units_dict[platform]
                        
                        # Debug: show what we got
                        if st.session_state.get("debug_unity", False):
                            st.json({"ad_units_dict_keys": list(ad_units_dict.keys()) if isinstance(ad_units_dict, dict) else "not a dict"})
                            for platform in ["apple", "google"]:
                                if platform in ad_units_dict:
                                    st.json({f"{platform}_ad_units_count": len(ad_units_dict[platform]) if isinstance(ad_units_dict[platform], dict) else 0})
                    else:
                        st.warning("⚠️ Ad Units를 가져올 수 없습니다. Project ID가 올바른지 확인해주세요.")
            except Exception as e:
                st.error(f"❌ Ad Units 조회 중 오류 발생: {str(e)}")
                import traceback
                st.exception(e)
        
        # Show available stores
        available_stores = []
        # Check if stores have adUnits (required for archiving)
        if stores_data.get("apple"):
            # Check if apple has adUnits or if it's a dict with ad units directly
            apple_ad_units = stores_data.get("apple", {}).get("adUnits")
            if not apple_ad_units and isinstance(stores_data.get("apple"), dict):
                # If adUnits key doesn't exist, check if the dict itself contains ad units (keys like "Interstitial_iOS")
                apple_data = stores_data.get("apple", {})
                # Check if it looks like ad units dict (has keys that look like ad unit IDs)
                if apple_data and any(key.endswith("_iOS") or key.endswith("_Android") for key in apple_data.keys()):
                    # This is already ad units dict, wrap it
                    stores_data["apple"] = {"adUnits": apple_data}
                    apple_ad_units = apple_data
            if apple_ad_units:
                available_stores.append("apple")
        
        if stores_data.get("google"):
            # Check if google has adUnits or if it's a dict with ad units directly
            google_ad_units = stores_data.get("google", {}).get("adUnits")
            if not google_ad_units and isinstance(stores_data.get("google"), dict):
                # If adUnits key doesn't exist, check if the dict itself contains ad units
                google_data = stores_data.get("google", {})
                # Check if it looks like ad units dict (has keys that look like ad unit IDs)
                if google_data and any(key.endswith("_iOS") or key.endswith("_Android") for key in google_data.keys()):
                    # This is already ad units dict, wrap it
                    stores_data["google"] = {"adUnits": google_data}
                    google_ad_units = google_data
            if google_ad_units:
                available_stores.append("google")
        
        if not available_stores:
            # Debug info
            st.warning("⚠️ stores 정보를 찾을 수 없습니다.")
            with st.expander("🔍 디버그 정보", expanded=False):
                st.write("**stores_data 구조:**")
                st.json(stores_data)
                st.write("**stores_data keys:**", list(stores_data.keys()) if stores_data else "empty")
                if stores_data.get("apple"):
                    st.write("**apple keys:**", list(stores_data.get("apple", {}).keys()))
                if stores_data.get("google"):
                    st.write("**google keys:**", list(stores_data.get("google", {}).keys()))
            st.info("💡 Create App을 다시 실행하거나 Unity Dashboard에서 프로젝트 정보를 확인해주세요.")
        else:
            st.write(f"**Available Stores:** {', '.join([s.capitalize() for s in available_stores])}")
            
            # Archive button for each store
            for store_name in available_stores:
                store_display = "Apple (iOS)" if store_name == "apple" else "Google (Android)"
                st.markdown(f"### {store_display}")
                
                # Get ad units from stores data
                store_data = stores_data.get(store_name, {})
                ad_units = store_data.get("adUnits", {})
                
                if ad_units:
                    ad_unit_names = list(ad_units.keys())
                    st.write(f"**Ad Units to archive:** {', '.join(ad_unit_names)}")
                    
                    # Build payload: set archive=true for each ad unit
                    archive_payload = {}
                    for ad_unit_id, ad_unit_data in ad_units.items():
                        archive_payload[ad_unit_id] = {
                            "archive": True
                        }
                    
                    if st.button(f"📦 Archive {store_display} Ad Units", key=f"archive_unity_{store_name}"):
                        with st.spinner(f"Archiving {store_display} ad units..."):
                            network_manager = get_network_manager()
                            response = network_manager._update_unity_ad_units(project_id, store_name, archive_payload)
                            
                            result = handle_api_response(response)
                            
                            if result and response.get("status") == 0:
                                st.success(f"✅ {store_display} Ad Units archived successfully!")
                                st.write(f"**Archived Ad Units:** {', '.join(ad_unit_names)}")
                            else:
                                st.error(f"❌ Failed to archive {store_display} ad units")
                else:
                    st.info(f"ℹ️ {store_display}에 Ad Units가 없습니다.")
    else:
        st.info("💡 Project ID를 입력하거나 Create App을 먼저 실행해주세요.")

