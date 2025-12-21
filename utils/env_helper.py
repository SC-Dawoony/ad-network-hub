"""Helper function to get environment variables from Streamlit secrets or .env file"""
import os
from typing import Optional

def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable from Streamlit secrets (if available) or .env file
    
    Args:
        key: Environment variable key
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    try:
        import streamlit as st
        # Try Streamlit secrets first (for Streamlit Cloud)
        if hasattr(st, 'secrets') and st.secrets and key in st.secrets:
            return st.secrets[key]
    except:
        pass
    
    # Fallback to environment variables (from .env file or system env)
    return os.getenv(key, default)

