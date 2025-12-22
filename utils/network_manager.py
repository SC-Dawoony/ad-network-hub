"""Network manager wrapper for API calls"""
from typing import Dict, List, Optional
import streamlit as st
import os
import requests
import time
import random
import hashlib
import json
import logging
import base64
from dotenv import load_dotenv


def _get_env_var(key: str) -> Optional[str]:
    """
    Get environment variable from Streamlit secrets (if available) or .env file
    
    Args:
        key: Environment variable key
        
    Returns:
        Environment variable value or None
    """
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        if hasattr(st, 'secrets') and st.secrets:
            # Log available secrets keys for debugging
            try:
                if hasattr(st.secrets, 'keys'):
                    available_keys = list(st.secrets.keys())
                    logger.info(f"[Env] Available Streamlit secrets keys: {available_keys}")
                elif isinstance(st.secrets, dict):
                    available_keys = list(st.secrets.keys())
                    logger.info(f"[Env] Available Streamlit secrets keys: {available_keys}")
            except Exception as e:
                logger.warning(f"[Env] Could not list secrets keys: {str(e)}")
            
            # Try direct access first
            try:
                if key in st.secrets:
                    value = st.secrets[key]
                    logger.info(f"[Env] Found {key} in Streamlit secrets (length: {len(str(value)) if value else 0})")
                    return str(value) if value is not None else None
            except (KeyError, AttributeError, TypeError) as e:
                logger.debug(f"[Env] Direct access failed for {key}: {str(e)}")
            
            # Try using .get() method if available
            try:
                if hasattr(st.secrets, 'get'):
                    value = st.secrets.get(key)
                    if value is not None:
                        logger.info(f"[Env] Found {key} in Streamlit secrets via .get() (length: {len(str(value))})")
                        return str(value)
            except Exception as e:
                logger.debug(f"[Env] .get() method failed for {key}: {str(e)}")
            
            # Try nested access (e.g., st.secrets["ironsource"]["SECRET_KEY"])
            try:
                if isinstance(st.secrets, dict):
                    for top_level_key in st.secrets.keys():
                        try:
                            nested_dict = st.secrets[top_level_key]
                            if isinstance(nested_dict, dict) and key in nested_dict:
                                value = nested_dict[key]
                                logger.info(f"[Env] Found {key} in Streamlit secrets[{top_level_key}] (length: {len(str(value)) if value else 0})")
                                return str(value) if value is not None else None
                        except (KeyError, AttributeError, TypeError):
                            continue
            except Exception as e:
                logger.debug(f"[Env] Nested access failed for {key}: {str(e)}")
            
            logger.warning(f"[Env] {key} not found in Streamlit secrets")
    except Exception as e:
        logger.warning(f"[Env] Error accessing Streamlit secrets: {str(e)}")
    
    # Fallback to environment variables (from .env file or system env)
    env_value = os.getenv(key)
    if env_value:
        logger.info(f"[Env] Found {key} in environment variables (length: {len(env_value)})")
    else:
        logger.warning(f"[Env] {key} not found in environment variables")
    return env_value

# Load environment variables (override to get latest values)
# Streamlit Cloud에서는 st.secrets 사용, 로컬에서는 .env 파일 사용
try:
    import streamlit as st
    # Streamlit Cloud 환경에서는 secrets가 자동으로 로드됨
    # 로컬에서는 .env 파일 로드
    if not hasattr(st, 'secrets') or not st.secrets:
        load_dotenv(override=True)
except:
    # Streamlit이 없는 환경 (예: 테스트)
    load_dotenv(override=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _mask_sensitive_data(data: Dict) -> Dict:
    """Mask sensitive data in request/response for logging"""
    masked = data.copy()
    sensitive_keys = ['security_key', 'sign', 'token', 'authorization', 'bearer_token', 
                     'refresh_token', 'secret_key', 'api_key', 'password']
    
    for key in sensitive_keys:
        if key in masked:
            masked[key] = "***MASKED***"
    
    # Also mask keys that contain these words
    for key in list(masked.keys()):
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in ['token', 'key', 'secret', 'password', 'sign']):
            if not isinstance(masked[key], (int, float)):
                masked[key] = "***MASKED***"
    
    return masked

# Note: This is a placeholder for the actual AdNetworkManager
# In a real implementation, this would import from BE/services/ad_network_manager.py
# For now, we'll create a mock implementation for demonstration


class MockNetworkManager:
    """Mock network manager for demonstration purposes"""
    
    def __init__(self):
        self.clients = {}
    
    def get_client(self, network: str):
        """Get API client for a network"""
        return self.clients.get(network)
    
    def create_app(self, network: str, payload: Dict) -> Dict:
        """Create app via network API"""
        if network == "ironsource":
            return self._create_ironsource_app(payload)
        elif network == "pangle":
            return self._create_pangle_app(payload)
        elif network == "bigoads":
            return self._create_bigoads_app(payload)
        elif network == "mintegral":
            return self._create_mintegral_app(payload)
        
        # Mock implementation for other networks
        logger.info(f"[{network.title()}] API Request: Create App (Mock)")
        logger.info(f"[{network.title()}] Request Payload: {json.dumps(_mask_sensitive_data(payload), indent=2)}")
        
        mock_response = {
            "status": 0,
            "code": 0,
            "msg": "Success",
            "result": {
                "appCode": "10*****7",
                "name": payload.get("name", "Test App")
            }
        }
        
        logger.info(f"[{network.title()}] Response (Mock): {json.dumps(mock_response, indent=2)}")
        return mock_response
    
    def _is_token_expired(self, token: str) -> bool:
        """Check if JWT token is expired by parsing exp claim
        
        Returns True if token is expired or will expire within 1 hour (23 hours passed)
        """
        try:
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning("[IronSource] Invalid JWT format (not 3 parts)")
                return True  # Invalid token format, consider expired
            
            # Decode payload (second part)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)
            
            # Check exp claim
            exp = claims.get('exp')
            if exp:
                current_time = int(time.time())
                # Token expires in 24 hours, refresh 1 hour before (23 hours passed)
                # So if less than 1 hour (3600 seconds) remaining, consider expired
                time_until_expiry = exp - current_time
                logger.info(f"[IronSource] Token expires in {time_until_expiry} seconds ({time_until_expiry // 3600} hours)")
                
                # Refresh if less than 1 hour remaining
                if time_until_expiry < 3600:
                    logger.info("[IronSource] Token will expire within 1 hour, needs refresh")
                    return True
                else:
                    logger.info("[IronSource] Token is still valid")
                    return False
            
            logger.warning("[IronSource] No exp claim in token, considering expired")
            return True  # No exp claim, consider expired
        except Exception as e:
            logger.warning(f"[IronSource] Error checking token expiration: {str(e)}")
            return True  # On error, consider expired to be safe
    
    def _get_ironsource_token(self) -> Optional[str]:
        """Get IronSource bearer token with automatic refresh
        
        Logic:
        1. Check if bearer_token exists and is not expired (1 hour buffer)
        2. If expired or missing, fetch new token using secret_key and refresh_token
        3. Return valid bearer token
        
        Required: IRONSOURCE_SECRET_KEY, IRONSOURCE_REFRESH_TOKEN
        Optional: IRONSOURCE_BEARER_TOKEN (if exists and valid, use it)
        """
        # Get credentials (required)
        refresh_token = _get_env_var("IRONSOURCE_REFRESH_TOKEN")
        secret_key = _get_env_var("IRONSOURCE_SECRET_KEY")
        
        # Log what we found
        logger.info(f"[IronSource] Checking credentials...")
        logger.info(f"[IronSource] IRONSOURCE_REFRESH_TOKEN: {'SET' if refresh_token else 'NOT SET'} (length: {len(refresh_token) if refresh_token else 0})")
        logger.info(f"[IronSource] IRONSOURCE_SECRET_KEY: {'SET' if secret_key else 'NOT SET'} (length: {len(secret_key) if secret_key else 0})")
        
        if not refresh_token or not secret_key:
            missing = []
            if not refresh_token:
                missing.append("IRONSOURCE_REFRESH_TOKEN")
            if not secret_key:
                missing.append("IRONSOURCE_SECRET_KEY")
            logger.error(f"[IronSource] Missing required credentials: {', '.join(missing)}")
            logger.error("[IronSource] Please set these in .env file or Streamlit secrets")
            return None
        
        # Check if we have a cached bearer token (optional)
        bearer_token = _get_env_var("IRONSOURCE_BEARER_TOKEN") or _get_env_var("IRONSOURCE_API_TOKEN")
        
        # If bearer token exists, check if it's still valid (1 hour buffer)
        if bearer_token:
            logger.info("[IronSource] Found existing bearer token, checking expiration...")
            if not self._is_token_expired(bearer_token):
                logger.info("[IronSource] Using existing valid bearer token")
                return bearer_token
            else:
                logger.info("[IronSource] Existing bearer token is expired or will expire soon, refreshing...")
        
        # Fetch new token using secret_key and refresh_token
        logger.info("[IronSource] Fetching new bearer token...")
        new_token = self._refresh_ironsource_token(refresh_token, secret_key)
        
        if new_token:
            logger.info("[IronSource] Successfully obtained new bearer token")
            return new_token
        else:
            logger.error("[IronSource] Failed to obtain bearer token. Check logs above for details.")
            return None
    
    def _get_ironsource_headers(self) -> Optional[Dict[str, str]]:
        """Get IronSource API headers with automatic token refresh
        
        This method is called before each API request to ensure we have a valid token.
        Logic:
        1. Get bearer token (with automatic refresh if needed)
        2. Return headers with Authorization: Bearer {token}
        """
        token = self._get_ironsource_token()
        if not token:
            return None
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_ironsource_token(self, refresh_token: str, secret_key: str) -> Optional[str]:
        """Get IronSource bearer token using refresh token and secret key
        
        API: GET https://platform.ironsrc.com/partners/publisher/auth
        Headers:
            secretkey: IRONSOURCE_SECRET_KEY value
            refreshToken: IRONSOURCE_REFRESH_TOKEN value
        Response: Bearer Token (JWT string, 24 hours valid)
        """
        try:
            url = "https://platform.ironsrc.com/partners/publisher/auth"
            headers = {
                "secretkey": secret_key,
                "refreshToken": refresh_token
            }
            
            logger.info(f"[IronSource] Attempting to get bearer token...")
            logger.info(f"[IronSource] Token URL: GET {url}")
            logger.info(f"[IronSource] Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
            
            response = requests.get(url, headers=headers)
            
            logger.info(f"[IronSource] Token response status: {response.status_code}")
            logger.info(f"[IronSource] Token response headers: {dict(response.headers)}")
            logger.info(f"[IronSource] Token response text (first 200 chars): {response.text[:200]}")
            
            response.raise_for_status()
            
            # Try to parse as JSON first (in case API returns JSON)
            bearer_token = None
            try:
                result = response.json()
                # If JSON, try common field names
                bearer_token = result.get("accessToken") or result.get("bearerToken") or result.get("token") or result.get("access_token")
                if bearer_token:
                    logger.info("[IronSource] Bearer token extracted from JSON response")
            except (ValueError, json.JSONDecodeError):
                # If not JSON, treat as plain text (JWT string)
                bearer_token = response.text.strip()
                logger.info("[IronSource] Bearer token extracted from text response")
            
            # Remove quotes if present
            if bearer_token and bearer_token.startswith('"') and bearer_token.endswith('"'):
                bearer_token = bearer_token[1:-1]
            
            if bearer_token:
                logger.info("[IronSource] Bearer token obtained successfully")
                logger.info(f"[IronSource] Token length: {len(bearer_token)}")
                logger.info(f"[IronSource] Token (first 30 chars): {bearer_token[:30]}...")
                logger.info(f"[IronSource] Token (last 10 chars): ...{bearer_token[-10:]}")
            else:
                logger.error("[IronSource] Empty bearer token in response")
                logger.error(f"[IronSource] Full response text: {response.text}")
            
            return bearer_token
        except requests.exceptions.RequestException as e:
            logger.error(f"[IronSource] Token refresh failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[IronSource] Token error response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[IronSource] Token error response (text): {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"[IronSource] Token refresh exception: {str(e)}")
            return None
    
    def _generate_pangle_signature(self, security_key: str, timestamp: int, nonce: int) -> str:
        """Generate Pangle API signature
        
        Signature generation (as per Pangle documentation):
        1. Convert security_key, timestamp, nonce to strings
        2. Sort alphabetically
        3. Join together
        4. Encrypt with SHA1
        """
        keys = [security_key, str(timestamp), str(nonce)]
        keys.sort()
        key_str = ''.join(keys)
        signature = hashlib.sha1(key_str.encode("utf-8")).hexdigest()
        return signature
    
    def _create_pangle_app(self, payload: Dict) -> Dict:
        """Create app via Pangle API"""
        security_key = _get_env_var("PANGLE_SECURITY_KEY")
        
        if not security_key:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "PANGLE_SECURITY_KEY must be set in .env file or Streamlit secrets"
            }
        
        # Get user_id and role_id from payload (set in Create App page from .env)
        user_id = payload.get("user_id")
        role_id = payload.get("role_id")
        
        if not user_id or not role_id:
            # Fallback to .env if not in payload
            user_id = _get_env_var("PANGLE_USER_ID")
            role_id = _get_env_var("PANGLE_ROLE_ID")
            if not user_id or not role_id:
                return {
                    "status": 1,
                    "code": "AUTH_ERROR",
                    "msg": "PANGLE_USER_ID and PANGLE_ROLE_ID must be set in .env file or provided in form"
                }
        
        try:
            user_id_int = int(user_id)
            role_id_int = int(role_id)
        except (ValueError, TypeError):
            return {
                "status": 1,
                "code": "INVALID_CREDENTIALS",
                "msg": "PANGLE_USER_ID and PANGLE_ROLE_ID must be integers"
            }
        
        # Build request parameters
        timestamp = int(time.time())
        nonce = random.randint(100000, 999999)
        version = "1.0"  # Fixed version
        status = 2  # Fixed status (Live)
        
        # Generate signature (only security_key, timestamp, nonce)
        sign = self._generate_pangle_signature(security_key, timestamp, nonce)
        
        # Prepare all request parameters
        request_params = {
            "user_id": user_id_int,
            "role_id": role_id_int,
            "timestamp": timestamp,
            "nonce": nonce,
            "sign": sign,
            "version": version,
            "status": status,
            "app_name": payload.get("app_name"),
            "download_url": payload.get("download_url"),
            "app_category_code": payload.get("app_category_code"),
        }
        
        # Use production URL (can be changed to sandbox if needed)
        url = "https://open-api.pangleglobal.com/union/media/open_api/site/create"
        # Sandbox URL: "http://open-api-sandbox.pangleglobal.com/union/media/open_api/site/create"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Log request
        logger.info(f"[Pangle] API Request: POST {url}")
        logger.info(f"[Pangle] Request Params: {json.dumps(_mask_sensitive_data(request_params), indent=2)}")
        
        try:
            response = requests.post(url, json=request_params, headers=headers)
            
            # Log response status
            logger.info(f"[Pangle] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Log response
            logger.info(f"[Pangle] Response Body: {json.dumps(result, indent=2)}")
            
            # Pangle API response format may vary, normalize it
            if result.get("code") == 0 or result.get("ret_code") == 0:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("message") or result.get("msg") or "Unknown error"
                error_code = result.get("code") or result.get("ret_code") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Pangle] API Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Pangle] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Pangle] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_ironsource_app(self, payload: Dict) -> Dict:
        """Create app via IronSource API"""
        token = self._get_ironsource_token()
        if not token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "IronSource authentication token not found. Please check IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY in .env file or Streamlit secrets."
            }
        
        # Validate token format (should be a JWT)
        if not token or len(token) < 20:
            logger.error(f"[IronSource] Invalid token format. Token length: {len(token) if token else 0}")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": f"Invalid bearer token format. Token length: {len(token) if token else 0}. Please check IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY."
            }
        
            url = "https://platform.ironsrc.com/partners/publisher/applications/v6"
            # headers already set by _get_ironsource_headers()
        
        # Log request
        logger.info(f"[IronSource] API Request: POST {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        logger.info(f"[IronSource] Request Body: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            # Log response status
            logger.info(f"[IronSource] Response Status: {response.status_code}")
            
            # Check for 401 Unauthorized - token might be expired
            if response.status_code == 401:
                logger.warning("[IronSource] Received 401 Unauthorized. Token may be expired. Attempting to refresh...")
                
                # Try to refresh token
                refresh_token = _get_env_var("IRONSOURCE_REFRESH_TOKEN")
                secret_key = _get_env_var("IRONSOURCE_SECRET_KEY")
                
                if refresh_token and secret_key:
                    new_token = self._refresh_ironsource_token(refresh_token, secret_key)
                    if new_token:
                        # Retry request with new token
                        logger.info("[IronSource] Retrying request with refreshed token...")
                        headers["Authorization"] = f"Bearer {new_token}"
                        response = requests.post(url, json=payload, headers=headers)
                        logger.info(f"[IronSource] Retry Response Status: {response.status_code}")
                    else:
                        logger.error("[IronSource] Token refresh failed. Please check IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY")
                else:
                    logger.error("[IronSource] No refresh token available. Please set IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY in .env file")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Log response
            logger.info(f"[IronSource] Response Body: {json.dumps(result, indent=2)}")
            # IronSource API response format may vary, normalize it
            if "appKey" in result:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": {
                        "appKey": result.get("appKey"),
                        "appName": payload.get("appName", ""),
                        "storeUrl": payload.get("storeUrl", "")
                    }
                }
            return {
                "status": 0,
                "code": 0,
                "msg": "Success",
                "result": result
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"[IronSource] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[IronSource] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_unit(self, network: str, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create unit via network API
        
        Args:
            network: Network name
            payload: Unit creation payload (for IronSource, this is a single ad unit object)
            app_key: App key (required for IronSource)
        """
        if network == "ironsource":
            if not app_key:
                return {
                    "status": 1,
                    "code": "MISSING_APP_KEY",
                    "msg": "App key is required for IronSource"
                }
            # IronSource accepts an array, so wrap the payload
            return self._create_ironsource_placements(app_key, [payload])
        elif network == "bigoads":
            return self._create_bigoads_unit(payload)
        elif network == "pangle":
            return self._create_pangle_unit(payload)
        elif network == "mintegral":
            return self._create_mintegral_unit(payload)
        
        # Mock implementation for other networks
        logger.info(f"[{network.title()}] API Request: Create Unit (Mock)")
        logger.info(f"[{network.title()}] Request Payload: {json.dumps(_mask_sensitive_data(payload), indent=2)}")
        
        mock_response = {
            "status": 0,
            "code": 0,
            "msg": "Success",
            "result": {
                "slotCode": "12345-67890",
                "name": payload.get("mediationAdUnitName", payload.get("name", "Test Slot"))
            }
        }
        
        logger.info(f"[{network.title()}] Response (Mock): {json.dumps(mock_response, indent=2)}")
        return mock_response
    
    def _create_ironsource_placements(self, app_key: str, ad_units: List[Dict]) -> Dict:
        """Create placements via IronSource API
        
        Args:
            app_key: Application key from IronSource platform
            ad_units: List of ad unit objects to create
        """
        headers = self._get_ironsource_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "IronSource authentication token not found. Please check IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY in .env file or Streamlit secrets."
            }
        
        url = f"https://platform.ironsrc.com/levelPlay/adUnits/v1/{app_key}"
        
        # Log request
        logger.info(f"[IronSource] API Request: POST {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        logger.info(f"[IronSource] Request Body: {json.dumps(ad_units, indent=2)}")
        
        try:
            response = requests.post(url, json=ad_units, headers=headers)
            
            # Log response status
            logger.info(f"[IronSource] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Log response
            logger.info(f"[IronSource] Response Body: {json.dumps(result, indent=2)}")
            # IronSource API response format may vary, normalize it
            return {
                "status": 0,
                "code": 0,
                "msg": "Success",
                "result": result
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"[IronSource] API Error (Placements): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[IronSource] Error Response (text): {e.response.text}")
                    return {
                        "status": 1,
                        "code": "API_ERROR",
                        "msg": str(e)
                    }
    
    def _generate_bigoads_sign(self, developer_id: str, token: str) -> tuple[str, str]:
        """Generate BigOAds API signature
        
        Args:
            developer_id: Developer ID from .env
            token: Token from .env
        
        Returns:
            Tuple of (signature_string, timestamp_milliseconds)
        """
        # Get current timestamp in milliseconds
        now = int(time.time() * 1000)
        
        # Step 1: Combine developerId-timestamp-token
        src = f"{developer_id}-{now}-{token}"
        
        # Step 2: Encrypt with SHA1
        encrypt = hashlib.sha1(src.encode('utf-8')).hexdigest()
        
        # Step 3: Connect encrypted string and timestamp with '.'
        sign = f"{encrypt}.{now}"
        
        return sign, str(now)
    
    def _generate_mintegral_signature(self, secret: str, timestamp: int) -> str:
        """Generate Mintegral API signature
        
        규칙: md5(SECRETmd5(time))
        
        Args:
            secret: Mintegral SECRET
            timestamp: Unix timestamp
            
        Returns:
            생성된 signature
        """
        # md5(time) 계산
        time_md5 = hashlib.md5(str(timestamp).encode()).hexdigest()
        
        # md5(SECRETmd5(time)) 계산
        sign_string = secret + time_md5
        signature = hashlib.md5(sign_string.encode()).hexdigest()
        
        return signature
    
    def _create_mintegral_app(self, payload: Dict) -> Dict:
        """Create app via Mintegral API"""
        url = "https://dev.mintegral.com/app/open_api_create"
        
        # Mintegral API 인증: SKEY와 SECRET 필요
        skey = _get_env_var("MINTEGRAL_SKEY")
        secret = _get_env_var("MINTEGRAL_SECRET")
        
        if not skey or not secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "MINTEGRAL_SKEY and MINTEGRAL_SECRET must be set in .env file"
            }
        
        # Generate timestamp and signature
        timestamp = int(time.time())
        signature = self._generate_mintegral_signature(secret, timestamp)
        
        # Add authentication parameters to payload
        request_params = payload.copy()
        request_params["skey"] = skey
        request_params["timestamp"] = timestamp
        request_params["sign"] = signature
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Log request
        logger.info(f"[Mintegral] API Request: POST {url}")
        logger.info(f"[Mintegral] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Mintegral] Request Body: {json.dumps(_mask_sensitive_data(request_params), indent=2)}")
        
        try:
            response = requests.post(url, json=request_params, headers=headers)
            
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"[Mintegral] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            
            # Mintegral API response format 확인 필요
            # 일반적으로 성공 시 code가 200 또는 0일 수 있음
            if result.get("code") == 200 or result.get("code") == 0 or response.status_code == 200:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("message") or result.get("msg") or "Unknown error"
                error_code = result.get("code") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Mintegral] API Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Mintegral] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_mintegral_unit(self, payload: Dict) -> Dict:
        """Create ad placement (unit) via Mintegral API"""
        url = "https://dev.mintegral.com/v2/placement/open_api_create"
        
        # Mintegral API 인증: skey, timestamp, sign
        skey = _get_env_var("MINTEGRAL_SKEY")
        secret = _get_env_var("MINTEGRAL_SECRET")
        
        if not skey or not secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "MINTEGRAL_SKEY and MINTEGRAL_SECRET must be set in .env file"
            }
        
        # Generate timestamp and signature
        timestamp = int(time.time())
        sign = self._generate_mintegral_signature(secret, timestamp)
        
        # Add authentication fields to payload
        api_payload = payload.copy()
        api_payload["skey"] = skey
        api_payload["timestamp"] = timestamp
        api_payload["sign"] = sign
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"[Mintegral] API Request: POST {url}")
        logger.info(f"[Mintegral] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Mintegral] Request Body: {json.dumps(_mask_sensitive_data(api_payload), indent=2)}")
        
        try:
            response = requests.post(url, json=api_payload, headers=headers)
            
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"[Mintegral] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            
            # Mintegral API response format normalization
            # Check common success indicators
            if result.get("code") == 0 or result.get("ret_code") == 0 or result.get("status") == 0:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("msg") or result.get("message") or result.get("error") or "Unknown error"
                error_code = result.get("code") or result.get("ret_code") or result.get("status") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Mintegral] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Mintegral] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_bigoads_app(self, payload: Dict) -> Dict:
        """Create app via BigOAds API"""
        url = "https://www.bigossp.com/open/app/add"
        
        # BigOAds API 인증: developerId와 token 필요
        developer_id = _get_env_var("BIGOADS_DEVELOPER_ID")
        token = _get_env_var("BIGOADS_TOKEN")
        
        if not developer_id or not token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set in .env file"
            }
        
        # Generate signature
        sign, timestamp = self._generate_bigoads_sign(developer_id, token)
        
        headers = {
            "Content-Type": "application/json",
            "X-BIGO-DeveloperId": developer_id,
            "X-BIGO-Sign": sign
        }
        
        # Remove None values from payload to avoid sending null
        cleaned_payload = {k: v for k, v in payload.items() if v is not None}
        
        logger.info(f"[BigOAds] API Request: POST {url}")
        logger.info(f"[BigOAds] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[BigOAds] Request Payload: {json.dumps(_mask_sensitive_data(cleaned_payload), indent=2)}")
        
        try:
            response = requests.post(url, json=cleaned_payload, headers=headers)
            
            # Log response even if status code is not 200
            logger.info(f"[BigOAds] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[BigOAds] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[BigOAds] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            response.raise_for_status()
            
            # BigOAds API 응답 형식에 맞게 정규화
            if result.get("code") == 0 or result.get("status") == 0:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or result.get("status") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[BigOAds] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[BigOAds] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[BigOAds] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_bigoads_unit(self, payload: Dict) -> Dict:
        """Create unit (slot) via BigOAds API"""
        url = "https://www.bigossp.com/open/slot/add"
        
        # BigOAds API 인증: developerId와 token 필요
        developer_id = _get_env_var("BIGOADS_DEVELOPER_ID")
        token = _get_env_var("BIGOADS_TOKEN")
        
        if not developer_id or not token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set in .env file"
            }
        
        # Generate signature
        sign, timestamp = self._generate_bigoads_sign(developer_id, token)
        
        headers = {
            "Content-Type": "application/json",
            "X-BIGO-DeveloperId": developer_id,
            "X-BIGO-Sign": sign
        }
        
        logger.info(f"[BigOAds] API Request: POST {url}")
        logger.info(f"[BigOAds] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[BigOAds] Request Payload: {json.dumps(_mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"[BigOAds] Response Status: {response.status_code}")
            logger.info(f"[BigOAds] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            
            # BigOAds API 응답 형식에 맞게 정규화
            if result.get("code") == 0 or result.get("status") == 0:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or result.get("status") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[BigOAds] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[BigOAds] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[BigOAds] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_pangle_unit(self, payload: Dict) -> Dict:
        """Create ad placement (unit) via Pangle API"""
        security_key = _get_env_var("PANGLE_SECURITY_KEY")
        
        if not security_key:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "PANGLE_SECURITY_KEY must be set in .env file or Streamlit secrets"
            }
        
        # Get user_id and role_id from .env
        user_id = _get_env_var("PANGLE_USER_ID")
        role_id = _get_env_var("PANGLE_ROLE_ID")
        
        if not user_id or not role_id:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "PANGLE_USER_ID and PANGLE_ROLE_ID must be set in .env file"
            }
        
        try:
            user_id_int = int(user_id)
            role_id_int = int(role_id)
        except (ValueError, TypeError):
            return {
                "status": 1,
                "code": "INVALID_CREDENTIALS",
                "msg": "PANGLE_USER_ID and PANGLE_ROLE_ID must be integers"
            }
        
        # Build request parameters
        timestamp = int(time.time())
        nonce = random.randint(100000, 999999)
        version = "1.0"  # Fixed version
        
        # Generate signature (only security_key, timestamp, nonce)
        sign = self._generate_pangle_signature(security_key, timestamp, nonce)
        
        # Prepare all request parameters
        request_params = {
            "user_id": user_id_int,
            "role_id": role_id_int,
            "timestamp": timestamp,
            "nonce": nonce,
            "sign": sign,
            "version": version,
        }
        
        # Add payload fields to request_params
        # Note: ad_placement_type in payload should be ad_slot_type in API
        api_payload = payload.copy()
        if "ad_placement_type" in api_payload:
            api_payload["ad_slot_type"] = api_payload.pop("ad_placement_type")
        
        request_params.update(api_payload)
        
        # Use production URL
        url = "https://open-api.pangleglobal.com/union/media/open_api/code/create"
        # Sandbox URL: "http://open-api-sandbox.pangleglobal.com/union/media/open_api/code/create"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"[Pangle] API Request: POST {url}")
        logger.info(f"[Pangle] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Pangle] Request Params: {json.dumps(_mask_sensitive_data(request_params), indent=2)}")
        
        try:
            response = requests.post(url, json=request_params, headers=headers)
            
            logger.info(f"[Pangle] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"[Pangle] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            
            # Pangle API response format may vary, normalize it
            if result.get("code") == 0 or result.get("ret_code") == 0:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("message") or result.get("msg") or "Unknown error"
                error_code = result.get("code") or result.get("ret_code") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Pangle] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Pangle] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Pangle] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _get_bigoads_apps(self) -> List[Dict]:
        """Get apps list from BigOAds API"""
        url = "https://www.bigossp.com/open/app/list"
        
        # BigOAds API 인증: developerId와 token 필요
        developer_id = _get_env_var("BIGOADS_DEVELOPER_ID")
        token = _get_env_var("BIGOADS_TOKEN")
        
        if not developer_id or not token:
            logger.error("[BigOAds] BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set")
            return []
        
        # Generate signature
        sign, timestamp = self._generate_bigoads_sign(developer_id, token)
        
        headers = {
            "Content-Type": "application/json",
            "X-BIGO-DeveloperId": developer_id,
            "X-BIGO-Sign": sign
        }
        
        # Request payload
        payload = {
            "pageNo": 1,
            "pageSize": 10
        }
        
        logger.info(f"[BigOAds] API Request: POST {url}")
        logger.info(f"[BigOAds] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[BigOAds] Request Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            logger.info(f"[BigOAds] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[BigOAds] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[BigOAds] Response Text: {response.text}")
                return []
            
            response.raise_for_status()
            
            # BigOAds API 응답 형식에 맞게 처리
            # Response format: {"code": "100", "status": 0, "result": {"list": [...], "total": 12}}
            code = result.get("code")
            status = result.get("status")
            
            # Success: code == "100" or status == 0
            if code == "100" or status == 0:
                # Extract apps from result.list
                result_data = result.get("result", {})
                apps_list = result_data.get("list", [])
                
                logger.info(f"[BigOAds] Extracted {len(apps_list)} apps from API response (total: {result_data.get('total', 0)})")
                
                # Convert to standard format
                apps = []
                for app in apps_list:
                    platform_value = app.get("platform")
                    platform_str = "Android" if platform_value == 1 else ("iOS" if platform_value == 2 else "N/A")
                    
                    apps.append({
                        "appCode": app.get("appCode", "N/A"),
                        "name": app.get("name", "Unknown"),
                        "platform": platform_str,
                        "status": app.get("status", "N/A"),
                        "pkgNameDisplay": app.get("pkgNameDisplay", "")  # For BigOAds slot name generation
                    })
                
                logger.info(f"[BigOAds] Converted to {len(apps)} apps in standard format")
                return apps
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                logger.error(f"[BigOAds] API Error (Get Apps): {error_msg}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[BigOAds] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[BigOAds] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[BigOAds] Error Response (text): {e.response.text}")
            return []
    
    def get_apps(self, network: str) -> List[Dict]:
        """Get apps list from network"""
        if network == "bigoads":
            return self._get_bigoads_apps()
        
        # Mock implementation for other networks
        return [
            {
                "appCode": "10*****7",
                "name": "MyTestApp",
                "platform": "Android",
                "status": "Active"
            },
            {
                "appCode": "10*****8",
                "name": "AnotherApp",
                "platform": "iOS",
                "status": "Active"
            }
        ]
    
    def get_units(self, network: str, app_code: str) -> List[Dict]:
        """Get units list for an app"""
        # Mock implementation
        return [
            {
                "slotCode": "12345-678",
                "name": "TestSlot1",
                "adType": "Native",
                "auctionType": "Waterfall"
            },
            {
                "slotCode": "12345-679",
                "name": "TestSlot2",
                "adType": "Banner",
                "auctionType": "Client Bidding"
            }
        ]


# Global instance
_network_manager = None


def get_network_manager():
    """Get or create network manager instance"""
    global _network_manager
    if _network_manager is None:
        # In real implementation, initialize from BE/services/ad_network_manager.py
        # For now, use mock
        _network_manager = MockNetworkManager()
    return _network_manager


def handle_api_response(response: Dict) -> Optional[Dict]:
    """Handle API response and display result"""
    import sys
    
    # Log full response to console
    logger.info(f"API Response: {json.dumps(_mask_sensitive_data(response), indent=2)}")
    print(f"[API Response] {json.dumps(_mask_sensitive_data(response), indent=2)}", file=sys.stderr)
    
    if response.get('status') == 0 or response.get('code') == 0:
        st.success("✅ Success!")
        
        # Display full response in expander
        with st.expander("📥 Full API Response", expanded=False):
            st.json(_mask_sensitive_data(response))
        
        result = response.get('result', {})
        if result:
            # Display result separately for clarity
            st.subheader("📝 Result Data")
            st.json(_mask_sensitive_data(result))
        
        return result
    else:
        error_msg = response.get('msg', 'Unknown error')
        error_code = response.get('code', 'N/A')
        
        # Parse and improve error messages for better user experience
        user_friendly_msg = error_msg
        if error_code == "105" or error_code == 105:
            if "app auditing" in error_msg.lower() or "app audit" in error_msg.lower():
                if "audit fail" in error_msg.lower():
                    user_friendly_msg = "⚠️ App audit failed. Please ensure your app has passed the audit before creating slots."
                else:
                    user_friendly_msg = "⏳ App is currently under audit. Please wait for the audit to complete before creating slots."
            else:
                user_friendly_msg = f"System error: {error_msg}"
        
        # Log error to console
        logger.error(f"API Error: {error_code} - {error_msg}")
        print(f"[API Error] {error_code} - {error_msg}", file=sys.stderr)
        
        st.error(f"❌ Error: {error_code} - {user_friendly_msg}")
        
        # Show original error message in expander for debugging
        with st.expander("📥 Full Error Response", expanded=False):
            st.json(_mask_sensitive_data(response))
            st.info(f"**Original error message:** {error_msg}")
        
        return None

