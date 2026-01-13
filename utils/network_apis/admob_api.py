"""AdMob API implementation"""
from typing import Dict, List, Optional
import os
import json
import logging
import glob
import requests
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from .base_network_api import BaseNetworkAPI, _get_env_var

logger = logging.getLogger(__name__)

# OAuth scopes
ADMOB_SCOPES = [
    'https://www.googleapis.com/auth/admob.monetization',
    'https://www.googleapis.com/auth/admob.googlebidding.readwrite'
]


class AdMobAPI(BaseNetworkAPI):
    """AdMob API implementation"""
    
    def __init__(self):
        super().__init__("AdMob")
        self._credentials = None
        self._account_id = None
    
    def _get_credentials(self):
        """Get OAuth credentials
        
        우선순위:
        1. session_state에 저장된 토큰 (웹 환경)
        2. 파일에 저장된 토큰 (로컬 환경)
        3. 새로 OAuth 인증 (첫 실행 또는 토큰 만료)
        """
        # 1. session_state에서 토큰 확인 (웹 환경)
        session_key = "admob_credentials"
        if hasattr(st, 'session_state') and session_key in st.session_state:
            try:
                creds_data = st.session_state[session_key]
                if isinstance(creds_data, str):
                    creds_data = json.loads(creds_data)
                creds = Credentials.from_authorized_user_info(creds_data, ADMOB_SCOPES)
                
                # 토큰이 만료되었으면 refresh
                if creds.expired and creds.refresh_token:
                    try:
                        logger.info("[AdMob] Refreshing expired token from session_state...")
                        creds.refresh(Request())
                        # 갱신된 토큰을 다시 저장
                        st.session_state[session_key] = json.loads(creds.to_json())
                        logger.info("[AdMob] Token refreshed successfully")
                    except Exception as e:
                        logger.warning(f"[AdMob] Failed to refresh token: {e}")
                        creds = None
                
                if creds and creds.valid:
                    self._credentials = creds
                    return creds
            except Exception as e:
                logger.warning(f"[AdMob] Failed to load credentials from session_state: {e}")
        
        # 2. 파일에서 토큰 로드 (로컬 환경)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        token_file = os.path.join(base_dir, 'admob_token.json')
        token_file = os.path.abspath(token_file)
        
        creds = None
        if os.path.exists(token_file):
            try:
                creds = Credentials.from_authorized_user_file(token_file, ADMOB_SCOPES)
                logger.info(f"[AdMob] Loaded credentials from {token_file}")
                
                # session_state에도 저장 (웹 환경에서 사용)
                if hasattr(st, 'session_state'):
                    st.session_state[session_key] = json.loads(creds.to_json())
            except Exception as e:
                logger.warning(f"[AdMob] Failed to load token from file: {e}")
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("[AdMob] Refreshing expired token...")
                creds.refresh(Request())
                logger.info("[AdMob] Token refreshed successfully")
                
                # 갱신된 토큰 저장
                try:
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.warning(f"[AdMob] Failed to save refreshed token: {e}")
                
                # session_state에도 저장
                if hasattr(st, 'session_state'):
                    st.session_state[session_key] = json.loads(creds.to_json())
            except Exception as e:
                logger.warning(f"[AdMob] Failed to refresh token: {e}")
                creds = None
        
        # 3. 새로 OAuth 인증 필요
        if not creds:
            # 웹 환경에서는 에러 메시지 표시
            if hasattr(st, 'session_state'):
                st.error("⚠️ AdMob 인증이 필요합니다. 아래 안내를 따라주세요.")
                st.info("""
                **로컬 환경에서 인증하는 방법:**
                1. 로컬에서 스크립트를 실행하여 OAuth 인증을 완료하세요
                2. 생성된 `admob_token.json` 파일의 내용을 복사하세요
                3. Streamlit Secrets에 `ADMOB_TOKEN_JSON` 키로 저장하세요
                
                **또는 Streamlit Secrets에 직접 저장:**
                - `client_secrets.json` 내용을 `ADMOB_CLIENT_SECRETS`에 저장
                - `admob_token.json` 내용을 `ADMOB_TOKEN_JSON`에 저장
                """)
                
                # Streamlit secrets에서 토큰 확인
                try:
                    if hasattr(st.secrets, 'get') and st.secrets.get('ADMOB_TOKEN_JSON'):
                        token_json_str = st.secrets.get('ADMOB_TOKEN_JSON')
                        if isinstance(token_json_str, str):
                            token_data = json.loads(token_json_str)
                        else:
                            token_data = token_json_str
                        creds = Credentials.from_authorized_user_info(token_data, ADMOB_SCOPES)
                        
                        # session_state에 저장
                        st.session_state[session_key] = json.loads(creds.to_json())
                        logger.info("[AdMob] Loaded credentials from Streamlit secrets")
                    else:
                        raise ValueError("No credentials found")
                except Exception as e:
                    logger.warning(f"[AdMob] Failed to load from Streamlit secrets: {e}")
                    raise ValueError(
                        "AdMob 인증이 필요합니다.\n\n"
                        "**방법 1 (로컬 인증):**\n"
                        "1. 로컬에서 `python -c \"from utils.network_apis.admob_api import AdMobAPI; api = AdMobAPI(); api._get_credentials()\"` 실행\n"
                        "2. 생성된 `admob_token.json` 파일 내용을 Streamlit Secrets의 `ADMOB_TOKEN_JSON`에 저장\n\n"
                        "**방법 2 (수동 저장):**\n"
                        "Streamlit Secrets에 `ADMOB_TOKEN_JSON` 키로 토큰 JSON을 저장하세요."
                    )
            else:
                # 로컬 환경: OAuth flow 시작
                client_secrets_file = self._find_client_secrets_file()
                if not client_secrets_file:
                    raise ValueError(
                        "Client secrets file not found. Please add client_secrets.json or client_secret.json to project root.\n"
                        "You can download it from Google Cloud Console > APIs & Services > Credentials > OAuth 2.0 Client ID"
                    )
                
                logger.info(f"[AdMob] Starting OAuth flow with {client_secrets_file}")
                logger.info("[AdMob] Browser will open for authentication. Please authorize the app.")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, ADMOB_SCOPES
                )
                creds = flow.run_local_server(port=0)
                
                # Save token to file
                try:
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
                    logger.info(f"[AdMob] Token saved to {token_file}")
                except Exception as e:
                    logger.warning(f"[AdMob] Failed to save token: {e}")
        
        self._credentials = creds
        return creds
    
    def _find_client_secrets_file(self):
        """Find client secrets file
        
        우선순위:
        1. Streamlit secrets에서 ADMOB_CLIENT_SECRETS
        2. 프로젝트 루트의 client_secrets.json 또는 client_secret.json
        """
        # 1. Streamlit secrets에서 확인
        if hasattr(st, 'secrets'):
            try:
                if hasattr(st.secrets, 'get') and st.secrets.get('ADMOB_CLIENT_SECRETS'):
                    client_secrets_data = st.secrets.get('ADMOB_CLIENT_SECRETS')
                    # 임시 파일로 저장
                    import tempfile
                    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                    if isinstance(client_secrets_data, str):
                        temp_file.write(client_secrets_data)
                    else:
                        json.dump(client_secrets_data, temp_file)
                    temp_file.close()
                    logger.info("[AdMob] Using client secrets from Streamlit secrets")
                    return temp_file.name
            except Exception as e:
                logger.debug(f"[AdMob] Failed to get client secrets from Streamlit secrets: {e}")
        
        # 2. 파일 시스템에서 찾기
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        possible_files = [
            os.path.join(base_dir, 'client_secrets.json'),
            os.path.join(base_dir, 'client_secret.json'),
        ]
        
        # Also search for client_secret*.json files
        client_secret_pattern = os.path.join(base_dir, 'client_secret*.json')
        glob_files = glob.glob(client_secret_pattern)
        if glob_files:
            possible_files.extend(glob_files)
        
        for file_path in possible_files:
            if os.path.exists(file_path):
                return os.path.abspath(file_path)
        return None
    
    def _get_account_id(self):
        """Get AdMob account ID"""
        if self._account_id:
            return self._account_id
        
        account_id = _get_env_var("ADMOB_ACCOUNT_ID")
        if account_id:
            if account_id.startswith('pub-'):
                self._account_id = f"accounts/{account_id}"
            elif account_id.startswith('accounts/'):
                self._account_id = account_id
            else:
                self._account_id = f"accounts/{account_id}"
            logger.info(f"[AdMob] Using account ID from env: {self._account_id}")
            return self._account_id
        
        # Try to get from API
        try:
            creds = self._get_credentials()
            service = build('admob', 'v1', credentials=creds)
            logger.info("[AdMob] Fetching account list from API...")
            accounts_response = service.accounts().list().execute()
            accounts = accounts_response.get('account', [])
            
            if accounts:
                self._account_id = accounts[0]['name']
                logger.info(f"[AdMob] Found account ID from API: {self._account_id}")
                return self._account_id
        except Exception as e:
            logger.warning(f"[AdMob] Failed to get account from API: {e}")
        
        raise ValueError(
            "AdMob Account ID not found. Please set ADMOB_ACCOUNT_ID in .env file.\n"
            "Format: pub-1234567890123456 or accounts/pub-1234567890123456"
        )
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get applications list
        
        Args:
            app_key: Optional app ID to filter by (not used in AdMob, kept for compatibility)
        """
        try:
            creds = self._get_credentials()
            service = build('admob', 'v1', credentials=creds)
            account_id = self._get_account_id()
            
            logger.info(f"[AdMob] Fetching apps for account: {account_id}")
            
            all_apps = []
            next_page_token = None
            page_count = 0
            
            while True:
                page_count += 1
                request_params = {
                    'parent': account_id,
                    'pageSize': 100
                }
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                response = service.accounts().apps().list(**request_params).execute()
                apps_list = response.get('apps', [])
                
                # Format apps: replace 'name' field with displayName from manualAppInfo or linkedAppInfo
                formatted_apps = []
                for app in apps_list:
                    formatted_app = app.copy()
                    # Use manualAppInfo.displayName if available, otherwise linkedAppInfo.displayName
                    manual_info = app.get('manualAppInfo', {})
                    linked_info = app.get('linkedAppInfo', {})
                    display_name = manual_info.get('displayName') or linked_info.get('displayName') or app.get('name', 'Unknown')
                    formatted_app['name'] = display_name
                    formatted_apps.append(formatted_app)
                
                all_apps.extend(formatted_apps)
                
                logger.info(f"[AdMob] Page {page_count}: {len(apps_list)} apps (total: {len(all_apps)})")
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            logger.info(f"[AdMob] Total apps retrieved: {len(all_apps)}")
            return all_apps
        except Exception as e:
            logger.error(f"[AdMob] Error getting apps: {e}")
            raise
    
    def get_ad_units(self, app_code: str) -> List[Dict]:
        """Get ad units list for an app
        
        Args:
            app_code: App ID (e.g., "ca-app-pub-1234567890123456~1234567890")
        """
        try:
            creds = self._get_credentials()
            service = build('admob', 'v1', credentials=creds)
            account_id = self._get_account_id()
            
            logger.info(f"[AdMob] Fetching ad units for app: {app_code}")
            
            all_units = []
            next_page_token = None
            page_count = 0
            
            while True:
                page_count += 1
                request_params = {
                    'parent': account_id,
                    'pageSize': 100
                }
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                response = service.accounts().adUnits().list(**request_params).execute()
                units_list = response.get('adUnits', [])
                
                # Filter by app_id if provided
                if app_code:
                    units_list = [u for u in units_list if u.get('appId') == app_code]
                
                all_units.extend(units_list)
                
                logger.info(f"[AdMob] Page {page_count}: {len(units_list)} units (total: {len(all_units)})")
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            logger.info(f"[AdMob] Total ad units retrieved: {len(all_units)}")
            return all_units
        except Exception as e:
            logger.error(f"[AdMob] Error getting ad units: {e}")
            raise
    
    def get_google_bidding_ad_units(self) -> List[Dict]:
        """Get Google Bidding ad units list
        
        API: GET https://admob.googleapis.com/v1alpha/{accountId}/googleBiddingAdUnits
        """
        try:
            creds = self._get_credentials()
            account_id = self._get_account_id()
            
            # v1alpha API는 googleapiclient에서 직접 지원하지 않으므로 REST API 사용
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            
            access_token = creds.token
            api_url = f"https://admob.googleapis.com/v1alpha/{account_id}/googleBiddingAdUnits"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"[AdMob] Fetching Google Bidding ad units from: {api_url}")
            
            all_units = []
            next_page_token = None
            page_count = 0
            
            while True:
                page_count += 1
                params = {}
                if next_page_token:
                    params['pageToken'] = next_page_token
                
                response = requests.get(api_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                units_list = data.get('googleBiddingAdUnits', [])
                all_units.extend(units_list)
                
                logger.info(f"[AdMob] Page {page_count}: {len(units_list)} Google Bidding units (total: {len(all_units)})")
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
            
            logger.info(f"[AdMob] Total Google Bidding ad units retrieved: {len(all_units)}")
            return all_units
        except Exception as e:
            logger.error(f"[AdMob] Error getting Google Bidding ad units: {e}")
            raise
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via AdMob API
        
        API: POST https://admob.googleapis.com/v1beta/{parent=accounts/*}/apps
        """
        try:
            creds = self._get_credentials()
            service = build('admob', 'v1', credentials=creds)
            account_id = self._get_account_id()
            
            logger.info(f"[AdMob] Creating app in account: {account_id}")
            logger.info(f"[AdMob] Request payload: {json.dumps(payload, indent=2)}")
            
            response = service.accounts().apps().create(
                parent=account_id,
                body=payload
            ).execute()
            
            logger.info(f"[AdMob] App created successfully: {json.dumps(response, indent=2)}")
            
            return {
                "status": 0,
                "code": 0,
                "msg": "Success",
                "result": response
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AdMob] Create app error: {error_msg}")
            
            # Parse error details if available
            error_details = {}
            if hasattr(e, 'content'):
                try:
                    error_details = json.loads(e.content)
                except:
                    pass
            
            return {
                "status": 1,
                "code": "ERROR",
                "msg": error_msg,
                "result": error_details if error_details else None
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create Google Bidding Ad Unit via AdMob API
        
        API: POST https://admob.googleapis.com/v1alpha/accounts/{accountId}/googleBiddingAdUnits:batchCreate
        
        Args:
            payload: Google Bidding Ad Unit payload (displayName, format, appId or appStoreId)
            app_key: App ID (optional, can be used as appId if not in payload)
        """
        try:
            creds = self._get_credentials()
            account_id = self._get_account_id()
            
            # If app_key is provided and appId is not in payload, use app_key as appId
            if not payload.get('appId') and not payload.get('appStoreId') and app_key:
                payload['appId'] = app_key
            
            # Validate that at least one of appId or appStoreId is provided
            if not payload.get('appId') and not payload.get('appStoreId'):
                return {
                    "status": 1,
                    "code": "MISSING_APP_ID",
                    "msg": "Either appId or appStoreId is required in payload",
                    "result": None
                }
            
            # v1alpha API는 googleapiclient에서 직접 지원하지 않으므로 REST API 사용
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            
            access_token = creds.token
            api_url = f"https://admob.googleapis.com/v1alpha/{account_id}/googleBiddingAdUnits:batchCreate"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Build request body according to API documentation
            # Format: {"requests": [{"googleBiddingAdUnit": {...}}]}
            request_body = {
                "requests": [
                    {
                        "googleBiddingAdUnit": payload
                    }
                ]
            }
            
            logger.info(f"[AdMob] Creating Google Bidding ad unit")
            logger.info(f"[AdMob] Request URL: {api_url}")
            logger.info(f"[AdMob] Request payload: {json.dumps(request_body, indent=2)}")
            
            response = requests.post(api_url, headers=headers, json=request_body, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()
            logger.info(f"[AdMob] Google Bidding ad unit created successfully: {json.dumps(response_data, indent=2)}")
            
            # Extract the created unit from response
            # Response format: {"googleBiddingAdUnits": [...]}
            created_units = response_data.get('googleBiddingAdUnits', [])
            result_data = created_units[0] if created_units else response_data
            
            return {
                "status": 0,
                "code": 0,
                "msg": "Success",
                "result": result_data
            }
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            logger.error(f"[AdMob] Create Google Bidding ad unit HTTP error: {error_msg}")
            
            # Try to parse error response
            error_details = {}
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    logger.error(f"[AdMob] Error response: {json.dumps(error_details, indent=2)}")
                except:
                    error_details = {"text": e.response.text}
            
            return {
                "status": 1,
                "code": "HTTP_ERROR",
                "msg": error_msg,
                "result": error_details if error_details else None
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AdMob] Create Google Bidding ad unit error: {error_msg}")
            
            return {
                "status": 1,
                "code": "ERROR",
                "msg": error_msg,
                "result": None
            }

