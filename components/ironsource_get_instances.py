"""IronSource GET Instances Component

This component handles the IronSource-specific workflow of querying instances
after creating ad units.
"""
import streamlit as st
import pandas as pd
from utils.network_manager import get_network_manager
from utils.session_manager import SessionManager


def render_ironsource_get_instances(current_network: str):
    """Render IronSource GET Instances section
    
    Args:
        current_network: Current network name (should be "ironsource")
    """
    if current_network != "ironsource":
        return
    
    st.divider()
    st.subheader("📡 GET Instance")
    st.info("💡 App Key를 입력하여 Instance를 조회할 수 있습니다.")
    
    # Get IronSource Create App response from cache
    ironsource_response_key = f"{current_network}_last_app_response"
    ironsource_response = st.session_state.get(ironsource_response_key)
    
    android_app_key = None
    ios_app_key = None
    
    if ironsource_response and ironsource_response.get("status") == 0:
        result_data = ironsource_response.get("result", {})
        if isinstance(result_data, list):
            for res in result_data:
                platform = res.get("platform", "")
                if platform == "Android":
                    android_app_key = res.get("appKey")
                elif platform == "iOS":
                    ios_app_key = res.get("appKey")
        else:
            platform = result_data.get("platform", "")
            if platform == "Android":
                android_app_key = result_data.get("appKey")
            elif platform == "iOS":
                ios_app_key = result_data.get("appKey")
    
    # Also check session state for app info
    last_app_info = SessionManager.get_last_created_app_info(current_network)
    if last_app_info:
        android_app_key = android_app_key or last_app_info.get("appKey")
        ios_app_key = ios_app_key or last_app_info.get("appKeyIOS")
    
    network_manager = get_network_manager()
    
    # App Key input
    col1, col2 = st.columns(2)
    with col1:
        android_app_key_input = st.text_input(
            "Android App Key",
            value=android_app_key or "",
            placeholder="Enter Android App Key",
            help="Enter the Android App Key to query instances",
            key="ironsource_android_app_key_input"
        )
    
    with col2:
        ios_app_key_input = st.text_input(
            "iOS App Key",
            value=ios_app_key or "",
            placeholder="Enter iOS App Key",
            help="Enter the iOS App Key to query instances",
            key="ironsource_ios_app_key_input"
        )
    
    # GET Instance buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 GET Android Instances", use_container_width=True, type="primary", key="get_ironsource_android_instances"):
            if not android_app_key_input or not android_app_key_input.strip():
                st.error("❌ Please enter an Android App Key")
            else:
                with st.spinner("📡 Fetching Android instances..."):
                    try:
                        instances_response = network_manager._get_ironsource_instances(android_app_key_input.strip())
                        
                        if instances_response.get("status") == 0:
                            instances = instances_response.get("result", [])
                            
                            if instances:
                                st.success(f"✅ Found {len(instances)} Android instances")
                                
                                # Group instances by ad format
                                instances_by_format = {}
                                for inst in instances:
                                    ad_format = inst.get("adFormat", "N/A")
                                    if ad_format not in instances_by_format:
                                        instances_by_format[ad_format] = []
                                    instances_by_format[ad_format].append(inst)
                                
                                # Display instances in a table-like format
                                for ad_format, format_instances in sorted(instances_by_format.items()):
                                    st.markdown(f"### {ad_format.title()}")
                                    
                                    # Create a table for instances
                                    instance_data = []
                                    for inst in format_instances:
                                        instance_data.append({
                                            "Instance ID": inst.get("instanceId", "N/A"),
                                            "Network": inst.get("networkName", "N/A"),
                                            "Instance Name": inst.get("instanceName", "") or "N/A",
                                            "Is Bidder": "✅" if inst.get("isBidder", False) else "❌",
                                            "Is Live": "✅" if inst.get("isLive", False) else "❌"
                                        })
                                    
                                    if instance_data:
                                        df = pd.DataFrame(instance_data)
                                        st.dataframe(df, use_container_width=True, hide_index=True)
                                        st.divider()
                            else:
                                st.info("ℹ️ No instances found for this Android App Key")
                        else:
                            error_code = instances_response.get("code", "UNKNOWN")
                            error_msg = instances_response.get("msg") or instances_response.get("message") or instances_response.get("error") or "Unknown error"
                            st.error(f"❌ Error [{error_code}]: {error_msg}")
                            with st.expander("🔍 Error Details", expanded=False):
                                st.json(instances_response)
                    except Exception as e:
                        st.error(f"❌ Error fetching Android instances: {str(e)}")
                        import traceback
                        with st.expander("🔍 Exception Details", expanded=False):
                            st.code(traceback.format_exc())
    
    with col2:
        if st.button("🔍 GET iOS Instances", use_container_width=True, type="primary", key="get_ironsource_ios_instances"):
            if not ios_app_key_input or not ios_app_key_input.strip():
                st.error("❌ Please enter an iOS App Key")
            else:
                with st.spinner("📡 Fetching iOS instances..."):
                    try:
                        instances_response = network_manager._get_ironsource_instances(ios_app_key_input.strip())
                        
                        if instances_response.get("status") == 0:
                            instances = instances_response.get("result", [])
                            
                            if instances:
                                st.success(f"✅ Found {len(instances)} iOS instances")
                                
                                # Group instances by ad format
                                instances_by_format = {}
                                for inst in instances:
                                    ad_format = inst.get("adFormat", "N/A")
                                    if ad_format not in instances_by_format:
                                        instances_by_format[ad_format] = []
                                    instances_by_format[ad_format].append(inst)
                                
                                # Display instances in a table-like format
                                for ad_format, format_instances in sorted(instances_by_format.items()):
                                    st.markdown(f"### {ad_format.title()}")
                                    
                                    # Create a table for instances
                                    instance_data = []
                                    for inst in format_instances:
                                        instance_data.append({
                                            "Instance ID": inst.get("instanceId", "N/A"),
                                            "Network": inst.get("networkName", "N/A"),
                                            "Instance Name": inst.get("instanceName", "") or "N/A",
                                            "Is Bidder": "✅" if inst.get("isBidder", False) else "❌",
                                            "Is Live": "✅" if inst.get("isLive", False) else "❌"
                                        })
                                    
                                    if instance_data:
                                        df = pd.DataFrame(instance_data)
                                        st.dataframe(df, use_container_width=True, hide_index=True)
                                        st.divider()
                            else:
                                st.info("ℹ️ No instances found for this iOS App Key")
                        else:
                            error_code = instances_response.get("code", "UNKNOWN")
                            error_msg = instances_response.get("msg") or instances_response.get("message") or instances_response.get("error") or "Unknown error"
                            st.error(f"❌ Error [{error_code}]: {error_msg}")
                            with st.expander("🔍 Error Details", expanded=False):
                                st.json(instances_response)
                    except Exception as e:
                        st.error(f"❌ Error fetching iOS instances: {str(e)}")
                        import traceback
                        with st.expander("🔍 Exception Details", expanded=False):
                            st.code(traceback.format_exc())

