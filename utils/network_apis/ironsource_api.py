"""IronSource API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
from .base_network_api import BaseNetworkAPI, _get_env_var, _mask_sensitive_data
from ..network_auth.ironsource_auth import IronSourceAuth

logger = logging.getLogger(__name__)


class IronSourceAPI(BaseNetworkAPI):
    """IronSource API implementation"""
    
    def __init__(self):
        super().__init__("IronSource")
        self.auth = IronSourceAuth()
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via IronSource API"""
        headers = self.auth.get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "IronSource authentication token not found. Please check IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY in .env file or Streamlit secrets."
            }
        
        url = "https://platform.ironsrc.com/partners/publisher/applications/v6"
        
        # Log request
        self.logger.info(f"[IronSource] API Request: POST {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        self.logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        self.logger.info(f"[IronSource] Request Body: {json.dumps(payload, indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=payload)
            
            # Check for 401 Unauthorized - token might be expired
            if response.status_code == 401:
                self.logger.warning("[IronSource] Received 401 Unauthorized. Token may be expired. Attempting to refresh...")
                
                # Try to refresh token
                refresh_token = _get_env_var("IRONSOURCE_REFRESH_TOKEN")
                secret_key = _get_env_var("IRONSOURCE_SECRET_KEY")
                
                if refresh_token and secret_key:
                    new_token = self.auth.refresh_token(refresh_token, secret_key)
                    if new_token:
                        # Retry request with new token
                        self.logger.info("[IronSource] Retrying request with refreshed token...")
                        headers["Authorization"] = f"Bearer {new_token}"
                        response = self._make_request("POST", url, headers=headers, json_data=payload)
                        self.logger.info(f"[IronSource] Retry Response Status: {response.status_code}")
                    else:
                        self.logger.error("[IronSource] Token refresh failed. Please check IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY")
                else:
                    self.logger.error("[IronSource] No refresh token available. Please set IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY in .env file")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Log response
            self.logger.info(f"[IronSource] Response Body: {json.dumps(result, indent=2)}")
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
            self.logger.error(f"[IronSource] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[IronSource] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create unit (placement) via IronSource API
        
        Args:
            payload: Single ad unit object (will be wrapped in array)
            app_key: App key (required)
        """
        if not app_key:
            return {
                "status": 1,
                "code": "MISSING_APP_KEY",
                "msg": "App key is required for IronSource"
            }
        # IronSource accepts an array, so wrap the payload
        return self.create_placements(app_key, [payload])
    
    def create_placements(self, app_key: str, ad_units: List[Dict]) -> Dict:
        """Create placements via IronSource API
        
        Args:
            app_key: Application key from IronSource platform
            ad_units: List of ad unit objects to create
        """
        headers = self.auth.get_headers()
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
        self.logger.info(f"[IronSource] API Request: POST {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        self.logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        self.logger.info(f"[IronSource] Request Body: {json.dumps(_mask_sensitive_data(ad_units), indent=2)}")
        
        try:
            # API accepts an array of ad units
            response = self._make_request("POST", url, headers=headers, json_data=ad_units)
            
            # Check response status before parsing
            if response.status_code >= 400:
                # Error response
                try:
                    error_body = response.json()
                    self.logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                    error_msg = error_body.get("message") or error_body.get("msg") or error_body.get("error") or response.text
                    error_code = error_body.get("code") or error_body.get("errorCode") or str(response.status_code)
                except:
                    error_msg = response.text or f"HTTP {response.status_code}"
                    error_code = str(response.status_code)
                    self.logger.error(f"[IronSource] Error Response (text): {error_msg}")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
            
            # Success response - handle empty or invalid JSON
            response_text = response.text.strip()
            if not response_text:
                # Empty response
                self.logger.warning(f"[IronSource] Empty response body (status {response.status_code})")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success (empty response)",
                    "result": {}
                }
            
            try:
                result = response.json()
                # Log response
                self.logger.info(f"[IronSource] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except json.JSONDecodeError as e:
                # Invalid JSON response
                self.logger.error(f"[IronSource] JSON decode error: {str(e)}")
                self.logger.error(f"[IronSource] Response text: {response_text[:500]}")
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
            self.logger.error(f"[IronSource] API Error (Placements): {str(e)}")
            error_msg = str(e)
            error_code = "API_ERROR"
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                    error_msg = error_body.get("message") or error_body.get("msg") or error_body.get("error") or error_msg
                    error_code = error_body.get("code") or error_body.get("errorCode") or error_code
                except:
                    self.logger.error(f"[IronSource] Error Response (text): {e.response.text}")
                    if e.response.text:
                        error_msg = e.response.text
            
            return {
                "status": 1,
                "code": error_code,
                "msg": error_msg
            }
        except Exception as e:
            # Catch any other unexpected errors
            self.logger.error(f"[IronSource] Unexpected Error (Placements): {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                "status": 1,
                "code": "UNEXPECTED_ERROR",
                "msg": str(e)
            }
    
    def update_ad_units(self, app_key: str, ad_units: List[Dict]) -> Dict:
        """Update (activate) ad units via IronSource API
        
        API: PUT https://platform.ironsrc.com/levelPlay/adUnits/v1/{appKey}
        
        Args:
            app_key: Application key from IronSource platform
            ad_units: List of ad unit objects to update
                Each ad unit must have:
                - mediationAdUnitId (required, uppercase U): ad unit ID from GET request
                - isPaused (optional): false to activate
                - mediationAdUnitName (optional): new name
        """
        headers = self.auth.get_headers()
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
            # Check both uppercase and lowercase versions
            if not (ad_unit.get("mediationAdUnitId") or ad_unit.get("mediationAdunitId")):
                return {
                    "status": 1,
                    "code": "INVALID_PAYLOAD",
                    "msg": f"mediationAdUnitId is required for ad unit at index {idx}"
                }
        
        # Log request
        self.logger.info(f"[IronSource] API Request: PUT {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        self.logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        self.logger.info(f"[IronSource] Request Body: {json.dumps(_mask_sensitive_data(ad_units), indent=2)}")
        
        try:
            # API accepts an array of ad units
            response = self._make_request("PUT", url, headers=headers, json_data=ad_units)
            
            # Check response status before parsing
            if response.status_code >= 400:
                # Error response
                try:
                    error_body = response.json()
                    self.logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                    error_msg = error_body.get("message") or error_body.get("msg") or error_body.get("error") or response.text
                    error_code = error_body.get("code") or error_body.get("errorCode") or str(response.status_code)
                except:
                    error_msg = response.text or f"HTTP {response.status_code}"
                    error_code = str(response.status_code)
                    self.logger.error(f"[IronSource] Error Response (text): {error_msg}")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
            
            # Success response - handle empty or invalid JSON
            response_text = response.text.strip()
            if not response_text:
                # Empty response
                self.logger.warning(f"[IronSource] Empty response body (status {response.status_code})")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success (empty response)",
                    "result": {}
                }
            
            try:
                result = response.json()
                # Log response
                self.logger.info(f"[IronSource] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
            except json.JSONDecodeError as e:
                # Invalid JSON response
                self.logger.error(f"[IronSource] JSON decode error: {str(e)}")
                self.logger.error(f"[IronSource] Response text: {response_text[:500]}")
                return {
                    "status": 1,
                    "code": "JSON_ERROR",
                    "msg": f"Invalid JSON response: {str(e)}. Response: {response_text[:200]}"
                }
            
            # IronSource API response format may vary, normalize it
            # For empty responses, result is already set to {}
            return {
                "status": 0,
                "code": 0,
                "msg": "Success" if result else "Success (empty response)",
                "result": result
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[IronSource] API Error (Update Ad Units): {str(e)}")
            error_msg = str(e)
            error_code = "API_ERROR"
            
            if hasattr(e, 'response') and e.response is not None:
                # Check if response is empty before trying to parse JSON
                response_text = e.response.text.strip() if e.response.text else ""
                if response_text:
                    try:
                        error_body = e.response.json()
                        self.logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                        error_msg = error_body.get("message") or error_body.get("msg") or error_body.get("error") or error_msg
                        error_code = error_body.get("code") or error_body.get("errorCode") or error_code
                    except json.JSONDecodeError:
                        # Response is not JSON
                        self.logger.error(f"[IronSource] Error Response (text): {response_text[:500]}")
                        error_msg = response_text
                else:
                    # Empty response with 200 status is actually success
                    if e.response.status_code == 200:
                        self.logger.info(f"[IronSource] Empty response with 200 status - treating as success")
                        return {
                            "status": 0,
                            "code": 0,
                            "msg": "Success (empty response)",
                            "result": {}
                        }
                    else:
                        self.logger.error(f"[IronSource] Empty error response (status {e.response.status_code})")
                        error_msg = f"HTTP {e.response.status_code} (empty response)"
                        error_code = str(e.response.status_code)
            
            return {
                "status": 1,
                "code": error_code,
                "msg": error_msg
            }
        except Exception as e:
            # Catch any other unexpected errors
            self.logger.error(f"[IronSource] Unexpected Error (Update Ad Units): {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                "status": 1,
                "code": "UNEXPECTED_ERROR",
                "msg": str(e)
            }
    
    def get_instances(self, app_key: str) -> Dict:
        """Get instances via IronSource API
        
        API: GET https://platform.ironsrc.com/levelPlay/network/instances/v4/{appKey}/
        
        Args:
            app_key: Application key from IronSource platform
        
        Returns:
            Dict with status, code, msg, and result (list of instances)
        """
        headers = self.auth.get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "IronSource authentication token not found. Please check IRONSOURCE_REFRESH_TOKEN and IRONSOURCE_SECRET_KEY in .env file or Streamlit secrets."
            }
        
        # API 문서에 따르면 appKey는 path parameter로 전달 (예시: /v4/142401ac1/)
        url = f"https://platform.ironsrc.com/levelPlay/network/instances/v4/{app_key}/"
        
        # Log request
        self.logger.info(f"[IronSource] API Request: GET {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        self.logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        
        try:
            response = self._make_request("GET", url, headers=headers)
            
            # Check response status before parsing
            if response.status_code >= 400:
                # Error response
                try:
                    error_body = response.json()
                    self.logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                    # Handle nested JSON string in error message
                    error_msg = error_body.get("message") or error_body.get("msg") or error_body.get("error") or response.text
                    error_code = error_body.get("code") or error_body.get("errorCode") or str(response.status_code)
                    
                    # If error_msg is a JSON string, try to parse it
                    if isinstance(error_msg, str) and error_msg.startswith("{") and error_msg.endswith("}"):
                        try:
                            parsed_error = json.loads(error_msg)
                            error_msg = parsed_error.get("errorMessage") or parsed_error.get("message") or parsed_error.get("msg") or error_msg
                            error_code = parsed_error.get("code") or parsed_error.get("errorCode") or error_code
                        except:
                            pass
                except:
                    error_msg = response.text or f"HTTP {response.status_code}"
                    error_code = str(response.status_code)
                    self.logger.error(f"[IronSource] Error Response (text): {error_msg}")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
            
            # Success response
            response_text = response.text.strip()
            if not response_text:
                self.logger.warning(f"[IronSource] Empty response body (status {response.status_code})")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success (empty response)",
                    "result": []
                }
            
            try:
                result = response.json()
                # Log response
                self.logger.info(f"[IronSource] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
                
                # Normalize response - should be a list
                instances = result if isinstance(result, list) else result.get("instances", result.get("data", result.get("list", [])))
                if not isinstance(instances, list):
                    instances = []
                
            except json.JSONDecodeError as e:
                # Invalid JSON response
                self.logger.error(f"[IronSource] JSON decode error: {str(e)}")
                self.logger.error(f"[IronSource] Response text: {response_text[:500]}")
                return {
                    "status": 1,
                    "code": "JSON_ERROR",
                    "msg": f"Invalid JSON response: {str(e)}. Response: {response_text[:200]}"
                }
            
            return {
                "status": 0,
                "code": 0,
                "msg": "Success",
                "result": instances
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[IronSource] API Error (Get Instances): {str(e)}")
            error_msg = str(e)
            error_code = "API_ERROR"
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                    error_msg = error_body.get("message") or error_body.get("msg") or error_body.get("error") or error_msg
                    error_code = error_body.get("code") or error_body.get("errorCode") or error_code
                except:
                    self.logger.error(f"[IronSource] Error Response (text): {e.response.text}")
                    if e.response.text:
                        error_msg = e.response.text
            
            return {
                "status": 1,
                "code": error_code,
                "msg": error_msg
            }
        except Exception as e:
            # Catch any other unexpected errors
            self.logger.error(f"[IronSource] Unexpected Error (Get Instances): {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                "status": 1,
                "code": "UNEXPECTED_ERROR",
                "msg": str(e)
            }
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
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
            headers = self.auth.get_headers()
            if not headers:
                self.logger.warning("[IronSource] Cannot get apps: authentication failed")
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
                self.logger.info(f"[IronSource] Filtering by appKey: {app_key}")
            
            self.logger.info(f"[IronSource] API Request: GET {url}")
            if params:
                self.logger.info(f"[IronSource] Query Parameters: {json.dumps(params, indent=2)}")
            else:
                self.logger.info("[IronSource] Query Parameters: None (전체 앱 조회)")
            masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
            self.logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
            
            response = self._make_request("GET", url, headers=headers, params=params if params else None)
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"[IronSource] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
                
                # IronSource API 응답 형식에 맞게 파싱
                # 응답은 JSON 배열 또는 객체일 수 있음
                # 예시 응답: [{"appKey": "22449a47d", "appName": "-", "platform": "iOS", ...}, ...]
                apps = []
                if isinstance(result, list):
                    # 응답이 직접 배열인 경우
                    apps = result
                    self.logger.info(f"[IronSource] Apps count (array): {len(apps)}")
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
                    self.logger.info(f"[IronSource] Apps count (object): {len(apps)}")
                else:
                    self.logger.warning(f"[IronSource] Unexpected response format: {type(result)}")
                    apps = []
            elif response.status_code == 401:
                self.logger.error("[IronSource] Authentication failed (401 Unauthorized)")
                self.logger.error(f"[IronSource] Response: {response.text[:500]}")
                self.logger.error("[IronSource] Bearer Token이 만료되었거나 유효하지 않습니다.")
                return []
            else:
                self.logger.error(f"[IronSource] API request failed with status {response.status_code}")
                self.logger.error(f"[IronSource] Response: {response.text[:500]}")
                return []
            
            # 표준 형식으로 변환
            formatted_apps = []
            for app in apps:
                # IronSource app 객체에서 appKey 추출
                app_key_val = app.get("appKey") or app.get("key") or app.get("id")
                app_name = app.get("appName") or app.get("name") or app.get("title", "Unknown")
                
                if app_key_val:
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
                        "appCode": app_key_val,  # IronSource는 appKey 사용
                        "appKey": app_key_val,  # IronSource 전용 필드
                        "name": app_name,
                        "platform": platform_display,  # "Android" or "iOS"
                        "platformNum": platform_num,  # 1 or 2
                        "platformStr": platform_str,  # "android" or "ios"
                        "pkgName": pkg_name,  # bundleId와 동일
                        "bundleId": bundle_id,  # IronSource bundleId (Mediation Ad Unit Name 생성에 사용)
                        "storeUrl": store_url  # Store URL (optional)
                    })
                    
                    self.logger.debug(f"[IronSource] Parsed app: appKey={app_key_val}, name={app_name}, platform={platform_display}, storeUrl={store_url[:50] if store_url else 'N/A'}")
            
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
            
            self.logger.info(f"[IronSource] Found {len(formatted_apps)} apps")
            return formatted_apps
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[IronSource] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[IronSource] Error Response (text): {e.response.text}")
            return []
        except Exception as e:
            self.logger.error(f"[IronSource] Unexpected error getting apps: {str(e)}")
            return []

