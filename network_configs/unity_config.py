"""Unity network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField


class UnityConfig(NetworkConfig):
    """Unity network configuration"""
    
    @property
    def network_name(self) -> str:
        return "unity"
    
    @property
    def display_name(self) -> str:
        return "Unity"
    
    def _get_ads_provider_options(self) -> List[Tuple[str, str]]:
        """Get Ads Provider options (same format as BigOAds Mediation Platform)"""
        return [
            ("MAX", "max"),
            ("Iron Source", "iron_source"),
            ("MoPub", "mopub"),
            ("AdMob", "admob"),
            ("Unity", "unity"),
            ("Self Mediated", "self_mediated"),
            ("Other", "other"),
            ("Unity Mediation", "unity_mediation"),
        ]
    
    def _get_coppa_options(self) -> List[Tuple[str, str]]:
        """Get COPPA compliance options"""
        return [
            ("Non Compliant", "non_compliant"),
            ("Compliant", "compliant"),
        ]
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for Unity project creation"""
        return [
            Field(
                name="name",
                field_type="text",
                required=True,
                label="Project Name*",
                placeholder="Enter project name",
                help_text="Name of the Unity project"
            ),
            Field(
                name="adsProvider",
                field_type="multiselect",
                required=True,
                label="Ads Provider*",
                options=self._get_ads_provider_options(),
                default=["max"],  # Default: MAX (same as BigOAds Mediation Platform)
                help_text="Ads provider for the project (select one or more)"
            ),
            Field(
                name="coppa",
                field_type="radio",
                required=True,
                label="COPPA Compliance*",
                options=self._get_coppa_options(),
                default="non_compliant",
                help_text="COPPA compliance status"
            ),
            # Apple Store (optional)
            Field(
                name="apple_storeId",
                field_type="text",
                required=False,
                label="Apple Store ID",
                placeholder="e.g., 1234567890",
                help_text="Apple App Store ID (optional)"
            ),
            Field(
                name="apple_storeUrl",
                field_type="text",
                required=False,
                label="Apple Store URL",
                placeholder="https://apps.apple.com/...",
                help_text="Apple App Store URL (optional)"
            ),
            # Google Play Store (optional)
            Field(
                name="google_storeId",
                field_type="text",
                required=False,
                label="Google Play Store ID",
                placeholder="com.example.app",
                help_text="Google Play Store package name (optional)"
            ),
            Field(
                name="google_storeUrl",
                field_type="text",
                required=False,
                label="Google Play Store URL",
                placeholder="https://play.google.com/...",
                help_text="Google Play Store URL (optional)"
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Unity does not support unit creation via API"""
        return []
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate Unity project creation data"""
        if not data.get("name"):
            return False, "Project name is required"
        if not data.get("adsProvider"):
            return False, "Ads Provider is required"
        if not data.get("coppa"):
            return False, "COPPA compliance is required"
        
        # Handle adsProvider as list (from multiselect) or string
        ads_provider = data.get("adsProvider")
        if isinstance(ads_provider, list):
            if len(ads_provider) == 0:
                return False, "At least one Ads Provider must be selected"
            # Use first selected value for validation
            ads_provider = ads_provider[0]
        
        # Validate adsProvider enum
        valid_ads_providers = ["iron_source", "mopub", "admob", "max", "unity", "self_mediated", "other", "unity_mediation"]
        if ads_provider not in valid_ads_providers:
            return False, f"Ads Provider must be one of: {', '.join(valid_ads_providers)}"
        
        # Validate coppa enum
        valid_coppa = ["non_compliant", "compliant"]
        if data.get("coppa") not in valid_coppa:
            return False, f"COPPA must be one of: {', '.join(valid_coppa)}"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Unity does not support unit creation via API"""
        return True, ""
    
    def build_app_payload(self, form_data: Dict) -> Dict:
        """Build API payload for Unity project creation"""
        # Handle adsProvider as list (from multiselect) or string
        # Unity API expects a single string value, so use first selected value
        ads_provider = form_data.get("adsProvider")
        if isinstance(ads_provider, list):
            ads_provider = ads_provider[0] if ads_provider else "max"
        elif not ads_provider:
            ads_provider = "max"
        
        payload = {
            "name": form_data.get("name"),
            "adsProvider": ads_provider,  # Single string value for Unity API
            "coppa": form_data.get("coppa"),
        }
        
        # Build stores object if any store fields are provided
        stores = {}
        apple = {}
        google = {}
        
        # Apple store fields
        apple_store_id = form_data.get("apple_storeId", "").strip()
        apple_store_url = form_data.get("apple_storeUrl", "").strip()
        if apple_store_id or apple_store_url:
            if apple_store_id:
                apple["storeId"] = apple_store_id
            if apple_store_url:
                apple["storeUrl"] = apple_store_url
            if apple:
                stores["apple"] = apple
        
        # Google store fields
        google_store_id = form_data.get("google_storeId", "").strip()
        google_store_url = form_data.get("google_storeUrl", "").strip()
        if google_store_id or google_store_url:
            if google_store_id:
                google["storeId"] = google_store_id
            if google_store_url:
                google["storeUrl"] = google_store_url
            if google:
                stores["google"] = google
        
        # Add stores to payload only if it has content
        if stores:
            payload["stores"] = stores
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Unity does not support unit creation via API"""
        return {}

