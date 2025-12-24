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

# Check API Key
api_key = get_applovin_api_key()
if not api_key:
    st.error("❌ APPLOVIN_API_KEY가 환경변수에 설정되지 않았습니다.")
    st.info("`.env` 파일에 `APPLOVIN_API_KEY=your_api_key`를 추가해주세요.")
    st.stop()

st.success(f"✅ AppLovin API Key가 설정되어 있습니다.")

# Simple API Test Section
with st.expander("📡 AppLovin Ad Units 조회", expanded=False):
    if st.button("📡 Get Ad Units", type="primary"):
        with st.spinner("API 호출 중..."):
            success, result = get_ad_units(api_key)
            
            if success:
                st.success("✅ API 호출 성공!")
                data = result.get("data", {})
                
                # Handle different response formats
                ad_units_list = []
                if isinstance(data, list):
                    ad_units_list = data
                elif isinstance(data, dict):
                    ad_units_list = data.get("ad_units", data.get("data", data.get("list", data.get("results", []))))
                
                if ad_units_list:
                    st.info(f"📊 총 {len(ad_units_list)}개의 Ad Unit이 조회되었습니다.")
                    
                    # Display as table
                    table_data = []
                    for unit in ad_units_list:
                        table_data.append({
                            "id": unit.get("id", ""),
                            "name": unit.get("name", ""),
                            "platform": unit.get("platform", ""),
                            "ad_format": unit.get("ad_format", ""),
                            "package_name": unit.get("package_name", "")
                        })
                    
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.json(data)
            else:
                st.error("❌ API 호출 실패")
                error_info = result.get("data", {})
                st.json(error_info)
                if "status_code" in result:
                    st.error(f"Status Code: {result['status_code']}")

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
    "MOLOCO_BIDDING",
    "TIKTOK_BIDDING",
    "UNITY_BIDDING",
    "VUNGLE_BIDDING",
    "YANDEX_BIDDING",
    "PUBMATIC_BIDDING"
]

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

# Instructions
with st.expander("📖 사용 방법", expanded=False):
    st.markdown("""
    **CSV 형식으로 데이터를 입력하세요:**
    - **id**: Ad Unit ID* (같은 id를 가진 행들은 같은 Ad Unit에 여러 네트워크 설정)
    - **name**: Ad Unit Name (선택사항)
    - **platform**: android 또는 ios*
    - **ad_format**: BANNER, INTER (Interstitial), 또는 REWARD*
    - **package_name**: 앱 패키지명 (선택사항)
    - **ad_network**: 네트워크 이름* (예: GOOGLE_AD_MANAGER_NETWORK, ironsource 등)
    - **ad_network_app_id**: Ad Network App ID (선택사항)
    - **ad_network_app_key**: Ad Network App Key (선택사항)
    - **ad_unit_id**: Ad Network의 Ad Unit ID*
    - **countries_type**: INCLUDE 또는 EXCLUDE (공란 가능)
    - **countries**: 국가 코드 (쉼표로 구분, 예: "us,kr", 공란 가능)
    - **cpm**: CPM 값* (기본값: 0)
    - **segment_name**: Segment Name (공란 가능)
    - **segment_id**: Segment ID (비워두면 "None", 공란 가능)
    - **disabled**: FALSE 또는 TRUE (기본값: FALSE)
    
    **예시:**
    - 같은 id를 가진 여러 행 = 하나의 Ad Unit에 여러 Ad Network 설정
    """)

# Get already added networks
added_networks = set()
if len(st.session_state.applovin_data) > 0 and "ad_network" in st.session_state.applovin_data.columns:
    added_networks = set(st.session_state.applovin_data["ad_network"].dropna().unique())
    added_networks.discard("")  # Remove empty strings

# Available networks (exclude already added ones)
available_networks = [net for net in AD_NETWORKS if net not in added_networks]

# Split into two columns: Left for input, Right for added networks
left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("📝 데이터 입력")
    
    if available_networks:
        selected_networks = st.multiselect(
            "Ad Network 선택 (여러 개 선택 가능)",
            options=available_networks,
            help="네트워크를 선택하고 'Add Networks' 버튼을 클릭하면 각 네트워크마다 6개 행이 자동으로 추가됩니다"
        )
    else:
        selected_networks = []
        st.multiselect(
            "Ad Network 선택",
            options=["모든 네트워크가 추가되었습니다"],
            disabled=True,
            help="모든 네트워크가 이미 추가되었습니다"
        )
    
    if st.button("➕ Add Networks", type="primary", use_container_width=True, disabled=not available_networks or len(selected_networks) == 0):
        if not selected_networks:
            st.error("❌ 네트워크를 선택해주세요.")
        else:
            platforms = ["android", "ios"]
            ad_formats = ["REWARD", "INTER", "BANNER"]
            
            new_rows = []
            for selected_network in selected_networks:
                if selected_network in added_networks:
                    st.warning(f"⚠️ {selected_network}는 이미 추가된 네트워크입니다. 건너뜁니다.")
                    continue
                
                for platform in platforms:
                    for ad_format in ad_formats:
                        new_rows.append({
                            "id": "",
                            "name": "",
                            "platform": platform,
                            "ad_format": ad_format,
                            "package_name": "",
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
                st.success(f"✅ {len(selected_networks)}개 네트워크의 {len(new_rows)}개 행이 추가되었습니다!")
                st.rerun()
            else:
                st.error("❌ 추가할 네트워크가 없습니다.")
    
    if len(st.session_state.applovin_data) == 0:
        st.info("💡 네트워크를 선택하고 'Add Network' 버튼을 클릭하여 시작하세요.")

with right_col:
    st.subheader("📋 추가된 네트워크")
    
    if added_networks:
        # Show added networks in a more compact format
        for network in sorted(added_networks):
            network_rows = len(st.session_state.applovin_data[st.session_state.applovin_data["ad_network"] == network])
            col_name, col_delete = st.columns([4, 1])
            with col_name:
                st.markdown(f"**{network}** <span style='color: gray; font-size: 0.8em'>({network_rows}행)</span>", unsafe_allow_html=True)
            with col_delete:
                if st.button("🗑️", key=f"delete_{network}", help="삭제"):
                    st.session_state.applovin_data = st.session_state.applovin_data[
                        st.session_state.applovin_data["ad_network"] != network
                    ].reset_index(drop=True)
                    st.success(f"✅ {network} 네트워크가 삭제되었습니다.")
                    st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)  # Small spacing
        
        # Reset button
        if st.button("🔄 전체 리셋", type="secondary", use_container_width=True):
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
            st.success("✅ 모든 데이터가 리셋되었습니다.")
            st.rerun()
    else:
        st.info("추가된 네트워크가 없습니다.")

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
