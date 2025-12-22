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
    try:
        # Try Streamlit secrets first (for Streamlit Cloud)
        if hasattr(st, 'secrets') and st.secrets and key in st.secrets:
            return st.secrets[key]
    except:
        pass
    
    # Fallback to environment variables (from .env file or system env)
    return os.getenv(key)

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
    
    def _get_ironsource_token(self) -> Optional[str]:
        """Get IronSource bearer token, refreshing if needed"""
        # Try bearer token first
        bearer_token = _get_env_var("IRONSOURCE_BEARER_TOKEN") or _get_env_var("IRONSOURCE_API_TOKEN")
        if bearer_token:
            return bearer_token
        
        # If no bearer token, try to get from refresh token
        refresh_token = _get_env_var("IRONSOURCE_REFRESH_TOKEN")
        secret_key = _get_env_var("IRONSOURCE_SECRET_KEY")
        
        if refresh_token and secret_key:
            # Try to refresh the token
            new_token = self._refresh_ironsource_token(refresh_token, secret_key)
            if new_token:
                return new_token
        
        return None
    
    def _refresh_ironsource_token(self, refresh_token: str, secret_key: str) -> Optional[str]:
        """Refresh IronSource bearer token using refresh token"""
        # IronSource token refresh endpoint (if available)
        # Note: This may vary depending on IronSource API version
        try:
            url = "https://platform.ironsrc.com/partners/publisher/auth/refresh"
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "refreshToken": refresh_token,
                "secretKey": secret_key
            }
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result.get("accessToken") or result.get("bearerToken")
        except Exception:
            # If refresh fails, return None
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
                "msg": "IronSource authentication token not found. Please set IRONSOURCE_BEARER_TOKEN (or IRONSOURCE_API_TOKEN) in .env file, or provide IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY for automatic token refresh."
            }
        
        url = "https://platform.ironsrc.com/partners/publisher/applications/v6"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Log request
        logger.info(f"[IronSource] API Request: POST {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        logger.info(f"[IronSource] Request Body: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            # Log response status
            logger.info(f"[IronSource] Response Status: {response.status_code}")
            
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
        token = self._get_ironsource_token()
        if not token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "IronSource authentication token not found. Please set IRONSOURCE_BEARER_TOKEN (or IRONSOURCE_API_TOKEN) in .env file, or provide IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY for automatic token refresh."
            }
        
        url = f"https://platform.ironsrc.com/levelPlay/adUnits/v1/{app_key}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
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
        developer_id = os.getenv("BIGOADS_DEVELOPER_ID")
        token = os.getenv("BIGOADS_TOKEN")
        
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
    
    def get_apps(self, network: str) -> List[Dict]:
        """Get apps list from network"""
        # Mock implementation
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
        
        # Log error to console
        logger.error(f"API Error: {error_code} - {error_msg}")
        print(f"[API Error] {error_code} - {error_msg}", file=sys.stderr)
        
        st.error(f"❌ Error: {error_code} - {error_msg}")
        
        # Display full error response in expander
        with st.expander("📥 Full Error Response", expanded=False):
            st.json(_mask_sensitive_data(response))
        
        return None

