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
        Each platform has its own App Name and App Store ID.
        """
        return [
            Field(
                name="androidAppName",
                field_type="text",
                required=False,
                label="Android App Name",
                placeholder="Enter Android app name",
                help_text="Name for the Android app. Leave empty if Android app is not needed."
            ),
            Field(
                name="androidAppStoreId",
                field_type="text",
                required=False,
                label="Android App Store ID",
                placeholder="com.example.app",
                help_text="Android package name. Leave empty if Android app is not needed."
            ),
            Field(
                name="iosAppName",
                field_type="text",
                required=False,
                label="iOS App Name",
                placeholder="Enter iOS app name",
                help_text="Name for the iOS app. Leave empty if iOS app is not needed."
            ),
            Field(
                name="iosAppStoreId",
                field_type="text",
                required=False,
                label="iOS App Store ID",
                placeholder="123456789",
                help_text="iOS App Store ID (numeric). Leave empty if iOS app is not needed."
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
        android_app_name = data.get("androidAppName", "").strip()
        android_app_store_id = data.get("androidAppStoreId", "").strip()
        ios_app_name = data.get("iosAppName", "").strip()
        ios_app_store_id = data.get("iosAppStoreId", "").strip()

        # At least one platform must be provided
        has_android = android_app_name or android_app_store_id
        has_ios = ios_app_name or ios_app_store_id

        if not has_android and not has_ios:
            return False, "At least one platform (Android or iOS) must be provided"

        # If Android fields are partially filled, require App Name
        if android_app_store_id and not android_app_name:
            return False, "Android App Name is required when Android App Store ID is provided"

        # If iOS fields are partially filled, require App Name
        if ios_app_store_id and not ios_app_name:
            return False, "iOS App Name is required when iOS App Store ID is provided"

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
            platform: "Android" or "iOS" (for dual-platform creation)
        """
        if platform == "Android":
            platform_str = "ANDROID"
            app_store_id = form_data.get("androidAppStoreId", "").strip()
            app_name = form_data.get("androidAppName", "").strip()
        elif platform == "iOS":
            platform_str = "IOS"
            app_store_id = form_data.get("iosAppStoreId", "").strip()
            app_name = form_data.get("iosAppName", "").strip()
        else:
            platform_str = form_data.get("platform", "ANDROID")
            app_store_id = form_data.get("appStoreId", "").strip()
            app_name = form_data.get("appName", "").strip()

        payload = {
            "platform": platform_str,
        }

        # linkedAppInfo: app linked to Play Store / App Store
        if app_store_id:
            payload["linkedAppInfo"] = {
                "appStoreId": app_store_id
            }
            # Also include displayName so the app has a name before store verification
            if app_name:
                payload["manualAppInfo"] = {
                    "displayName": app_name
                }
        # manualAppInfo: app not linked to a store
        else:
            payload["manualAppInfo"] = {
                "displayName": app_name
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

