"""IronSource authentication utilities"""
from typing import Optional, Dict
import requests
import json
import time
import base64
import logging
from .base_auth import BaseAuth, _get_env_var

logger = logging.getLogger(__name__)


class IronSourceAuth(BaseAuth):
    """IronSource authentication handler"""
    
    def __init__(self):
        super().__init__("IronSource")
    
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
    
    def get_token(self) -> Optional[str]:
        """Get IronSource bearer token with automatic refresh
        
        Logic:
        1. Check if bearer_token exists and is not expired (1 hour buffer)
        2. If expired or missing, fetch new token using secret_key and refresh_token
        3. Return valid bearer token
        
        Required: IRONSOURCE_SECRET_KEY, IRONSOURCE_REFRESH_TOKEN
        Optional: IRONSOURCE_BEARER_TOKEN (if exists and valid, use it)
        """
        # Get credentials (required)
        refresh_token = self.get_env_var("IRONSOURCE_REFRESH_TOKEN")
        secret_key = self.get_env_var("IRONSOURCE_SECRET_KEY")
        
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
        bearer_token = self.get_env_var("IRONSOURCE_BEARER_TOKEN") or self.get_env_var("IRONSOURCE_API_TOKEN")
        
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
        new_token = self.refresh_token(refresh_token, secret_key)
        
        if new_token:
            logger.info("[IronSource] Successfully obtained new bearer token")
            return new_token
        else:
            logger.error("[IronSource] Failed to obtain bearer token. Check logs above for details.")
            return None
    
    def get_headers(self) -> Optional[Dict[str, str]]:
        """Get IronSource API headers with automatic token refresh
        
        This method is called before each API request to ensure we have a valid token.
        Logic:
        1. Get bearer token (with automatic refresh if needed)
        2. Return headers with Authorization: Bearer {token}
        """
        token = self.get_token()
        if not token:
            return None
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def refresh_token(self, refresh_token: str, secret_key: str) -> Optional[str]:
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
            logger.info(f"[IronSource] Headers: {json.dumps({k: '***MASKED***' if 'token' in k.lower() or 'key' in k.lower() else v for k, v in headers.items()}, indent=2)}")
            
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

