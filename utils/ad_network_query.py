"""Ad Network Query Utilities for Update Ad Unit page

This module provides functions to query applications and units from various ad networks
to automatically populate ad_network_app_id, ad_network_app_key, and ad_unit_id fields
in the Update Ad Unit page.
"""
import logging
import json
from typing import Dict, List, Optional, Tuple
from utils.network_manager import get_network_manager, _get_env_var

logger = logging.getLogger(__name__)


def find_app_by_name(network: str, app_name: str, platform: Optional[str] = None) -> Optional[Dict]:
    """Find an app by name from a network
    
    Args:
        network: Network name (e.g., "ironsource", "bigoads", "inmobi")
        app_name: App name to search for
        platform: Optional platform filter ("android" or "ios")
    
    Returns:
        App dict with appKey/appCode/appId if found, None otherwise
    """
    try:
        network_manager = get_network_manager()
        apps = network_manager.get_apps(network)
        
        if not apps:
            logger.warning(f"[{network}] No apps found")
            return None
        
        # Search for app by name (case-insensitive, partial match)
        app_name_lower = app_name.lower().strip()
        for app in apps:
            app_name_in_list = app.get("name") or app.get("appName") or ""
            if app_name_lower in app_name_in_list.lower():
                # Check platform if provided
                if platform:
                    app_platform = app.get("platform", "")
                    platform_normalized = _normalize_platform_for_matching(app_platform, network)
                    if platform_normalized != platform.lower():
                        continue
                
                return app
        
        logger.warning(f"[{network}] App '{app_name}' not found")
        return None
    except Exception as e:
        logger.error(f"[{network}] Error finding app by name: {str(e)}")
        return None


def find_app_by_package_name(network: str, package_name: str, platform: Optional[str] = None) -> Optional[Dict]:
    """Find an app by package name from a network
    
    Args:
        network: Network name (e.g., "ironsource", "bigoads", "inmobi")
        package_name: Package name to search for (e.g., "com.example.app")
        platform: Optional platform filter ("android" or "ios")
    
    Returns:
        App dict with appKey/appCode/appId if found, None otherwise
    """
    try:
        network_manager = get_network_manager()
        apps = network_manager.get_apps(network)
        
        if not apps:
            logger.warning(f"[{network}] No apps found")
            return None
        
        # Search for app by package name
        package_name_lower = package_name.lower().strip()
        for app in apps:
            # Check various package name fields
            app_pkg = (
                app.get("pkgName", "") or 
                app.get("packageName", "") or 
                app.get("bundleId", "") or
                app.get("package", "")
            )
            
            if app_pkg and package_name_lower == app_pkg.lower():
                # Check platform if provided
                if platform:
                    app_platform = app.get("platform", "")
                    platform_normalized = _normalize_platform_for_matching(app_platform, network)
                    if platform_normalized != platform.lower():
                        continue
                
                return app
        
        logger.warning(f"[{network}] App with package name '{package_name}' not found")
        return None
    except Exception as e:
        logger.error(f"[{network}] Error finding app by package name: {str(e)}")
        return None


def _normalize_platform_for_matching(platform: str, network: str) -> str:
    """Normalize platform string for matching
    
    Args:
        platform: Platform string from API
        network: Network name
    
    Returns:
        Normalized platform string ("android" or "ios")
    """
    if not platform:
        return ""
    
    platform_str = str(platform).strip()
    platform_upper = platform_str.upper()
    platform_lower = platform_str.lower()
    
    # Handle Mintegral format: "ANDROID" or "IOS"
    if platform_upper == "ANDROID" or platform_upper == "AND":
        return "android"
    elif platform_upper == "IOS" or platform_upper == "IPHONE":
        return "ios"
    
    # Handle common formats
    if platform_lower in ["android", "1", "and", "aos"]:
        return "android"
    elif platform_lower in ["ios", "2", "iphone"]:
        return "ios"
    elif platform_str == "Android":
        return "android"
    elif platform_str == "iOS":
        return "ios"
    
    return platform_lower


def get_ironsource_app_by_name(app_name: str, platform: Optional[str] = None) -> Optional[Dict]:
    """Get IronSource app by appName
    
    Args:
        app_name: App name to search for
        platform: Optional platform filter ("android" or "ios")
    
    Returns:
        App dict with appKey if found, None otherwise
    """
    return find_app_by_name("ironsource", app_name, platform)


def get_ironsource_units(app_key: str) -> List[Dict]:
    """Get IronSource ad units (placements) for an app
    
    API: GET https://platform.ironsrc.com/levelPlay/adUnits/v1/{appKey}
    
    Args:
        app_key: IronSource app key
    
    Returns:
        List of ad unit dicts with mediationAdUnitName, adFormat, etc.
    """
    try:
        network_manager = get_network_manager()
        # Access private method through the instance
        headers = network_manager._get_ironsource_headers()
        
        if not headers:
            logger.error("[IronSource] Cannot get units: authentication failed")
            return []
        
        url = f"https://platform.ironsrc.com/levelPlay/adUnits/v1/{app_key}"
        
        logger.info(f"[IronSource] API Request: GET {url}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        logger.info(f"[IronSource] Request Headers: {json.dumps(masked_headers, indent=2)}")
        
        import requests
        response = requests.get(url, headers=headers, timeout=30)
        
        logger.info(f"[IronSource] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Handle empty response
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"[IronSource] Empty response body (status {response.status_code})")
                return []
            
            try:
                result = response.json()
                logger.info(f"[IronSource] Response Body: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"[IronSource] JSON decode error: {str(e)}")
                logger.error(f"[IronSource] Response text: {response_text[:500]}")
                return []
            
            # IronSource API 응답 형식에 맞게 파싱
            units = []
            if isinstance(result, list):
                units = result
            elif isinstance(result, dict):
                units = result.get("adUnits", result.get("data", result.get("list", [])))
                if not isinstance(units, list):
                    units = []
            
            logger.info(f"[IronSource] Units count: {len(units)}")
            return units
        else:
            try:
                error_body = response.json()
                logger.error(f"[IronSource] Error Response: {json.dumps(error_body, indent=2)}")
            except:
                logger.error(f"[IronSource] Error Response (text): {response.text}")
            return []
    except Exception as e:
        logger.error(f"[IronSource] API Error (Get Units): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def match_applovin_unit_to_network(
    network: str,
    applovin_unit: Dict,
    network_apps: Optional[List[Dict]] = None
) -> Optional[Dict]:
    """Match AppLovin ad unit to a network app
    
    Args:
        network: Network name (e.g., "ironsource", "bigoads")
        applovin_unit: AppLovin ad unit dict with id, name, platform, package_name
        network_apps: Optional pre-fetched network apps list (to avoid multiple API calls)
    
    Returns:
        Matched app dict with appKey/appCode/appId, or None if not found
    """
    package_name = applovin_unit.get("package_name", "")
    app_name = applovin_unit.get("name", "")
    platform = applovin_unit.get("platform", "").lower()
    
    # Try to find app by package name first (more reliable)
    if package_name:
        app = find_app_by_package_name(network, package_name, platform)
        if app:
            return app
    
    # Fallback to app name matching
    if app_name:
        app = find_app_by_name(network, app_name, platform)
        if app:
            return app
    
    return None


def find_matching_unit(
    network_units: List[Dict],
    ad_format: str,
    network: str,
    platform: Optional[str] = None
) -> Optional[Dict]:
    """Find matching ad unit by ad format
    
    Args:
        network_units: List of ad units from network API
        ad_format: AppLovin ad format (REWARD, INTER, BANNER)
        network: Network name
        platform: Optional platform ("android" or "ios") for filtering by mediationAdUnitName
    
    Returns:
        Matched unit dict with mediationAdUnitId/adUnitId, or None if not found
    """
    target_format = map_ad_format_to_network_format(ad_format, network)
    
    # For IronSource, if platform is provided and multiple units match the format,
    # prioritize units with platform indicator in mediationAdUnitName
    if network == "ironsource" and platform:
        platform_normalized = platform.lower()
        platform_indicator = "_aos_" if platform_normalized == "android" else "_ios_"
        
        # First, collect all matching units
        matching_units = []
        for unit in network_units:
            unit_format = unit.get("adFormat", "").lower()
            if unit_format == target_format.lower():
                matching_units.append(unit)
        
        # If multiple matches, prioritize by platform indicator in mediationAdUnitName
        if len(matching_units) > 1:
            for unit in matching_units:
                mediation_name = unit.get("mediationAdUnitName", "").lower()
                if platform_indicator in mediation_name:
                    logger.info(f"[IronSource] Found unit with platform indicator '{platform_indicator}' in mediationAdUnitName: {unit.get('mediationAdUnitName')}")
                    return unit
            
            # If no unit has platform indicator, return first match
            logger.warning(f"[IronSource] Multiple units found for format '{target_format}' but none have platform indicator '{platform_indicator}' in mediationAdUnitName")
            return matching_units[0]
        elif len(matching_units) == 1:
            return matching_units[0]
        else:
            return None
    
    # For other networks or when platform is not provided, use simple format matching
    for unit in network_units:
        unit_format = unit.get("adFormat", "").lower()
        if unit_format == target_format.lower():
            return unit
    
    return None


def get_network_units(network: str, app_code: str) -> List[Dict]:
    """Get ad units for a network app
    
    Args:
        network: Network name (e.g., "ironsource", "bigoads", "inmobi")
        app_code: App code (appKey for IronSource, appCode for others, etc.)
    
    Returns:
        List of ad unit dicts
    """
    if network == "ironsource":
        return get_ironsource_units(app_code)
    # TODO: Add other networks
    # elif network == "bigoads":
    #     return get_bigoads_units(app_code)
    # elif network == "inmobi":
    #     return get_inmobi_units(app_code)
    
    logger.warning(f"[{network}] get_network_units not implemented yet")
    return []


def map_applovin_network_to_actual_network(applovin_network: str) -> Optional[str]:
    """Map AppLovin network name to actual network identifier
    
    Args:
        applovin_network: AppLovin network name (e.g., "IRONSOURCE_BIDDING", "BIGO_BIDDING")
    
    Returns:
        Actual network identifier (e.g., "ironsource", "bigoads") or None if not supported
    """
    mapping = {
        "IRONSOURCE_BIDDING": "ironsource",
        "BIGO_BIDDING": "bigoads",
        "INMOBI_BIDDING": "inmobi",
        "FYBER_BIDDING": "fyber",
        "MINTEGRAL_BIDDING": "mintegral",
        "PANGLE_BIDDING": "pangle",
        # Add more mappings as needed
    }
    return mapping.get(applovin_network.upper())


def map_ad_format_to_network_format(ad_format: str, network: str) -> str:
    """Map AppLovin ad format to network-specific ad format
    
    Args:
        ad_format: AppLovin ad format (REWARD, INTER, BANNER)
        network: Network name
    
    Returns:
        Network-specific ad format string
    """
    ad_format_upper = ad_format.upper()
    
    if network == "ironsource":
        # IronSource: rewarded, interstitial, banner
        format_map = {
            "REWARD": "rewarded",
            "INTER": "interstitial",
            "BANNER": "banner"
        }
        return format_map.get(ad_format_upper, ad_format.lower())
    
    # Default: return lowercase
    return ad_format.lower()


def extract_app_identifiers(app: Dict, network: str) -> Dict[str, Optional[str]]:
    """Extract app identifiers (app_id, app_key, app_code) from app dict
    
    Args:
        app: App dict from network API
        network: Network name
    
    Returns:
        Dict with app_id, app_key, app_code (network-specific)
    """
    result = {
        "app_id": None,
        "app_key": None,
        "app_code": None
    }
    
    if network == "ironsource":
        result["app_key"] = app.get("appKey")
        result["app_code"] = app.get("appKey")  # For IronSource, appKey is the app code
    elif network == "bigoads":
        result["app_code"] = app.get("appCode")
        result["app_id"] = app.get("appId")
    elif network == "inmobi":
        result["app_id"] = app.get("appId") or app.get("id")
        result["app_code"] = str(result["app_id"]) if result["app_id"] else None
    elif network == "mintegral":
        result["app_id"] = app.get("app_id") or app.get("id")
        result["app_code"] = str(result["app_id"]) if result["app_id"] else None
    elif network == "fyber":
        result["app_id"] = app.get("appId") or app.get("id")
        result["app_code"] = str(result["app_id"]) if result["app_id"] else None
    else:
        # Generic fallback
        result["app_code"] = app.get("appCode") or app.get("appKey") or app.get("appId")
        result["app_id"] = app.get("appId") or app.get("id")
        result["app_key"] = app.get("appKey")
    
    return result

