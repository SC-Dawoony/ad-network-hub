"""Vungle Deactivate Placements Component

This component handles the Vungle-specific workflow of deactivating existing placements
after creating a Vungle app, before creating new placements.
"""
import streamlit as st
import logging
from utils.network_manager import get_network_manager, handle_api_response

logger = logging.getLogger(__name__)


def render_vungle_deactivate_placements(current_network: str):
    """Render Vungle Deactivate Placements section
    
    Args:
        current_network: Current network name (should be "vungle")
    """
    if current_network != "vungle":
        return
    
    st.divider()
    st.subheader("📦 Deactivate Existing Placements (Vungle)")
    st.info("💡 Vungle 앱 생성 시 기본 Placement가 자동으로 생성됩니다. Create Unit 전에 기존 Placements를 inactive로 변경해야 합니다.")
    
    # Get Vungle Create App response from cache
    vungle_response_key = f"{current_network}_last_app_response"
    vungle_response = st.session_state.get(vungle_response_key)
    
    vungle_app_id = None
    default_placement = None
    
    if vungle_response and vungle_response.get("status") == 0:
        result_data = vungle_response.get("result", {})
        vungle_app_id = result_data.get("vungleAppId")
        default_placement = result_data.get("defaultPlacement")
    
    # Manual input option
    with st.expander("📝 Vungle App ID 입력 (수동)", expanded=not vungle_app_id):
        manual_app_id = st.text_input(
            "Vungle App ID",
            value=vungle_app_id or "",
            placeholder="5e56099c57d130000137da68",
            help="Vungle App ID를 입력하세요 (Create App response의 result.vungleAppId)",
            key="vungle_manual_app_id"
        )
        if manual_app_id:
            vungle_app_id = manual_app_id.strip()
        
        manual_default_placement = st.text_input(
            "Default Placement ID (Optional)",
            value=default_placement or "",
            placeholder="5e56099c57d130000137da6a",
            help="Default Placement ID (Create App response의 result.defaultPlacement)",
            key="vungle_manual_default_placement"
        )
        if manual_default_placement:
            default_placement = manual_default_placement.strip()
    
    if vungle_app_id:
        # Fetch existing placements for this app
        try:
            with st.spinner("🔄 Placements 정보를 조회하는 중..."):
                network_manager = get_network_manager()
                placements = network_manager._get_vungle_placements()
                
                # Filter placements for this app
                app_placements = [
                    p for p in placements 
                    if p.get("application") == vungle_app_id or p.get("applicationId") == vungle_app_id
                ]
                
                # Filter out already inactive placements
                active_placements = [
                    p for p in app_placements 
                    if p.get("status", "").lower() != "inactive"
                ]
                
                if active_placements:
                    st.write(f"**Found {len(active_placements)} active placement(s) for this app:**")
                    
                    # Display placements
                    for placement in active_placements:
                        placement_id = placement.get("id")
                        placement_name = placement.get("name", "N/A")
                        placement_type = placement.get("type", "N/A")
                        placement_status = placement.get("status", "N/A")
                        
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.write(f"**{placement_name}**")
                        with col2:
                            st.write(f"Type: {placement_type}")
                        with col3:
                            st.write(f"Status: {placement_status}")
                    
                    # Deactivate button
                    if st.button("📦 Deactivate All Active Placements", key="deactivate_vungle_placements", type="primary"):
                        with st.spinner("Deactivating placements..."):
                            success = network_manager._deactivate_vungle_placements(vungle_app_id, default_placement)
                            
                            if success:
                                st.success(f"✅ {len(active_placements)} placement(s) deactivated successfully!")
                                st.balloons()
                                # Refresh to show updated status
                                st.rerun()
                            else:
                                st.warning("⚠️ Some placements may not have been deactivated. Please check the logs above.")
                elif app_placements:
                    st.info("ℹ️ All placements for this app are already inactive.")
                else:
                    st.info("ℹ️ No placements found for this app.")
        except Exception as e:
            st.error(f"❌ Placements 조회 중 오류 발생: {str(e)}")
            logger.exception(f"[Vungle] Error fetching placements: {str(e)}")
    else:
        st.info("💡 Vungle App ID를 입력하거나 Create App을 먼저 실행해주세요.")

