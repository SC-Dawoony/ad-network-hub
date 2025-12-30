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
                app.get("package", "") or
                app.get("pkgNameDisplay", "")  # BigOAds uses pkgNameDisplay
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
    
    # Handle BigOAds format: 1 = android, 2 = ios
    if network == "bigoads":
        try:
            platform_value = int(platform_str) if platform_str.isdigit() else None
            if platform_value == 1:
                return "android"
            elif platform_value == 2:
                return "ios"
        except (ValueError, TypeError):
            pass
    
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


def get_inmobi_app_by_name(app_name: str, platform: Optional[str] = None) -> Optional[Dict]:
    """Get InMobi app by appName
    
    Args:
        app_name: App name to search for
        platform: Optional platform filter ("android" or "ios")
    
    Returns:
        App dict with appId if found, None otherwise
    """
    return find_app_by_name("inmobi", app_name, platform)


def get_mintegral_app_by_name(app_name: str, platform: Optional[str] = None) -> Optional[Dict]:
    """Get Mintegral app by appName
    
    Args:
        app_name: App name to search for
        platform: Optional platform filter ("android" or "ios")
    
    Returns:
        App dict with app_id if found, None otherwise
    """
    return find_app_by_name("mintegral", app_name, platform)


def get_fyber_app_by_name(app_name: str, platform: Optional[str] = None) -> Optional[Dict]:
    """Get Fyber app by name
    
    Args:
        app_name: App name to search for
        platform: Optional platform filter ("android" or "ios")
    
    Returns:
        App dict with appId if found, None otherwise
    """
    return find_app_by_name("fyber", app_name, platform)


def get_bigoads_app_by_name(app_name: str, platform: Optional[str] = None) -> Optional[Dict]:
    """Get BigOAds app by name
    
    Args:
        app_name: App name to search for
        platform: Optional platform filter ("android" or "ios")
    
    Returns:
        App dict with appCode if found, None otherwise
    """
    return find_app_by_name("bigoads", app_name, platform)


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
        platform: Optional platform ("android" or "ios") for filtering by mediationAdUnitName or placementName
    
    Returns:
        Matched unit dict with placementId/adUnitId, or None if not found
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
    
    # For InMobi, match by placementType
    if network == "inmobi":
        # InMobi uses placementType field (e.g., "REWARDED_VIDEO", "INTERSTITIAL", "BANNER")
        matching_units = []
        for unit in network_units:
            unit_format = unit.get("placementType", "").upper()
            if unit_format == target_format.upper():
                matching_units.append(unit)
        
        # If multiple matches and platform is provided, prioritize by platform indicator in placementName
        if len(matching_units) > 1 and platform:
            platform_normalized = platform.lower()
            platform_indicator = "_aos_" if platform_normalized == "android" else "_ios_"
            
            for unit in matching_units:
                placement_name = unit.get("placementName", "").lower()
                if platform_indicator in placement_name:
                    logger.info(f"[InMobi] Found unit with platform indicator '{platform_indicator}' in placementName: {unit.get('placementName')}")
                    return unit
            
            # If no unit has platform indicator, return first match
            logger.warning(f"[InMobi] Multiple units found for format '{target_format}' but none have platform indicator '{platform_indicator}' in placementName")
            return matching_units[0] if matching_units else None
        elif len(matching_units) == 1:
            return matching_units[0]
        else:
            return None
    
    # For Mintegral, match by ad_type
    if network == "mintegral":
        # Mintegral uses ad_type field (e.g., "rewarded_video", "new_interstitial", "banner")
        matching_units = []
        for unit in network_units:
            unit_format = unit.get("ad_type", "").lower()
            if unit_format == target_format.lower():
                matching_units.append(unit)
        
        # If multiple matches and platform is provided, prioritize by platform indicator in placement_name
        if len(matching_units) > 1 and platform:
            platform_normalized = platform.lower()
            platform_indicator = "_aos_" if platform_normalized == "android" else "_ios_"
            
            for unit in matching_units:
                placement_name = unit.get("placement_name", "").lower()
                if platform_indicator in placement_name:
                    logger.info(f"[Mintegral] Found unit with platform indicator '{platform_indicator}' in placement_name: {unit.get('placement_name')}")
                    return unit
            
            # If no unit has platform indicator, return first match
            logger.warning(f"[Mintegral] Multiple units found for format '{target_format}' but none have platform indicator '{platform_indicator}' in placement_name")
            return matching_units[0] if matching_units else None
        elif len(matching_units) == 1:
            return matching_units[0]
        else:
            return None
    
    # For Fyber, match by placementType
    if network == "fyber":
        # Fyber uses placementType field (e.g., "Rewarded", "Interstitial", "Banner")
        matching_units = []
        for unit in network_units:
            unit_format = unit.get("placementType", "")
            # Case-insensitive comparison
            if unit_format.lower() == target_format.lower():
                matching_units.append(unit)
        
        # If multiple matches and platform is provided, prioritize by platform indicator in name
        if len(matching_units) > 1 and platform:
            platform_normalized = platform.lower()
            platform_indicator = "_aos_" if platform_normalized == "android" else "_ios_"
            
            for unit in matching_units:
                placement_name = unit.get("name", "").lower()
                if platform_indicator in placement_name:
                    logger.info(f"[Fyber] Found unit with platform indicator '{platform_indicator}' in name: {unit.get('name')}")
                    return unit
            
            # If no unit has platform indicator, return first match
            logger.warning(f"[Fyber] Multiple units found for format '{target_format}' but none have platform indicator '{platform_indicator}' in name")
            return matching_units[0] if matching_units else None
        elif len(matching_units) == 1:
            return matching_units[0]
        else:
            return None
    
    # For BigOAds, match by adType (numeric)
    if network == "bigoads":
        # BigOAds uses adType field (2: Banner, 3: Interstitial, 4: Reward Video)
        matching_units = []
        target_ad_type = target_format  # target_format is already the numeric adType
        logger.info(f"[BigOAds] Finding unit: ad_format={ad_format}, target_format={target_format}, target_ad_type={target_ad_type} (type: {type(target_ad_type)})")
        logger.info(f"[BigOAds] Total units to check: {len(network_units)}")
        
        # Debug: Log all units' adType values
        for idx, unit in enumerate(network_units):
            unit_ad_type = unit.get("adType")
            unit_name = unit.get("name", "N/A")
            unit_slot_code = unit.get("slotCode", "N/A")
            logger.info(f"[BigOAds] Unit[{idx}]: name={unit_name}, slotCode={unit_slot_code}, adType={unit_ad_type} (type: {type(unit_ad_type)}), all_keys={list(unit.keys())}")
        
        for unit in network_units:
            unit_ad_type = unit.get("adType")
            unit_name = unit.get("name", "N/A")
            
            # Check if adType field exists
            if unit_ad_type is None:
                logger.warning(f"[BigOAds] Unit '{unit_name}' has no 'adType' field. Available keys: {list(unit.keys())}")
                # Try alternative field names
                unit_ad_type = unit.get("ad_type") or unit.get("adTypeCode") or unit.get("type")
                if unit_ad_type is not None:
                    logger.info(f"[BigOAds] Found alternative field: {unit_ad_type}")
                else:
                    logger.warning(f"[BigOAds] No adType found in unit '{unit_name}', skipping")
                    continue
            
            logger.info(f"[BigOAds] Checking unit: name={unit_name}, adType={unit_ad_type} (type: {type(unit_ad_type)})")
            # Compare as integers if possible
            try:
                unit_ad_type_int = int(unit_ad_type)
                target_ad_type_int = int(target_ad_type)
                if unit_ad_type_int == target_ad_type_int:
                    logger.info(f"[BigOAds] ✓ Match found: {unit_name} (adType={unit_ad_type_int} == target={target_ad_type_int})")
                    matching_units.append(unit)
                else:
                    logger.info(f"[BigOAds] ✗ No match: {unit_name} (adType={unit_ad_type_int} != target={target_ad_type_int})")
            except (ValueError, TypeError) as e:
                # If conversion fails, skip
                logger.warning(f"[BigOAds] Cannot compare adType: {unit_name}, adType={unit_ad_type}, error={e}")
                continue
        
        logger.info(f"[BigOAds] Total matching units found: {len(matching_units)}")
        
        # If multiple matches and platform is provided, prioritize by platform indicator in name
        if len(matching_units) > 1 and platform:
            platform_normalized = platform.lower()
            platform_indicator = "_aos_" if platform_normalized == "android" else "_ios_"
            
            for unit in matching_units:
                slot_name = unit.get("name", "").lower()
                if platform_indicator in slot_name:
                    logger.info(f"[BigOAds] Found unit with platform indicator '{platform_indicator}' in name: {unit.get('name')}")
                    return unit
            
            # If no unit has platform indicator, return first match
            logger.warning(f"[BigOAds] Multiple units found for format '{target_format}' but none have platform indicator '{platform_indicator}' in name")
            return matching_units[0] if matching_units else None
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


def get_inmobi_units(app_id: str) -> List[Dict]:
    """Get InMobi ad units (placements) for an app
    
    API: GET https://publisher.inmobi.com/rest/api/v1/placements?appId={appId}
    
    Args:
        app_id: InMobi app ID (Integer)
    
    Returns:
        List of ad unit dicts with placementId, placementName, placementType, etc.
    """
    try:
        # InMobi uses x-client-id, x-account-id, x-client-secret headers
        username = _get_env_var("INMOBI_USERNAME")
        account_id = _get_env_var("INMOBI_ACCOUNT_ID")
        client_secret = _get_env_var("INMOBI_CLIENT_SECRET")
        
        if not username or not account_id or not client_secret:
            logger.error("[InMobi] Cannot get units: INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set")
            return []
        
        headers = {
            "x-client-id": username,
            "x-account-id": account_id,
            "x-client-secret": client_secret,
            "Accept": "application/json",
        }
        
        url = "https://publisher.inmobi.com/rest/api/v1/placements"
        
        # Query parameters
        params = {
            "appId": int(app_id) if app_id.isdigit() else app_id,
            "pageNum": 1,
            "pageLength": 100,  # Get more results per page
        }
        
        logger.info(f"[InMobi] API Request: GET {url}")
        logger.info(f"[InMobi] Request Params: {json.dumps(params, indent=2)}")
        masked_headers = {k: "***MASKED***" if k in ["x-client-secret"] else v for k, v in headers.items()}
        logger.info(f"[InMobi] Request Headers: {json.dumps(masked_headers, indent=2)}")
        
        import requests
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        logger.info(f"[InMobi] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Handle empty response
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"[InMobi] Empty response body (status {response.status_code})")
                return []
            
            try:
                result = response.json()
                logger.info(f"[InMobi] Response Body: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"[InMobi] JSON decode error: {str(e)}")
                logger.error(f"[InMobi] Response text: {response_text[:500]}")
                return []
            
            # InMobi API 응답 형식에 맞게 파싱
            # Response format: {"success": true, "data": {"records": [...], "totalRecords": ...}}
            units = []
            if isinstance(result, dict):
                if result.get("success") is True:
                    data = result.get("data", {})
                    if isinstance(data, dict):
                        units = data.get("records", data.get("placements", []))
                    elif isinstance(data, list):
                        units = data
                else:
                    # If success is false, check if there's error info
                    error_msg = result.get("msg") or result.get("message") or "Unknown error"
                    logger.error(f"[InMobi] API returned success=false: {error_msg}")
            elif isinstance(result, list):
                units = result
            
            logger.info(f"[InMobi] Units count: {len(units)}")
            return units
        else:
            try:
                error_body = response.json()
                logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
            except:
                logger.error(f"[InMobi] Error Response (text): {response.text}")
            return []
    except Exception as e:
        logger.error(f"[InMobi] API Error (Get Units): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_mintegral_units(app_id: str) -> List[Dict]:
    """Get Mintegral ad units (placements) for an app
    
    API: GET https://dev.mintegral.com/v2/placement/open_api_list?app_id={app_id}
    
    Args:
        app_id: Mintegral app ID
    
    Returns:
        List of ad unit dicts with placement_id, placement_name, ad_type, etc.
    """
    try:
        # Mintegral API 인증: skey, time, sign
        skey = _get_env_var("MINTEGRAL_SKEY")
        secret = _get_env_var("MINTEGRAL_SECRET")
        
        if not skey or not secret:
            logger.error("[Mintegral] Cannot get units: MINTEGRAL_SKEY and MINTEGRAL_SECRET must be set")
            return []
        
        import time
        import hashlib
        
        # Generate timestamp and signature
        current_time = int(time.time())
        time_str = str(current_time)
        
        # Generate signature: md5(SECRETmd5(time))
        time_md5 = hashlib.md5(time_str.encode('utf-8')).hexdigest()
        sign_string = secret + time_md5
        signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        
        url = "https://dev.mintegral.com/v2/placement/open_api_list"
        
        # Query parameters
        params = {
            "app_id": int(app_id) if app_id.isdigit() else app_id,
            "skey": skey,
            "time": time_str,
            "sign": signature,
            "page": 1,
            "per_page": 100,  # Get more results per page
        }
        
        logger.info(f"[Mintegral] API Request: GET {url}")
        masked_params = {k: '***MASKED***' if k in ['skey', 'sign'] else v for k, v in params.items()}
        logger.info(f"[Mintegral] Request Params: {json.dumps(masked_params, indent=2)}")
        
        import requests
        response = requests.get(url, params=params, timeout=30)
        
        logger.info(f"[Mintegral] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Handle empty response
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"[Mintegral] Empty response body (status {response.status_code})")
                return []
            
            try:
                result = response.json()
                logger.info(f"[Mintegral] Response Body: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"[Mintegral] JSON decode error: {str(e)}")
                logger.error(f"[Mintegral] Response text: {response_text[:500]}")
                return []
            
            # Mintegral API 응답 형식에 맞게 파싱
            # Response format: {"code": 200, "data": {"lists": [...], "total": ...}}
            units = []
            if isinstance(result, dict):
                if result.get("code") == 200:
                    data = result.get("data", {})
                    if isinstance(data, dict):
                        units = data.get("lists", data.get("placements", []))
                    elif isinstance(data, list):
                        units = data
                else:
                    error_msg = result.get("msg") or result.get("message") or "Unknown error"
                    logger.error(f"[Mintegral] API returned code={result.get('code')}: {error_msg}")
            elif isinstance(result, list):
                units = result
            
            logger.info(f"[Mintegral] Units count: {len(units)}")
            return units
        else:
            try:
                error_body = response.json()
                logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
            except:
                logger.error(f"[Mintegral] Error Response (text): {response.text}")
            return []
    except Exception as e:
        logger.error(f"[Mintegral] API Error (Get Units): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_fyber_units(app_id: str) -> List[Dict]:
    """Get Fyber ad units (placements) for an app
    
    API: GET https://console.fyber.com/api/management/v1/placement?appId={appId}
    
    Args:
        app_id: Fyber app ID
    
    Returns:
        List of ad unit dicts with placementId, placementName, placementType, etc.
    """
    try:
        network_manager = get_network_manager()
        # Access private method through the instance
        access_token = network_manager._get_fyber_access_token()
        
        if not access_token:
            logger.error("[Fyber] Cannot get units: failed to get access token")
            return []
        
        url = "https://console.fyber.com/api/management/v1/placement"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {
            "appId": int(app_id) if app_id.isdigit() else app_id,
        }
        
        logger.info(f"[Fyber] API Request: GET {url}")
        logger.info(f"[Fyber] Request Params: {json.dumps(params, indent=2)}")
        masked_headers = {k: "***MASKED***" if k.lower() == "authorization" else v for k, v in headers.items()}
        logger.info(f"[Fyber] Request Headers: {json.dumps(masked_headers, indent=2)}")
        
        import requests
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        logger.info(f"[Fyber] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Handle empty response
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"[Fyber] Empty response body (status {response.status_code})")
                return []
            
            try:
                result = response.json()
                logger.info(f"[Fyber] Response Body: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"[Fyber] JSON decode error: {str(e)}")
                logger.error(f"[Fyber] Response text: {response_text[:500]}")
                return []
            
            # Fyber API 응답 형식에 맞게 파싱
            # Response format: can be single placement object, list of placements, or dict with placements array
            units = []
            if isinstance(result, list):
                # Array of placements
                units = result
            elif isinstance(result, dict):
                # Check if it's a dict with placements array or a single placement object
                if "placementId" in result or "placementType" in result:
                    # Single placement object (has placementId or placementType field)
                    units = [result]
                else:
                    # Dict with placements array
                    units = result.get("placements", result.get("data", result.get("list", [])))
                    if not isinstance(units, list):
                        units = []
            
            logger.info(f"[Fyber] Units count: {len(units)}")
            return units
        else:
            try:
                error_body = response.json()
                logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
            except:
                logger.error(f"[Fyber] Error Response (text): {response.text}")
            return []
    except Exception as e:
        logger.error(f"[Fyber] API Error (Get Units): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_bigoads_units(app_code: str) -> List[Dict]:
    """Get BigOAds ad units (slots) for an app
    
    API: POST https://www.bigossp.com/open/slot/list
    
    Args:
        app_code: BigOAds app code
    
    Returns:
        List of ad unit dicts with slotCode, name, adType, auctionType, etc.
    """
    try:
        # Add delay to avoid QPS limit (BigOAds has strict rate limiting)
        import time
        time.sleep(0.5)  # 500ms delay to avoid QPS limit
        
        network_manager = get_network_manager()
        # Access private method through the instance
        developer_id = _get_env_var("BIGOADS_DEVELOPER_ID")
        token = _get_env_var("BIGOADS_TOKEN")
        
        if not developer_id or not token:
            logger.error("[BigOAds] Cannot get units: BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set")
            return []
        
        # Generate signature using network_manager's method
        sign, timestamp = network_manager._generate_bigoads_sign(developer_id, token)
        
        url = "https://www.bigossp.com/open/slot/list"
        
        headers = {
            "Content-Type": "application/json",
            "X-BIGO-DeveloperId": developer_id,
            "X-BIGO-Sign": sign
        }
        
        payload = {
            "appCode": app_code
        }
        
        logger.info(f"[BigOAds] ========== Get Units API Call ==========")
        logger.info(f"[BigOAds] App Code: {app_code}")
        logger.info(f"[BigOAds] API Request: POST {url}")
        logger.info(f"[BigOAds] Request Payload: {json.dumps(payload, indent=2)}")
        masked_headers = {k: "***MASKED***" if k in ["X-BIGO-Sign"] else v for k, v in headers.items()}
        logger.info(f"[BigOAds] Request Headers: {json.dumps(masked_headers, indent=2)}")
        
        import requests
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"[BigOAds] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Handle empty response
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"[BigOAds] Empty response body (status {response.status_code})")
                return []
            
            try:
                result = response.json()
                logger.info(f"[BigOAds] Response Body: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"[BigOAds] JSON decode error: {str(e)}")
                logger.error(f"[BigOAds] Response text: {response_text[:500]}")
                return []
            
            # BigOAds API 응답 형식에 맞게 파싱
            # Response format: {"code": "100", "status": 0, "result": {"list": [...], "total": ...}}
            units = []
            code = result.get("code")
            status = result.get("status")
            
            if code == "100" or status == 0:
                result_data = result.get("result", {})
                units = result_data.get("list", [])
                
                # Debug: Log all units structure to check field names and adType values
                if units and len(units) > 0:
                    logger.info(f"[BigOAds] ========== Units Response Analysis ==========")
                    logger.info(f"[BigOAds] Total units returned: {len(units)}")
                    for idx, unit in enumerate(units):
                        unit_name = unit.get("name", "N/A")
                        unit_ad_type = unit.get("adType")
                        unit_slot_code = unit.get("slotCode", "N/A")
                        logger.info(f"[BigOAds] Unit[{idx}]: name='{unit_name}', slotCode='{unit_slot_code}', adType={unit_ad_type} (type: {type(unit_ad_type)}), all_keys={list(unit.keys())}")
                    
                    # Log first unit full structure for detailed inspection
                    first_unit = units[0]
                    logger.info(f"[BigOAds] First unit full structure: {json.dumps(first_unit, indent=2)}")
                else:
                    logger.warning(f"[BigOAds] No units returned from API!")
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                logger.error(f"[BigOAds] API returned code={code}, status={status}: {error_msg}")
            
            logger.info(f"[BigOAds] Units count: {len(units)}")
            return units
        else:
            try:
                error_body = response.json()
                logger.error(f"[BigOAds] Error Response: {json.dumps(error_body, indent=2)}")
            except:
                logger.error(f"[BigOAds] Error Response (text): {response.text}")
            return []
    except Exception as e:
        logger.error(f"[BigOAds] API Error (Get Units): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_network_units(network: str, app_code: str) -> List[Dict]:
    """Get ad units for a network app
    
    Args:
        network: Network name (e.g., "ironsource", "bigoads", "inmobi", "mintegral", "fyber")
        app_code: App code (appKey for IronSource, appId for InMobi/Mintegral/Fyber, appCode for BigOAds, etc.)
    
    Returns:
        List of ad unit dicts
    """
    if network == "ironsource":
        return get_ironsource_units(app_code)
    elif network == "inmobi":
        return get_inmobi_units(app_code)
    elif network == "mintegral":
        return get_mintegral_units(app_code)
    elif network == "fyber":
        return get_fyber_units(app_code)
    elif network == "bigoads":
        return get_bigoads_units(app_code)
    
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
    elif network == "inmobi":
        # InMobi: REWARDED_VIDEO, INTERSTITIAL, BANNER
        format_map = {
            "REWARD": "REWARDED_VIDEO",
            "INTER": "INTERSTITIAL",
            "BANNER": "BANNER"
        }
        return format_map.get(ad_format_upper, ad_format.upper())
    elif network == "mintegral":
        # Mintegral: rewarded_video, new_interstitial, banner
        format_map = {
            "REWARD": "rewarded_video",
            "INTER": "new_interstitial",
            "BANNER": "banner"
        }
        return format_map.get(ad_format_upper, ad_format.lower())
    elif network == "fyber":
        # Fyber: Rewarded, Interstitial, Banner
        format_map = {
            "REWARD": "Rewarded",
            "INTER": "Interstitial",
            "BANNER": "Banner"
        }
        return format_map.get(ad_format_upper, ad_format.capitalize())
    elif network == "bigoads":
        # BigOAds: adType numbers (2: Banner, 3: Interstitial, 4: Reward Video)
        format_map = {
            "REWARD": 4,  # Reward Video
            "INTER": 3,   # Interstitial
            "BANNER": 2   # Banner
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
        app_code = app.get("appCode")
        # Handle "N/A" as None (from _get_bigoads_apps default value)
        if app_code == "N/A" or not app_code:
            app_code = None
        result["app_code"] = app_code
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

