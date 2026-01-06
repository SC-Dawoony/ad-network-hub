"""AppLovin Ad Unit Settings Update page"""
import streamlit as st
import json
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.applovin_manager import (
    get_applovin_api_key,
    transform_csv_data_to_api_format,
    update_multiple_ad_units,
    get_ad_units,
    get_ad_unit_details
)
from utils.ad_network_query import (
    map_applovin_network_to_actual_network,
    match_applovin_unit_to_network,
    get_network_units,
    find_matching_unit,
    extract_app_identifiers
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Update Ad Unit Settings",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ MAX Ad Unit Settings 업데이트")
st.markdown("AppLovin API를 통해 MAX Ad Unit의 ad_network_settings를 업데이트합니다.")

# Display persisted update result if exists
if "applovin_update_result" in st.session_state:
    last_result = st.session_state["applovin_update_result"]
    st.info("📥 Last Update Result (persisted)")
    with st.expander("📥 Last Update Result", expanded=True):
        st.json(last_result)
        st.subheader("📊 Summary")
        st.write(f"✅ 성공: {len(last_result.get('success', []))}개")
        st.write(f"❌ 실패: {len(last_result.get('fail', []))}개")
        
        # Success list
        if last_result.get("success"):
            st.subheader("✅ 성공한 업데이트")
            success_data = []
            for item in last_result["success"]:
                success_data.append({
                    "Segment ID": item.get("segment_id", "N/A"),
                    "Ad Unit ID": item.get("ad_unit_id", "N/A"),
                    "Status": "Success"
                })
            st.dataframe(success_data, use_container_width=True, hide_index=True)
        
        # Fail list
        if last_result.get("fail"):
            st.subheader("❌ 실패한 업데이트")
            fail_data = []
            for item in last_result["fail"]:
                error_info = item.get("error", {})
                fail_data.append({
                    "Segment ID": item.get("segment_id", "N/A"),
                    "Ad Unit ID": item.get("ad_unit_id", "N/A"),
                    "Status Code": error_info.get("status_code", "N/A"),
                    "Error": json.dumps(error_info.get("data", {}), ensure_ascii=False)
                })
            st.dataframe(fail_data, use_container_width=True, hide_index=True)
        
        # Download result
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_json = json.dumps(last_result, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Download Result (JSON)",
            data=result_json,
            file_name=f"applovin_update_result_{timestamp}.json",
            mime="application/json",
            key="download_persisted_result"
        )
    
    if st.button("🗑️ Clear Result", key="clear_applovin_result"):
        del st.session_state["applovin_update_result"]
        st.rerun()
    st.divider()

# Available ad networks
AD_NETWORKS = [
    "ADMOB_BIDDING",
    "BIGO_BIDDING",
    "CHARTBOOST_BIDDING",
    "FACEBOOK_NETWORK",
    "FYBER_BIDDING",
    "INMOBI_BIDDING",
    "IRONSOURCE_BIDDING",
    "MINTEGRAL_BIDDING",
    "MOLOCO_BIDDING",
    "TIKTOK_BIDDING",
    "UNITY_BIDDING",
    "VUNGLE_BIDDING",
    "YANDEX_BIDDING",
    "PUBMATIC_BIDDING"
]

# Check API Key
api_key = get_applovin_api_key()
if not api_key:
    st.error("❌ APPLOVIN_API_KEY가 환경변수에 설정되지 않았습니다.")
    st.info("`.env` 파일에 `APPLOVIN_API_KEY=your_api_key`를 추가해주세요.")
    st.stop()

st.success(f"✅ AppLovin API Key가 설정되어 있습니다.")

# AppLovin Ad Units 조회 및 검색 섹션
with st.expander("📡 AppLovin Ad Units 조회 및 검색", expanded=False):
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "검색 (name 또는 package_name)",
            key="ad_units_search",
            placeholder="예: Aim Master 또는 com.pungang.shooter",
            help="name 또는 package_name에 포함된 Ad Unit을 검색합니다"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("📡 조회", type="primary", use_container_width=True):
            st.session_state.applovin_ad_units_raw = None
    
    # Load ad units data
    if "applovin_ad_units_raw" not in st.session_state or st.session_state.applovin_ad_units_raw is None:
        if st.button("📡 Get Ad Units", type="secondary", use_container_width=True):
            # Show prominent loading message
            loading_placeholder = st.empty()
            with loading_placeholder.container():
                st.info("⏳ **AppLovin API에서 Ad Units를 조회하는 중입니다...**")
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            try:
                status_text.text("🔄 API 연결 중...")
                progress_bar.progress(20)
                
                success, result = get_ad_units(api_key)
                
                status_text.text("📊 데이터 처리 중...")
                progress_bar.progress(60)
                
                if success:
                    data = result.get("data", {})
                    
                    # Handle different response formats
                    ad_units_list = []
                    if isinstance(data, list):
                        ad_units_list = data
                    elif isinstance(data, dict):
                        ad_units_list = data.get("ad_units", data.get("data", data.get("list", data.get("results", []))))
                    
                    progress_bar.progress(90)
                    status_text.text("✅ 완료!")
                    
                    if ad_units_list:
                        st.session_state.applovin_ad_units_raw = ad_units_list
                        progress_bar.progress(100)
                        loading_placeholder.empty()
                        st.success(f"✅ {len(ad_units_list)}개의 Ad Unit이 조회되었습니다!")
                    else:
                        progress_bar.progress(100)
                        loading_placeholder.empty()
                        st.json(data)
                        st.session_state.applovin_ad_units_raw = []
                else:
                    progress_bar.progress(100)
                    loading_placeholder.empty()
                    st.error("❌ API 호출 실패")
                    error_info = result.get("data", {})
                    st.json(error_info)
                    if "status_code" in result:
                        st.error(f"Status Code: {result['status_code']}")
                    st.session_state.applovin_ad_units_raw = []
            except Exception as e:
                progress_bar.progress(100)
                loading_placeholder.empty()
                st.error(f"❌ 오류 발생: {str(e)}")
                st.session_state.applovin_ad_units_raw = []
    
    # Display filtered and selectable ad units
    if st.session_state.get("applovin_ad_units_raw"):
        ad_units_list = st.session_state.applovin_ad_units_raw
        
        # Apply search filter
        filtered_units = ad_units_list
        if search_query:
            search_lower = search_query.lower()
            filtered_units = [
                unit for unit in ad_units_list
                if search_lower in unit.get("name", "").lower() or search_lower in unit.get("package_name", "").lower()
            ]
        
        if filtered_units:
            st.info(f"📊 검색 결과: {len(filtered_units)}개 (전체: {len(ad_units_list)}개)")
            
            # Sort by platform ASC, ad_format DESC (alphabetical order: REWARD > INTER > BANNER)
            def sort_key(unit):
                platform = unit.get("platform", "").lower()
                ad_format = unit.get("ad_format", "")
                # For platform: android < ios (ASC)
                # For ad_format: alphabetical order DESC (REWARD > INTER > BANNER)
                # Use tuple with negative for DESC: (platform ASC, -ad_format for DESC)
                # But since we can't negate strings, we'll use a two-step sort
                return (platform, ad_format)
            
            # First sort by platform ASC, then by ad_format DESC
            # Sort by platform first
            filtered_units_sorted = sorted(filtered_units, key=lambda x: x.get("platform", "").lower())
            # Then sort by ad_format DESC within each platform group
            from itertools import groupby
            result = []
            for platform_key, group in groupby(filtered_units_sorted, key=lambda x: x.get("platform", "").lower()):
                group_list = list(group)
                # Sort group by ad_format DESC (reverse alphabetical: REWARD > INTER > BANNER)
                group_list_sorted = sorted(group_list, key=lambda x: x.get("ad_format", ""), reverse=True)
                result.extend(group_list_sorted)
            filtered_units_sorted = result
            
            # 선택 상태를 저장할 session state 초기화
            if "ad_unit_selections" not in st.session_state:
                st.session_state.ad_unit_selections = {}
            
            # 자동 선택: 필터된 모든 unit을 기본적으로 선택 (처음 로드되거나 필터가 변경될 때)
            if filtered_units_sorted:
                # 필터된 unit들의 ID 목록
                filtered_unit_ids = {unit.get("id", "") for unit in filtered_units_sorted}
                
                # 필터된 unit 중 선택되지 않은 것이 있으면 자동으로 선택
                for unit in filtered_units_sorted:
                    unit_id = unit.get("id", "")
                    if unit_id not in st.session_state.ad_unit_selections:
                        # 새로 필터된 unit은 자동으로 선택
                        st.session_state.ad_unit_selections[unit_id] = True
                    # 이미 선택 상태가 있으면 그대로 유지
                # Add custom CSS for better table styling with reduced spacing and dark mode support
                st.markdown("""
                <style>
                .ad-unit-table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }
                /* Header - dark background with white text (both modes) */
                .ad-unit-table-header {
                    background-color: #2e2e2e !important;
                    padding: 8px 8px;
                    font-weight: 600;
                    border-bottom: 2px solid #4a4a4a !important;
                    text-align: left;
                    margin: 0;
                    color: #ffffff !important;
                }
                /* Cell - always white text for visibility */
                .ad-unit-table-cell {
                    padding: 4px 8px;
                    vertical-align: middle;
                    margin: 0;
                    line-height: 1.4;
                    color: #ffffff !important;
                }
                .ad-unit-code {
                    font-size: 0.85em;
                    color: #ffffff !important;
                    background-color: transparent;
                }
                /* Light mode: override to dark text */
                [data-theme="light"] .ad-unit-table-cell {
                    color: #1f1f1f !important;
                }
                [data-theme="light"] .ad-unit-code {
                    color: #1f1f1f !important;
                }
                /* Dark mode: ensure white text with all possible selectors */
                [data-theme="dark"] .ad-unit-table-cell,
                .stApp [data-theme="dark"] .ad-unit-table-cell,
                section[data-testid="stAppViewContainer"] [data-theme="dark"] .ad-unit-table-cell,
                div[data-testid="stAppViewContainer"] [data-theme="dark"] .ad-unit-table-cell,
                html[data-theme="dark"] .ad-unit-table-cell,
                body[data-theme="dark"] .ad-unit-table-cell {
                    color: #ffffff !important;
                }
                [data-theme="dark"] .ad-unit-code,
                .stApp [data-theme="dark"] .ad-unit-code,
                section[data-testid="stAppViewContainer"] [data-theme="dark"] .ad-unit-code,
                div[data-testid="stAppViewContainer"] [data-theme="dark"] .ad-unit-code,
                html[data-theme="dark"] .ad-unit-code,
                body[data-theme="dark"] .ad-unit-code {
                    color: #ffffff !important;
                    background-color: transparent !important;
                }
                /* Format column keeps its color (inline style will override) */
                .ad-unit-table-cell .format-text {
                    /* Format color is set inline, so it will override */
                }
                /* Reduce Streamlit column spacing */
                div[data-testid="column"] {
                    padding: 0 4px;
                }
                /* Reduce checkbox container height */
                div[data-testid="column"] > div {
                    padding: 2px 0;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Create table with individual checkboxes (more reliable than data_editor)
                # Header with better styling
                header_cols = st.columns([0.4, 1.5, 1.5, 0.8, 0.9, 2.2])
                with header_cols[0]:
                    st.markdown('<div class="ad-unit-table-header">선택</div>', unsafe_allow_html=True)
                with header_cols[1]:
                    st.markdown('<div class="ad-unit-table-header">ID</div>', unsafe_allow_html=True)
                with header_cols[2]:
                    st.markdown('<div class="ad-unit-table-header">Name</div>', unsafe_allow_html=True)
                with header_cols[3]:
                    st.markdown('<div class="ad-unit-table-header">Platform</div>', unsafe_allow_html=True)
                with header_cols[4]:
                    st.markdown('<div class="ad-unit-table-header">Format</div>', unsafe_allow_html=True)
                with header_cols[5]:
                    st.markdown('<div class="ad-unit-table-header">Package Name</div>', unsafe_allow_html=True)
                
                # Display each row with checkbox
                selected_unit_ids = []
                for idx, unit in enumerate(filtered_units_sorted):
                    unit_id = unit.get("id", "")
                    unit_name = unit.get("name", "")
                    platform = unit.get("platform", "")
                    ad_format = unit.get("ad_format", "")
                    package_name = unit.get("package_name", "")
                    
                    # Get current selection state from session_state (always use latest value)
                    is_selected = st.session_state.ad_unit_selections.get(unit_id, False)
                    
                    # Create row with columns - better proportions
                    row_cols = st.columns([0.4, 1.5, 1.5, 0.8, 0.9, 2.2])
                    
                    # Alternate row background for better readability (with dark mode support)
                    # Use CSS variables or minimal styling that works in both modes
                    # In dark mode, Streamlit handles background, so we use minimal styling
                    row_style = ""
                    
                    with row_cols[0]:
                        # Checkbox with unique key - centered
                        checkbox_key = f"ad_unit_checkbox_{unit_id}"
                        # Always read latest value from session_state to reflect button clicks
                        current_value = st.session_state.ad_unit_selections.get(unit_id, False)
                        new_selection = st.checkbox("", value=current_value, key=checkbox_key, label_visibility="collapsed")
                        
                        # Always update session state to keep it in sync
                        # This ensures button clicks are reflected in checkboxes
                        st.session_state.ad_unit_selections[unit_id] = new_selection
                    
                    with row_cols[1]:
                        st.markdown(f'<div class="ad-unit-table-cell" style="color: #ffffff !important;"><code class="ad-unit-code" style="color: #ffffff !important;">{unit_id}</code></div>', unsafe_allow_html=True)
                    with row_cols[2]:
                        display_name = unit_name[:30] + "..." if len(unit_name) > 30 else unit_name if unit_name else ""
                        st.markdown(f'<div class="ad-unit-table-cell" style="color: #ffffff !important;">{display_name}</div>', unsafe_allow_html=True)
                    with row_cols[3]:
                        # Android, iOS 아이콘 사용
                        if platform.lower() == "android":
                            platform_icon = "🤖"  # Android robot icon
                        elif platform.lower() == "ios":
                            platform_icon = "🍎"  # Apple icon
                        else:
                            platform_icon = "📱"  # Default mobile icon
                        platform_text = f"{platform_icon} {platform}" if platform else ""
                        st.markdown(f'<div class="ad-unit-table-cell" style="color: #ffffff !important;">{platform_text}</div>', unsafe_allow_html=True)
                    with row_cols[4]:
                        format_color = {
                            "REWARD": "#4CAF50",
                            "INTER": "#2196F3",
                            "BANNER": "#FF9800"
                        }.get(ad_format, "#757575")
                        st.markdown(f'<div class="ad-unit-table-cell"><span style="color: {format_color}; font-weight: 500;">{ad_format}</span></div>', unsafe_allow_html=True)
                    with row_cols[5]:
                        display_pkg = package_name[:35] + "..." if len(package_name) > 35 else package_name if package_name else ""
                        st.markdown(f'<div class="ad-unit-table-cell" style="color: #ffffff !important;"><code class="ad-unit-code" style="color: #ffffff !important;">{display_pkg}</code></div>', unsafe_allow_html=True)
                    
                    # Track selected units
                    if st.session_state.ad_unit_selections.get(unit_id, False):
                        selected_unit_ids.append(unit_id)
                
                # Get selected rows for compatibility (convert to dict format)
                selected_rows_dict = []
                for unit in filtered_units_sorted:
                    unit_id = unit.get("id", "")
                    if unit_id in selected_unit_ids:
                        selected_rows_dict.append({
                            "id": unit_id,
                            "name": unit.get("name", ""),
                            "platform": unit.get("platform", ""),
                            "ad_format": unit.get("ad_format", ""),
                            "package_name": unit.get("package_name", "")
                        })
                
                # selected_ad_unit_ids는 하위 호환성을 위해 유지
                st.session_state.selected_ad_unit_ids = selected_unit_ids
                
                if len(selected_rows_dict) > 0:
                    st.markdown(f"**선택된 Ad Units: {len(selected_rows_dict)}개**")
                    
                    # Initialize selected networks in session state (default: all networks)
                    if "selected_ad_networks" not in st.session_state:
                        st.session_state.selected_ad_networks = AD_NETWORKS.copy()
                    
                    # Track if processing is in progress to prevent UI layout issues
                    processing_key = "_ad_units_processing"
                    is_processing = st.session_state.get(processing_key, False)
                    
                    # Show selected networks with remove buttons (compact format) - only when not processing
                    if st.session_state.selected_ad_networks and not is_processing:
                        st.markdown("**선택된 네트워크:**")
                        sorted_networks = sorted(st.session_state.selected_ad_networks.copy())  # Use copy to avoid modification during iteration
                        
                        # Display in a compact grid (4 columns)
                        num_cols = 4
                        for i in range(0, len(sorted_networks), num_cols):
                            cols = st.columns(num_cols)
                            for j, network in enumerate(sorted_networks[i:i+num_cols]):
                                with cols[j]:
                                    # Compact display with inline remove button
                                    col_name, col_btn = st.columns([3, 1])
                                    with col_name:
                                        st.markdown(f'<span style="font-size: 0.85em;">{network}</span>', unsafe_allow_html=True)
                                    with col_btn:
                                        remove_key = f"remove_network_{network}"
                                        if st.button("🗑️", key=remove_key, help=f"{network} 제거", use_container_width=True):
                                            if network in st.session_state.selected_ad_networks:
                                                st.session_state.selected_ad_networks.remove(network)
                                            st.rerun()
                    
                    # Add button - only show when not processing
                    if st.session_state.selected_ad_networks and not is_processing:
                        if st.button(f"➕ 선택한 {len(selected_rows_dict)}개 Ad Units + {len(st.session_state.selected_ad_networks)}개 네트워크 추가", type="primary", use_container_width=True):
                            # Mark as processing to prevent UI layout issues
                            st.session_state[processing_key] = True
                            
                            # Show prominent loading message (use direct rendering instead of container to avoid layout issues)
                            total_tasks = len(selected_rows_dict) * len(st.session_state.selected_ad_networks)
                            
                            # Use a divider to separate sections and prevent layout shift
                            st.divider()
                            
                            # Use a more stable approach: render directly without container
                            st.info(f"⏳ **네트워크에서 데이터를 조회하는 중입니다...**\n\n📊 {len(selected_rows_dict)}개 Ad Units × {len(st.session_state.selected_ad_networks)}개 네트워크 = 총 {total_tasks}개 작업")
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            # Map AppLovin networks to actual network identifiers
                            network_mapping = {}
                            for applovin_network in st.session_state.selected_ad_networks:
                                actual_network = map_applovin_network_to_actual_network(applovin_network)
                                if actual_network:
                                    network_mapping[applovin_network] = actual_network
                            
                            def process_network_unit(row_data: Dict, selected_network: str) -> Tuple[Dict, Dict]:
                                """Process a single network-unit combination
                                
                                Returns:
                                    Tuple of (row_data, result_info)
                                """
                                applovin_unit = row_data["applovin_unit"]
                                actual_network = network_mapping.get(selected_network)
                                
                                # Skip if network is not supported for auto-fetch
                                if not actual_network:
                                    return {
                                        "id": applovin_unit["id"],
                                        "name": applovin_unit["name"],
                                        "platform": applovin_unit["platform"],
                                        "ad_format": applovin_unit["ad_format"],
                                        "package_name": applovin_unit["package_name"],
                                        "ad_network": selected_network,
                                        "ad_network_app_id": "",
                                        "ad_network_app_key": "",
                                        "ad_unit_id": "",
                                        "countries_type": "",
                                        "countries": "",
                                        "cpm": 0.0,
                                        "segment_name": "",
                                        "segment_id": "",
                                        "disabled": "FALSE"
                                    }, {"status": "skipped", "network": selected_network}
                                
                                # Try to find matching app (platform must match)
                                matched_app = match_applovin_unit_to_network(
                                    actual_network,
                                    applovin_unit
                                )
                                
                                if matched_app:
                                    # Extract app identifiers
                                    app_ids = extract_app_identifiers(matched_app, actual_network)
                                    app_key = app_ids.get("app_key") or app_ids.get("app_code")
                                    app_id = app_ids.get("app_id")
                                    
                                    # For BigOAds, ensure app_key is set (fallback to app_id if app_code is missing)
                                    if actual_network == "bigoads" and not app_key:
                                        app_key = app_id  # Fallback to appId if appCode is not available
                                        if app_key:
                                            logger.warning(f"[BigOAds] app_code not found, using appId as fallback: {app_key}")
                                    
                                    # Debug logging for Fyber
                                    if actual_network == "fyber":
                                        logger.info(f"[Fyber] Matched app: {matched_app.get('name', 'N/A')}")
                                        logger.info(f"[Fyber] Matched app keys: {list(matched_app.keys())}")
                                        logger.info(f"[Fyber] Matched app platform: {matched_app.get('platform', 'N/A')}")
                                        logger.info(f"[Fyber] Matched app appId: {matched_app.get('appId', 'N/A')}, id: {matched_app.get('id', 'N/A')}")
                                        logger.info(f"[Fyber] Extracted app_ids: {app_ids}")
                                        logger.info(f"[Fyber] Extracted app_id: {app_id}, app_key: {app_key}")
                                    
                                    # For Unity, use projectId to get units
                                    if actual_network == "unity":
                                        project_id = app_ids.get("projectId") or app_id
                                        app_key = project_id  # Use projectId for Unity unit lookup
                                    
                                    # Debug logging for BigOAds
                                    if actual_network == "bigoads":
                                        logger.info(f"[BigOAds] ========== Debug Info ==========")
                                        logger.info(f"[BigOAds] Ad Format: {applovin_unit.get('ad_format')}")
                                        logger.info(f"[BigOAds] Platform: {applovin_unit.get('platform')}")
                                        logger.info(f"[BigOAds] Matched app: {matched_app.get('name', 'N/A')}")
                                        logger.info(f"[BigOAds] Matched app keys: {list(matched_app.keys())}")
                                        logger.info(f"[BigOAds] Matched app appCode: {matched_app.get('appCode', 'N/A')}")
                                        logger.info(f"[BigOAds] Matched app platform: {matched_app.get('platform', 'N/A')}")
                                        logger.info(f"[BigOAds] Extracted app_ids: {app_ids}")
                                        logger.info(f"[BigOAds] Extracted app_code: {app_ids.get('app_code')}, app_key: {app_key}, app_id: {app_id}")
                                        st.write(f"🔍 [BigOAds Debug] Ad Format: {applovin_unit.get('ad_format')}")
                                        st.write(f"🔍 [BigOAds Debug] Platform: {applovin_unit.get('platform')}")
                                        st.write(f"🔍 [BigOAds Debug] App found: {matched_app.get('name', 'N/A')}")
                                        st.write(f"🔍 [BigOAds Debug] appCode from matched_app: {matched_app.get('appCode', 'N/A')}")
                                        st.write(f"🔍 [BigOAds Debug] app_ids: {app_ids}")
                                        st.write(f"🔍 [BigOAds Debug] app_key: {app_key}, app_id: {app_id}")
                                    
                                    # Get units for this app (sequential: app -> units)
                                    units = get_network_units(actual_network, app_key or app_id or "")
                                    
                                    # Debug logging for BigOAds units
                                    if actual_network == "bigoads":
                                        st.write(f"🔍 [BigOAds Debug] Units count: {len(units) if units else 0}")
                                        if units:
                                            st.write(f"🔍 [BigOAds Debug] First unit: {units[0]}")
                                    
                                    # Find matching unit by ad_format
                                    matched_unit = None
                                    if units:
                                        matched_unit = find_matching_unit(
                                            units,
                                            applovin_unit["ad_format"],
                                            actual_network,
                                            applovin_unit["platform"]
                                        )
                                        
                                        # Debug logging for Vungle
                                        if actual_network == "vungle":
                                            if matched_unit:
                                                st.write(f"🔍 [Vungle Debug] Matched unit: {matched_unit.get('name', 'N/A')}")
                                                st.write(f"🔍 [Vungle Debug] referenceID: {matched_unit.get('referenceID', 'N/A')}")
                                                st.write(f"🔍 [Vungle Debug] All keys: {list(matched_unit.keys())}")
                                            else:
                                                st.write(f"⚠️ [Vungle Debug] No unit matched!")
                                                if units:
                                                    st.write(f"🔍 [Vungle Debug] Available units: {len(units)}")
                                                    st.write(f"🔍 [Vungle Debug] First unit keys: {list(units[0].keys()) if units else []}")
                                        
                                        # Debug logging for BigOAds unit matching
                                        if actual_network == "bigoads":
                                            st.write(f"🔍 [BigOAds Debug] ========== Unit Matching ==========")
                                            st.write(f"🔍 [BigOAds Debug] Ad format: {applovin_unit['ad_format']}")
                                            st.write(f"🔍 [BigOAds Debug] Platform: {applovin_unit['platform']}")
                                            st.write(f"🔍 [BigOAds Debug] Total units available: {len(units)}")
                                            if units:
                                                st.write(f"🔍 [BigOAds Debug] All units adType: {[u.get('adType') for u in units]}")
                                                st.write(f"🔍 [BigOAds Debug] All units name: {[u.get('name') for u in units]}")
                                            st.write(f"🔍 [BigOAds Debug] Matched unit: {matched_unit}")
                                            if matched_unit:
                                                st.write(f"🔍 [BigOAds Debug] Matched unit name: {matched_unit.get('name', 'N/A')}")
                                                st.write(f"🔍 [BigOAds Debug] Matched unit slotCode: {matched_unit.get('slotCode', 'N/A')}")
                                                st.write(f"🔍 [BigOAds Debug] Matched unit adType: {matched_unit.get('adType', 'N/A')}")
                                            else:
                                                st.write(f"⚠️ [BigOAds Debug] No unit matched!")
                                                st.write(f"⚠️ [BigOAds Debug] This means ad_network_app_id should still be set from app_key: {app_key}")
                                    else:
                                        # No units found
                                        if actual_network == "bigoads":
                                            st.write(f"⚠️ [BigOAds Debug] No units returned from API!")
                                            st.write(f"⚠️ [BigOAds Debug] app_key used for API call: {app_key}")
                                            st.write(f"⚠️ [BigOAds Debug] This means ad_network_app_id should still be set from app_key: {app_key}")
                                    
                                    # Extract unit ID
                                    unit_id = ""
                                    if matched_unit:
                                        if actual_network == "ironsource":
                                            # For IronSource, use instanceId from GET Instance API
                                            unit_id = str(matched_unit.get("instanceId", "")) if matched_unit.get("instanceId") else ""
                                        elif actual_network == "inmobi":
                                            unit_id = matched_unit.get("placementId") or matched_unit.get("id") or ""
                                        elif actual_network == "mintegral":
                                            # Mintegral uses placement_id
                                            unit_id = matched_unit.get("placement_id") or matched_unit.get("id") or ""
                                        elif actual_network == "fyber":
                                            # Fyber uses placementId or id
                                            unit_id = matched_unit.get("placementId") or matched_unit.get("id") or ""
                                        elif actual_network == "bigoads":
                                            # BigOAds uses slotCode for ad_unit_id
                                            unit_id = matched_unit.get("slotCode") or matched_unit.get("id") or ""
                                        elif actual_network == "vungle":
                                            # Vungle uses referenceID for ad_unit_id
                                            unit_id = matched_unit.get("referenceID") or matched_unit.get("placementId") or matched_unit.get("id") or ""
                                        elif actual_network == "unity":
                                            # Unity uses placements.id for ad_unit_id
                                            # placements is a JSON string like: '{"placement_name": {"id": "...", ...}}'
                                            # We need to extract the "id" from the first placement
                                            unit_id = ""
                                            placements_parsed = matched_unit.get("placements_parsed", {})
                                            
                                            # If not already parsed, try to parse placements
                                            if not placements_parsed:
                                                placements_str = matched_unit.get("placements", "")
                                                if placements_str:
                                                    try:
                                                        import json
                                                        if isinstance(placements_str, str):
                                                            # Try normal parsing first
                                                            try:
                                                                placements_parsed = json.loads(placements_str)
                                                            except json.JSONDecodeError:
                                                                # Handle escaped double quotes ("" -> ")
                                                                cleaned_str = placements_str.replace('""', '"')
                                                                placements_parsed = json.loads(cleaned_str)
                                                        elif isinstance(placements_str, dict):
                                                            placements_parsed = placements_str
                                                    except (json.JSONDecodeError, TypeError) as e:
                                                        logger.warning(f"[Unity] Failed to parse placements: {e}")
                                                        placements_parsed = {}
                                            
                                            # Extract first placement id from placements dict
                                            # placements_parsed structure: {"placement_name": {"id": "...", "name": "...", ...}}
                                            if isinstance(placements_parsed, dict) and placements_parsed:
                                                # Get the first placement (any key)
                                                for placement_name, placement_data in placements_parsed.items():
                                                    if isinstance(placement_data, dict):
                                                        placement_id = placement_data.get("id", "")
                                                        if placement_id:
                                                            unit_id = placement_id
                                                            logger.info(f"[Unity] Extracted unit_id '{unit_id}' from placement '{placement_name}'")
                                                            break
                                            
                                            # Fallback: use unit's id field if placements id not found
                                            if not unit_id:
                                                unit_id = matched_unit.get("id") or matched_unit.get("adUnitId") or matched_unit.get("unitId") or ""
                                                if unit_id:
                                                    logger.warning(f"[Unity] Using fallback unit_id from unit.id: {unit_id}")
                                                else:
                                                    logger.warning(f"[Unity] No unit_id found in placements or unit fields")
                                            
                                            logger.info(f"[Unity] Final unit_id: {unit_id}")
                                        else:
                                            unit_id = (
                                                matched_unit.get("adUnitId") or
                                                matched_unit.get("unitId") or
                                                matched_unit.get("placementId") or
                                                matched_unit.get("id") or
                                                ""
                                            )
                                    
                                    # For IronSource, appKey goes to ad_network_app_id
                                    # For InMobi, use fixed value for ad_network_app_id and empty ad_network_app_key
                                    # For Mintegral, use app_id for ad_network_app_id and fixed value for ad_network_app_key
                                    # For Fyber, use app_id for ad_network_app_id and empty ad_network_app_key
                                    # For BigOAds, use appCode for ad_network_app_id and empty ad_network_app_key
                                    # For Vungle, use applicationId for ad_network_app_id and empty ad_network_app_key
                                    if actual_network == "ironsource":
                                        ad_network_app_id = str(app_key) if app_key else ""
                                        ad_network_app_key = ""
                                    elif actual_network == "inmobi":
                                        ad_network_app_id = "8400e4e3995a4ed2b0be0ef1e893e606"  # Fixed value for InMobi
                                        ad_network_app_key = ""  # Empty for InMobi
                                    elif actual_network == "mintegral":
                                        ad_network_app_id = str(app_id) if app_id else ""  # Use actual app_id for Mintegral
                                        ad_network_app_key = "8dcb744465a574d79bf29f1a7a25c6ce"  # Fixed value for Mintegral
                                    elif actual_network == "fyber":
                                        ad_network_app_id = str(app_id) if app_id else ""
                                        ad_network_app_key = ""  # Empty for Fyber
                                    elif actual_network == "bigoads":
                                        # For BigOAds, use appCode (app_key) for ad_network_app_id
                                        # Fallback to appId if appCode is not available
                                        if app_key:
                                            ad_network_app_id = str(app_key)
                                        elif app_id:
                                            ad_network_app_id = str(app_id)
                                            logger.warning(f"[BigOAds] Using appId as fallback for ad_network_app_id: {ad_network_app_id}")
                                        else:
                                            # Last resort: try to get from matched_app directly
                                            ad_network_app_id = str(matched_app.get("appCode") or matched_app.get("appId") or "")
                                            if ad_network_app_id:
                                                logger.warning(f"[BigOAds] Using direct matched_app value for ad_network_app_id: {ad_network_app_id}")
                                            else:
                                                logger.error(f"[BigOAds] Could not extract ad_network_app_id. matched_app keys: {list(matched_app.keys())}")
                                        ad_network_app_key = ""  # Empty for BigOAds
                                        
                                        # Debug logging for BigOAds ad_network_app_id
                                        if not ad_network_app_id:
                                            st.write(f"⚠️ [BigOAds Debug] ========== ad_network_app_id is EMPTY ==========")
                                            st.write(f"⚠️ [BigOAds Debug] app_key value: {app_key}")
                                            st.write(f"⚠️ [BigOAds Debug] app_id value: {app_id}")
                                            st.write(f"⚠️ [BigOAds Debug] app_ids dict: {app_ids}")
                                            st.write(f"⚠️ [BigOAds Debug] matched_app appCode: {matched_app.get('appCode') if matched_app else 'N/A'}")
                                            st.write(f"⚠️ [BigOAds Debug] matched_app appId: {matched_app.get('appId') if matched_app else 'N/A'}")
                                            st.write(f"⚠️ [BigOAds Debug] matched_app keys: {list(matched_app.keys()) if matched_app else []}")
                                        else:
                                            st.write(f"✅ [BigOAds Debug] ad_network_app_id set to: {ad_network_app_id}")
                                    elif actual_network == "vungle":
                                        # Vungle uses vungleAppId from application object
                                        # app_id should already contain vungleAppId from match_applovin_unit_to_network
                                        ad_network_app_id = str(app_id) if app_id else ""
                                        ad_network_app_key = ""  # Empty for Vungle
                                    elif actual_network == "unity":
                                        # Unity uses gameId from stores (platform-specific)
                                        # Extract gameId based on platform
                                        game_id = ""
                                        if matched_app:
                                            stores_raw = matched_app.get("stores", "")
                                            stores = {}
                                            
                                            # Parse stores - can be JSON string or dict
                                            if stores_raw:
                                                try:
                                                    import json
                                                    if isinstance(stores_raw, str):
                                                        # Handle escaped JSON string with double quotes (e.g., '{"apple": {...}}')
                                                        # First, try to parse as-is
                                                        try:
                                                            stores = json.loads(stores_raw)
                                                        except json.JSONDecodeError:
                                                            # If that fails, try replacing double quotes
                                                            # Handle case where JSON has escaped quotes: "{""apple"": ...}"
                                                            cleaned_str = stores_raw.replace('""', '"')
                                                            stores = json.loads(cleaned_str)
                                                    elif isinstance(stores_raw, dict):
                                                        stores = stores_raw
                                                    else:
                                                        logger.warning(f"[Unity] Unexpected stores type: {type(stores_raw)}")
                                                except (json.JSONDecodeError, TypeError) as e:
                                                    logger.warning(f"[Unity] Failed to parse stores JSON: {stores_raw[:200]}, error: {e}")
                                            
                                            platform_lower = applovin_unit.get("platform", "").lower()
                                            logger.info(f"[Unity] Platform: {platform_lower}, Stores keys: {list(stores.keys()) if isinstance(stores, dict) else 'not a dict'}")
                                            
                                            if platform_lower == "ios":
                                                # iOS: use apple.gameId
                                                apple_store = stores.get("apple", {})
                                                if isinstance(apple_store, dict):
                                                    game_id = apple_store.get("gameId", "")
                                                logger.info(f"[Unity] iOS gameId: {game_id} from apple store: {apple_store}")
                                            elif platform_lower == "android":
                                                # Android: use google.gameId
                                                google_store = stores.get("google", {})
                                                if isinstance(google_store, dict):
                                                    game_id = google_store.get("gameId", "")
                                                logger.info(f"[Unity] Android gameId: {game_id} from google store: {google_store}")
                                            
                                            if not game_id:
                                                logger.warning(f"[Unity] No gameId found for platform {platform_lower}, stores: {stores}")
                                        
                                        ad_network_app_id = str(game_id) if game_id else ""
                                        ad_network_app_key = ""  # Empty for Unity
                                        
                                        # Debug logging
                                        if not ad_network_app_id:
                                            logger.warning(f"[Unity] Empty ad_network_app_id for platform {applovin_unit.get('platform')}, matched_app name: {matched_app.get('name') if matched_app else 'None'}")
                                    else:
                                        ad_network_app_id = str(app_id) if app_id else ""
                                        ad_network_app_key = str(app_key) if app_key else ""
                                    
                                    row = {
                                        "id": applovin_unit["id"],
                                        "name": applovin_unit["name"],
                                        "platform": applovin_unit["platform"],
                                        "ad_format": applovin_unit["ad_format"],
                                        "package_name": applovin_unit["package_name"],
                                        "ad_network": selected_network,
                                        "ad_network_app_id": ad_network_app_id,
                                        "ad_network_app_key": ad_network_app_key,
                                        "ad_unit_id": str(unit_id) if unit_id else "",
                                        "countries_type": "",
                                        "countries": "",
                                        "cpm": 0.0,
                                        "segment_name": "",
                                        "segment_id": "",
                                        "disabled": "FALSE"
                                    }
                                    
                                    result_info = {
                                        "status": "success" if unit_id else "unit_not_found",
                                        "network": selected_network,
                                        "app_name": applovin_unit["name"],
                                        "platform": applovin_unit["platform"],
                                        "ad_format": applovin_unit["ad_format"],
                                        "reason": "Unit not found" if not unit_id else None
                                    }
                                    
                                    return row, result_info
                                else:
                                    # App not found
                                    # For InMobi, still use fixed value for ad_network_app_id
                                    # For Mintegral, still use fixed value for ad_network_app_key
                                    # For Fyber, empty both fields
                                    # For BigOAds, empty both fields
                                    # For Vungle, empty both fields
                                    if actual_network == "inmobi":
                                        ad_network_app_id = "8400e4e3995a4ed2b0be0ef1e893e606"  # Fixed value for InMobi
                                        ad_network_app_key = ""
                                    elif actual_network == "mintegral":
                                        ad_network_app_id = ""  # Empty for Mintegral
                                        ad_network_app_key = "8dcb744465a574d79bf29f1a7a25c6ce"  # Fixed value for Mintegral
                                    elif actual_network == "fyber":
                                        ad_network_app_id = ""  # Empty for Fyber (app not found)
                                        ad_network_app_key = ""  # Empty for Fyber
                                    elif actual_network == "bigoads":
                                        ad_network_app_id = ""  # Empty for BigOAds (app not found)
                                        ad_network_app_key = ""  # Empty for BigOAds
                                    elif actual_network == "vungle":
                                        ad_network_app_id = ""  # Empty for Vungle (app not found)
                                        ad_network_app_key = ""  # Empty for Vungle
                                    else:
                                        ad_network_app_id = ""
                                        ad_network_app_key = ""
                                    
                                    row = {
                                        "id": applovin_unit["id"],
                                        "name": applovin_unit["name"],
                                        "platform": applovin_unit["platform"],
                                        "ad_format": applovin_unit["ad_format"],
                                        "package_name": applovin_unit["package_name"],
                                        "ad_network": selected_network,
                                        "ad_network_app_id": ad_network_app_id,
                                        "ad_network_app_key": ad_network_app_key,
                                        "ad_unit_id": "",
                                        "countries_type": "",
                                        "countries": "",
                                        "cpm": 0.0,
                                        "segment_name": "",
                                        "segment_id": "",
                                        "disabled": "FALSE"
                                    }
                                    
                                    result_info = {
                                        "status": "app_not_found",
                                        "network": selected_network,
                                        "app_name": applovin_unit["name"],
                                        "platform": applovin_unit["platform"],
                                        "ad_format": applovin_unit["ad_format"],
                                        "reason": "App not found"
                                    }
                                    
                                    return row, result_info
                            
                            try:
                                new_rows = []
                                fetch_results = {
                                    "success": [],
                                    "failed": [],
                                    "not_found": []
                                }
                                
                                status_text.text("🔄 네트워크 매핑 완료. API 호출 시작...")
                                progress_bar.progress(10)
                                
                                # Prepare tasks for parallel processing
                                tasks = []
                                for row in selected_rows_dict:
                                    applovin_unit = {
                                        "id": row["id"],
                                        "name": row["name"],
                                        "platform": row["platform"].lower(),
                                        "ad_format": row["ad_format"],
                                        "package_name": row["package_name"]
                                    }
                                    
                                    for selected_network in st.session_state.selected_ad_networks:
                                        tasks.append({
                                            "applovin_unit": applovin_unit,
                                            "selected_network": selected_network
                                        })
                                
                                # Process tasks in parallel (multiple networks) but sequential within each network (app -> units)
                                status_text.text(f"🔄 {len(tasks)}개 작업 처리 중... (병렬 처리)")
                                progress_bar.progress(20)
                                
                                completed_tasks = 0
                                with ThreadPoolExecutor(max_workers=min(len(st.session_state.selected_ad_networks), 5)) as executor:
                                    future_to_task = {
                                        executor.submit(
                                            process_network_unit,
                                            {"applovin_unit": task["applovin_unit"]},
                                            task["selected_network"]
                                        ): task
                                        for task in tasks
                                    }
                                    
                                    for future in as_completed(future_to_task):
                                        try:
                                            row, result_info = future.result()
                                            new_rows.append(row)
                                            completed_tasks += 1
                                            
                                            # Update progress
                                            progress = 20 + int((completed_tasks / len(tasks)) * 70)
                                            progress_bar.progress(progress)
                                            status_text.text(f"🔄 진행 중... ({completed_tasks}/{len(tasks)} 완료)")
                                            
                                            # Track results
                                            if result_info["status"] == "success":
                                                fetch_results["success"].append({
                                                    "network": result_info["network"],
                                                    "app_name": result_info["app_name"],
                                                    "platform": result_info["platform"],
                                                    "ad_format": result_info["ad_format"]
                                                })
                                            elif result_info["status"] in ["app_not_found", "unit_not_found"]:
                                                fetch_results["not_found"].append({
                                                    "network": result_info["network"],
                                                    "app_name": result_info["app_name"],
                                                    "platform": result_info["platform"],
                                                    "ad_format": result_info["ad_format"],
                                                    "reason": result_info.get("reason", "Unknown")
                                                })
                                        except Exception as e:
                                            task = future_to_task[future]
                                            logging.error(f"Error processing {task['selected_network']}: {str(e)}")
                                            fetch_results["failed"].append({
                                                "network": task["selected_network"],
                                                "error": str(e)
                                            })
                                            completed_tasks += 1
                                
                                status_text.text("📊 데이터 정리 중...")
                                progress_bar.progress(95)
                                
                                if new_rows:
                                    new_df = pd.DataFrame(new_rows)
                                    # If data was already prepared, we need to sort again after adding new data
                                    # Reset the prepared flag so data will be sorted and reordered
                                    if st.session_state.get("_applovin_data_prepared", False):
                                        st.session_state["_applovin_data_prepared"] = False
                                    st.session_state.applovin_data = pd.concat([st.session_state.applovin_data, new_df], ignore_index=True)
                                    
                                    progress_bar.progress(100)
                                    status_text.text("✅ 완료!")
                                    
                                    # Show results summary
                                    success_count = len(fetch_results["success"])
                                    not_found_count = len(fetch_results["not_found"])
                                    
                                    if success_count > 0:
                                        st.success(f"✅ {len(new_rows)}개 행이 데이터 테이블에 추가되었습니다! ({success_count}개 자동 채움)")
                                    else:
                                        st.info(f"ℹ️ {len(new_rows)}개 행이 데이터 테이블에 추가되었습니다. (자동 채움: {success_count}개, 찾지 못함: {not_found_count}개)")
                                    
                                    # Show details if there are failures
                                    if not_found_count > 0:
                                        with st.expander(f"⚠️ 찾지 못한 항목 ({not_found_count}개)", expanded=False):
                                            for item in fetch_results["not_found"][:10]:  # Show first 10
                                                st.write(f"- {item['network']}: {item['app_name']} ({item['platform']}, {item['ad_format']}) - {item.get('reason', 'Unknown')}")
                                            if not_found_count > 10:
                                                st.write(f"... 외 {not_found_count - 10}개")
                                    
                                    # Clear processing flag and selections
                                    st.session_state[processing_key] = False
                                    st.session_state.selected_ad_networks = []
                                    st.rerun()
                                else:
                                    progress_bar.progress(100)
                                    status_text.text("⚠️ 완료 (데이터 없음)")
                                    st.warning("⚠️ 선택한 항목과 일치하는 platform/ad_format 조합이 없습니다.")
                                    # Clear processing flag
                                    st.session_state[processing_key] = False
                            except Exception as e:
                                progress_bar.progress(100)
                                status_text.text("❌ 오류 발생")
                                st.error(f"❌ 오류 발생: {str(e)}")
                                import traceback
                                st.exception(e)
                                # Clear processing flag
                                st.session_state[processing_key] = False
        else:
            st.info("검색 조건에 맞는 Ad Unit이 없습니다.")

st.divider()

# Initialize session state
if "applovin_data" not in st.session_state:
    # Start with empty DataFrame
    st.session_state.applovin_data = pd.DataFrame({
        "id": pd.Series(dtype="string"),
        "name": pd.Series(dtype="string"),
        "platform": pd.Series(dtype="string"),
        "ad_format": pd.Series(dtype="string"),
        "package_name": pd.Series(dtype="string"),
        "ad_network": pd.Series(dtype="string"),
        "ad_network_app_id": pd.Series(dtype="string"),
        "ad_network_app_key": pd.Series(dtype="string"),
        "ad_unit_id": pd.Series(dtype="string"),
        "countries_type": pd.Series(dtype="string"),
        "countries": pd.Series(dtype="string"),
        "cpm": pd.Series(dtype="float64"),
        "segment_name": pd.Series(dtype="string"),
        "segment_id": pd.Series(dtype="string"),
        "disabled": pd.Series(dtype="string")
    })
    # Mark that sorting is needed when data is first initialized
    st.session_state["_applovin_data_sort_needed"] = True

st.divider()

# Data table section
if len(st.session_state.applovin_data) > 0:
    st.subheader("📊 데이터 테이블")
else:
    st.subheader("📊 데이터 테이블")
    st.info("네트워크를 추가하면 테이블이 표시됩니다.")

# Ensure column order
column_order = [
    "id", "name", "platform", "ad_format", "package_name",
    "ad_network", "ad_network_app_id", "ad_network_app_key", "ad_unit_id",
    "countries_type", "countries", "cpm",
    "segment_name", "segment_id", "disabled"
]

# Prepare data for editor - do all transformations BEFORE data_editor
# Sort and reorder columns ONLY when data is first added (not on every rerun)
# This prevents focus loss during editing
if len(st.session_state.applovin_data) > 0:
    # Track if data has been prepared (sorted and reordered) for the first time
    data_prepared_key = "_applovin_data_prepared"
    
    # Only sort and reorder on first time (when data is first added)
    if not st.session_state.get(data_prepared_key, False):
        # Reorder columns if needed
        col_order_key = "_applovin_data_column_order"
        current_cols = list(st.session_state.applovin_data.columns)
        existing_cols = [col for col in column_order if col in st.session_state.applovin_data.columns]
        missing_cols = [col for col in st.session_state.applovin_data.columns if col not in column_order]
        expected_cols = existing_cols + missing_cols
        
        if current_cols != expected_cols:
            st.session_state.applovin_data = st.session_state.applovin_data[expected_cols]
            st.session_state[col_order_key] = expected_cols
        else:
            st.session_state[col_order_key] = current_cols
        
        # Sort data by ad_network, platform, ad_format (only once, when first added)
        if "ad_network" in st.session_state.applovin_data.columns:
            # Define sort order for ad_format
            ad_format_order = {"REWARD": 0, "INTER": 1, "BANNER": 2}
            platform_order = {"android": 0, "ios": 1}
            
            # Create temporary columns for sorting
            temp_df = st.session_state.applovin_data.copy()
            temp_df["_sort_ad_format"] = temp_df["ad_format"].map(ad_format_order).fillna(99)
            temp_df["_sort_platform"] = temp_df["platform"].map(platform_order).fillna(99)
            
            # Sort
            temp_df = temp_df.sort_values(
                by=["ad_network", "_sort_platform", "_sort_ad_format"],
                ascending=[True, True, True]
            ).reset_index(drop=True)
            
            # Remove temporary columns
            temp_df = temp_df.drop(columns=["_sort_ad_format", "_sort_platform"], errors="ignore")
            
            # Update session state
            st.session_state.applovin_data = temp_df
            # Update column order cache
            if col_order_key in st.session_state:
                st.session_state[col_order_key] = list(temp_df.columns)
        
        # Mark as prepared (sorted and reordered) - never sort again
        st.session_state[data_prepared_key] = True

# Data editor with fixed key to prevent focus loss
# Note: st.data_editor automatically triggers reruns on edit
# We minimize DataFrame changes to reduce focus loss
data_editor_key = "applovin_data_editor"
edited_df = st.data_editor(
    st.session_state.applovin_data,
    num_rows="dynamic",
    use_container_width=True,
    key=data_editor_key,
    column_config={
        "id": st.column_config.TextColumn(
            "id",
            help="AppLovin Ad Unit ID",
            required=True
        ),
        "name": st.column_config.TextColumn(
            "name",
            help="Ad Unit 이름 (선택사항)"
        ),
        "platform": st.column_config.SelectboxColumn(
            "platform",
            options=["android", "ios"],
            required=True
        ),
        "ad_format": st.column_config.SelectboxColumn(
            "ad_format",
            options=["BANNER", "INTER", "REWARD"],
            required=True
        ),
        "package_name": st.column_config.TextColumn(
            "package_name",
            help="앱 패키지명 (선택사항)"
        ),
        "ad_network": st.column_config.TextColumn(
            "ad_network",
            help="네트워크 이름 (읽기 전용 - 상단에서 선택)",
            required=True,
            disabled=True
        ),
        "ad_network_app_id": st.column_config.TextColumn(
            "ad_network_app_id",
            help="Ad Network App ID (선택사항)"
        ),
        "ad_network_app_key": st.column_config.TextColumn(
            "ad_network_app_key",
            help="Ad Network App Key (선택사항)"
        ),
        "ad_unit_id": st.column_config.TextColumn(
            "ad_unit_id",
            help="Ad Network의 Ad Unit ID",
            required=True
        ),
        "countries_type": st.column_config.SelectboxColumn(
            "countries_type",
            options=["", "INCLUDE", "EXCLUDE"],
            help="INCLUDE 또는 EXCLUDE (공란 가능)"
        ),
        "countries": st.column_config.TextColumn(
            "countries",
            help="국가 코드 (쉼표로 구분, 예: us,kr, 공란 가능)"
        ),
        "cpm": st.column_config.NumberColumn(
            "cpm",
            help="CPM 값 (기본값: 0)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            required=True,
            default=0.0
        ),
        "segment_name": st.column_config.TextColumn(
            "segment_name",
            help="Segment Name (공란 가능)"
        ),
        "segment_id": st.column_config.TextColumn(
            "segment_id",
            help="Segment ID (비워두면 'None', 공란 가능)"
        ),
        "disabled": st.column_config.SelectboxColumn(
            "disabled",
            options=["FALSE", "TRUE"],
            help="비활성화 여부 (기본값: FALSE)",
            default="FALSE"
        )
    },
    hide_index=True
)

# DO NOT update session_state here to prevent focus loss
# We will update session_state only when "Update All Ad Units" button is clicked
# This prevents reruns during editing and maintains focus

st.divider()

# Validation and Submit
if len(edited_df) > 0:
    st.divider()
    
    if st.button("🚀 Update All Ad Units", type="primary", use_container_width=True):
        # Save edited data to session_state before validation and API call
        st.session_state.applovin_data = edited_df.copy()
        
        # Validate data
        errors = []
        
        # Check required columns
        required_columns = ["id", "platform", "ad_format", "ad_network", "ad_unit_id", "cpm"]
        missing_columns = [col for col in required_columns if col not in edited_df.columns]
        if missing_columns:
            errors.append(f"필수 컬럼이 없습니다: {', '.join(missing_columns)}")
        
        # Check required fields
        if "id" in edited_df.columns:
            empty_ids = edited_df[edited_df["id"].isna() | (edited_df["id"] == "")]
            if len(empty_ids) > 0:
                errors.append(f"{len(empty_ids)}개의 행에 Ad Unit ID가 없습니다.")
        
        if "ad_network" in edited_df.columns:
            empty_networks = edited_df[edited_df["ad_network"].isna() | (edited_df["ad_network"] == "")]
            if len(empty_networks) > 0:
                errors.append(f"{len(empty_networks)}개의 행에 Ad Network가 없습니다.")
        
        if "ad_unit_id" in edited_df.columns:
            empty_unit_ids = edited_df[edited_df["ad_unit_id"].isna() | (edited_df["ad_unit_id"] == "")]
            if len(empty_unit_ids) > 0:
                errors.append(f"{len(empty_unit_ids)}개의 행에 Ad Network Ad Unit ID가 없습니다.")
        
        if errors:
            st.error("❌ 다음 오류를 수정해주세요:")
            for error in errors:
                st.error(f"  - {error}")
        else:
            # Transform data
            with st.spinner("데이터 변환 중..."):
                try:
                    # Fill default values before conversion
                    df_filled = edited_df.copy()
                    
                    # Fill NaN values with defaults
                    if "cpm" in df_filled.columns:
                        df_filled["cpm"] = df_filled["cpm"].fillna(0.0)
                    if "disabled" in df_filled.columns:
                        df_filled["disabled"] = df_filled["disabled"].fillna("FALSE")
                    
                    # Convert DataFrame to list of dicts
                    csv_data = df_filled.to_dict('records')
                    ad_units_by_segment = transform_csv_data_to_api_format(csv_data)
                except Exception as e:
                    st.error(f"❌ 데이터 변환 중 오류 발생: {str(e)}")
                    logger.error(f"Data transformation error: {str(e)}", exc_info=True)
                    st.stop()
            
            # Update ad units
            with st.spinner("Ad Units 업데이트 중..."):
                try:
                    result = update_multiple_ad_units(api_key, ad_units_by_segment)
                    
                    # Store response in session_state to persist it
                    st.session_state["applovin_update_result"] = result
                    
                    # Display results
                    st.success(f"✅ 완료! 성공: {len(result['success'])}, 실패: {len(result['fail'])}")
                    
                    # Success list
                    if result["success"]:
                        st.subheader("✅ 성공한 업데이트")
                        success_data = []
                        for item in result["success"]:
                            success_data.append({
                                "Segment ID": item["segment_id"],
                                "Ad Unit ID": item["ad_unit_id"],
                                "Status": "Success"
                            })
                        st.dataframe(success_data, use_container_width=True, hide_index=True)
                    
                    # Fail list
                    if result["fail"]:
                        st.subheader("❌ 실패한 업데이트")
                        fail_data = []
                        for item in result["fail"]:
                            error_info = item.get("error", {})
                            fail_data.append({
                                "Segment ID": item["segment_id"],
                                "Ad Unit ID": item["ad_unit_id"],
                                "Status Code": error_info.get("status_code", "N/A"),
                                "Error": json.dumps(error_info.get("data", {}), ensure_ascii=False)
                            })
                        st.dataframe(fail_data, use_container_width=True, hide_index=True)
                    
                    # Download result
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    result_json = json.dumps(result, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📥 Download Result (JSON)",
                        data=result_json,
                        file_name=f"applovin_update_result_{timestamp}.json",
                        mime="application/json"
                    )
                    
                except Exception as e:
                    st.error(f"❌ 업데이트 중 오류 발생: {str(e)}")
                    logger.error(f"Update error: {str(e)}", exc_info=True)
else:
    st.info("📝 위 테이블에 데이터를 입력하세요. 행을 추가하려면 테이블 하단의 '+' 버튼을 클릭하세요.")
