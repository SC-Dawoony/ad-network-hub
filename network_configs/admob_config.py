"""AdMob network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field


class AdMobConfig(NetworkConfig):
    """AdMob network configuration"""
    
    @property
    def network_name(self) -> str:
        return "admob"
    
    @property
    def display_name(self) -> str:
        return "AdMob"
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation
        
        Note: For AdMob, we support creating apps for both iOS and Android simultaneously.
        Store IDs are separated by platform.
        """
        return [
            Field(
                name="appName",
                field_type="text",
                required=True,
                label="App Name*",
                placeholder="Enter app name",
                help_text="Name of the application (applies to both platforms)"
            ),
            Field(
                name="androidAppStoreId",
                field_type="text",
                required=False,
                label="Android App Store ID (Optional)",
                placeholder="com.example.app",
                help_text="Android package name. Leave empty if Android app is not needed."
            ),
            Field(
                name="iosAppStoreId",
                field_type="text",
                required=False,
                label="iOS App Store ID (Optional)",
                placeholder="123456789",
                help_text="iOS App Store ID. Leave empty if iOS app is not needed."
            ),
            Field(
                name="androidManualAppId",
                field_type="text",
                required=False,
                label="Android Manual App ID (Optional)",
                placeholder="ca-app-pub-1234567890123456~1234567890",
                help_text="Manual Android app ID (optional, auto-generated if not provided)"
            ),
            Field(
                name="iosManualAppId",
                field_type="text",
                required=False,
                label="iOS Manual App ID (Optional)",
                placeholder="ca-app-pub-1234567890123456~1234567890",
                help_text="Manual iOS app ID (optional, auto-generated if not provided)"
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit creation (Google Bidding Ad Unit)"""
        return [
            Field(
                name="format",
                field_type="dropdown",
                required=True,
                label="Ad Format*",
                options=[
                    ("Rewarded", "REWARDED"),
                    ("Interstitial", "INTERSTITIAL"),
                    ("Banner", "BANNER"),
                ],
                help_text="Select ad format"
            ),
            Field(
                name="appId",
                field_type="text",
                required=False,
                label="App ID (Optional)",
                placeholder="ca-app-pub-1234567890123456~1234567890",
                help_text="App ID (e.g., ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY). If provided, appStoreId will be ignored."
            ),
            Field(
                name="appStoreId",
                field_type="text",
                required=False,
                label="App Store ID (Optional)",
                placeholder="com.example.app",
                help_text="App Store ID (e.g., com.example.app). Used only if appId is not provided."
            ),
        ]
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        if not data.get("appName"):
            return False, "App Name is required"
        
        # At least one platform must have appStoreId
        android_app_store_id = data.get("androidAppStoreId", "").strip()
        ios_app_store_id = data.get("iosAppStoreId", "").strip()
        
        if not android_app_store_id and not ios_app_store_id:
            return False, "At least one App Store ID (Android or iOS) must be provided"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        if not data.get("format"):
            return False, "Ad Format is required"
        valid_formats = ["BANNER", "INTERSTITIAL", "REWARDED"]
        if data.get("format") not in valid_formats:
            return False, f"Ad Format must be one of: {', '.join(valid_formats)}"
        
        # At least one of appId or appStoreId must be provided
        app_id = data.get("appId", "").strip()
        app_store_id = data.get("appStoreId", "").strip()
        if not app_id and not app_store_id:
            return False, "Either App ID or App Store ID must be provided"
        
        return True, ""
    
    def build_app_payload(self, form_data: Dict, platform: Optional[str] = None) -> Dict:
        """Build API payload for app creation
        
        API: POST https://admob.googleapis.com/v1beta/{parent=accounts/*}/apps
        
        Args:
            form_data: Form data from UI
            platform: "Android" or "iOS" (optional, for dual-platform creation)
        """
        # Determine platform and appStoreId based on platform parameter
        if platform == "Android":
            platform_str = "ANDROID"
            app_store_id = form_data.get("androidAppStoreId", "").strip()
            manual_app_id = form_data.get("androidManualAppId", "").strip()
        elif platform == "iOS":
            platform_str = "IOS"
            app_store_id = form_data.get("iosAppStoreId", "").strip()
            manual_app_id = form_data.get("iosManualAppId", "").strip()
        else:
            # Legacy: use form_data directly (backward compatibility)
            platform_str = form_data.get("platform", "ANDROID")
            app_store_id = form_data.get("appStoreId", "").strip()
            manual_app_id = form_data.get("manualAppId", "").strip()
            
            # Try to get from platform-specific fields
            if not app_store_id:
                if platform_str == "ANDROID":
                    app_store_id = form_data.get("androidAppStoreId", "").strip()
                    if not manual_app_id:
                        manual_app_id = form_data.get("androidManualAppId", "").strip()
                elif platform_str == "IOS":
                    app_store_id = form_data.get("iosAppStoreId", "").strip()
                    if not manual_app_id:
                        manual_app_id = form_data.get("iosManualAppId", "").strip()
        
        payload = {
            "platform": platform_str,
        }

        # linkedAppInfo: app linked to Play Store / App Store
        if app_store_id:
            payload["linkedAppInfo"] = {
                "appStoreId": app_store_id
            }
        # manualAppInfo: app not linked to a store
        else:
            payload["manualAppInfo"] = {
                "displayName": form_data.get("appName", "")
            }

        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for Google Bidding Ad Unit creation
        
        API: POST https://admob.googleapis.com/v1alpha/accounts/{accountId}/googleBiddingAdUnits:batchCreate
        
        Args:
            form_data: Form data including displayName (auto-generated), format, appId/appStoreId
        
        Returns:
            Payload for googleBiddingAdUnit object
        """
        payload = {
            "displayName": form_data.get("displayName"),  # Auto-generated, should be provided by UI
            "format": form_data.get("format"),
        }
        
        # appId takes precedence over appStoreId
        app_id = form_data.get("appId", "").strip()
        if app_id:
            payload["appId"] = app_id
        else:
            # Use appStoreId if appId is not provided
            app_store_id = form_data.get("appStoreId", "").strip()
            if app_store_id:
                payload["appStoreId"] = app_store_id
        
        return payload

