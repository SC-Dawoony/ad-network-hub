"""Network configuration registry"""
from .base_config import NetworkConfig, Field, ConditionalField
from .bigoads_config import BigOAdsConfig
from .ironsource_config import IronSourceConfig
from .pangle_config import PangleConfig
from .mintegral_config import MintegralConfig
from .inmobi_config import InMobiConfig
from .fyber_config import FyberConfig
from .applovin_config import AppLovinConfig
from .unity_config import UnityConfig
from .admob_config import AdMobConfig

# Network registry
NETWORK_REGISTRY = {
    'bigoads': BigOAdsConfig(),
    'ironsource': IronSourceConfig(),
    'pangle': PangleConfig(),
    'mintegral': MintegralConfig(),
    'inmobi': InMobiConfig(),
    'fyber': FyberConfig(),
    'applovin': AppLovinConfig(),
    'unity': UnityConfig(),
    'admob': AdMobConfig(),
    # Future networks will be added here
}

def get_network_config(network_name: str) -> NetworkConfig:
    """Get network configuration by name"""
    return NETWORK_REGISTRY.get(network_name.lower())

def get_available_networks() -> list[str]:
    """Get list of available network names"""
    return list(NETWORK_REGISTRY.keys())

def get_network_display_names() -> dict[str, str]:
    """Get display names for all networks"""
    return {key: config.display_name for key, config in NETWORK_REGISTRY.items()}

