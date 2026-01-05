"""Base class for network API implementations"""
from typing import Dict, List, Optional
import requests
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


def _get_env_var(key: str) -> Optional[str]:
    """
    Get environment variable from Streamlit secrets (if available) or .env file
    
    Args:
        key: Environment variable key
        
    Returns:
        Environment variable value or None
    """
    import streamlit as st
    import os
    
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        if hasattr(st, 'secrets') and st.secrets:
            # Try direct access first
            try:
                if key in st.secrets:
                    value = st.secrets[key]
                    logger.info(f"[Env] Found {key} in Streamlit secrets (length: {len(str(value)) if value else 0})")
                    return str(value) if value is not None else None
            except (KeyError, AttributeError, TypeError):
                pass
            
            # Try using .get() method if available
            try:
                if hasattr(st.secrets, 'get'):
                    value = st.secrets.get(key)
                    if value is not None:
                        logger.info(f"[Env] Found {key} in Streamlit secrets via .get() (length: {len(str(value))})")
                        return str(value)
            except Exception:
                pass
            
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
            except Exception:
                pass
            
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


class BaseNetworkAPI(ABC):
    """Base class for network API implementations"""
    
    def __init__(self, network_name: str):
        self.network_name = network_name
        self.logger = logging.getLogger(f"{__name__}.{network_name}")
    
    @abstractmethod
    def create_app(self, payload: Dict) -> Dict:
        """Create app via network API
        
        Args:
            payload: App creation payload
            
        Returns:
            API response dict
        """
        pass
    
    @abstractmethod
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create unit (placement/ad unit) via network API
        
        Args:
            payload: Unit creation payload
            app_key: Optional app key/ID
            
        Returns:
            API response dict
        """
        pass
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from network
        
        Args:
            app_key: Optional app key to filter by
            
        Returns:
            List of app dicts
        """
        # Default implementation returns empty list
        # Override in subclasses if network supports app listing
        return []
    
    def get_units(self, app_code: str) -> List[Dict]:
        """Get units list for an app
        
        Args:
            app_code: App code/ID
            
        Returns:
            List of unit dicts
        """
        # Default implementation returns empty list
        # Override in subclasses if network supports unit listing
        return []
    
    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 30
    ) -> requests.Response:
        """Make HTTP request with logging
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            url: Request URL
            headers: Request headers
            data: Request data (for form data)
            json_data: Request JSON data
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        self.logger.info(f"[{self.network_name}] API Request: {method} {url}")
        
        if headers:
            self.logger.info(f"[{self.network_name}] Request Headers: {json.dumps(_mask_sensitive_data(headers), indent=2)}")
        
        if json_data:
            self.logger.info(f"[{self.network_name}] Request Payload: {json.dumps(_mask_sensitive_data(json_data), indent=2)}")
        elif data:
            self.logger.info(f"[{self.network_name}] Request Data: {json.dumps(_mask_sensitive_data(data), indent=2)}")
        
        if params:
            self.logger.info(f"[{self.network_name}] Request Params: {json.dumps(_mask_sensitive_data(params), indent=2)}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                params=params,
                timeout=timeout
            )
            
            self.logger.info(f"[{self.network_name}] Response Status: {response.status_code}")
            
            # Check if response is empty before trying to parse JSON
            response_text = response.text.strip()
            if response_text:
                try:
                    response_data = response.json()
                    self.logger.info(f"[{self.network_name}] Response Data: {json.dumps(_mask_sensitive_data(response_data), indent=2)}")
                except json.JSONDecodeError:
                    # Non-JSON response is OK, just log it
                    self.logger.warning(f"[{self.network_name}] Response is not JSON: {response_text[:500]}")
            else:
                # Empty response is OK, just log it
                self.logger.info(f"[{self.network_name}] Response is empty (status {response.status_code})")
            
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[{self.network_name}] Request Error: {str(e)}")
            raise
        except Exception as e:
            # Catch any other unexpected errors (like JSONDecodeError if it somehow propagates)
            # But JSONDecodeError should be caught above, so this is just a safety net
            self.logger.error(f"[{self.network_name}] Unexpected error in _make_request: {str(e)}")
            raise

