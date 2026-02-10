"""AdMob API implementation"""
from typing import Dict, List, Optional
import os
import json
import logging
import glob
import requests
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from .base_network_api import BaseNetworkAPI, _get_env_var

logger = logging.getLogger(__name__)

# OAuth scopes
ADMOB_SCOPES = [
    'https://www.googleapis.com/auth/admob.readonly',
    'https://www.googleapis.com/auth/admob.monetization',
    'https://www.googleapis.com/auth/admob.googlebidding.readwrite',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
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
        1. Streamlit secrets (웹 환경 우선)
        2. session_state에 저장된 토큰 (웹 환경)
        3. 파일에 저장된 토큰 (로컬 환경)
        4. 새로 OAuth 인증 (첫 실행 또는 토큰 만료)
        """
        session_key = "admob_credentials"
        creds = None
        
        # 1. Streamlit secrets에서 토큰 먼저 확인 (웹 환경 우선)
        if hasattr(st, 'secrets'):
            try:
                # 여러 방법으로 Streamlit secrets 접근 시도
                token_json_str = None
                if hasattr(st.secrets, 'get'):
                    token_json_str = st.secrets.get('ADMOB_TOKEN_JSON')
                elif hasattr(st.secrets, 'ADMOB_TOKEN_JSON'):
                    token_json_str = getattr(st.secrets, 'ADMOB_TOKEN_JSON', None)
                elif 'ADMOB_TOKEN_JSON' in st.secrets:
                    token_json_str = st.secrets['ADMOB_TOKEN_JSON']
                
                if token_json_str:
                    logger.info("[AdMob] Found ADMOB_TOKEN_JSON in Streamlit secrets")
                    if isinstance(token_json_str, str):
                        try:
                            token_data = json.loads(token_json_str)
                        except json.JSONDecodeError as e:
                            logger.error(f"[AdMob] Failed to parse ADMOB_TOKEN_JSON as JSON: {e}")
                            logger.error(f"[AdMob] Token JSON string (first 100 chars): {token_json_str[:100]}")
                            token_data = None
                    else:
                        token_data = token_json_str
                    
                    if token_data:
                        try:
                            creds = Credentials.from_authorized_user_info(token_data, ADMOB_SCOPES)
                            logger.info("[AdMob] Created credentials from Streamlit secrets")
                            
                            # 토큰이 만료되었으면 refresh
                            if creds.expired and creds.refresh_token:
                                try:
                                    logger.info("[AdMob] Refreshing expired token from Streamlit secrets...")
                                    creds.refresh(Request())
                                    logger.info("[AdMob] Token refreshed successfully")
                                    
                                    # 갱신된 토큰을 session_state에 저장
                                    if hasattr(st, 'session_state'):
                                        st.session_state[session_key] = json.loads(creds.to_json())
                                except Exception as e:
                                    error_str = str(e)
                                    logger.error(f"[AdMob] Failed to refresh token from Streamlit secrets: {e}")
                                    import traceback
                                    logger.error(traceback.format_exc())
                                    
                                    # Scope 불일치 감지
                                    if "invalid_scope" in error_str.lower() or "bad request" in error_str.lower():
                                        logger.error("[AdMob] ⚠️ Scope 불일치 감지: 토큰이 이전 scope로 생성되어 있습니다.")
                                        logger.error("[AdMob] 새로운 scope로 토큰을 재생성해야 합니다.")
                                        logger.error("[AdMob] 로컬에서 'python regenerate_admob_token.py' 실행 후 Streamlit Secrets 업데이트 필요")
                                    creds = None
                            
                            if creds and creds.valid:
                                # session_state에 저장
                                if hasattr(st, 'session_state'):
                                    st.session_state[session_key] = json.loads(creds.to_json())
                                logger.info("[AdMob] ✅ Successfully loaded credentials from Streamlit secrets")
                                self._credentials = creds
                                return creds
                            else:
                                logger.warning(f"[AdMob] Credentials from Streamlit secrets are not valid. expired={creds.expired if creds else 'N/A'}, valid={creds.valid if creds else 'N/A'}")
                        except Exception as e:
                            logger.error(f"[AdMob] Failed to create credentials from Streamlit secrets: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                else:
                    logger.debug("[AdMob] ADMOB_TOKEN_JSON not found in Streamlit secrets")
            except Exception as e:
                logger.error(f"[AdMob] Failed to load from Streamlit secrets: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # 2. session_state에서 토큰 확인 (웹 환경)
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
        
        # 3. 파일에서 토큰 로드 (로컬 환경)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        token_file = os.path.join(base_dir, 'admob_token.json')
        token_file = os.path.abspath(token_file)
        
        if os.path.exists(token_file):
            try:
                creds = Credentials.from_authorized_user_file(token_file, ADMOB_SCOPES)
                logger.info(f"[AdMob] Loaded credentials from {token_file}")
                
                # session_state에도 저장 (웹 환경에서 사용)
                if hasattr(st, 'session_state'):
                    st.session_state[session_key] = json.loads(creds.to_json())
            except Exception as e:
                logger.warning(f"[AdMob] Failed to load token from file: {e}")
                creds = None
        
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
        
        # 4. 모든 방법 실패 - OAuth flow 시작
        if not creds:
            # Streamlit 환경인지 확인 (실제로 실행 중인지 체크)
            is_streamlit_running = False
            try:
                # Streamlit이 실제로 실행 중인지 확인
                from streamlit.runtime.scriptrunner import get_script_run_ctx
                ctx = get_script_run_ctx()
                is_streamlit_running = ctx is not None
            except:
                # Streamlit이 설치되지 않았거나 실행 중이 아님
                is_streamlit_running = False
            
            # Streamlit 환경: 불량 토큰 정리 후 재인증 안내
            if is_streamlit_running:
                # 불량 토큰 파일/세션 자동 정리
                if os.path.exists(token_file):
                    try:
                        os.remove(token_file)
                        logger.info(f"[AdMob] Removed stale token file: {token_file}")
                    except Exception:
                        pass
                if hasattr(st, 'session_state') and session_key in st.session_state:
                    del st.session_state[session_key]
                raise ValueError(
                    "AdMob 인증이 필요합니다. 홈페이지에서 Google 로그인을 해주세요."
                )
            
            # 로컬 환경: OAuth flow 시작
            client_secrets_file = self._find_client_secrets_file()
            if not client_secrets_file:
                raise ValueError(
                    "AdMob OAuth client configuration not found. Options:\n"
                    "1. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file\n"
                    "2. Add client_secrets.json to the project root\n"
                    "   (Download from Google Cloud Console > APIs & Services > Credentials)\n"
                    "3. Run 'python regenerate_admob_token.py' to generate admob_token.json"
                )
            
            logger.info(f"[AdMob] Starting OAuth flow with {client_secrets_file}")
            logger.info("[AdMob] Browser will open for authentication. Please authorize the app.")
            print("[AdMob] 🌐 브라우저가 열립니다. Google 계정으로 로그인하고 권한을 승인하세요.")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, ADMOB_SCOPES
            )
            creds = flow.run_local_server(port=0)
            
            # Save token to file
            try:
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"[AdMob] Token saved to {token_file}")
                print(f"[AdMob] ✅ 토큰이 저장되었습니다: {token_file}")
            except Exception as e:
                logger.warning(f"[AdMob] Failed to save token: {e}")
                print(f"[AdMob] ⚠️  토큰 저장 실패: {e}")
        
        self._credentials = creds
        return creds
    
    def _build_web_client_config(self):
        """Build OAuth client config for web-based flow"""
        client_id = _get_env_var("GOOGLE_CLIENT_ID")
        client_secret = _get_env_var("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            return None, None
        redirect_uri = _get_env_var("GOOGLE_REDIRECT_URI") or "http://localhost:8501"
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        return client_config, redirect_uri

    def _get_auth_url(self):
        """Generate OAuth authorization URL for Streamlit environment"""
        client_config, redirect_uri = self._build_web_client_config()
        if not client_config:
            return None
        try:
            flow = Flow.from_client_config(
                client_config, ADMOB_SCOPES, redirect_uri=redirect_uri
            )
            auth_url, state = flow.authorization_url(
                access_type='offline',
                prompt='consent'
            )
            st.session_state['admob_oauth_state'] = state
            return auth_url
        except Exception as e:
            logger.error(f"[AdMob] Failed to generate auth URL: {e}")
            return None

    def _exchange_auth_code(self, code: str):
        """Exchange OAuth authorization code for credentials"""
        import os
        # Allow scope changes (Google may reorder or modify returned scopes)
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        client_config, redirect_uri = self._build_web_client_config()
        if not client_config:
            raise ValueError("GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET not configured")
        flow = Flow.from_client_config(
            client_config, ADMOB_SCOPES, redirect_uri=redirect_uri
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        logger.info("[AdMob] Successfully exchanged auth code for credentials")
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
        
        # 2. Construct from GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET env vars
        client_id = _get_env_var("GOOGLE_CLIENT_ID")
        client_secret = _get_env_var("GOOGLE_CLIENT_SECRET")

        if client_id and client_secret:
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"]
                }
            }
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', delete=False
            )
            json.dump(client_config, temp_file)
            temp_file.close()
            logger.info("[AdMob] Constructed client secrets from GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET env vars")
            return temp_file.name

        # 3. 파일 시스템에서 찾기
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
                    display_name = (
                        manual_info.get('displayName')
                        or linked_info.get('displayName')
                        or linked_info.get('appStoreId')
                        or app.get('name', 'Unknown')
                    )
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
        Note: v1 API does not support app creation, must use v1beta REST API
        """
        try:
            creds = self._get_credentials()
            account_id = self._get_account_id()

            # Ensure token is valid
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())

            access_token = creds.token
            api_url = f"https://admob.googleapis.com/v1beta/{account_id}/apps"

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            logger.info(f"[AdMob] Creating app in account: {account_id}")
            logger.info(f"[AdMob] Request URL: {api_url}")
            logger.info(f"[AdMob] Request payload: {json.dumps(payload, indent=2)}")

            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            response_data = response.json()
            logger.info(f"[AdMob] App created successfully: {json.dumps(response_data, indent=2)}")

            return {
                "status": 0,
                "code": 0,
                "msg": "Success",
                "result": response_data
            }
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            logger.error(f"[AdMob] Create app HTTP error: {error_msg}")

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
            logger.error(f"[AdMob] Create app error: {error_msg}")

            return {
                "status": 1,
                "code": "ERROR",
                "msg": error_msg,
                "result": None
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

