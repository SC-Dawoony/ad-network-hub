"""AppLovin API manager for Ad Unit settings updates"""
from typing import Dict, List, Optional, Tuple
import requests
import json
import logging
import pandas as pd
from utils.network_manager import _get_env_var

logger = logging.getLogger(__name__)


def get_applovin_api_key() -> Optional[str]:
    """Get AppLovin API Key from environment variables"""
    return _get_env_var("APPLOVIN_API_KEY")


def transform_csv_data_to_api_format(csv_data: List[Dict]) -> Dict:
    """
    Transform CSV-like data to AppLovin API format (same logic as original read_file function)
    
    Args:
        csv_data: List of dicts from CSV/DataFrame
            Each item should have:
            - id, name, platform, ad_format, package_name, segment_id (optional)
            - ad_network, ad_unit_id, countries_type, countries, cpm, disabled (optional)
    
    Returns:
        Dictionary with structure: {segment_id: {ad_unit_id: {...}}}
    """
    ad_unit_by_ad_id = {}
    
    for row in csv_data:
        # Get segment_id (default to "None")
        segment_id = "None"
        if row.get("segment_id") and pd.notna(row.get("segment_id")) and str(row["segment_id"]).strip():
            segment_id = str(int(row["segment_id"]))
        
        if segment_id not in ad_unit_by_ad_id:
            ad_unit_by_ad_id[segment_id] = {}
        
        # Get ad unit ID
        ad_unit_id = row.get("id")
        if not ad_unit_id or (isinstance(ad_unit_id, float) and pd.isna(ad_unit_id)):
            continue
        
        ad_unit_id = str(ad_unit_id).strip()
        if not ad_unit_id:
            continue
        
        if ad_unit_id not in ad_unit_by_ad_id[segment_id]:
            ad_unit_by_ad_id[segment_id][ad_unit_id] = {
                "id": ad_unit_id,
                "name": str(row.get("name", "")).strip() if row.get("name") and pd.notna(row.get("name")) else "",
                "platform": str(row.get("platform", "")).strip().lower() if row.get("platform") and pd.notna(row.get("platform")) else "",
                "ad_format": str(row.get("ad_format", "")).strip().upper() if row.get("ad_format") and pd.notna(row.get("ad_format")) else "",
                "package_name": str(row.get("package_name", "")).strip() if row.get("package_name") and pd.notna(row.get("package_name")) else "",
                "ad_network_settings": {}
            }
        
        data = ad_unit_by_ad_id[segment_id][ad_unit_id]
        
        # Get ad network
        ad_network = row.get("ad_network")
        if not ad_network or (isinstance(ad_network, float) and pd.isna(ad_network)):
            continue
        
        ad_network = str(ad_network).strip()
        if not ad_network:
            continue
        
        if ad_network not in data["ad_network_settings"]:
            disabled = False
            if row.get("disabled") is not None:
                if isinstance(row.get("disabled"), bool):
                    disabled = row.get("disabled")
                elif isinstance(row.get("disabled"), str):
                    disabled = row.get("disabled").upper() in ["TRUE", "1", "YES"]
            
            network_config = {
                "disabled": disabled,
                "ad_network_ad_units": []
            }
            
            # Add ad_network_app_id if provided
            if row.get("ad_network_app_id") and pd.notna(row.get("ad_network_app_id")):
                app_id = str(row["ad_network_app_id"]).strip()
                if app_id:
                    network_config["ad_network_app_id"] = app_id
            
            # Add ad_network_app_key if provided
            if row.get("ad_network_app_key") and pd.notna(row.get("ad_network_app_key")):
                app_key = str(row["ad_network_app_key"]).strip()
                if app_key:
                    network_config["ad_network_app_key"] = app_key
            
            data["ad_network_settings"][ad_network] = network_config
        
        # Get ad network ad unit data
        ad_network_ad_unit_id = row.get("ad_unit_id")
        if not ad_network_ad_unit_id or (isinstance(ad_network_ad_unit_id, float) and pd.isna(ad_network_ad_unit_id)):
            continue
        
        ad_network_ad_unit_id = str(ad_network_ad_unit_id).strip()
        if not ad_network_ad_unit_id:
            continue
        
        # Get countries
        countries = []
        if row.get("countries") and pd.notna(row.get("countries")):
            countries_str = str(row["countries"]).strip()
            if countries_str:
                # Remove quotes if present
                countries_str = countries_str.strip('"').strip("'")
                countries = [c.strip().upper() for c in countries_str.split(",") if c.strip()]
        
        # Get countries_type
        countries_type = "include"
        if row.get("countries_type") and pd.notna(row.get("countries_type")):
            ct = str(row["countries_type"]).strip().upper()
            if ct in ["INCLUDE", "EXCLUDE"]:
                countries_type = ct.lower()
        
        # Get CPM
        cpm = 0.0
        if row.get("cpm") is not None and pd.notna(row.get("cpm")):
            try:
                cpm = float(row["cpm"])
            except (ValueError, TypeError):
                cpm = 0.0
        
        # Get disabled for ad unit
        ad_unit_disabled = False
        if row.get("disabled") is not None:
            if isinstance(row.get("disabled"), bool):
                ad_unit_disabled = row.get("disabled")
            elif isinstance(row.get("disabled"), str):
                ad_unit_disabled = row.get("disabled").upper() in ["TRUE", "1", "YES"]
        
        ad_unit_item = {
            "ad_network_ad_unit_id": ad_network_ad_unit_id,
            "cpm": cpm,
            "countries": {
                "type": countries_type,
                "values": countries
            },
            "disabled": ad_unit_disabled
        }
        
        data["ad_network_settings"][ad_network]["ad_network_ad_units"].append(ad_unit_item)
    
    # Transform ad_network_settings from dict to list format
    for segment_id in ad_unit_by_ad_id:
        for ad_unit_id in ad_unit_by_ad_id[segment_id]:
            ad_network_settings = ad_unit_by_ad_id[segment_id][ad_unit_id]["ad_network_settings"]
            new_ad_network_settings = []
            
            for network in ad_network_settings:
                obj = {network: ad_network_settings[network]}
                new_ad_network_settings.append(obj)
            
            ad_unit_by_ad_id[segment_id][ad_unit_id]["ad_network_settings"] = new_ad_network_settings
    
    return ad_unit_by_ad_id


def transform_form_data_to_api_format(ad_units_data: List[Dict]) -> Dict:
    """
    Transform form data to AppLovin API format (same logic as original read_file function)
    
    Args:
        ad_units_data: List of ad unit data from form
            Each item should have:
            - id, name, platform, ad_format, package_name, segment_id
            - ad_networks: List of ad network configs with:
              - ad_network, ad_network_app_id, ad_network_app_key
              - ad_network_ad_units: List with:
                - ad_network_ad_unit_id, cpm, countries, countries_type, disabled
    
    Returns:
        Dictionary with structure: {segment_id: {ad_unit_id: {...}}}
    """
    ad_unit_by_ad_id = {}
    
    for ad_unit in ad_units_data:
        # Get segment_id (default to "None")
        segment_id = "None"
        if ad_unit.get("segment_id") and str(ad_unit["segment_id"]).strip():
            segment_id = str(int(ad_unit["segment_id"]))
        
        if segment_id not in ad_unit_by_ad_id:
            ad_unit_by_ad_id[segment_id] = {}
        
        # Get ad unit ID
        ad_unit_id = ad_unit.get("id")
        if not ad_unit_id:
            continue
        
        if ad_unit_id not in ad_unit_by_ad_id[segment_id]:
            ad_unit_by_ad_id[segment_id][ad_unit_id] = {
                "id": ad_unit_id,
                "name": ad_unit.get("name", ""),
                "platform": ad_unit.get("platform", ""),
                "ad_format": ad_unit.get("ad_format", ""),
                "package_name": ad_unit.get("package_name", ""),
                "ad_network_settings": {}
            }
        
        data = ad_unit_by_ad_id[segment_id][ad_unit_id]
        
        # Process each ad network
        for network_config in ad_unit.get("ad_networks", []):
            ad_network = network_config.get("ad_network")
            if not ad_network:
                continue
            
            if ad_network not in data["ad_network_settings"]:
                data["ad_network_settings"][ad_network] = {
                    "disabled": network_config.get("disabled", False),
                    "ad_network_ad_units": []
                }
            
            # Add ad_network_app_id and ad_network_app_key if provided
            if network_config.get("ad_network_app_id"):
                data["ad_network_settings"][ad_network]["ad_network_app_id"] = network_config["ad_network_app_id"]
            
            if network_config.get("ad_network_app_key"):
                data["ad_network_settings"][ad_network]["ad_network_app_key"] = network_config["ad_network_app_key"]
            
            # Process ad network ad units
            for ad_unit_config in network_config.get("ad_network_ad_units", []):
                countries = []
                if ad_unit_config.get("countries"):
                    countries_str = str(ad_unit_config["countries"])
                    if countries_str:
                        countries = [c.strip() for c in countries_str.split(",") if c.strip()]
                
                ad_unit_item = {
                    "ad_network_ad_unit_id": ad_unit_config.get("ad_network_ad_unit_id", ""),
                    "cpm": ad_unit_config.get("cpm", 0),
                    "countries": {
                        "type": ad_unit_config.get("countries_type", "include"),
                        "values": countries
                    },
                    "disabled": ad_unit_config.get("disabled", False)
                }
                
                data["ad_network_settings"][ad_network]["ad_network_ad_units"].append(ad_unit_item)
    
    # Transform ad_network_settings from dict to list format
    for segment_id in ad_unit_by_ad_id:
        for ad_unit_id in ad_unit_by_ad_id[segment_id]:
            ad_network_settings = ad_unit_by_ad_id[segment_id][ad_unit_id]["ad_network_settings"]
            new_ad_network_settings = []
            
            for network in ad_network_settings:
                obj = {network: ad_network_settings[network]}
                new_ad_network_settings.append(obj)
            
            ad_unit_by_ad_id[segment_id][ad_unit_id]["ad_network_settings"] = new_ad_network_settings
    
    return ad_unit_by_ad_id


def get_api_url(ad_unit_id: str, segment_id: str) -> str:
    """Get AppLovin API URL for ad unit update"""
    if segment_id == "None":
        return f"https://o.applovin.com/mediation/v1/ad_unit/{ad_unit_id}?fields=ad_network_settings"
    else:
        return f"https://o.applovin.com/mediation/v1/ad_unit/{ad_unit_id}/{segment_id}?fields=ad_network_settings"


def update_ad_unit_settings(
    api_key: str,
    ad_unit_id: str,
    segment_id: str,
    data: Dict
) -> Tuple[bool, Dict]:
    """
    Update ad unit settings via AppLovin API
    
    Args:
        api_key: AppLovin API Key
        ad_unit_id: Ad Unit ID
        segment_id: Segment ID (or "None")
        data: Request payload
    
    Returns:
        Tuple of (success: bool, response_data: Dict)
    """
    url = get_api_url(ad_unit_id, segment_id)
    headers = {
        "Accept": "application/json",
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"[AppLovin] API Request: POST {url}")
        logger.info(f"[AppLovin] Request Payload: {json.dumps(data, indent=2)}")
        
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(data),
            timeout=30
        )
        
        logger.info(f"[AppLovin] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"[AppLovin] Response Body: {json.dumps(result, indent=2)}")
                return True, {"status": "success", "data": result}
            except json.JSONDecodeError:
                return True, {"status": "success", "data": {"message": "Updated successfully"}}
        else:
            try:
                error_data = response.json()
                logger.error(f"[AppLovin] Error Response: {json.dumps(error_data, indent=2)}")
                return False, {"status": "error", "status_code": response.status_code, "data": error_data}
            except json.JSONDecodeError:
                logger.error(f"[AppLovin] Error Response Text: {response.text}")
                return False, {"status": "error", "status_code": response.status_code, "data": {"message": response.text}}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[AppLovin] Request Error: {str(e)}")
        return False, {"status": "error", "error": str(e)}


def update_multiple_ad_units(
    api_key: str,
    ad_units_by_segment: Dict
) -> Dict:
    """
    Update multiple ad units (batch processing)
    
    Args:
        api_key: AppLovin API Key
        ad_units_by_segment: Dictionary with structure: {segment_id: {ad_unit_id: {...}}}
    
    Returns:
        Dictionary with success and fail lists
    """
    success_list = []
    fail_list = []
    
    for segment_id in ad_units_by_segment:
        for ad_unit_id in ad_units_by_segment[segment_id]:
            data = ad_units_by_segment[segment_id][ad_unit_id]
            
            success, result = update_ad_unit_settings(api_key, ad_unit_id, segment_id, data)
            
            if success:
                success_list.append({
                    "segment_id": segment_id,
                    "ad_unit_id": ad_unit_id,
                    "data": result.get("data", {})
                })
            else:
                fail_list.append({
                    "segment_id": segment_id,
                    "ad_unit_id": ad_unit_id,
                    "error": result
                })
    
    return {
        "success": success_list,
        "fail": fail_list
    }


def get_ad_units(api_key: str) -> Tuple[bool, Dict]:
    """
    Get ad units list from AppLovin API
    
    Args:
        api_key: AppLovin API Key
    
    Returns:
        Tuple of (success: bool, response_data: Dict)
    """
    url = "https://o.applovin.com/mediation/v1/ad_units"
    headers = {
        "Accept": "application/json",
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"[AppLovin] API Request: GET {url}")
        
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"[AppLovin] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"[AppLovin] Response Body: {json.dumps(result, indent=2)}")
                return True, {"status": "success", "data": result}
            except json.JSONDecodeError:
                return True, {"status": "success", "data": {"message": response.text}}
        else:
            try:
                error_data = response.json()
                logger.error(f"[AppLovin] Error Response: {json.dumps(error_data, indent=2)}")
                return False, {"status": "error", "status_code": response.status_code, "data": error_data}
            except json.JSONDecodeError:
                logger.error(f"[AppLovin] Error Response Text: {response.text}")
                return False, {"status": "error", "status_code": response.status_code, "data": {"message": response.text}}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[AppLovin] Request Error: {str(e)}")
        return False, {"status": "error", "error": str(e)}


def get_ad_unit_details(api_key: str, ad_unit_id: str) -> Tuple[bool, Dict]:
    """
    Get ad unit details including ad_network_settings
    
    Args:
        api_key: AppLovin API Key
        ad_unit_id: Ad Unit ID
    
    Returns:
        Tuple of (success: bool, response_data: Dict)
    """
    url = f"https://o.applovin.com/mediation/v1/ad_unit/{ad_unit_id}?fields=ad_network_settings"
    headers = {
        "Accept": "application/json",
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"[AppLovin] API Request: GET {url}")
        
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"[AppLovin] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                return True, {"status": "success", "data": result}
            except json.JSONDecodeError:
                return True, {"status": "success", "data": {"message": response.text}}
        else:
            try:
                error_data = response.json()
                return False, {"status": "error", "status_code": response.status_code, "data": error_data}
            except json.JSONDecodeError:
                return False, {"status": "error", "status_code": response.status_code, "data": {"message": response.text}}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[AppLovin] Request Error: {str(e)}")
        return False, {"status": "error", "error": str(e)}

