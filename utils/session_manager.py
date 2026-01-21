"""Session state management utilities"""
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st


class SessionManager:
    """Manage Streamlit session state"""
    
    @staticmethod
    def initialize():
        """Initialize session state with default values"""
        if 'selected_network' not in st.session_state:
            st.session_state.selected_network = 'applovin'
        
        if 'apps_cache' not in st.session_state:
            st.session_state.apps_cache = {}
        
        if 'units_cache' not in st.session_state:
            st.session_state.units_cache = {}
        
        if 'created_apps' not in st.session_state:
            st.session_state.created_apps = []
        
        if 'created_units' not in st.session_state:
            st.session_state.created_units = []
        
        if 'last_sync_time' not in st.session_state:
            st.session_state.last_sync_time = {}
        
        if 'error_log' not in st.session_state:
            st.session_state.error_log = []
        
        if 'app_match_name' not in st.session_state:
            st.session_state.app_match_name = ""
    
    @staticmethod
    def switch_network(network_name: str):
        """Switch to a different network"""
        st.session_state.selected_network = network_name.lower()
    
    @staticmethod
    def get_current_network() -> str:
        """Get currently selected network"""
        return st.session_state.get('selected_network', 'applovin')
    
    @staticmethod
    def cache_apps(network: str, apps: List[Dict]):
        """Cache apps list for a network"""
        if 'apps_cache' not in st.session_state:
            st.session_state.apps_cache = {}
        st.session_state.apps_cache[network] = apps
        st.session_state.last_sync_time[network] = datetime.now()
    
    @staticmethod
    def get_cached_apps(network: str) -> List[Dict]:
        """Get cached apps for a network"""
        return st.session_state.get('apps_cache', {}).get(network, [])
    
    @staticmethod
    def cache_units(network: str, app_code: str, units: List[Dict]):
        """Cache units for a specific app"""
        if 'units_cache' not in st.session_state:
            st.session_state.units_cache = {}
        if network not in st.session_state.units_cache:
            st.session_state.units_cache[network] = {}
        st.session_state.units_cache[network][app_code] = units
    
    @staticmethod
    def get_cached_units(network: str, app_code: str) -> List[Dict]:
        """Get cached units for a specific app"""
        return st.session_state.get('units_cache', {}).get(network, {}).get(app_code, [])
    
    @staticmethod
    def add_created_app(network: str, app_data: Dict):
        """Add created app to history"""
        if 'created_apps' not in st.session_state:
            st.session_state.created_apps = []
        app_entry = {
            'network': network,
            'timestamp': datetime.now().isoformat(),
            **app_data
        }
        st.session_state.created_apps.append(app_entry)
        
        # Store the most recently created app code for this network
        if 'last_created_app_code' not in st.session_state:
            st.session_state.last_created_app_code = {}
        st.session_state.last_created_app_code[network] = app_data.get('appCode')
        
        # Store full app info for slot creation
        if 'last_created_app_info' not in st.session_state:
            st.session_state.last_created_app_info = {}
        st.session_state.last_created_app_info[network] = app_data
    
    @staticmethod
    def get_last_created_app_code(network: str) -> Optional[str]:
        """Get the most recently created app code for a network"""
        return st.session_state.get('last_created_app_code', {}).get(network)
    
    @staticmethod
    def get_last_created_app_info(network: str) -> Optional[Dict]:
        """Get the full info of the most recently created app for a network"""
        return st.session_state.get('last_created_app_info', {}).get(network)
    
    @staticmethod
    def add_created_unit(network: str, unit_data: Dict):
        """Add created unit to history"""
        if 'created_units' not in st.session_state:
            st.session_state.created_units = []
        st.session_state.created_units.append({
            'network': network,
            'timestamp': datetime.now().isoformat(),
            **unit_data
        })
    
    @staticmethod
    def log_error(network: str, error: str):
        """Log an error"""
        if 'error_log' not in st.session_state:
            st.session_state.error_log = []
        st.session_state.error_log.append({
            'network': network,
            'timestamp': datetime.now().isoformat(),
            'error': error
        })
    
    @staticmethod
    def set_app_match_name(name: str):
        """Set the app match name for ad unit name generation
        
        This value will be used instead of Android package name
        when generating ad unit names (placement names).
        """
        st.session_state.app_match_name = name.strip() if name else ""
    
    @staticmethod
    def get_app_match_name() -> str:
        """Get the app match name for ad unit name generation
        
        Returns:
            The app match name if set, otherwise empty string
        """
        return st.session_state.get('app_match_name', "")

