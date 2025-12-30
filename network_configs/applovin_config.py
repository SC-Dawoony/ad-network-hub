"""AppLovin network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField


class AppLovinConfig(NetworkConfig):
    """AppLovin network configuration"""
    
    @property
    def network_name(self) -> str:
        return "applovin"
    
    @property
    def display_name(self) -> str:
        return "AppLovin"
    
    def get_app_creation_fields(self) -> List[Field]:
        """AppLovin does not support app creation via API"""
        return []
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit creation"""
        return [
            Field(
                name="name",
                field_type="text",
                required=True,
                label="Ad Unit Name*",
                placeholder="Enter ad unit name",
                help_text="Name of the ad unit"
            ),
            Field(
                name="package_name",
                field_type="text",
                required=True,
                label="Package Name*",
                placeholder="com.example.app",
                help_text="Package name (Android) or Bundle ID (iOS)"
            ),
            Field(
                name="platform",
                field_type="radio",
                required=True,
                label="Platform*",
                options=[("Android", "android"), ("iOS", "ios")],
                default="android",
                help_text="Select platform"
            ),
            Field(
                name="ad_format",
                field_type="dropdown",
                required=True,
                label="Ad Format*",
                options=[
                    ("Interstitial", "INTER"),
                    ("Banner", "BANNER"),
                    ("Rewarded Video", "REWARD")
                ],
                default="INTER",
                help_text="Ad format type"
            )
        ]
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """AppLovin does not support app creation"""
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        if not data.get("name"):
            return False, "Ad unit name is required"
        if not data.get("package_name"):
            return False, "Package name is required"
        if not data.get("platform"):
            return False, "Platform is required"
        if not data.get("ad_format"):
            return False, "Ad format is required"
        
        # Validate ad_format value
        valid_formats = ["INTER", "BANNER", "REWARD"]
        if data.get("ad_format") not in valid_formats:
            return False, f"Ad format must be one of: {', '.join(valid_formats)}"
        
        # Validate platform value
        valid_platforms = ["android", "ios"]
        if data.get("platform") not in valid_platforms:
            return False, f"Platform must be one of: {', '.join(valid_platforms)}"
        
        return True, ""
    
    def build_app_payload(self, form_data: Dict) -> Dict:
        """AppLovin does not support app creation"""
        return {}
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit creation"""
        return {
            "name": form_data.get("name"),
            "platform": form_data.get("platform"),
            "package_name": form_data.get("package_name"),
            "ad_format": form_data.get("ad_format")
        }

