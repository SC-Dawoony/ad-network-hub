"""AppLovin Ad Unit Settings Update page"""
import streamlit as st
import json
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List
from utils.applovin_manager import (
    get_applovin_api_key,
    transform_csv_data_to_api_format,
    update_multiple_ad_units,
    get_ad_units,
    get_ad_unit_details
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Update Ad Unit Settings",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ AppLovin Ad Unit Settings 업데이트")
st.markdown("AppLovin API를 통해 Ad Unit의 ad_network_settings를 업데이트합니다.")

# Available ad networks
AD_NETWORKS = [
    "ADMOB_BIDDING",
    "BIGO_BIDDING",
    "CHARTBOOST_BIDDING",
    "FACEBOOK_NETWORK",
    "FYBER_BIDDING",
    "INMOBI_BIDDING",
    "IRONSOURCE_BIDDING",
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
            with st.spinner("API 호출 중..."):
                success, result = get_ad_units(api_key)
                
                if success:
                    data = result.get("data", {})
                    
                    # Handle different response formats
                    ad_units_list = []
                    if isinstance(data, list):
                        ad_units_list = data
                    elif isinstance(data, dict):
                        ad_units_list = data.get("ad_units", data.get("data", data.get("list", data.get("results", []))))
                    
                    if ad_units_list:
                        st.session_state.applovin_ad_units_raw = ad_units_list
                        st.success(f"✅ {len(ad_units_list)}개의 Ad Unit이 조회되었습니다!")
                    else:
                        st.json(data)
                        st.session_state.applovin_ad_units_raw = []
                else:
                    st.error("❌ API 호출 실패")
                    error_info = result.get("data", {})
                    st.json(error_info)
                    if "status_code" in result:
                        st.error(f"Status Code: {result['status_code']}")
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
            
            # Create table with checkbox
            table_data = []
            for unit in filtered_units:
                table_data.append({
                    "선택": False,
                    "id": unit.get("id", ""),
                    "name": unit.get("name", ""),
                    "platform": unit.get("platform", ""),
                    "ad_format": unit.get("ad_format", ""),
                    "package_name": unit.get("package_name", "")
                })
            
            if table_data:
                df = pd.DataFrame(table_data)
                
                # Initialize select all state
                if "select_all_ad_units_flag" not in st.session_state:
                    st.session_state.select_all_ad_units_flag = None
                
                # Select all / Deselect all buttons
                col_select, col_deselect = st.columns(2)
                with col_select:
                    if st.button("✅ 전체 선택", use_container_width=True, key="select_all_ad_units"):
                        st.session_state.select_all_ad_units_flag = True
                        st.rerun()
                with col_deselect:
                    if st.button("❌ 전체 해제", use_container_width=True, key="deselect_all_ad_units"):
                        st.session_state.select_all_ad_units_flag = False
                        st.rerun()
                
                # Apply select all/deselect all
                if st.session_state.select_all_ad_units_flag is not None:
                    df["선택"] = st.session_state.select_all_ad_units_flag
                    st.session_state.select_all_ad_units_flag = None
                
                # Restore selected Ad Unit IDs if they exist (after network removal)
                # This must happen BEFORE data_editor to ensure the selection is restored
                if "selected_ad_unit_ids" in st.session_state and st.session_state.selected_ad_unit_ids:
                    # Only restore if we have saved IDs and they match current dataframe
                    saved_ids = set(st.session_state.selected_ad_unit_ids)
                    current_ids = set(df["id"].tolist())
                    if saved_ids.issubset(current_ids):
                        df.loc[df["id"].isin(st.session_state.selected_ad_unit_ids), "선택"] = True
                
                # Display with checkbox
                # Use a dynamic key that changes when networks are removed to force refresh
                editor_key = f"ad_units_selection_table_{len(st.session_state.get('selected_ad_networks', []))}"
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택", default=False),
                        "id": st.column_config.TextColumn("id"),
                        "name": st.column_config.TextColumn("name"),
                        "platform": st.column_config.TextColumn("platform"),
                        "ad_format": st.column_config.TextColumn("ad_format"),
                        "package_name": st.column_config.TextColumn("package_name")
                    },
                    disabled=["id", "name", "platform", "ad_format", "package_name"],
                    key=editor_key
                )
                
                # Get selected rows and save IDs
                selected_rows = edited_df[edited_df["선택"] == True]
                # Always save current selection (will be used if rerun happens)
                if len(selected_rows) > 0:
                    st.session_state.selected_ad_unit_ids = selected_rows["id"].tolist()
                else:
                    # Only clear if user explicitly deselected everything (not after network removal)
                    if "network_removed" not in st.session_state:
                        st.session_state.selected_ad_unit_ids = []
                
                # Clear network_removed flag after processing
                if "network_removed" in st.session_state:
                    del st.session_state.network_removed
                
                if len(selected_rows) > 0:
                    st.markdown(f"**선택된 Ad Units: {len(selected_rows)}개**")
                    
                    # Initialize selected networks in session state (default: all networks)
                    if "selected_ad_networks" not in st.session_state:
                        st.session_state.selected_ad_networks = AD_NETWORKS.copy()
                    
                    # Show selected networks with remove buttons (compact format)
                    if st.session_state.selected_ad_networks:
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
                                            # Mark that network removal is happening (to preserve selection)
                                            st.session_state.network_removed = True
                                            # Remove network directly
                                            if network in st.session_state.selected_ad_networks:
                                                st.session_state.selected_ad_networks.remove(network)
                                            st.rerun()
                    
                    # Add button
                    if st.session_state.selected_ad_networks:
                        if st.button(f"➕ 선택한 {len(selected_rows)}개 Ad Units + {len(st.session_state.selected_ad_networks)}개 네트워크 추가", type="primary", use_container_width=True):
                            new_rows = []
                            for _, row in selected_rows.iterrows():
                                for selected_network in st.session_state.selected_ad_networks:
                                    # Create 6 rows for each selected unit (android/ios × REWARD/INTER/BANNER)
                                    platforms = ["android", "ios"]
                                    ad_formats = ["REWARD", "INTER", "BANNER"]
                                    
                                    for platform in platforms:
                                        for ad_format in ad_formats:
                                            # Only add if platform and ad_format match the selected unit
                                            if row["platform"].lower() == platform and row["ad_format"] == ad_format:
                                                new_rows.append({
                                                    "id": row["id"],
                                                    "name": row["name"],
                                                    "platform": platform,
                                                    "ad_format": ad_format,
                                                    "package_name": row["package_name"],
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
                                                })
                            
                            if new_rows:
                                new_df = pd.DataFrame(new_rows)
                                st.session_state.applovin_data = pd.concat([st.session_state.applovin_data, new_df], ignore_index=True)
                                st.success(f"✅ {len(new_rows)}개 행이 데이터 테이블에 추가되었습니다!")
                                # Clear selections
                                st.session_state.selected_ad_networks = []
                                st.rerun()
                            else:
                                st.warning("⚠️ 선택한 항목과 일치하는 platform/ad_format 조합이 없습니다.")
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

# Reorder columns if they exist
if len(st.session_state.applovin_data) > 0 or any(col in st.session_state.applovin_data.columns for col in column_order):
    existing_cols = [col for col in column_order if col in st.session_state.applovin_data.columns]
    missing_cols = [col for col in st.session_state.applovin_data.columns if col not in column_order]
    st.session_state.applovin_data = st.session_state.applovin_data[existing_cols + missing_cols]

# Sort data by ad_network, platform, ad_format
if len(st.session_state.applovin_data) > 0:
    if "ad_network" in st.session_state.applovin_data.columns:
        # Define sort order for ad_format
        ad_format_order = {"REWARD": 0, "INTER": 1, "BANNER": 2}
        platform_order = {"android": 0, "ios": 1}
        
        # Create temporary columns for sorting
        st.session_state.applovin_data["_sort_ad_format"] = st.session_state.applovin_data["ad_format"].map(ad_format_order).fillna(99)
        st.session_state.applovin_data["_sort_platform"] = st.session_state.applovin_data["platform"].map(platform_order).fillna(99)
        
        # Sort
        st.session_state.applovin_data = st.session_state.applovin_data.sort_values(
            by=["ad_network", "_sort_platform", "_sort_ad_format"],
            ascending=[True, True, True]
        ).reset_index(drop=True)
        
        # Remove temporary columns
        st.session_state.applovin_data = st.session_state.applovin_data.drop(columns=["_sort_ad_format", "_sort_platform"], errors="ignore")

# Data editor
edited_df = st.data_editor(
    st.session_state.applovin_data,
    num_rows="dynamic",
    use_container_width=True,
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

# Update session state
st.session_state.applovin_data = edited_df

st.divider()

# Validation and Submit
if len(edited_df) > 0:
    st.divider()
    
    if st.button("🚀 Update All Ad Units", type="primary", use_container_width=True):
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
