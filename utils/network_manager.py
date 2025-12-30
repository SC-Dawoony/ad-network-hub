"""Network manager wrapper for API calls"""
from typing import Dict, List, Optional
import streamlit as st
import os
import sys
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


def _mask_sensitive_data(data) -> Dict:
    """Mask sensitive data in request/response for logging
    
    Args:
        data: Dict, List, or None to mask
        
    Returns:
        Masked data (Dict or List)
    """
    if data is None:
        return {}
    
    # Handle list data
    if isinstance(data, list):
        return [_mask_sensitive_data(item) if isinstance(item, dict) else item for item in data]
    
    # Handle dict data
    if not isinstance(data, dict):
        return data
    
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
        elif network == "inmobi":
            return self._create_inmobi_app(payload)
        elif network == "fyber":
            return self._create_fyber_app(payload)
        
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
            
            response = requests.get(url, headers=headers, timeout=30)
            
            logger.info(f"[IronSource] Token response status: {response.status_code}")
            
            if response.status_code == 200:
                # 응답은 따옴표로 감싸진 문자열이므로 제거 (reference code 방식)
                bearer_token = response.text.strip().strip('"')
                
                if bearer_token:
                    logger.info("[IronSource] Bearer token obtained successfully")
                    logger.info(f"[IronSource] Token length: {len(bearer_token)}")
                    logger.info(f"[IronSource] Token (first 50 chars): {bearer_token[:50]}...")
                    logger.info(f"[IronSource] Token valid for: 24 hours")
                    return bearer_token
                else:
                    logger.error("[IronSource] Empty bearer token in response")
                    logger.error(f"[IronSource] Full response text: {response.text}")
                    return None
            else:
                logger.error(f"[IronSource] Token request failed with status {response.status_code}")
                logger.error(f"[IronSource] Response: {response.text[:500]}")
                return None
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
        
        Signature generation (exact implementation as per Pangle documentation):
        
        import hashlib
        keys = [security_key, str(timestamp), str(nonce)] 
        keys.sort() 
        keyStr = ''.join(keys) 
        signature = hashlib.sha1(keyStr.encode("utf-8")).hexdigest()
        
        Returns:
            Lowercase hex digest (40 characters)
        """
        # Exact implementation as per Pangle documentation
        keys = [security_key, str(timestamp), str(nonce)]
        keys.sort()
        keyStr = ''.join(keys)
        signature = hashlib.sha1(keyStr.encode("utf-8")).hexdigest()
        
        logger.info(f"[Pangle] Signature generation:")
        logger.info(f"[Pangle]   security_key: {security_key[:20]}... (length: {len(security_key)})")
        logger.info(f"[Pangle]   timestamp: {timestamp}")
        logger.info(f"[Pangle]   nonce: {nonce}")
        logger.info(f"[Pangle]   keys (before sort): [{security_key[:20]}..., '{timestamp}', '{nonce}']")
        logger.info(f"[Pangle]   keys (after sort): {keys}")
        logger.info(f"[Pangle]   keyStr: {keyStr[:50]}... (length: {len(keyStr)})")
        logger.info(f"[Pangle]   signature: {signature} (length: {len(signature)})")
        
        return signature
    
    def _create_pangle_app(self, payload: Dict) -> Dict:
        """Create app via Pangle API
        
        Note: payload from build_app_payload() contains only user-input fields.
        This method adds authentication fields: timestamp, nonce, sign, version, status.
        """
        security_key = _get_env_var("PANGLE_SECURITY_KEY")
        
        if not security_key:
            logger.error("[Pangle] PANGLE_SECURITY_KEY not found in environment")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "PANGLE_SECURITY_KEY must be set in .env file or Streamlit secrets"
            }
        
        logger.info(f"[Pangle] Starting app creation with payload keys: {list(payload.keys())}")
        
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
        # IMPORTANT: Generate timestamp and nonce immediately before API call
        # to ensure they are fresh and signature matches
        timestamp = int(time.time())  # Posix timestamp (seconds) - generated fresh
        nonce = random.randint(1, 2147483647)  # Random integer (1 to 2^31-1) - generated fresh
        version = "1.0"  # Fixed version
        status = 2  # Fixed status (Live)
        
        # Generate signature immediately after timestamp/nonce generation
        # This ensures signature is calculated with the exact same timestamp/nonce used in request
        sign = self._generate_pangle_signature(security_key, timestamp, nonce)
        
        # Log timestamp age (should be very recent, < 1 second)
        current_time_check = int(time.time())
        timestamp_age = current_time_check - timestamp
        if timestamp_age > 1:
            logger.warning(f"[Pangle] WARNING: Timestamp is {timestamp_age} seconds old! This may cause validation failure.")
        
        # Check if sandbox mode is enabled (before building request_params)
        # Default to Production (false) if not set
        sandbox_env = _get_env_var("PANGLE_SANDBOX")
        sandbox = sandbox_env and sandbox_env.lower() == "true" if sandbox_env else False
        logger.info(f"[Pangle] PANGLE_SANDBOX: {sandbox_env if sandbox_env else 'not set (default: Production)'}")
        
        if sandbox:
            # Sandbox URL (HTTP, not HTTPS)
            url = "http://open-api-sandbox.pangleglobal.com/union/media/open_api/site/create"
            logger.info("[Pangle] Using SANDBOX environment")
            # Sandbox requires status: 6 (test) instead of 2 (Live)
            status = 6
        else:
            # Production URL
            url = "https://open-api.pangleglobal.com/union/media/open_api/site/create"
            logger.info("[Pangle] Using PRODUCTION environment")
            status = 2  # Live
        
        # Prepare all request parameters (status is now set based on environment)
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
        
        # Add optional fields if present
        if payload.get("mask_rule_ids"):
            request_params["mask_rule_ids"] = payload.get("mask_rule_ids")
        
        if payload.get("coppa_value") is not None:
            request_params["coppa_value"] = payload.get("coppa_value")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Log request with detailed signature information
        logger.info(f"[Pangle] API Request: POST {url}")
        logger.info(f"[Pangle] Security Key: {'SET' if security_key else 'NOT SET'} (length: {len(security_key) if security_key else 0})")
        logger.info(f"[Pangle] User ID: {user_id_int}, Role ID: {role_id_int}")
        logger.info(f"[Pangle] Timestamp: {timestamp}, Nonce: {nonce}")
        logger.info(f"[Pangle] Signature: {sign} (length: {len(sign)})")
        
        # Log signature generation details for debugging (INFO level for troubleshooting)
        keys_for_signature = [security_key, str(timestamp), str(nonce)]
        keys_for_signature.sort()
        key_str_for_signature = ''.join(keys_for_signature)
        logger.info(f"[Pangle] Signature generation details:")
        logger.info(f"[Pangle]   - Security Key: {security_key[:10]}... (length: {len(security_key)})")
        logger.info(f"[Pangle]   - Timestamp: {timestamp}")
        logger.info(f"[Pangle]   - Nonce: {nonce}")
        logger.info(f"[Pangle]   - Sorted keys: {keys_for_signature}")
        logger.info(f"[Pangle]   - Concatenated string: {key_str_for_signature}")
        logger.info(f"[Pangle]   - Generated signature: {sign}")
        logger.info(f"[Pangle]   - Signature length: {len(sign)} (expected: 40)")
        
        # Verify signature is lowercase
        if sign != sign.lower():
            logger.warning(f"[Pangle] WARNING: Signature contains uppercase characters!")
        
        masked_params = _mask_sensitive_data(request_params.copy())
        # Also mask sign in logging
        if "sign" in masked_params:
            masked_params["sign"] = "***MASKED***"
        logger.info(f"[Pangle] Full Request Params (masked): {json.dumps(masked_params, indent=2)}")
        
        # Log actual request params structure (without sensitive data)
        logger.info(f"[Pangle] Request structure check:")
        logger.info(f"[Pangle]   - Has user_id: {('user_id' in request_params)}")
        logger.info(f"[Pangle]   - Has role_id: {('role_id' in request_params)}")
        logger.info(f"[Pangle]   - Has timestamp: {('timestamp' in request_params)}")
        logger.info(f"[Pangle]   - Has nonce: {('nonce' in request_params)}")
        logger.info(f"[Pangle]   - Has sign: {('sign' in request_params)}")
        logger.info(f"[Pangle]   - Has version: {('version' in request_params)}")
        logger.info(f"[Pangle]   - Version value: {request_params.get('version')}")
        logger.info(f"[Pangle]   - Has status: {('status' in request_params)}")
        logger.info(f"[Pangle]   - Status value: {request_params.get('status')}")
        
        try:
            # Verify timestamp is still fresh (re-check right before API call)
            current_time_before_request = int(time.time())
            timestamp_age_seconds = current_time_before_request - timestamp
            logger.info(f"[Pangle] Timestamp age before request: {timestamp_age_seconds} seconds")
            
            if timestamp_age_seconds > 5:
                logger.warning(f"[Pangle] WARNING: Timestamp is {timestamp_age_seconds} seconds old! Regenerating...")
                # Regenerate timestamp and nonce if too old
                timestamp = int(time.time())
                nonce = random.randint(1, 2147483647)
                sign = self._generate_pangle_signature(security_key, timestamp, nonce)
                # Update request_params with fresh values
                request_params["timestamp"] = timestamp
                request_params["nonce"] = nonce
                request_params["sign"] = sign
                logger.info(f"[Pangle] Regenerated: timestamp={timestamp}, nonce={nonce}, sign={sign[:20]}...")
            
            # Log actual JSON being sent (for debugging) - Print to console
            print("=" * 60, file=sys.stderr)
            print("[Pangle] ========== CREATE APP REQUEST ==========", file=sys.stderr)
            print(f"[Pangle] URL: {url}", file=sys.stderr)
            print(f"[Pangle] Headers: {json.dumps(headers, indent=2)}", file=sys.stderr)
            print(f"[Pangle] Request Body (full):", file=sys.stderr)
            # Create a copy for logging (mask sensitive data)
            log_params = request_params.copy()
            if "sign" in log_params:
                log_params["sign"] = f"{log_params['sign'][:20]}... (masked, full length: {len(log_params['sign'])})"
            print(f"[Pangle] {json.dumps(log_params, indent=2, ensure_ascii=False)}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            
            # Also log via logger
            logger.info(f"[Pangle] ========== FINAL REQUEST BEING SENT ==========")
            logger.info(f"[Pangle] URL: {url}")
            logger.info(f"[Pangle] Headers: {json.dumps(headers, indent=2)}")
            logger.info(f"[Pangle] Request Body (full):")
            logger.info(f"[Pangle] {json.dumps(log_params, indent=2, ensure_ascii=False)}")
            logger.info(f"[Pangle] ===============================================")
            
            response = requests.post(url, json=request_params, headers=headers, timeout=30)
            
            # Log response status - Print to console
            print(f"[Pangle] Response Status: {response.status_code}", file=sys.stderr)
            print(f"[Pangle] Response Headers: {dict(response.headers)}", file=sys.stderr)
            
            # Also log via logger
            logger.info(f"[Pangle] Response Status: {response.status_code}")
            logger.info(f"[Pangle] Response Headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Log response - Print to console
            print(f"[Pangle] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            
            # Also log via logger
            logger.info(f"[Pangle] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # If error, log more details
            error_code = result.get("code") or result.get("ret_code")
            error_msg = result.get("msg") or result.get("message") or "Unknown error"
            
            if error_code != 0 and error_code is not None:
                print(f"[Pangle] ❌ Error: {error_code} - {error_msg}", file=sys.stderr)
                print(f"[Pangle] Full error response: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
                
                # Parse 50003 error to extract internal_code and internal_message
                if error_code == 50003:
                    import re
                    # Parse "Internal code:[50001], internal message:[API System error]"
                    internal_code_match = re.search(r'Internal code:\[(\d+)\]', str(error_msg))
                    internal_msg_match = re.search(r'internal message:\[([^\]]+)\]', str(error_msg))
                    
                    if internal_code_match:
                        internal_code = internal_code_match.group(1)
                        internal_message = internal_msg_match.group(1) if internal_msg_match else "Unknown internal error"
                        
                        print(f"[Pangle] ⚠️  Internal Error Details:", file=sys.stderr)
                        print(f"[Pangle]   - Internal Code: {internal_code}", file=sys.stderr)
                        print(f"[Pangle]   - Internal Message: {internal_message}", file=sys.stderr)
                        print(f"[Pangle]   - Note: 50003 indicates an error occurred when API server calls its subordinate HTTP services", file=sys.stderr)
                        print(f"[Pangle]   - Refer to section 5.1.3 Internal Code List for details about code {internal_code}", file=sys.stderr)
                        
                        logger.error(f"[Pangle] Internal Error Details:")
                        logger.error(f"[Pangle]   - Internal Code: {internal_code}")
                        logger.error(f"[Pangle]   - Internal Message: {internal_message}")
                        
                        # Handle specific internal codes based on Pangle API documentation
                        # Internal Code List (5.1.3) mappings
                        internal_code_descriptions = {
                            "0": "Success - Operation successful",
                            "SY_1000": "System error - Unknown system error",
                            "SY_1001": "Parameter error - Failed to parse the request",
                            "SY_1009": "Database error - An error has occurred in the database",
                            "SY_1005": "Permission denied - Insufficient permissions",
                            "SY_1011": "Invalid value for the field - The value of the field does not meet the requirements",
                            "SY_1012": "The field cannot be modified - Due to some restrictions, the target field cannot be edited",
                            "SY_1013": "Missing required field - Some essential fields are missing",
                            "21000": "Download URL error - The app download URL is incorrect",
                            "21001": "App downloading error - Failed to download the app",
                            "21003": "Package parsing error - Failed to parse the app package",
                            "21005": "Verification failed - The download link format is not correct",
                            "21007": "Application package name is blocked - Verification failed",
                            "21008": "Unsupported app store - This app store is not supported yet",
                            "21011": "Package name error - Package name is incorrect",
                            "21012": "SHA1 error - SHA1 is incorrect",
                            "21014": "App validation still in processing - Verification has timed out",
                            "21017": "Package name already exist - This package name already exists",
                            "21020": "App downloading time out - App download has timed out",
                            "21023": "App store has not been registered by media - This app store is not supported",
                        }
                        
                        # Check if internal_code is in the list
                        if internal_code in internal_code_descriptions:
                            description = internal_code_descriptions[internal_code]
                            print(f"[Pangle]   - Internal Code {internal_code}: {description}", file=sys.stderr)
                            logger.error(f"[Pangle]   - Internal Code {internal_code}: {description}")
                        elif internal_code == "50001":
                            # 50001 is a Return Code, not Internal Code, but may appear as internal_code in some cases
                            print(f"[Pangle]   - Internal Code 50001: System error (Return Code)", file=sys.stderr)
                            print(f"[Pangle]   - An error has occurred on the API server or in its subordinate services", file=sys.stderr)
                            print(f"[Pangle]   - This may indicate server-side issue or invalid request parameters", file=sys.stderr)
                            print(f"[Pangle]   - Check request parameters above", file=sys.stderr)
                            logger.error(f"[Pangle]   - Internal Code 50001: System error (Return Code)")
                            logger.error(f"[Pangle]   - An error has occurred on the API server or in its subordinate services")
                        elif internal_code == "41001":
                            print(f"[Pangle]   - Internal Code 41001: OAuth validation failure", file=sys.stderr)
                            print(f"[Pangle]   - Security Key length: {len(security_key) if security_key else 0}", file=sys.stderr)
                            print(f"[Pangle]   - User ID: {user_id_int}, Role ID: {role_id_int}", file=sys.stderr)
                            print(f"[Pangle]   - Timestamp: {timestamp}, Nonce: {nonce}", file=sys.stderr)
                            print(f"[Pangle]   - Signature: {sign}", file=sys.stderr)
                            print(f"[Pangle]   - Request URL: {url}", file=sys.stderr)
                            logger.error(f"[Pangle]   - Internal Code 41001: OAuth validation failure")
                            logger.error(f"[Pangle]   - Security Key length: {len(security_key) if security_key else 0}")
                            logger.error(f"[Pangle]   - User ID: {user_id_int}, Role ID: {role_id_int}")
                            logger.error(f"[Pangle]   - Timestamp: {timestamp}, Nonce: {nonce}")
                            logger.error(f"[Pangle]   - Signature: {sign}")
                            logger.error(f"[Pangle]   - Request URL: {url}")
                
                # Legacy check for OAuth validation failure (direct in error_msg)
                elif error_code == 50003 and "oauth validation failure" in str(error_msg).lower():
                    print(f"[Pangle] OAuth Validation Failure Details:", file=sys.stderr)
                    print(f"[Pangle]   - Security Key length: {len(security_key) if security_key else 0}", file=sys.stderr)
                    print(f"[Pangle]   - User ID: {user_id_int}, Role ID: {role_id_int}", file=sys.stderr)
                    print(f"[Pangle]   - Timestamp: {timestamp}, Nonce: {nonce}", file=sys.stderr)
                    print(f"[Pangle]   - Signature: {sign}", file=sys.stderr)
                    print(f"[Pangle]   - Request URL: {url}", file=sys.stderr)
                    logger.error(f"[Pangle] OAuth Validation Failure Details:")
                    logger.error(f"[Pangle]   - Security Key length: {len(security_key) if security_key else 0}")
                    logger.error(f"[Pangle]   - User ID: {user_id_int}, Role ID: {role_id_int}")
                    logger.error(f"[Pangle]   - Timestamp: {timestamp}, Nonce: {nonce}")
                    logger.error(f"[Pangle]   - Signature: {sign}")
                    logger.error(f"[Pangle]   - Request URL: {url}")
            
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
                
                # Extract internal_code from 50003 error messages for better error reporting
                if error_code == 50003:
                    import re
                    internal_code_match = re.search(r'Internal code:\[(\d+)\]', str(error_msg))
                    internal_msg_match = re.search(r'internal message:\[([^\]]+)\]', str(error_msg))
                    
                    if internal_code_match:
                        internal_code = internal_code_match.group(1)
                        internal_message = internal_msg_match.group(1) if internal_msg_match else "Unknown internal error"
                        # Include internal_code in the error message for user visibility
                        error_msg = f"{error_msg} (Internal Code: {internal_code})"
                
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
        headers = self._get_ironsource_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "IronSource authentication token not found. Please check IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY in .env file or Streamlit secrets."
            }
        
        url = "https://platform.ironsrc.com/partners/publisher/applications/v6"
        
        # Log request
        logger.info(f"[IronSource] API Request: POST {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        logger.info(f"[IronSource] Request Body: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
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
                        response = requests.post(url, json=payload, headers=headers, timeout=30)
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
        elif network == "inmobi":
            return self._create_inmobi_unit(payload)
        elif network == "fyber":
            return self._create_fyber_unit(payload)
        elif network == "applovin":
            return self._create_applovin_unit(payload)
        
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
        
        # Validate ad_units
        if not ad_units:
            return {
                "status": 1,
                "code": "INVALID_PAYLOAD",
                "msg": "Ad units list is empty"
            }
        
        # Validate each ad unit has required fields
        for idx, ad_unit in enumerate(ad_units):
            if not isinstance(ad_unit, dict):
                return {
                    "status": 1,
                    "code": "INVALID_PAYLOAD",
                    "msg": f"Ad unit at index {idx} must be a dictionary"
                }
            if not ad_unit.get("mediationAdUnitName"):
                return {
                    "status": 1,
                    "code": "INVALID_PAYLOAD",
                    "msg": f"mediationAdUnitName is required for ad unit at index {idx}"
                }
            if not ad_unit.get("adFormat"):
                return {
                    "status": 1,
                    "code": "INVALID_PAYLOAD",
                    "msg": f"adFormat is required for ad unit at index {idx}"
                }
        
        # Log request
        logger.info(f"[IronSource] API Request: POST {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        logger.info(f"[IronSource] Request Body: {json.dumps(_mask_sensitive_data(ad_units), indent=2)}")
        
        try:
            # API accepts an array of ad units
            response = requests.post(url, json=ad_units, headers=headers, timeout=30)
            
            # Log response status
            logger.info(f"[IronSource] Response Status: {response.status_code}")
            
            # Check response status before parsing
            if response.status_code >= 400:
                # Error response
                try:
                    error_body = response.json()
                    logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                    error_msg = error_body.get("message") or error_body.get("msg") or error_body.get("error") or response.text
                    error_code = error_body.get("code") or error_body.get("errorCode") or str(response.status_code)
                except:
                    error_msg = response.text or f"HTTP {response.status_code}"
                    error_code = str(response.status_code)
                    logger.error(f"[IronSource] Error Response (text): {error_msg}")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
            
            # Success response - handle empty or invalid JSON
            response_text = response.text.strip()
            if not response_text:
                # Empty response
                logger.warning(f"[IronSource] Empty response body (status {response.status_code})")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success (empty response)",
                    "result": {}
                }
            
            try:
                result = response.json()
                # Log response
                logger.info(f"[IronSource] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except json.JSONDecodeError as e:
                # Invalid JSON response
                logger.error(f"[IronSource] JSON decode error: {str(e)}")
                logger.error(f"[IronSource] Response text: {response_text[:500]}")
                return {
                    "status": 1,
                    "code": "JSON_ERROR",
                    "msg": f"Invalid JSON response: {str(e)}. Response: {response_text[:200]}"
                }
            
            # IronSource API response format may vary, normalize it
            # Response might be an array of created ad units or a single object
            return {
                "status": 0,
                "code": 0,
                "msg": "Success",
                "result": result
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"[IronSource] API Error (Placements): {str(e)}")
            error_msg = str(e)
            error_code = "API_ERROR"
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                    error_msg = error_body.get("message") or error_body.get("msg") or error_body.get("error") or error_msg
                    error_code = error_body.get("code") or error_body.get("errorCode") or error_code
                except:
                    logger.error(f"[IronSource] Error Response (text): {e.response.text}")
                    if e.response.text:
                        error_msg = e.response.text
            
            return {
                "status": 1,
                "code": error_code,
                "msg": error_msg
            }
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"[IronSource] Unexpected Error (Placements): {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": 1,
                "code": "UNEXPECTED_ERROR",
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
        # Reference code uses 'time' (string) instead of 'timestamp' (int)
        current_time = int(time.time())
        signature = self._generate_mintegral_signature(secret, current_time)
        
        # Add authentication parameters to payload
        # Reference code pattern: use 'time' as string parameter
        request_params = payload.copy()
        request_params["skey"] = skey
        request_params["time"] = str(current_time)  # Use 'time' as string, not 'timestamp'
        request_params["sign"] = signature
        
        # Reference code uses application/x-www-form-urlencoded for Media List
        # Create App might also use the same format
        # Try form-urlencoded first (matching Media List pattern)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Print to console for debugging
        print("\n" + "=" * 80, file=sys.stderr)
        print("🟢 [Mintegral] ========== CREATE APP REQUEST ==========", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(f"[Mintegral] URL: {url}", file=sys.stderr)
        print(f"[Mintegral] Headers: {json.dumps(headers, indent=2)}", file=sys.stderr)
        print(f"[Mintegral] Request Parameters (full): {json.dumps(request_params, indent=2, ensure_ascii=False)}", file=sys.stderr)
        print(f"[Mintegral] Request Parameters Summary:", file=sys.stderr)
        for key, value in request_params.items():
            if key == "sign":
                print(f"[Mintegral]   - {key}: {str(value)[:20]}... (masked)", file=sys.stderr)
            elif key == "skey":
                print(f"[Mintegral]   - {key}: {str(value)[:20]}... (masked)", file=sys.stderr)
            else:
                print(f"[Mintegral]   - {key}: {value} (type: {type(value).__name__})", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        
        # Also log via logger
        logger.info(f"[Mintegral] API Request: POST {url}")
        logger.info(f"[Mintegral] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Mintegral] Request Body: {json.dumps(_mask_sensitive_data(request_params), indent=2)}")
        
        try:
            # Use form-urlencoded (matching Media List API pattern)
            response = requests.post(url, data=request_params, headers=headers, timeout=30)
            
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Print to console for debugging
            print("\n" + "=" * 80, file=sys.stderr)
            print("🟢 [Mintegral] ========== CREATE APP RESPONSE ==========", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print(f"[Mintegral] Response Status: {response.status_code}", file=sys.stderr)
            print(f"[Mintegral] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            
            # Also log via logger
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            logger.info(f"[Mintegral] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            
            # Mintegral API response format:
            # Success: {"code": 0, "msg": "Success", ...}
            # Error: {"code": -2007, "msg": "Invalid Params", "traceid": "..."}
            # Check top-level code first
            top_level_code = result.get("code")
            
            # Success: code must be 0 or 200 (positive or zero)
            # Error: code is negative (e.g., -2007, -2004)
            if top_level_code is not None:
                if top_level_code == 0 or top_level_code == 200:
                    # Success
                    print(f"[Mintegral] ✅ Success (code: {top_level_code})", file=sys.stderr)
                    logger.info(f"[Mintegral] ✅ Success (code: {top_level_code})")
                    return {
                        "status": 0,
                        "code": 0,
                        "msg": result.get("msg", "Success"),
                        "result": result.get("result", result.get("data", result))
                    }
                else:
                    # Error: negative code or non-zero positive code
                    error_msg = result.get("msg") or "Unknown error"
                    print(f"[Mintegral] ❌ Error: code={top_level_code}, msg={error_msg}", file=sys.stderr)
                    logger.error(f"[Mintegral] ❌ Error: code={top_level_code}, msg={error_msg}")
                    return {
                        "status": 1,
                        "code": top_level_code,
                        "msg": error_msg
                    }
            
            # Fallback: if code is not present, check HTTP status
            if response.status_code == 200:
                print(f"[Mintegral] ✅ Success (HTTP 200, no code in response)", file=sys.stderr)
                logger.info(f"[Mintegral] ✅ Success (HTTP 200, no code in response)")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("result", result.get("data", result))
                }
            else:
                error_msg = result.get("msg") or "Unknown error"
                print(f"[Mintegral] ❌ Error: HTTP {response.status_code}, msg={error_msg}", file=sys.stderr)
                logger.error(f"[Mintegral] ❌ Error: HTTP {response.status_code}, msg={error_msg}")
                return {
                    "status": 1,
                    "code": response.status_code,
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
    
    def _get_mintegral_apps(self) -> List[Dict]:
        """Get media list from Mintegral API
        
        API: GET https://dev.mintegral.com/v2/app/open_api_list
        Reference: Uses GET with params (skey, time, sign) and application/x-www-form-urlencoded
        """
        url = "https://dev.mintegral.com/v2/app/open_api_list"
        
        # Mintegral API 인증: SKEY와 SECRET 필요
        skey = _get_env_var("MINTEGRAL_SKEY")
        secret = _get_env_var("MINTEGRAL_SECRET")
        
        if not skey or not secret:
            logger.error("[Mintegral] MINTEGRAL_SKEY or MINTEGRAL_SECRET not found")
            return []
        
        # Generate timestamp and signature (use 'time' as parameter name, not 'timestamp')
        current_time = int(time.time())
        signature = self._generate_mintegral_signature(secret, current_time)
        
        # Build request params (GET request with query parameters)
        # Reference code uses: skey, time (not timestamp), sign
        request_params = {
            "skey": skey,
            "time": str(current_time),  # Note: 'time' as string, not 'timestamp'
            "sign": signature
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"  # Reference code uses this
        }
        
        # Print to console for debugging
        print("\n" + "=" * 80, file=sys.stderr)
        print("🟢 [Mintegral] ========== GET MEDIA LIST REQUEST ==========", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(f"[Mintegral] URL: {url}", file=sys.stderr)
        print(f"[Mintegral] Headers: {json.dumps(headers, indent=2)}", file=sys.stderr)
        print(f"[Mintegral] Request Params: {json.dumps(request_params, indent=2, ensure_ascii=False)}", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        
        # Also log via logger
        logger.info(f"[Mintegral] API Request: GET {url}")
        logger.info(f"[Mintegral] Request Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"[Mintegral] Request Params: {json.dumps(_mask_sensitive_data(request_params), indent=2)}")
        
        try:
            # GET request with params (as per reference code)
            response = requests.get(url, headers=headers, params=request_params, timeout=30)
            
            print(f"[Mintegral] Response Status: {response.status_code}", file=sys.stderr)
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Print to console
            print(f"[Mintegral] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            logger.info(f"[Mintegral] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            
            # Check response code (reference code: code == 200 means success)
            response_code = result.get("code")
            response_msg = result.get("msg")
            data = result.get("data")
            
            print(f"[Mintegral] Response code: {response_code}", file=sys.stderr)
            print(f"[Mintegral] Response msg: {response_msg}", file=sys.stderr)
            
            if response_code != 200:
                error_msg = response_msg or "Unknown error"
                print(f"[Mintegral] ❌ Error: code={response_code}, msg={error_msg}", file=sys.stderr)
                logger.error(f"[Mintegral] Error: code={response_code}, msg={error_msg}")
                
                # Common error codes from reference
                error_codes = {
                    -2004: "No Access - 인증 실패 (skey, secret, sign 확인)",
                    -2006: "Permission denied - 권한 없음",
                    -2007: "Invalid Params - 잘못된 파라미터"
                }
                if response_code in error_codes:
                    print(f"[Mintegral] 💡 {error_codes[response_code]}", file=sys.stderr)
                
                return []
            
            # Parse response - Reference code: data.lists contains the app list
            if isinstance(data, dict):
                lists = data.get("lists", [])
                total = data.get("total", 0)
                page = data.get("page", 1)
                per_page = data.get("per_page", 0)
                
                print(f"[Mintegral] Response data structure:", file=sys.stderr)
                print(f"[Mintegral]   - total: {total}", file=sys.stderr)
                print(f"[Mintegral]   - page: {page}", file=sys.stderr)
                print(f"[Mintegral]   - per_page: {per_page}", file=sys.stderr)
                print(f"[Mintegral]   - lists length: {len(lists) if isinstance(lists, list) else 0}", file=sys.stderr)
                
                apps_data = lists if isinstance(lists, list) else []
            else:
                apps_data = []
            
            # Format apps to standard format
            formatted_apps = []
            for app in apps_data:
                if isinstance(app, dict):
                    formatted_apps.append({
                        "appCode": str(app.get("app_id", app.get("id", app.get("media_id", "N/A")))),
                        "app_id": app.get("app_id", app.get("id", app.get("media_id"))),
                        "name": app.get("app_name", app.get("name", app.get("media_name", "Unknown"))),
                        "platform": app.get("os", app.get("platform", "N/A")),
                        "pkgName": app.get("package", app.get("pkg_name", app.get("package_name", ""))),
                    })
            
            print(f"[Mintegral] ✅ Successfully loaded {len(formatted_apps)} apps from API", file=sys.stderr)
            logger.info(f"[Mintegral] Successfully loaded {len(formatted_apps)} apps from API")
            
            return formatted_apps
            
        except requests.exceptions.RequestException as e:
            print(f"[Mintegral] ❌ API Error (Get Apps): {str(e)}", file=sys.stderr)
            logger.error(f"[Mintegral] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    print(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2, ensure_ascii=False)}", file=sys.stderr)
                    logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    print(f"[Mintegral] Error Response (text): {e.response.text[:500]}", file=sys.stderr)
                    logger.error(f"[Mintegral] Error Response (text): {e.response.text[:500]}")
            return []
        except Exception as e:
            print(f"[Mintegral] ❌ Unexpected Error (Get Apps): {str(e)}", file=sys.stderr)
            logger.error(f"[Mintegral] Unexpected Error (Get Apps): {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
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
                # Handle empty result object - this is a valid success response
                result_data = result.get("data")
                if result_data is None:
                    # If "data" field doesn't exist, check if "result" field exists
                    result_data = result.get("result", {})
                
                # If result_data is empty dict and msg indicates empty response, keep it as is
                # This is a valid success case for Mintegral API
                msg = result.get("msg", "Success")
                if not result_data and "empty response" in msg.lower():
                    # This is expected - empty result is valid for Mintegral create unit
                    result_data = {}
                
                return {
                    "status": 0,
                    "code": 0,
                    "msg": msg,
                    "result": result_data if result_data else {}
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
    
    def _create_inmobi_app(self, payload: Dict) -> Dict:
        """Create app via InMobi API"""
        url = "https://publisher.inmobi.com/rest/api/v2/apps"
        
        # InMobi API 인증: x-client-id, x-account-id, x-client-secret 헤더 사용
        username = _get_env_var("INMOBI_USERNAME")  # x-client-id (email ID)
        account_id = _get_env_var("INMOBI_ACCOUNT_ID")  # x-account-id (Account ID)
        client_secret = _get_env_var("INMOBI_CLIENT_SECRET")  # x-client-secret (API key)
        
        if not username or not account_id or not client_secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set in .env file or Streamlit secrets"
            }
        
        # InMobi 인증 헤더 설정
        headers = {
            "x-client-id": username,
            "x-account-id": account_id,
            "x-client-secret": client_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Remove None values and empty strings from payload
        cleaned_payload = {k: v for k, v in payload.items() if v is not None and v != ""}
        
        logger.info(f"[InMobi] API Request: POST {url}")
        logger.info(f"[InMobi] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[InMobi] Request Payload: {json.dumps(_mask_sensitive_data(cleaned_payload), indent=2)}")
        
        try:
            response = requests.post(url, json=cleaned_payload, headers=headers, timeout=30)
            
            # Log response even if status code is not 200
            logger.info(f"[InMobi] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[InMobi] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[InMobi] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # For 400 errors, log detailed error information
            if response.status_code == 400:
                logger.error(f"[InMobi] Bad Request (400) - Full Response: {response.text}")
                print(f"[InMobi] ❌ Bad Request (400)", file=sys.stderr)
                print(f"[InMobi] Response: {response.text}", file=sys.stderr)
                # Try to extract more details from error response
                try:
                    error_detail = response.json()
                    if isinstance(error_detail, dict):
                        error_msg = error_detail.get("message") or error_detail.get("error") or error_detail.get("msg") or str(error_detail)
                        logger.error(f"[InMobi] Error Details: {error_msg}")
                        print(f"[InMobi] Error Details: {error_msg}", file=sys.stderr)
                except:
                    pass
            
            response.raise_for_status()
            
            # InMobi API 응답 형식에 맞게 정규화
            # 응답 형식은 API 문서를 참조하여 수정 필요
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[InMobi] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                    print(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}", file=sys.stderr)
                except:
                    logger.error(f"[InMobi] Error Response (text): {e.response.text}")
                    print(f"[InMobi] Error Response (text): {e.response.text}", file=sys.stderr)
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _get_fyber_access_token(self) -> Optional[str]:
        """Get Fyber (DT) Access Token
        
        Always fetches a new access token using DT_CLIENT_ID and DT_CLIENT_SECRET.
        API: POST https://console.fyber.com/api/v2/management/auth
        Payload: grant_type, client_id, client_secret
        """
        client_id_raw = _get_env_var("DT_CLIENT_ID") or _get_env_var("FYBER_CLIENT_ID")
        client_secret_raw = _get_env_var("DT_CLIENT_SECRET") or _get_env_var("FYBER_CLIENT_SECRET")
        
        # Strip whitespace and check if empty
        client_id = client_id_raw.strip() if client_id_raw else None
        client_secret = client_secret_raw.strip() if client_secret_raw else None
        
        # Debug logging - check all possible env var names
        logger.info(f"[Fyber] Fetching new access token...")
        dt_client_id = _get_env_var("DT_CLIENT_ID")
        fyber_client_id = _get_env_var("FYBER_CLIENT_ID")
        dt_client_secret = _get_env_var("DT_CLIENT_SECRET")
        fyber_client_secret = _get_env_var("FYBER_CLIENT_SECRET")
        
        logger.info(f"[Fyber] Environment variable check:")
        logger.info(f"[Fyber]   DT_CLIENT_ID: {'✓' if dt_client_id else '✗'} (length: {len(dt_client_id) if dt_client_id else 0})")
        logger.info(f"[Fyber]   FYBER_CLIENT_ID: {'✓' if fyber_client_id else '✗'} (length: {len(fyber_client_id) if fyber_client_id else 0})")
        logger.info(f"[Fyber]   DT_CLIENT_SECRET: {'✓' if dt_client_secret else '✗'} (length: {len(dt_client_secret) if dt_client_secret else 0})")
        logger.info(f"[Fyber]   FYBER_CLIENT_SECRET: {'✓' if fyber_client_secret else '✗'} (length: {len(fyber_client_secret) if fyber_client_secret else 0})")
        logger.info(f"[Fyber] Final client_id: {'✓' if client_id else '✗'} (length: {len(client_id) if client_id else 0})")
        logger.info(f"[Fyber] Final client_secret: {'✓' if client_secret else '✗'} (length: {len(client_secret) if client_secret else 0})")
        
        if not client_id or not client_secret:
            logger.error("[Fyber] DT_CLIENT_ID and DT_CLIENT_SECRET must be set")
            logger.error(f"[Fyber] client_id is None or empty: {not client_id}, client_secret is None or empty: {not client_secret}")
            logger.error(f"[Fyber] Please check:")
            logger.error(f"[Fyber]   1. .env file has DT_CLIENT_ID and DT_CLIENT_SECRET (or FYBER_CLIENT_ID and FYBER_CLIENT_SECRET)")
            logger.error(f"[Fyber]   2. Streamlit secrets has DT_CLIENT_ID and DT_CLIENT_SECRET")
            logger.error(f"[Fyber]   3. Values are not empty or whitespace-only")
            return None
        
        auth_url = "https://console.fyber.com/api/v2/management/auth"
        
        payload = {
            "grant_type": "management_client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"[Fyber] Requesting new access token from: {auth_url}")
        logger.info(f"[Fyber] Request Payload: {json.dumps(_mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(auth_url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                # Check both accessToken and access_token (API may return either)
                access_token = result.get("accessToken") or result.get("access_token")
                if access_token:
                    logger.info(f"[Fyber] ✅ Successfully obtained new access token (length: {len(access_token)})")
                    return access_token
                else:
                    logger.error(f"[Fyber] ❌ Access token not found in response: {result}")
                    return None
            else:
                logger.error(f"[Fyber] ❌ Failed to get access token. Status: {response.status_code}")
                logger.error(f"[Fyber] Response: {response.text}")
                
                # Provide helpful error messages
                if "invalid_client" in response.text:
                    logger.error("[Fyber] 💡 'invalid_client' 오류:")
                    logger.error("[Fyber]   → Client ID 또는 Client Secret이 올바르지 않습니다.")
                    logger.error("[Fyber]   → Fyber Console > Settings > API Credentials > Management API")
                    logger.error("[Fyber]   → UI에서 받은 Client ID와 Client Secret을 정확히 복사했는지 확인")
                elif "invalid_request" in response.text:
                    logger.error("[Fyber] 💡 'invalid_request' 오류:")
                    logger.error("[Fyber]   → 요청 파라미터가 올바르지 않습니다.")
                    logger.error("[Fyber]   → grant_type이 'management_client_credentials'인지 확인")
                
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[Fyber] ❌ API Error (Get Access Token): {str(e)}")
            return None
    
    def _create_fyber_app(self, payload: Dict) -> Dict:
        """Create app via Fyber (DT) API"""
        url = "https://console.fyber.com/api/management/v1/app"
        
        # Get access token
        access_token = self._get_fyber_access_token()
        if not access_token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to obtain Fyber access token. Please check DT_CLIENT_ID and DT_CLIENT_SECRET in .env file or Streamlit secrets."
            }
        
        # Fyber API 인증 헤더 설정
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        logger.info(f"[Fyber] API Request: POST {url}")
        logger.info(f"[Fyber] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Fyber] Request Payload: {json.dumps(_mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log response even if status code is not 200
            logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[Fyber] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[Fyber] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Fyber API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Extract error message from response
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                # Provide helpful error messages for common errors
                if response.status_code == 409:
                    if "Invalid store category1" in error_msg:
                        logger.error("[Fyber] 💡 카테고리 오류:")
                        logger.error("[Fyber]   → 선택한 카테고리가 플랫폼에 맞지 않습니다.")
                        logger.error("[Fyber]   → Android와 iOS는 서로 다른 카테고리를 사용합니다.")
                        logger.error(f"[Fyber]   → 에러 메시지: {error_msg[:200]}...")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Fyber] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Fyber] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_fyber_unit(self, payload: Dict) -> Dict:
        """Create placement (unit) via Fyber (DT) API
        
        API: POST https://console.fyber.com/api/management/v1/placement
        """
        url = "https://console.fyber.com/api/management/v1/placement"
        
        # Get access token
        access_token = self._get_fyber_access_token()
        if not access_token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to obtain Fyber access token. Please check DT_CLIENT_ID and DT_CLIENT_SECRET in .env file or Streamlit secrets."
            }
        
        # Fyber API 인증 헤더 설정
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        logger.info(f"[Fyber] API Request: POST {url}")
        logger.info(f"[Fyber] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Fyber] Request Payload: {json.dumps(_mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log response even if status code is not 200
            logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[Fyber] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[Fyber] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Fyber API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Extract error message from response
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Fyber] API Error (Create Placement): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Fyber] Error Response (text): {e.response.text}")
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
        
        # Print to stderr so it shows in console (Streamlit terminal)
        print("=" * 60, file=sys.stderr)
        print("[BigOAds] ========== CREATE UNIT REQUEST ==========", file=sys.stderr)
        print(f"[BigOAds] API Request: POST {url}", file=sys.stderr)
        
        # Log headers (mask sensitive data)
        masked_headers = _mask_sensitive_data(headers.copy())
        print(f"[BigOAds] Request Headers: {json.dumps(masked_headers, indent=2)}", file=sys.stderr)
        
        # Log payload WITHOUT masking for debugging (no sensitive data in unit payload)
        print(f"[BigOAds] Request Payload (full): {json.dumps(payload, indent=2, ensure_ascii=False)}", file=sys.stderr)
        print(f"[BigOAds] Payload keys: {list(payload.keys())}", file=sys.stderr)
        print(f"[BigOAds] Payload values: {list(payload.values())}", file=sys.stderr)
        
        # Also log via logger
        logger.info(f"[BigOAds] ========== CREATE UNIT REQUEST ==========")
        logger.info(f"[BigOAds] API Request: POST {url}")
        logger.info(f"[BigOAds] Request Headers: {json.dumps(masked_headers, indent=2)}")
        logger.info(f"[BigOAds] Request Payload (full): {json.dumps(payload, indent=2, ensure_ascii=False)}")
        logger.info(f"[BigOAds] Payload keys: {list(payload.keys())}")
        logger.info(f"[BigOAds] Payload values: {list(payload.values())}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            print(f"[BigOAds] Response Status: {response.status_code}", file=sys.stderr)
            print(f"[BigOAds] Response Headers: {dict(response.headers)}", file=sys.stderr)
            
            # Try to parse JSON response
            try:
                result = response.json()
                print(f"[BigOAds] Response Body (JSON): {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            except ValueError:
                # If not JSON, log as text
                print(f"[BigOAds] Response Body (text): {response.text[:500]}", file=sys.stderr)
                result = {"status": 1, "code": "PARSE_ERROR", "msg": f"Non-JSON response: {response.text[:200]}"}
            
            # Also log via logger
            logger.info(f"[BigOAds] Response Status: {response.status_code}")
            logger.info(f"[BigOAds] Response Headers: {dict(response.headers)}")
            if "result" in locals():
                logger.info(f"[BigOAds] Response Body (JSON): {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # BigOAds API 응답 형식에 맞게 정규화
            if result.get("code") == 0 or result.get("status") == 0:
                print(f"[BigOAds] ✅ Success: {result.get('msg', 'Success')}", file=sys.stderr)
                logger.info(f"[BigOAds] ✅ Success: {result.get('msg', 'Success')}")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or result.get("status") or "N/A"
                print(f"[BigOAds] ❌ Error: {error_code} - {error_msg}", file=sys.stderr)
                print(f"[BigOAds] Full error response: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
                logger.error(f"[BigOAds] ❌ Error: {error_code} - {error_msg}")
                logger.error(f"[BigOAds] Full error response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            print(f"[BigOAds] ❌ API Error (Create Unit): {str(e)}", file=sys.stderr)
            print(f"[BigOAds] Error type: {type(e).__name__}", file=sys.stderr)
            
            if hasattr(e, 'response') and e.response is not None:
                print(f"[BigOAds] Response Status: {e.response.status_code}", file=sys.stderr)
                print(f"[BigOAds] Response Headers: {dict(e.response.headers)}", file=sys.stderr)
                try:
                    error_body = e.response.json()
                    print(f"[BigOAds] Error Response (JSON): {json.dumps(error_body, indent=2, ensure_ascii=False)}", file=sys.stderr)
                except:
                    error_text = e.response.text
                    print(f"[BigOAds] Error Response (text, first 500 chars): {error_text[:500]}", file=sys.stderr)
            else:
                print(f"[BigOAds] No response object available", file=sys.stderr)
            
            print("=" * 60, file=sys.stderr)
            
            # Also log via logger
            logger.error(f"[BigOAds] ❌ API Error (Create Unit): {str(e)}")
            logger.error(f"[BigOAds] Error type: {type(e).__name__}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"[BigOAds] Response Status: {e.response.status_code}")
                try:
                    error_body = e.response.json()
                    logger.error(f"[BigOAds] Error Response (JSON): {json.dumps(error_body, indent=2, ensure_ascii=False)}")
                except:
                    logger.error(f"[BigOAds] Error Response (text): {e.response.text[:500]}")
            
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": f"Error creating unit: {str(e)}"
            }
    
    def _create_inmobi_unit(self, payload: Dict) -> Dict:
        """Create unit (placement) via InMobi API"""
        url = "https://publisher.inmobi.com/rest/api/v1/placements"
        
        # InMobi API 인증: x-client-id, x-account-id, x-client-secret 헤더 사용
        username = _get_env_var("INMOBI_USERNAME")  # x-client-id (email ID)
        account_id = _get_env_var("INMOBI_ACCOUNT_ID")  # x-account-id (Account ID)
        client_secret = _get_env_var("INMOBI_CLIENT_SECRET")  # x-client-secret (API key)
        
        if not username or not account_id or not client_secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set in .env file or Streamlit secrets"
            }
        
        # InMobi 인증 헤더 설정
        headers = {
            "x-client-id": username,
            "x-account-id": account_id,
            "x-client-secret": client_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        logger.info(f"[InMobi] API Request: POST {url}")
        logger.info(f"[InMobi] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[InMobi] Request Payload: {json.dumps(_mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log response even if status code is not 200
            logger.info(f"[InMobi] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[InMobi] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[InMobi] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            response.raise_for_status()
            
            # InMobi API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[InMobi] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[InMobi] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_applovin_unit(self, payload: Dict) -> Dict:
        """Create ad unit via AppLovin API
        
        API: POST https://o.applovin.com/mediation/v1/ad_unit
        
        Args:
            payload: Unit creation payload with name, platform, package_name, ad_format
        
        Returns:
            API response dict
        """
        api_key = _get_env_var("APPLOVIN_API_KEY")
        
        if not api_key:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "APPLOVIN_API_KEY must be set in .env file or Streamlit secrets"
            }
        
        url = "https://o.applovin.com/mediation/v1/ad_unit"
        
        headers = {
            "Accept": "application/json",
            "Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"[AppLovin] API Request: POST {url}")
        logger.info(f"[AppLovin] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[AppLovin] Request Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"[AppLovin] Response Status: {response.status_code}")
            
            # Handle empty response
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"[AppLovin] Empty response body (status {response.status_code})")
                return {
                    "status": 1,
                    "code": "EMPTY_RESPONSE",
                    "msg": "Empty response from API"
                }
            
            try:
                result = response.json()
                logger.info(f"[AppLovin] Response Body: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"[AppLovin] JSON decode error: {str(e)}")
                logger.error(f"[AppLovin] Response text: {response_text[:500]}")
                return {
                    "status": 1,
                    "code": "JSON_ERROR",
                    "msg": f"Invalid JSON response: {str(e)}"
                }
            
            if response.status_code == 200:
                # Success response
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Error response
                error_msg = result.get("message") or result.get("msg") or result.get("error") or "Unknown error"
                error_code = result.get("code") or response.status_code
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[AppLovin] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[AppLovin] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[AppLovin] Error Response (text): {e.response.text}")
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
        timestamp = int(time.time())  # Posix timestamp (seconds)
        nonce = random.randint(1, 2147483647)  # Random integer (1 to 2^31-1)
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
    
    def _get_ironsource_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get IronSource applications list from API
        
        API: GET https://platform.ironsrc.com/partners/publisher/applications/v6
        Headers:
            Authorization: Bearer {token}
            Content-Type: application/json
        Query Parameters (optional):
            platform: "ios" or "android" (from IRONSOURCE_PLATFORM env var)
            appStatus: "Active" or "archived" (from IRONSOURCE_APP_STATUS env var)
            appKey: Specific app key to filter (if provided)
        
        Args:
            app_key: Optional app key to filter by. If provided, only returns that app.
        """
        try:
            headers = self._get_ironsource_headers()
            if not headers:
                logger.warning("[IronSource] Cannot get apps: authentication failed")
                return []
            
            url = "https://platform.ironsrc.com/partners/publisher/applications/v6"
            
            # Build query parameters (optional) - reference code 방식
            params = {}
            platform = _get_env_var("IRONSOURCE_PLATFORM")  # ios / android
            if platform:
                params['platform'] = platform
            
            app_status = _get_env_var("IRONSOURCE_APP_STATUS")  # Active / archived
            if app_status:
                params['appStatus'] = app_status
            
            # If app_key is provided, use it as filter parameter
            if app_key:
                params['appKey'] = app_key
                logger.info(f"[IronSource] Filtering by appKey: {app_key}")
            
            logger.info(f"[IronSource] API Request: GET {url}")
            if params:
                logger.info(f"[IronSource] Query Parameters: {json.dumps(params, indent=2)}")
            else:
                logger.info("[IronSource] Query Parameters: None (전체 앱 조회)")
            masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
            logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
            
            response = requests.get(url, headers=headers, params=params if params else None, timeout=30)
            
            logger.info(f"[IronSource] Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[IronSource] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
                
                # IronSource API 응답 형식에 맞게 파싱
                # 응답은 JSON 배열 또는 객체일 수 있음
                # 예시 응답: [{"appKey": "22449a47d", "appName": "-", "platform": "iOS", ...}, ...]
                apps = []
                if isinstance(result, list):
                    # 응답이 직접 배열인 경우
                    apps = result
                    logger.info(f"[IronSource] Apps count (array): {len(apps)}")
                elif isinstance(result, dict):
                    # 응답이 객체인 경우 applications 필드 확인
                    if "applications" in result:
                        apps = result["applications"]
                    elif "data" in result:
                        apps = result["data"]
                    elif "result" in result:
                        apps = result["result"]
                    else:
                        # 단일 앱 객체인 경우 배열로 감싸기
                        if "appKey" in result:
                            apps = [result]
                    
                    if not isinstance(apps, list):
                        apps = []
                    logger.info(f"[IronSource] Apps count (object): {len(apps)}")
                else:
                    logger.warning(f"[IronSource] Unexpected response format: {type(result)}")
                    apps = []
            elif response.status_code == 401:
                logger.error("[IronSource] Authentication failed (401 Unauthorized)")
                logger.error(f"[IronSource] Response: {response.text[:500]}")
                logger.error("[IronSource] Bearer Token이 만료되었거나 유효하지 않습니다.")
                return []
            else:
                logger.error(f"[IronSource] API request failed with status {response.status_code}")
                logger.error(f"[IronSource] Response: {response.text[:500]}")
                return []
            
            # 표준 형식으로 변환
            formatted_apps = []
            for app in apps:
                # IronSource app 객체에서 appKey 추출
                app_key = app.get("appKey") or app.get("key") or app.get("id")
                app_name = app.get("appName") or app.get("name") or app.get("title", "Unknown")
                
                if app_key:
                    # Platform 변환: API 응답은 "iOS" 또는 "Android" (대문자 시작)
                    platform_raw = app.get("platform", "")
                    if isinstance(platform_raw, str):
                        platform_raw_lower = platform_raw.lower()
                    else:
                        platform_raw_lower = ""
                    
                    if platform_raw_lower == "android":
                        platform_display = "Android"
                        platform_str = "android"
                        platform_num = 1
                    elif platform_raw_lower == "ios":
                        platform_display = "iOS"
                        platform_str = "ios"
                        platform_num = 2
                    else:
                        # 기본값은 Android
                        platform_display = "Android"
                        platform_str = "android"
                        platform_num = 1
                    
                    # appName이 "-"인 경우 "Unknown"으로 표시
                    if app_name == "-" or not app_name or app_name.strip() == "":
                        app_name = "Unknown"
                    
                    # Store URL 추출 (여러 가능한 필드명 확인)
                    store_url = app.get("storeUrl") or app.get("store_url") or ""
                    
                    # Bundle ID 추출 (IronSource API 응답에서 bundleId 필드 사용)
                    bundle_id = app.get("bundleId") or ""
                    
                    # Package name은 bundleId와 동일 (IronSource의 경우)
                    pkg_name = bundle_id
                    
                    formatted_apps.append({
                        "appCode": app_key,  # IronSource는 appKey 사용
                        "appKey": app_key,  # IronSource 전용 필드
                        "name": app_name,
                        "platform": platform_display,  # "Android" or "iOS"
                        "platformNum": platform_num,  # 1 or 2
                        "platformStr": platform_str,  # "android" or "ios"
                        "pkgName": pkg_name,  # bundleId와 동일
                        "bundleId": bundle_id,  # IronSource bundleId (Mediation Ad Unit Name 생성에 사용)
                        "storeUrl": store_url  # Store URL (optional)
                    })
                    
                    logger.debug(f"[IronSource] Parsed app: appKey={app_key}, name={app_name}, platform={platform_display}, storeUrl={store_url[:50] if store_url else 'N/A'}")
            
            # 최신순 정렬 (appKey나 id 기준으로 정렬, 또는 timestamp가 있으면 그것으로)
            # IronSource 응답에 timestamp가 있다면 그것으로 정렬
            if formatted_apps:
                # timestamp나 createdAt 필드가 있으면 사용, 없으면 appKey로 정렬
                formatted_apps.sort(
                    key=lambda x: (
                        x.get("timestamp", 0) if isinstance(x.get("timestamp"), (int, float)) else 0,
                        x.get("appKey", "")
                    ),
                    reverse=True
                )
            
            logger.info(f"[IronSource] Found {len(formatted_apps)} apps")
            return formatted_apps
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[IronSource] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[IronSource] Error Response (text): {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"[IronSource] Unexpected error getting apps: {str(e)}")
            return []
    
    def _get_bigoads_apps(self) -> List[Dict]:
        """Get apps list from BigOAds API"""
        # Add delay to avoid QPS limit (BigOAds has strict rate limiting)
        import time
        time.sleep(0.5)  # 500ms delay to avoid QPS limit
        
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
    
    def _get_inmobi_apps(self) -> List[Dict]:
        """Get apps list from InMobi API
        
        API: GET https://publisher.inmobi.com/rest/api/v2/apps
        Headers: x-client-id, x-account-id, x-client-secret
        """
        url = "https://publisher.inmobi.com/rest/api/v2/apps"
        
        # InMobi API 인증: x-client-id, x-account-id, x-client-secret 헤더 사용
        username = _get_env_var("INMOBI_USERNAME")  # x-client-id (email ID)
        account_id = _get_env_var("INMOBI_ACCOUNT_ID")  # x-account-id (Account ID)
        client_secret = _get_env_var("INMOBI_CLIENT_SECRET")  # x-client-secret (API key)
        
        if not username or not account_id or not client_secret:
            logger.error("[InMobi] INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set")
            return []
        
        # InMobi 인증 헤더 설정
        headers = {
            "x-client-id": username,
            "x-account-id": account_id,
            "x-client-secret": client_secret,
            "Accept": "application/json",
        }
        
        # Query parameters
        params = {
            "pageNum": 1,
            "pageLength": 10,
            "status": "ACTIVE",
        }
        
        logger.info(f"[InMobi] API Request: GET {url}")
        logger.info(f"[InMobi] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[InMobi] Request Params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            logger.info(f"[InMobi] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[InMobi] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[InMobi] Response Text: {response.text}")
                return []
            
            response.raise_for_status()
            
            # InMobi API 응답 형식에 맞게 처리
            # Response format: {"data": {"records": [...], "totalRecords": ...}} or {"data": {"apps": [...]}} or {"data": [...]}
            if response.status_code == 200:
                # Extract apps from response
                if isinstance(result, dict):
                    apps_data = result.get("data", {})
                    if isinstance(apps_data, dict):
                        apps = apps_data.get("records", apps_data.get("apps", []))
                        total = apps_data.get("totalRecords", len(apps) if isinstance(apps, list) else 0)
                    else:
                        apps = apps_data if isinstance(apps_data, list) else []
                        total = len(apps) if isinstance(apps, list) else 0
                elif isinstance(result, list):
                    apps = result
                    total = len(apps)
                else:
                    logger.error(f"[InMobi] Unexpected response format: {type(result)}")
                    return []
                
                logger.info(f"[InMobi] Extracted {len(apps)} apps from API response (total: {total})")
                
                # Convert to standard format
                formatted_apps = []
                for app in apps:
                    if isinstance(app, dict):
                        # Extract app information (field names may vary)
                        app_id = app.get("appId") or app.get("id") or app.get("app_id")
                        app_name = app.get("appName") or app.get("name") or app.get("app_name")
                        platform = app.get("platform") or app.get("os") or "N/A"
                        status = app.get("status") or "N/A"
                        
                        formatted_apps.append({
                            "appCode": str(app_id) if app_id else "N/A",
                            "appId": str(app_id) if app_id else "N/A",  # For InMobi, appCode and appId are the same
                            "name": app_name or "Unknown",
                            "platform": platform,
                            "status": status,
                            "bundleId": app.get("bundleId") or app.get("bundle_id") or app.get("packageName") or "",  # For placement name generation
                        })
                
                logger.info(f"[InMobi] Converted to {len(formatted_apps)} apps in standard format")
                return formatted_apps
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                logger.error(f"[InMobi] API Error (Get Apps): {error_msg}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[InMobi] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[InMobi] Error Response (text): {e.response.text}")
            return []
    
    def _get_fyber_apps(self, publisher_id: Optional[int] = None, app_id: Optional[int] = None) -> List[Dict]:
        """Get apps list from Fyber (DT) API
        
        API: GET https://console.fyber.com/api/management/v1/app?publisherId={publisherId}
        or GET https://console.fyber.com/api/management/v1/app?appId={appId}
        
        Args:
            publisher_id: Publisher ID (optional)
            app_id: App ID (optional)
        """
        # Get access token
        access_token = self._get_fyber_access_token()
        if not access_token:
            logger.error("[Fyber] Failed to get access token for get_apps")
            return []
        
        # Get publisher_id or app_id from environment if not provided
        if not publisher_id and not app_id:
            publisher_id_str = _get_env_var("FYBER_PUBLISHER_ID") or _get_env_var("DT_PUBLISHER_ID")
            app_id_str = _get_env_var("FYBER_APP_ID") or _get_env_var("DT_APP_ID")
            
            if app_id_str:
                try:
                    app_id = int(app_id_str)
                except ValueError:
                    logger.warning(f"[Fyber] Invalid FYBER_APP_ID: {app_id_str}")
            elif publisher_id_str:
                try:
                    publisher_id = int(publisher_id_str)
                except ValueError:
                    logger.warning(f"[Fyber] Invalid FYBER_PUBLISHER_ID: {publisher_id_str}")
        
        if not publisher_id and not app_id:
            logger.error("[Fyber] publisher_id or app_id is required for get_apps")
            return []
        
        url = "https://console.fyber.com/api/management/v1/app"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {}
        if publisher_id:
            params["publisherId"] = publisher_id
        if app_id:
            params["appId"] = app_id
        
        logger.info(f"[Fyber] Get Apps API Request: GET {url}")
        logger.info(f"[Fyber] Params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[Fyber] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
                
                # Parse response - can be list or dict
                apps = []
                if isinstance(result, list):
                    apps = result
                elif isinstance(result, dict):
                    apps = result.get("apps", result.get("data", result.get("list", [])))
                    if not isinstance(apps, list):
                        # Single app object
                        apps = [result]
                
                # Convert to standard format
                formatted_apps = []
                for app in apps:
                    app_id_val = app.get("id") or app.get("appId")
                    app_name = app.get("name") or "Unknown"
                    platform = app.get("platform", "").lower()
                    bundle_id = app.get("bundle") or app.get("bundleId") or ""
                    
                    formatted_apps.append({
                        "appCode": str(app_id_val) if app_id_val else "N/A",
                        "appId": str(app_id_val) if app_id_val else "N/A",
                        "name": app_name,
                        "platform": platform,
                        "status": app.get("status") or "Active",
                        "bundleId": bundle_id,
                    })
                
                logger.info(f"[Fyber] Converted to {len(formatted_apps)} apps in standard format")
                return formatted_apps
            else:
                logger.error(f"[Fyber] Failed to get apps. Status: {response.status_code}")
                logger.error(f"[Fyber] Response: {response.text}")
                
                if response.status_code == 401:
                    logger.error("[Fyber] 💡 인증 오류: Access Token이 만료되었거나 유효하지 않습니다.")
                elif response.status_code == 403:
                    logger.error("[Fyber] 💡 권한 오류: Publisher ID 또는 App ID에 대한 접근 권한이 없습니다.")
                elif response.status_code == 404:
                    logger.error("[Fyber] 💡 리소스를 찾을 수 없음: Publisher ID 또는 App ID가 올바른지 확인해주세요.")
                
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[Fyber] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Fyber] Error Response (text): {e.response.text}")
            return []
    
    def _get_vungle_jwt_token(self) -> Optional[str]:
        """Get Vungle JWT Token for API calls
        
        API: GET https://auth-api.vungle.com/v2/auth
        Header: x-api-key: [secret_token]
        
        Returns:
            JWT Token string or None
        """
        # Check for existing JWT token in environment
        jwt_token = _get_env_var("LIFTOFF_JWT_TOKEN") or _get_env_var("VUNGLE_JWT_TOKEN")
        if jwt_token:
            logger.info("[Vungle] Using existing JWT token from environment")
            return jwt_token
        
        # Get secret token
        secret_token = _get_env_var("LIFTOFF_SECRET_TOKEN") or _get_env_var("VUNGLE_SECRET_TOKEN")
        if not secret_token:
            logger.error("[Vungle] LIFTOFF_SECRET_TOKEN or VUNGLE_SECRET_TOKEN not found")
            return None
        
        # Request new JWT token
        auth_url = "https://auth-api.vungle.com/v2/auth"
        headers = {
            "x-api-key": secret_token
        }
        
        logger.info(f"[Vungle] Requesting JWT token from {auth_url}")
        
        try:
            response = requests.get(auth_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for error messages
                if "messages" in result:
                    error_msg = result.get("messages", [])
                    error_code = result.get("code")
                    logger.error(f"[Vungle] Error getting JWT token: {error_msg} (code: {error_code})")
                    return None
                
                jwt_token = result.get("token")
                if jwt_token:
                    logger.info("[Vungle] JWT token obtained successfully")
                    return jwt_token
                else:
                    logger.error("[Vungle] JWT token not found in response")
                    return None
            else:
                logger.error(f"[Vungle] Failed to get JWT token: {response.status_code} - {response.text[:200]}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[Vungle] Error requesting JWT token: {str(e)}")
            return None
    
    def _get_vungle_placements(self) -> List[Dict]:
        """Get all placements from Vungle API
        
        API: GET https://publisher-api.vungle.com/api/v1/placements
        
        Returns:
            List of placement dicts (each contains app and unit info)
        """
        jwt_token = self._get_vungle_jwt_token()
        if not jwt_token:
            logger.error("[Vungle] Failed to get JWT token for placements")
            return []
        
        base_url = "https://publisher-api.vungle.com/api/v1"
        placements_url = f"{base_url}/placements"
        
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        
        logger.info(f"[Vungle] Fetching all placements from {placements_url}")
        
        try:
            response = requests.get(placements_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response - can be list or dict
                placements = []
                if isinstance(result, list):
                    placements = result
                elif isinstance(result, dict):
                    placements = result.get("data", result.get("placements", result.get("list", [])))
                    if not isinstance(placements, list):
                        placements = []
                
                logger.info(f"[Vungle] Retrieved {len(placements)} placements")
                return placements
            else:
                logger.error(f"[Vungle] Failed to get placements: {response.status_code} - {response.text[:200]}")
                if response.status_code == 401:
                    logger.error("[Vungle] Authentication failed - JWT token may be expired")
                elif response.status_code == 403:
                    logger.error("[Vungle] Permission denied")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[Vungle] Error fetching placements: {str(e)}")
            return []
    
    def _get_unity_projects(self) -> List[Dict]:
        """Get all projects (apps) from Unity API
        
        API: GET https://services.api.unity.com/monetize/v1/organizations/{organizationId}/projects
        
        Returns:
            List of project dicts
        """
        organization_id = _get_env_var("UNITY_ORGANIZATION_ID")
        if not organization_id:
            logger.error("[Unity] UNITY_ORGANIZATION_ID not found")
            return []
        
        # Get Unity API credentials for Basic Auth
        key_id = _get_env_var("UNITY_KEY_ID")
        secret_key = _get_env_var("UNITY_SECRET_KEY")
        
        if not key_id or not secret_key:
            logger.error("[Unity] UNITY_KEY_ID or UNITY_SECRET_KEY not found")
            return []
        
        # Create Basic Auth header
        credentials = f"{key_id}:{secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        url = f"https://services.api.unity.com/monetize/v1/organizations/{organization_id}/projects"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json"
        }
        
        logger.info(f"[Unity] Fetching projects from {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response - can be list or dict
                projects = []
                if isinstance(result, list):
                    projects = result
                elif isinstance(result, dict):
                    projects = result.get("data", result.get("projects", result.get("list", [])))
                    if not isinstance(projects, list):
                        projects = []
                
                # For Unity, ensure stores field is preserved (can be JSON string or dict)
                # The API might return stores as a JSON string that needs parsing
                for project in projects:
                    stores = project.get("stores", "")
                    if stores and isinstance(stores, str):
                        # Try to parse if it's a JSON string
                        try:
                            import json
                            # Handle escaped JSON strings
                            parsed_stores = json.loads(stores)
                            # Keep both original string and parsed dict for compatibility
                            project["stores_parsed"] = parsed_stores
                        except (json.JSONDecodeError, TypeError):
                            # If parsing fails, keep original string
                            pass
                
                logger.info(f"[Unity] Retrieved {len(projects)} projects")
                if projects:
                    logger.info(f"[Unity] First project keys: {list(projects[0].keys())}")
                    logger.info(f"[Unity] First project stores type: {type(projects[0].get('stores', ''))}")
                
                return projects
            else:
                logger.error(f"[Unity] Failed to get projects: {response.status_code} - {response.text[:200]}")
                if response.status_code == 401:
                    logger.error("[Unity] Authentication failed - check KEY_ID and SECRET_KEY")
                elif response.status_code == 403:
                    logger.error("[Unity] Permission denied")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[Unity] Error fetching projects: {str(e)}")
            return []
    
    def _get_unity_ad_units(self, project_id: str) -> Dict:
        """Get ad units for a Unity project
        
        API: GET https://services.api.unity.com/monetize/v1/projects/{projectId}/adunits
        
        Args:
            project_id: Unity project ID
        
        Returns:
            Dict with "apple" and "google" keys containing ad units
        """
        # Get Unity API credentials for Basic Auth
        key_id = _get_env_var("UNITY_KEY_ID")
        secret_key = _get_env_var("UNITY_SECRET_KEY")
        
        if not key_id or not secret_key:
            logger.error("[Unity] UNITY_KEY_ID or UNITY_SECRET_KEY not found")
            return {}
        
        # Create Basic Auth header
        credentials = f"{key_id}:{secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        url = f"https://services.api.unity.com/monetize/v1/projects/{project_id}/adunits"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json"
        }
        
        logger.info(f"[Unity] Fetching ad units from {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[Unity] Retrieved ad units for project {project_id}")
                logger.info(f"[Unity] Ad units response type: {type(result)}")
                if isinstance(result, dict):
                    logger.info(f"[Unity] Ad units response keys: {list(result.keys())}")
                    for key, value in result.items():
                        if isinstance(value, list):
                            logger.info(f"[Unity] {key} has {len(value)} units")
                            if value:
                                logger.info(f"[Unity] First {key} unit keys: {list(value[0].keys())}")
                                logger.info(f"[Unity] First {key} unit sample: {json.dumps(value[0], indent=2)[:500]}")
                        elif isinstance(value, dict):
                            logger.info(f"[Unity] {key} is dict with keys: {list(value.keys())}")
                return result  # Returns { "apple": {}, "google": {} }
            else:
                logger.error(f"[Unity] Failed to get ad units: {response.status_code} - {response.text[:200]}")
                if response.status_code == 401:
                    logger.error("[Unity] Authentication failed - check KEY_ID and SECRET_KEY")
                elif response.status_code == 403:
                    logger.error("[Unity] Permission denied")
                elif response.status_code == 404:
                    logger.error(f"[Unity] Project {project_id} not found")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"[Unity] Error fetching ad units: {str(e)}")
            return {}
    
    def get_apps(self, network: str, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from network
        
        Args:
            network: Network name (e.g., "bigoads", "ironsource", "fyber", "vungle")
            app_key: Optional app key to filter by (for IronSource)
        """
        if network == "bigoads":
            return self._get_bigoads_apps()
        elif network == "ironsource":
            return self._get_ironsource_apps(app_key=app_key)
        elif network == "mintegral":
            return self._get_mintegral_apps()
        elif network == "inmobi":
            return self._get_inmobi_apps()
        elif network == "fyber":
            # For Fyber, app_key can be publisher_id or app_id
            publisher_id = None
            app_id = None
            if app_key:
                try:
                    if app_key.startswith("app:"):
                        app_id = int(app_key.split(":")[1])
                    else:
                        publisher_id = int(app_key)
                except ValueError:
                    logger.warning(f"[Fyber] Invalid app_key format: {app_key}")
            return self._get_fyber_apps(publisher_id=publisher_id, app_id=app_id)
        elif network == "vungle":
            # For Vungle, placements contain both app and unit info
            # Extract unique apps from placements
            placements = self._get_vungle_placements()
            apps_dict = {}
            for placement in placements:
                app_id = placement.get("applicationId")
                if app_id and app_id not in apps_dict:
                    apps_dict[app_id] = {
                        "appId": app_id,
                        "name": placement.get("applicationName", ""),
                        "platform": placement.get("platform", ""),
                        "packageName": placement.get("packageName", ""),
                        "bundleId": placement.get("bundleId", "")
                    }
            return list(apps_dict.values())
        elif network == "unity":
            return self._get_unity_projects()
        
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

