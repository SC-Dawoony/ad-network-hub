"""Ad Network Query Utilities for Update Ad Unit page

This module provides functions to query applications and units from various ad networks
to automatically populate ad_network_app_id, ad_network_app_key, and ad_unit_id fields
in the Update Ad Unit page.
"""
import logging
import json
import re
from typing import Dict, List, Optional, Tuple
from utils.network_manager import get_network_manager, _get_env_var

logger = logging.getLogger(__name__)


def find_app_by_name(network: str, app_name: str, platform: Optional[str] = None) -> Optional[Dict]:
    """Find an app by name from a network
    
    Args:
        network: Network name (e.g., "ironsource", "bigoads", "inmobi", "unity")
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
        
        # For Unity, name matching doesn't need platform check (one project can have both iOS and Android)
        if network == "unity":
            app_name_lower = app_name.lower().strip()
            for app in apps:
                app_name_in_list = app.get("name") or app.get("appName") or ""
                if app_name_lower in app_name_in_list.lower() or app_name_in_list.lower() in app_name_lower:
                    logger.info(f"[Unity] Found app by name: '{app_name_in_list}' matches '{app_name}'")
                    return app
            logger.warning(f"[Unity] App '{app_name}' not found by name")
            return None
        
        # For Fyber, add more detailed logging
        if network == "fyber":
            app_name_lower = app_name.lower().strip()
            logger.info(f"[Fyber] Searching for app by name: '{app_name}', platform filter: {platform}")
            logger.info(f"[Fyber] Total apps available: {len(apps)}")
            
            for idx, app in enumerate(apps):
                app_name_in_list = app.get("name") or app.get("appName") or ""
                app_platform = app.get("platform", "")
                app_bundle = app.get("bundle") or app.get("bundleId", "")
                
                logger.info(f"[Fyber] App[{idx}]: name='{app_name_in_list}', platform='{app_platform}', bundle='{app_bundle}'")
                
                if app_name_lower in app_name_in_list.lower():
                    # Check platform if provided
                    if platform:
                        platform_normalized = _normalize_platform_for_matching(app_platform, network)
                        target_platform = platform.lower()
                        logger.info(f"[Fyber] Platform check: app_platform='{app_platform}' -> normalized='{platform_normalized}', target='{target_platform}'")
                        if platform_normalized != target_platform:
                            logger.info(f"[Fyber] Platform mismatch, skipping")
                            continue
                    
                    logger.info(f"[Fyber] ✓ Found matching app: '{app_name_in_list}'")
                    return app
            
            logger.warning(f"[Fyber] App '{app_name}' not found")
            return None
        
        # For other networks, use standard name matching with platform check
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
        network: Network name (e.g., "ironsource", "bigoads", "inmobi", "unity")
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
        
        # For Unity, check stores.storeId
        if network == "unity":
            package_name_lower = package_name.lower().strip()
            target_platform = platform.lower() if platform else None
            
            for app in apps:
                stores_str = app.get("stores", "")
                if not stores_str:
                    continue
                
                # Parse stores JSON string
                try:
                    import json
                    if isinstance(stores_str, str):
                        stores = json.loads(stores_str)
                    else:
                        stores = stores_str
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"[Unity] Failed to parse stores JSON: {stores_str}")
                    continue
                
                # Check apple storeId (iOS)
                if target_platform in (None, "ios"):
                    apple_store = stores.get("apple", {})
                    apple_store_id = apple_store.get("storeId", "")
                    if apple_store_id and package_name_lower == apple_store_id.lower():
                        return app
                
                # Check google storeId (Android)
                if target_platform in (None, "android"):
                    google_store = stores.get("google", {})
                    google_store_id = google_store.get("storeId", "")
                    if google_store_id and package_name_lower == google_store_id.lower():
                        return app
            
            logger.warning(f"[Unity] App with package name '{package_name}' not found in stores")
            return None
        
        # For Fyber, check bundle field
        if network == "fyber":
            package_name_lower = package_name.lower().strip()
            # For Fyber Android, remove trailing "2" if present (e.g., "com.example.app2" -> "com.example.app")
            package_name_normalized = package_name_lower
            if platform and platform.lower() == "android" and package_name_normalized.endswith("2"):
                package_name_normalized = package_name_normalized[:-1]  # Remove trailing "2"
                logger.info(f"[Fyber] Normalized package_name from '{package_name_lower}' to '{package_name_normalized}' (removed trailing '2')")
            
            for app in apps:
                # Fyber uses "bundle" field for package name
                app_bundle = app.get("bundle") or app.get("bundleId") or app.get("packageName", "")
                
                if app_bundle:
                    app_bundle_lower = app_bundle.lower()
                    # Try exact match first
                    if package_name_lower == app_bundle_lower:
                        # Check platform if provided
                        if platform:
                            app_platform = app.get("platform", "")
                            platform_normalized = _normalize_platform_for_matching(app_platform, network)
                            if platform_normalized != platform.lower():
                                continue
                        
                        logger.info(f"[Fyber] Found app by bundle (exact match): {app_bundle}, platform: {app.get('platform')}")
                        return app
                    
                    # For Android, try normalized match (without trailing "2")
                    if platform and platform.lower() == "android" and package_name_normalized == app_bundle_lower:
                        app_platform = app.get("platform", "")
                        platform_normalized = _normalize_platform_for_matching(app_platform, network)
                        if platform_normalized == platform.lower():
                            logger.info(f"[Fyber] Found app by bundle (normalized match, removed '2'): {app_bundle}, platform: {app.get('platform')}")
                            return app
            
            logger.warning(f"[Fyber] App with package name '{package_name}' not found in bundle field")
            return None
        
        # For other networks, use standard package name matching
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
    
    # Handle Fyber format: "android" or "ios" (lowercase)
    if network == "fyber":
        if platform_lower in ["android", "and"]:
            return "android"
        elif platform_lower in ["ios", "iphone", "iphoneos"]:
            return "ios"
    
    # Handle common formats
    if platform_lower in ["android", "1", "and", "aos"]:
        return "android"
    elif platform_lower in ["ios", "2", "iphone", "iphoneos"]:
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


def get_ironsource_instances(app_key: str) -> List[Dict]:
    """Get IronSource instances for an app
    
    API: GET https://platform.ironsrc.com/levelPlay/network/instances/v4/{appKey}/
    
    Args:
        app_key: IronSource app key
    
    Returns:
        List of instance dicts with instanceId, adFormat, networkName, etc.
    """
    try:
        network_manager = get_network_manager()
        instances_response = network_manager._get_ironsource_instances(app_key)
        
        if instances_response.get("status") == 0:
            instances = instances_response.get("result", [])
            logger.info(f"[IronSource] Instances count: {len(instances)}")
            return instances
        else:
            logger.error(f"[IronSource] Failed to get instances: {instances_response.get('msg', 'Unknown error')}")
            return []
    except Exception as e:
        logger.error(f"[IronSource] API Error (Get Instances): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


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
        network: Network name (e.g., "ironsource", "bigoads", "vungle")
        applovin_unit: AppLovin ad unit dict with id, name, platform, package_name
        network_apps: Optional pre-fetched network apps list (to avoid multiple API calls)
    
    Returns:
        Matched app dict with appKey/appCode/appId, or None if not found
    """
    package_name = applovin_unit.get("package_name", "")
    app_name = applovin_unit.get("name", "")
    platform = applovin_unit.get("platform", "").lower()
    
    # For Vungle, placements contain app info, so we need to search placements
    if network == "vungle":
        placements = get_vungle_placements()
        if not placements:
            return None
        
        # Search for placement matching package_name or app_name
        for placement in placements:
            # Parse application object (can be string or dict)
            application = placement.get("application", {})
            if isinstance(application, str):
                try:
                    import json
                    application = json.loads(application)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"[Vungle] Failed to parse application JSON: {application}")
                    application = {}
            
            # Extract app info from application object
            placement_pkg = application.get("store", {}).get("id", "")  # Store ID can be used as package identifier
            placement_app_name = application.get("name", "")
            placement_platform = application.get("platform", "").lower()
            vungle_app_id = application.get("vungleAppId", "")
            application_id = application.get("id", "")
            
            # Normalize platform for comparison
            placement_platform_normalized = _normalize_platform_for_matching(placement_platform, network)
            target_platform_normalized = _normalize_platform_for_matching(platform, network)
            
            # Match by package name first (using store.id or application.id)
            if package_name:
                # Try matching with store.id (iOS App Store ID or Android package)
                if placement_pkg and package_name.lower() == placement_pkg.lower():
                    if placement_platform_normalized == target_platform_normalized:
                        # Extract app info from placement with vungleAppId
                        return {
                            "appId": vungle_app_id or application_id,  # Use vungleAppId as primary identifier
                            "vungleAppId": vungle_app_id,  # Store vungleAppId separately
                            "applicationId": application_id,
                            "name": placement_app_name,
                            "platform": placement_platform,
                            "packageName": placement_pkg,
                            "storeId": placement_pkg
                        }
            
            # Fallback to app name matching
            if app_name and placement_app_name:
                if app_name.lower() in placement_app_name.lower() or placement_app_name.lower() in app_name.lower():
                    if placement_platform_normalized == target_platform_normalized:
                        # Extract app info from placement with vungleAppId
                        return {
                            "appId": vungle_app_id or application_id,  # Use vungleAppId as primary identifier
                            "vungleAppId": vungle_app_id,  # Store vungleAppId separately
                            "applicationId": application_id,
                            "name": placement_app_name,
                            "platform": placement_platform,
                            "packageName": placement_pkg,
                            "storeId": placement_pkg
                        }
        
        return None
    
    # For Unity, match by app name or storeId
    if network == "unity":
        # Try package_name first (storeId matching)
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
    
    # For Fyber iOS, bundle contains App Store ID, so we need a different strategy
    if network == "fyber" and platform == "ios":
        # Strategy 1: Try name matching first (direct match)
        if app_name:
            app = find_app_by_name(network, app_name, platform)
            if app:
                logger.info(f"[Fyber] Found iOS app by name (direct): '{app_name}'")
                return app
        
        # Strategy 2: Find Android app by package_name, then find iOS app with same name
        # This works because Android bundle = package name, iOS bundle = iTunes ID
        if package_name:
            # First, try to find Android app by package_name
            android_app = find_app_by_package_name(network, package_name, "android")
            if android_app:
                android_app_name = android_app.get("name") or android_app.get("appName") or ""
                logger.info(f"[Fyber] Found Android app by package_name: '{package_name}', name: '{android_app_name}'")
                
                # Now find iOS app with the same name
                if android_app_name:
                    ios_app = find_app_by_name(network, android_app_name, "ios")
                    if ios_app:
                        logger.info(f"[Fyber] Found iOS app by matching name from Android app: '{android_app_name}'")
                        return ios_app
                    else:
                        logger.warning(f"[Fyber] Android app found but no iOS app with same name '{android_app_name}'")
        
        # Strategy 3: Fallback to direct package_name matching (unlikely to work for iOS)
        if package_name:
            app = find_app_by_package_name(network, package_name, platform)
            if app:
                logger.info(f"[Fyber] Found iOS app by package_name (fallback): '{package_name}'")
                return app
        
        logger.warning(f"[Fyber] Could not find iOS app for package_name='{package_name}', app_name='{app_name}'")
        return None
    
    # For Mintegral iOS, if standard matching fails, try matching by placement name
    if network == "mintegral" and platform == "ios":
        # Try standard matching first
        if package_name:
            app = find_app_by_package_name(network, package_name, platform)
            if app:
                return app
        
        if app_name:
            app = find_app_by_name(network, app_name, platform)
            if app:
                return app
        
        # If standard matching failed, try matching by placement name
        # Compare AppLovin unit name with Mintegral placement names
        if app_name:
            logger.info(f"[Mintegral] Standard matching failed for iOS, trying placement name matching with AppLovin name: '{app_name}'")
            
            # Normalize AppLovin unit name for comparison
            # Example: "Glamour Boutique iOS RV" -> "glamourboutique"
            applovin_name_normalized = re.sub(r'\s+', '', app_name.lower())  # Remove spaces
            # Remove platform and ad format indicators
            applovin_name_normalized = re.sub(r'\s*(ios|android|aos)\s*', '', applovin_name_normalized, flags=re.IGNORECASE)
            applovin_name_normalized = re.sub(r'\s*(rv|is|bn|reward|interstitial|banner)\s*', '', applovin_name_normalized, flags=re.IGNORECASE)
            applovin_name_normalized = applovin_name_normalized.strip()
            
            logger.info(f"[Mintegral] Normalized AppLovin name: '{applovin_name_normalized}'")
            
            # Get all Mintegral iOS apps
            network_manager = get_network_manager()
            apps = network_manager.get_apps(network)
            if not apps:
                logger.warning(f"[Mintegral] No apps found for placement name matching")
                return None
            
            # Filter iOS apps
            ios_apps = []
            for app in apps:
                app_platform = app.get("platform", "")
                platform_normalized = _normalize_platform_for_matching(app_platform, network)
                if platform_normalized == "ios":
                    ios_apps.append(app)
            
            logger.info(f"[Mintegral] Found {len(ios_apps)} iOS apps to check")
            
            # Check each iOS app's placements
            for app in ios_apps:
                app_id = app.get("app_id") or app.get("id")
                if not app_id:
                    continue
                
                # Get placements for this app
                placements = get_mintegral_units(str(app_id))
                if not placements:
                    continue
                
                # Check if any placement name matches
                for placement in placements:
                    placement_name = placement.get("placement_name", "")
                    if not placement_name:
                        continue
                    
                    # Normalize placement name for comparison
                    # Example: "glamourboutique_ios_mintegral_rv_bidding" -> "glamourboutique"
                    placement_name_normalized = placement_name.lower()
                    # Remove common suffixes/prefixes
                    placement_name_normalized = re.sub(r'_[a-z]+_(ios|android|aos)_', '_', placement_name_normalized)
                    placement_name_normalized = re.sub(r'_(mintegral|rv|is|bn|rewarded|interstitial|banner|bidding).*$', '', placement_name_normalized)
                    placement_name_normalized = placement_name_normalized.strip('_')
                    
                    # Compare normalized names
                    if applovin_name_normalized and placement_name_normalized:
                        # Check if normalized names match (exact or contains)
                        # Also check if one is a suffix/prefix of the other (for cases like "arrowflow" vs "rrow")
                        is_match = False
                        
                        # Exact match
                        if applovin_name_normalized == placement_name_normalized:
                            is_match = True
                        # Contains match (one contains the other)
                        elif applovin_name_normalized in placement_name_normalized or \
                             placement_name_normalized in applovin_name_normalized:
                            is_match = True
                        # Suffix/Prefix match: check if shorter string is a suffix or prefix of longer string
                        else:
                            shorter = min(applovin_name_normalized, placement_name_normalized, key=len)
                            longer = max(applovin_name_normalized, placement_name_normalized, key=len)
                            
                            # Check if shorter is a suffix of longer (e.g., "rrow" is suffix of "arrowflow")
                            if len(shorter) >= 3 and longer.endswith(shorter):
                                is_match = True
                            # Check if shorter is a prefix of longer
                            elif len(shorter) >= 3 and longer.startswith(shorter):
                                is_match = True
                            # Check if there's significant overlap (at least 3 consecutive characters)
                            elif len(shorter) >= 3:
                                for i in range(len(longer) - len(shorter) + 1):
                                    if longer[i:i+len(shorter)] == shorter:
                                        is_match = True
                                        break
                        
                        if is_match:
                            logger.info(f"[Mintegral] Found matching app by placement name: app_id={app_id}, placement_name='{placement_name}', normalized='{placement_name_normalized}', applovin_normalized='{applovin_name_normalized}'")
                            return app
            
            logger.warning(f"[Mintegral] No iOS app found by placement name matching for AppLovin name: '{app_name}'")
            return None
    
    # For other networks, use standard app matching
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
    
    # For IronSource, use GET Instance API (instances instead of ad units)
    # Instances have instanceId, adFormat, networkName, etc.
    if network == "ironsource":
        # First, collect all matching instances by adFormat
        matching_instances = []
        for instance in network_units:
            instance_format = instance.get("adFormat", "").lower()
            if instance_format == target_format.lower():
                matching_instances.append(instance)
        
        # If multiple matches, prioritize bidding instances (isBidder: true)
        if len(matching_instances) > 1:
            # First try to find bidding instances
            bidding_instances = [inst for inst in matching_instances if inst.get("isBidder", False)]
            if bidding_instances:
                logger.info(f"[IronSource] Found {len(bidding_instances)} bidding instances for format '{target_format}'")
                return bidding_instances[0]  # Return first bidding instance
            
            # If no bidding instances, return first match
            logger.warning(f"[IronSource] Multiple instances found for format '{target_format}' but none are bidding instances")
            return matching_instances[0]
        elif len(matching_instances) == 1:
            return matching_instances[0]
        else:
            logger.warning(f"[IronSource] No instances found for format '{target_format}'")
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
    
    # For Vungle, match by type (not placementType)
    if network == "vungle":
        # Vungle uses "type" field (e.g., "interstitial", "rewarded", "banner")
        # Note: API response uses "type" field, not "placementType"
        matching_units = []
        logger.info(f"[Vungle] Finding unit: ad_format={ad_format}, target_format={target_format}")
        logger.info(f"[Vungle] Total units to check: {len(network_units)}")
        
        # Map target_format to lowercase for comparison
        # target_format is "Rewarded", "Interstitial", "Banner" from map_ad_format_to_network_format
        # But actual API response uses lowercase: "interstitial", "rewarded", "banner"
        type_mapping = {
            "rewarded": "rewarded",
            "interstitial": "interstitial",
            "banner": "banner"
        }
        target_type = type_mapping.get(target_format.lower(), target_format.lower())
        
        for idx, unit in enumerate(network_units):
            # Get type field (should be lowercase in API response)
            unit_type = unit.get("type", "").lower()
            unit_name = unit.get("name", "N/A")
            unit_reference_id = unit.get("referenceID", "N/A")
            
            # Also check application.platform for platform matching
            application = unit.get("application", {})
            if isinstance(application, str):
                try:
                    import json
                    application = json.loads(application)
                except (json.JSONDecodeError, TypeError):
                    application = {}
            unit_platform = application.get("platform", "").lower()
            
            logger.info(f"[Vungle] Unit[{idx}]: name={unit_name}, type={unit_type}, referenceID={unit_reference_id}, platform={unit_platform}")
            
            # Match by type (lowercase comparison)
            if unit_type == target_type:
                # Also check platform if provided
                if platform:
                    platform_normalized = _normalize_platform_for_matching(platform, network)
                    unit_platform_normalized = _normalize_platform_for_matching(unit_platform, network)
                    if platform_normalized == unit_platform_normalized:
                        logger.info(f"[Vungle] ✓ Match found: {unit_name} (type={unit_type} == target={target_type}, platform={unit_platform_normalized})")
                        matching_units.append(unit)
                    else:
                        logger.info(f"[Vungle] ✗ Platform mismatch: {unit_name} (type={unit_type} matches but platform {unit_platform_normalized} != {platform_normalized})")
                else:
                    logger.info(f"[Vungle] ✓ Match found: {unit_name} (type={unit_type} == target={target_type})")
                    matching_units.append(unit)
        
        logger.info(f"[Vungle] Total matching units found: {len(matching_units)}")
        
        # If multiple matches and platform is provided, prioritize by platform indicator in name
        if len(matching_units) > 1 and platform:
            platform_normalized = platform.lower()
            platform_indicator = "_aos_" if platform_normalized == "android" else "_ios_"
            
            for unit in matching_units:
                placement_name = unit.get("name", "").lower()
                if platform_indicator in placement_name:
                    logger.info(f"[Vungle] Found unit with platform indicator '{platform_indicator}' in name: {unit.get('name')}, referenceID={unit.get('referenceID')}")
                    return unit
            
            # If no unit has platform indicator, return first match
            logger.warning(f"[Vungle] Multiple units found for format '{target_format}' but none have platform indicator '{platform_indicator}' in name")
            matched_unit = matching_units[0] if matching_units else None
            if matched_unit:
                logger.info(f"[Vungle] Returning first match: {matched_unit.get('name')}, referenceID={matched_unit.get('referenceID')}")
            return matched_unit
        elif len(matching_units) == 1:
            matched_unit = matching_units[0]
            logger.info(f"[Vungle] Returning single match: {matched_unit.get('name')}, referenceID={matched_unit.get('referenceID')}")
            return matched_unit
        else:
            logger.warning(f"[Vungle] No matching units found for format '{target_format}' (target_type={target_type})")
            return None
    
    # For Unity, match by ad format and platform
    if network == "unity":
        # Unity ad units have adFormat field (rewarded, interstitial, banner)
        # Match by ad format and platform
        matching_units = []
        for unit in network_units:
            unit_format = unit.get("adFormat", "").lower()
            unit_platform = unit.get("platform", "").lower()
            
            # Map platform: apple -> ios, google -> android
            platform_mapping = {
                "apple": "ios",
                "google": "android"
            }
            unit_platform_normalized = platform_mapping.get(unit_platform, unit_platform)
            
            # Check format match (target_format is "Rewarded", "Interstitial", "Banner")
            # unit_format is "rewarded", "interstitial", "banner"
            if unit_format == target_format.lower():
                # If platform is provided, check platform match
                if platform:
                    target_platform_normalized = _normalize_platform_for_matching(platform, network)
                    if unit_platform_normalized == target_platform_normalized:
                        matching_units.append(unit)
                else:
                    # No platform filter, match any
                    matching_units.append(unit)
        
        if len(matching_units) == 1:
            matched_unit = matching_units[0]
            logger.info(f"[Unity] Found matching unit: {matched_unit.get('name')}, adFormat: {matched_unit.get('adFormat')}, platform: {matched_unit.get('platform')}")
            return matched_unit
        elif len(matching_units) > 1:
            # If multiple matches, return first one (or could prioritize by platform)
            logger.warning(f"[Unity] Multiple units found for format '{target_format}', returning first match")
            return matching_units[0]
        else:
            logger.warning(f"[Unity] No matching units found for format '{target_format}' (target_format={target_format.lower()})")
            return None
    
    # For Pangle, match by ad_slot_type from API response
    if network == "pangle":
        # Pangle API response structure: data.ad_slot_list[].ad_slot_type
        # ad_slot_type values: 1 (Native Ad), 2 (Banner Ad), 3 (App Open Ad), 5 (Rewarded Video Ad), 6 (Interstitial Ad)
        # We match by comparing ad_slot_type from response with target_format (already mapped to numeric value)
        matching_units = []
        target_ad_slot_type = target_format  # target_format is already the numeric ad_slot_type from map_ad_format_to_network_format
        logger.info(f"[Pangle] Finding unit: ad_format={ad_format}, target_format={target_format}, target_ad_slot_type={target_ad_slot_type} (type: {type(target_ad_slot_type)})")
        logger.info(f"[Pangle] Total units to check: {len(network_units)}")
        
        # Debug: Log all units' ad_slot_type values from API response
        for idx, unit in enumerate(network_units):
            unit_ad_slot_type = unit.get("ad_slot_type")  # From API response: data.ad_slot_list[].ad_slot_type
            unit_name = unit.get("ad_slot_name", "N/A")
            unit_ad_slot_id = unit.get("ad_slot_id", "N/A")
            logger.info(f"[Pangle] Unit[{idx}]: name={unit_name}, ad_slot_id={unit_ad_slot_id}, ad_slot_type={unit_ad_slot_type} (type: {type(unit_ad_slot_type)}), all_keys={list(unit.keys())}")
        
        for unit in network_units:
            # Get ad_slot_type from API response (data.ad_slot_list[].ad_slot_type)
            unit_ad_slot_type = unit.get("ad_slot_type")
            unit_name = unit.get("ad_slot_name", "N/A")
            
            # Check if ad_slot_type field exists in response
            if unit_ad_slot_type is None:
                logger.warning(f"[Pangle] Unit '{unit_name}' has no 'ad_slot_type' field in API response. Available keys: {list(unit.keys())}")
                continue
            
            logger.info(f"[Pangle] Checking unit: name={unit_name}, ad_slot_type={unit_ad_slot_type} (from API response, type: {type(unit_ad_slot_type)})")
            # Compare ad_slot_type from API response with target ad_slot_type
            try:
                unit_ad_slot_type_int = int(unit_ad_slot_type)
                target_ad_slot_type_int = int(target_ad_slot_type)
                if unit_ad_slot_type_int == target_ad_slot_type_int:
                    logger.info(f"[Pangle] ✓ Match found: {unit_name} (ad_slot_type={unit_ad_slot_type_int} from API response == target={target_ad_slot_type_int})")
                    matching_units.append(unit)
                else:
                    logger.info(f"[Pangle] ✗ No match: {unit_name} (ad_slot_type={unit_ad_slot_type_int} from API response != target={target_ad_slot_type_int})")
            except (ValueError, TypeError) as e:
                # If conversion fails, skip
                logger.warning(f"[Pangle] Cannot compare ad_slot_type: {unit_name}, ad_slot_type={unit_ad_slot_type}, error={e}")
                continue
        
        logger.info(f"[Pangle] Total matching units found: {len(matching_units)}")
        
        # If multiple matches and platform is provided, prioritize by platform indicator in name
        if len(matching_units) > 1 and platform:
            platform_normalized = platform.lower()
            platform_indicator = "_aos_" if platform_normalized == "android" else "_ios_"
            
            for unit in matching_units:
                slot_name = unit.get("ad_slot_name", "").lower()
                if platform_indicator in slot_name:
                    logger.info(f"[Pangle] Found unit with platform indicator '{platform_indicator}' in name: {unit.get('ad_slot_name')}")
                    return unit
            
            # If no unit has platform indicator, return first match
            logger.warning(f"[Pangle] Multiple units found for format '{target_format}' but none have platform indicator '{platform_indicator}' in name")
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


def get_mintegral_units_by_placement(placement_id: int) -> List[Dict]:
    """Get Mintegral ad units by placement_id
    
    API: GET https://dev.mintegral.com/v2/unit/open_api_list?placement_id={placement_id}
    
    Args:
        placement_id: Mintegral placement ID
    
    Returns:
        List of ad unit dicts with unit_id, unit_name, etc.
    """
    try:
        # Mintegral API 인증: skey, time, sign
        skey = _get_env_var("MINTEGRAL_SKEY")
        secret = _get_env_var("MINTEGRAL_SECRET")
        
        if not skey or not secret:
            logger.error("[Mintegral] Cannot get units by placement: MINTEGRAL_SKEY and MINTEGRAL_SECRET must be set")
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
        
        url = "https://dev.mintegral.com/v2/unit/open_api_list"
        
        # Query parameters
        params = {
            "placement_id": int(placement_id) if isinstance(placement_id, (int, str)) and str(placement_id).isdigit() else placement_id,
            "skey": skey,
            "time": time_str,
            "sign": signature,
            "page": 1,
            "per_page": 100,
        }
        
        logger.info(f"[Mintegral] API Request: GET {url} (placement_id={placement_id})")
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
                if result.get("code") == 200 or result.get("code") == 0:
                    data = result.get("data", {})
                    if isinstance(data, dict):
                        units = data.get("lists", data.get("units", []))
                    elif isinstance(data, list):
                        units = data
                else:
                    error_msg = result.get("msg") or result.get("message") or "Unknown error"
                    logger.error(f"[Mintegral] API returned code={result.get('code')}: {error_msg}")
            elif isinstance(result, list):
                units = result
            
            logger.info(f"[Mintegral] Units count for placement_id {placement_id}: {len(units)}")
            return units
        else:
            try:
                error_body = response.json()
                logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
            except:
                logger.error(f"[Mintegral] Error Response (text): {response.text}")
            return []
    except Exception as e:
        logger.error(f"[Mintegral] API Error (Get Units by Placement): {str(e)}")
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


def get_vungle_placements() -> List[Dict]:
    """Get all placements from Vungle API
    
    Note: Vungle placements contain both app and unit info in a single response
    
    Returns:
        List of placement dicts
    """
    try:
        network_manager = get_network_manager()
        placements = network_manager._get_vungle_placements()
        return placements
    except Exception as e:
        logger.error(f"[Vungle] Error getting placements: {str(e)}")
        return []


def get_unity_projects() -> List[Dict]:
    """Get all projects (apps) from Unity API
    
    Returns:
        List of project dicts
    """
    try:
        network_manager = get_network_manager()
        projects = network_manager._get_unity_projects()
        return projects
    except Exception as e:
        logger.error(f"[Unity] Error getting projects: {str(e)}")
        return []


def get_unity_ad_units(project_id: str) -> Dict:
    """Get ad units for a Unity project
    
    Args:
        project_id: Unity project ID
    
    Returns:
        Dict with "apple" and "google" keys containing ad units
    """
    try:
        network_manager = get_network_manager()
        ad_units = network_manager._get_unity_ad_units(project_id)
        return ad_units
    except Exception as e:
        logger.error(f"[Unity] Error getting ad units: {str(e)}")
        return {}


def get_unity_units(project_id: str) -> List[Dict]:
    """Get ad units for a Unity project (flattened format)
    
    Args:
        project_id: Unity project ID
    
    Returns:
        List of ad unit dicts (flattened from apple/google structure)
        Each unit has: id, name, adFormat, placements (parsed), platform, etc.
    """
    try:
        ad_units_dict = get_unity_ad_units(project_id)
        logger.info(f"[Unity] get_unity_units: ad_units_dict type: {type(ad_units_dict)}, keys: {list(ad_units_dict.keys()) if isinstance(ad_units_dict, dict) else 'not a dict'}")
        units = []
        
        # Flatten apple and google ad units
        # Unity API returns: {"apple": {"iOS_RV_Bidding": {...}, "iOS_IS_Bidding": {...}}, "google": {...}}
        for platform, platform_units in ad_units_dict.items():
            logger.info(f"[Unity] Processing platform: {platform}, type: {type(platform_units)}")
            
            if isinstance(platform_units, dict):
                # platform_units is a dict where keys are ad unit IDs (e.g., "iOS_RV_Bidding")
                # and values are ad unit objects
                logger.info(f"[Unity] platform_units dict keys: {list(platform_units.keys())[:5]}")
                
                for unit_key, unit in platform_units.items():
                    if isinstance(unit, dict):
                        unit_with_platform = unit.copy()
                        unit_with_platform["platform"] = platform
                        # Ensure unit has id field (use the key if not present)
                        if "id" not in unit_with_platform:
                            unit_with_platform["id"] = unit_key
                        
                        # Parse placements JSON string if present
                        placements_str = unit_with_platform.get("placements", "")
                        logger.info(f"[Unity] Unit {unit_key} placements type: {type(placements_str)}, value: {str(placements_str)[:200] if placements_str else 'empty'}")
                        
                        if placements_str:
                            if isinstance(placements_str, str):
                                try:
                                    import json
                                    # Handle escaped double quotes
                                    try:
                                        placements = json.loads(placements_str)
                                        logger.info(f"[Unity] Successfully parsed placements (first attempt) for {unit_key}")
                                    except json.JSONDecodeError:
                                        cleaned_str = placements_str.replace('""', '"')
                                        placements = json.loads(cleaned_str)
                                        logger.info(f"[Unity] Successfully parsed placements (after cleaning) for {unit_key}")
                                    unit_with_platform["placements_parsed"] = placements
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.warning(f"[Unity] Failed to parse placements JSON for {unit_key}: {placements_str[:100]}, error: {e}")
                                    unit_with_platform["placements_parsed"] = {}
                            elif isinstance(placements_str, dict):
                                # Already a dict, use as-is
                                logger.info(f"[Unity] placements is already a dict for {unit_key}")
                                unit_with_platform["placements_parsed"] = placements_str
                            else:
                                logger.warning(f"[Unity] Unexpected placements type for {unit_key}: {type(placements_str)}")
                                unit_with_platform["placements_parsed"] = {}
                        else:
                            logger.warning(f"[Unity] Unit {unit_key} has no placements field: {list(unit_with_platform.keys())}")
                            unit_with_platform["placements_parsed"] = {}
                        
                        units.append(unit_with_platform)
                        logger.info(f"[Unity] Added unit: {unit_with_platform.get('name')}, id: {unit_with_platform.get('id')}, adFormat: {unit_with_platform.get('adFormat')}, platform: {platform}")
            elif isinstance(platform_units, list):
                # If it's a list (unlikely but handle it)
                for unit in platform_units:
                    if isinstance(unit, dict):
                        unit_with_platform = unit.copy()
                        unit_with_platform["platform"] = platform
                        # Parse placements JSON string if present
                        placements_str = unit_with_platform.get("placements", "")
                        if placements_str:
                            if isinstance(placements_str, str):
                                try:
                                    import json
                                    try:
                                        placements = json.loads(placements_str)
                                    except json.JSONDecodeError:
                                        cleaned_str = placements_str.replace('""', '"')
                                        placements = json.loads(cleaned_str)
                                    unit_with_platform["placements_parsed"] = placements
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.warning(f"[Unity] Failed to parse placements JSON: {placements_str[:100]}, error: {e}")
                                    unit_with_platform["placements_parsed"] = {}
                            elif isinstance(placements_str, dict):
                                unit_with_platform["placements_parsed"] = placements_str
                        else:
                            unit_with_platform["placements_parsed"] = {}
                        units.append(unit_with_platform)
        
        return units
    except Exception as e:
        logger.error(f"[Unity] Error getting units: {str(e)}")
        return []


def get_vungle_units(app_id: Optional[str] = None) -> List[Dict]:
    """Get placements (units) for a Vungle app
    
    Args:
        app_id: Optional vungleAppId to filter by (if None, returns all placements)
    
    Returns:
        List of placement dicts with status "active" only
    """
    try:
        placements = get_vungle_placements()
        
        # Filter by status "active" first
        active_placements = []
        for placement in placements:
            status = placement.get("status", "").lower()
            if status == "active":
                active_placements.append(placement)
            else:
                logger.debug(f"[Vungle] Skipping placement '{placement.get('name', 'N/A')}' with status '{status}' (not active)")
        
        logger.info(f"[Vungle] Filtered {len(active_placements)} active placements from {len(placements)} total placements")
        
        if app_id:
            # Filter by vungleAppId from application object
            filtered = []
            for placement in active_placements:
                # Parse application object (can be string or dict)
                application = placement.get("application", {})
                if isinstance(application, str):
                    try:
                        import json
                        application = json.loads(application)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"[Vungle] Failed to parse application JSON in get_vungle_units: {application[:100]}")
                        continue
                
                # Check vungleAppId
                vungle_app_id = application.get("vungleAppId", "")
                if str(vungle_app_id) == str(app_id):
                    filtered.append(placement)
            
            logger.info(f"[Vungle] Filtered {len(filtered)} active placements for app_id={app_id}")
            return filtered
        
        return active_placements
    except Exception as e:
        logger.error(f"[Vungle] Error getting units: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def _mask_sensitive_data(data: Dict) -> Dict:
    """Mask sensitive data in dict for logging"""
    masked = data.copy()
    sensitive_keys = ["sign", "skey", "secret", "token", "password", "authorization"]
    for key in sensitive_keys:
        if key in masked:
            masked[key] = "***MASKED***"
    return masked


def get_pangle_units(app_id: Optional[str] = None) -> List[Dict]:
    """Get Pangle ad units (placements)
    
    API: POST https://open-api.pangleglobal.com/union/media/open_api/code/query
    
    Strategy: Query all ad units using user_id and role_id (no app_id filter),
    then filter by app_id on client side for better performance and caching.
    
    Args:
        app_id: Optional Pangle app ID (site_id or app_id) to filter by.
                If provided, filters results on client side.
                If None, returns all ad units.
    
    Returns:
        List of ad unit dicts with ad_slot_id, ad_slot_name, ad_slot_type, app_id, etc.
        Filtered by app_id on client side if app_id is provided.
    """
    try:
        security_key = _get_env_var("PANGLE_SECURITY_KEY")
        user_id = _get_env_var("PANGLE_USER_ID")
        role_id = _get_env_var("PANGLE_ROLE_ID")
        
        if not security_key or not user_id or not role_id:
            logger.error("[Pangle] Cannot get units: PANGLE_SECURITY_KEY, PANGLE_USER_ID, and PANGLE_ROLE_ID must be set")
            return []
        
        try:
            user_id_int = int(user_id)
            role_id_int = int(role_id)
            app_id_int = int(app_id) if app_id and app_id.isdigit() else None
        except (ValueError, TypeError):
            logger.error("[Pangle] PANGLE_USER_ID, PANGLE_ROLE_ID must be integers")
            if app_id:
                logger.error(f"[Pangle] app_id must be an integer if provided: {app_id}")
            return []
        
        # Check if sandbox mode is enabled
        sandbox_env = _get_env_var("PANGLE_SANDBOX")
        sandbox = sandbox_env and sandbox_env.lower() == "true" if sandbox_env else False
        
        if sandbox:
            url = "http://open-api-sandbox.pangleglobal.com/union/media/open_api/code/query"
            logger.info("[Pangle] Using SANDBOX environment for unit query")
        else:
            url = "https://open-api.pangleglobal.com/union/media/open_api/code/query"
            logger.info("[Pangle] Using PRODUCTION environment for unit query")
        
        # Generate signature
        import time
        import random
        timestamp = int(time.time())
        nonce = random.randint(1, 2147483647)
        
        # Generate signature using network_manager's method
        network_manager = get_network_manager()
        signature = network_manager._generate_pangle_signature(security_key, timestamp, nonce)
        
        # Request payload: Query ALL ad units using user_id and role_id (no app_id filter)
        # This allows us to cache all ad units and filter on client side
        payload = {
            "user_id": user_id_int,
            "role_id": role_id_int,
            "timestamp": timestamp,
            "nonce": nonce,
            "sign": signature,
            "version": "1.0",
            "page": 1,
            "page_size": 100  # Increase page size to get more results
        }
        
        # Do NOT include app_id in payload - query all ad units
        # Filter by app_id on client side after receiving response
        logger.info(f"[Pangle] Querying ALL ad units (user_id={user_id_int}, role_id={role_id_int}, no app_id filter)")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"[Pangle] Unit Query API Request: POST {url}")
        logger.info(f"[Pangle] Request Payload: {json.dumps(_mask_sensitive_data(payload), indent=2)}")
        
        import requests
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        logger.info(f"[Pangle] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"[Pangle] Response Body: {json.dumps(_mask_sensitive_data(result), indent=2)}")
                
                code = result.get("code")
                data = result.get("data", {})
                
                if code == 0 or code == 200:
                    # Pangle API response structure: {code: 0, data: {ad_slot_list: [...], page_info: {...}}}
                    # Extract ad_slot_list from data
                    ad_slot_list = data.get("ad_slot_list", [])
                    
                    # Fallback to other possible field names
                    if not ad_slot_list:
                        ad_slot_list = (
                            data.get("list") or
                            data.get("ad_slots") or
                            data.get("slots") or
                            []
                        )
                    
                    # If data itself is a list, use it directly
                    if isinstance(data, list):
                        ad_slot_list = data
                    
                    # Get total from page_info if available
                    page_info = data.get("page_info", {})
                    total = page_info.get("total_number") if page_info else data.get("total", len(ad_slot_list))
                    
                    logger.info(f"[Pangle] Extracted {len(ad_slot_list)} ad units from API response (total: {total})")
                    
                    # Filter by app_id on client side if provided
                    if app_id_int:
                        original_count = len(ad_slot_list)
                        ad_slot_list = [unit for unit in ad_slot_list if unit.get("app_id") == app_id_int]
                        logger.info(f"[Pangle] Filtered {original_count} units to {len(ad_slot_list)} units for app_id: {app_id_int}")
                    elif app_id:
                        # app_id was provided but not a valid integer, try string comparison
                        original_count = len(ad_slot_list)
                        ad_slot_list = [unit for unit in ad_slot_list if str(unit.get("app_id")) == str(app_id)]
                        logger.info(f"[Pangle] Filtered {original_count} units to {len(ad_slot_list)} units for app_id: {app_id} (string comparison)")
                    
                    if ad_slot_list and len(ad_slot_list) > 0:
                        logger.info(f"[Pangle] First unit keys: {list(ad_slot_list[0].keys())}")
                        logger.info(f"[Pangle] First unit ad_slot_id: {ad_slot_list[0].get('ad_slot_id', 'N/A')}")
                        logger.info(f"[Pangle] First unit app_id: {ad_slot_list[0].get('app_id', 'N/A')}")
                        logger.info(f"[Pangle] First unit: {json.dumps(_mask_sensitive_data(ad_slot_list[0]), indent=2)}")
                    return ad_slot_list
                else:
                    error_msg = result.get("msg") or result.get("message") or "Unknown error"
                    logger.error(f"[Pangle] API returned code={code}: {error_msg}")
                    return []
            except json.JSONDecodeError as e:
                logger.error(f"[Pangle] JSON decode error: {str(e)}")
                logger.error(f"[Pangle] Response text: {response.text[:500]}")
                return []
        else:
            try:
                error_body = response.json()
                logger.error(f"[Pangle] Error Response: {json.dumps(error_body, indent=2)}")
            except:
                logger.error(f"[Pangle] Error Response (text): {response.text}")
            return []
    except Exception as e:
        logger.error(f"[Pangle] API Error (Get Units): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_network_units(network: str, app_code: str) -> List[Dict]:
    """Get ad units for a network app
    
    Args:
        network: Network name (e.g., "ironsource", "bigoads", "inmobi", "mintegral", "fyber", "vungle", "unity", "pangle")
        app_code: App code (appKey for IronSource, appId for InMobi/Mintegral/Fyber/Vungle/Pangle, appCode for BigOAds, projectId for Unity, etc.)
    
    Returns:
        List of ad unit dicts
    """
    if network == "ironsource":
        # For Update Ad Unit page, use GET Instance API instead of GET Ad Units API
        return get_ironsource_instances(app_code)
    elif network == "inmobi":
        return get_inmobi_units(app_code)
    elif network == "mintegral":
        return get_mintegral_units(app_code)
    elif network == "fyber":
        return get_fyber_units(app_code)
    elif network == "bigoads":
        return get_bigoads_units(app_code)
    elif network == "vungle":
        return get_vungle_units(app_code)
    elif network == "unity":
        return get_unity_units(app_code)  # app_code is projectId for Unity
    elif network == "pangle":
        logger.info(f"[Pangle] get_network_units called with app_code: {app_code}")
        units = get_pangle_units(app_code)  # app_code is app_id for Pangle
        logger.info(f"[Pangle] get_pangle_units returned {len(units) if units else 0} units")
        return units
    
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
        "TIKTOK_BIDDING": "pangle",  # TikTok is Pangle
        "VUNGLE_BIDDING": "vungle",
        "UNITY_BIDDING": "unity",
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
    elif network == "vungle":
        # Vungle: placementType (Rewarded, Interstitial, Banner, MREC)
        format_map = {
            "REWARD": "Rewarded",
            "INTER": "Interstitial",
            "BANNER": "Banner"
        }
        return format_map.get(ad_format_upper, ad_format.capitalize())
    elif network == "unity":
        # Unity: Rewarded, Interstitial, Banner
        format_map = {
            "REWARD": "Rewarded",
            "INTER": "Interstitial",
            "BANNER": "Banner"
        }
        return format_map.get(ad_format_upper, ad_format.capitalize())
    elif network == "pangle":
        # Pangle: ad_slot_type numbers from API response
        # API response field: ad_slot_type
        # Available values: 1 (Native Ad), 2 (Banner Ad), 3 (App Open Ad), 5 (Rewarded Video Ad), 6 (Interstitial Ad)
        format_map = {
            "REWARD": 5,  # Rewarded Video Ad (ad_slot_type: 5)
            "INTER": 6,   # Interstitial Ad (ad_slot_type: 6)
            "BANNER": 2   # Banner Ad (ad_slot_type: 2)
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
        # Debug logging for BigOAds
        logger.info(f"[BigOAds] extract_app_identifiers: app keys={list(app.keys())}, appCode={app.get('appCode')}, extracted app_code={app_code}")
    elif network == "inmobi":
        result["app_id"] = app.get("appId") or app.get("id")
        result["app_code"] = str(result["app_id"]) if result["app_id"] else None
    elif network == "mintegral":
        result["app_id"] = app.get("app_id") or app.get("id")
        result["app_code"] = str(result["app_id"]) if result["app_id"] else None
    elif network == "fyber":
        # Fyber uses "id" field for appId
        # Note: _get_fyber_apps converts to standard format with "appId" field
        # But original API response uses "id" field
        app_id_value = app.get("id") or app.get("appId")
        
        # Handle "N/A" as None (from _get_fyber_apps default value)
        if app_id_value == "N/A" or app_id_value == "":
            app_id_value = None
        
        result["app_id"] = app_id_value
        result["app_code"] = str(app_id_value) if app_id_value else None
        logger.info(f"[Fyber] extract_app_identifiers: app keys={list(app.keys())}, id={app.get('id')}, appId={app.get('appId')}, extracted app_id={app_id_value}")
    elif network == "vungle":
        # Vungle uses vungleAppId from application object
        result["app_id"] = app.get("vungleAppId") or app.get("appId") or app.get("applicationId") or app.get("id")
        result["app_code"] = str(result["app_id"]) if result["app_id"] else None
    elif network == "unity":
        # Unity uses gameId from stores (platform-specific)
        # projectId is stored for reference, but gameId will be extracted based on platform
        project_id = app.get("projectId") or app.get("id")
        result["projectId"] = project_id  # Store projectId for reference
        result["app_code"] = str(project_id) if project_id else None
        
        # Store stores info for later gameId extraction
        stores_str = app.get("stores", "")
        stores = None
        if stores_str:
            try:
                import json
                if isinstance(stores_str, str):
                    stores = json.loads(stores_str)
                else:
                    stores = stores_str
            except (json.JSONDecodeError, TypeError):
                pass
        
        result["stores"] = stores  # Store stores for gameId extraction
        result["app_id"] = project_id  # For now, use projectId (gameId will be extracted separately)
    elif network == "pangle":
        # Pangle uses app_id (or site_id) for app identification
        app_id_value = app.get("appId") or app.get("siteId") or app.get("id")
        result["app_id"] = app_id_value
        result["app_code"] = str(app_id_value) if app_id_value else None
        logger.info(f"[Pangle] extract_app_identifiers: app keys={list(app.keys())}, appId={app.get('appId')}, siteId={app.get('siteId')}, extracted app_id={app_id_value}")
    else:
        # Generic fallback
        result["app_code"] = app.get("appCode") or app.get("appKey") or app.get("appId")
        result["app_id"] = app.get("appId") or app.get("id")
        result["app_key"] = app.get("appKey")
    
    return result

