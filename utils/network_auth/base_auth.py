"""Base class for network authentication"""
from typing import Optional
import logging
import streamlit as st
import os

logger = logging.getLogger(__name__)


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


class BaseAuth:
    """Base class for network authentication"""
    
    def __init__(self, network_name: str):
        self.network_name = network_name
        self.logger = logging.getLogger(f"{__name__}.{network_name}")
    
    def get_env_var(self, key: str) -> Optional[str]:
        """Get environment variable"""
        return _get_env_var(key)

