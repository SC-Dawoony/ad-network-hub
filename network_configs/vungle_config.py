"""Vungle (Liftoff) network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field


class VungleConfig(NetworkConfig):
    """Vungle (Liftoff) network configuration"""
    
    @property
    def network_name(self) -> str:
        return "vungle"
    
    @property
    def display_name(self) -> str:
        return "Vungle (Liftoff)"
    
    def _get_store_categories(self) -> List[Tuple[str, str]]:
        """Get store category options"""
        return [
            ("Action", "Action"),
            ("Adventure", "Adventure"),
            ("Arcade", "Arcade"),
            ("Board", "Board"),
            ("Card", "Card"),
            ("Casino", "Casino"),
            ("Casual", "Casual"),
            ("Educational", "Educational"),
            ("Family", "Family"),
            ("Music", "Music"),
            ("Puzzle", "Puzzle"),
            ("Racing", "Racing"),
            ("Role Playing", "Role Playing"),
            ("Simulation", "Simulation"),
            ("Sports", "Sports"),
            ("Strategy", "Strategy"),
            ("Trivia", "Trivia"),
            ("Word", "Word"),
            ("Battle Royale", "Battle Royale"),
            ("Other", "Other"),
        ]
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation - supports dual-platform creation"""
        return [
            Field(
                name="app_name",
                field_type="text",
                required=True,
                label="App Name*",
                placeholder="Enter app name",
                help_text="Name of the application"
            ),
            # Android fields
            Field(
                name="androidStoreId",
                field_type="text",
                required=False,
                label="Android Store ID",
                placeholder="com.example.app",
                help_text="Android package name (Google Play Store ID)"
            ),
            Field(
                name="androidStoreUrl",
                field_type="text",
                required=False,
                label="Android Store URL",
                placeholder="https://play.google.com/store/apps/details?id=...",
                help_text="Google Play Store URL (optional)"
            ),
            # iOS fields
            Field(
                name="iosStoreId",
                field_type="text",
                required=False,
                label="iOS Store ID",
                placeholder="1234567890",
                help_text="iOS App Store ID"
            ),
            Field(
                name="iosStoreUrl",
                field_type="text",
                required=False,
                label="iOS Store URL",
                placeholder="https://apps.apple.com/.../id1234567890",
                help_text="Apple App Store URL (optional)"
            ),
            Field(
                name="category",
                field_type="dropdown",
                required=False,
                label="Category",
                options=self._get_store_categories(),
                help_text="App category (applies to both Android and iOS)"
            ),
            Field(
                name="isCoppa",
                field_type="radio",
                required=False,
                label="COPPA",
                options=[("Yes", True), ("No", False)],
                default=False,
                help_text="Is the app directed to children under 13 years of age?"
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit (placement) creation"""
        return [
            Field(
                name="application",
                field_type="text",
                required=True,
                label="Application ID*",
                placeholder="Enter Vungle App ID (vungleAppId)",
                help_text="Vungle App ID from created app"
            ),
            Field(
                name="name",
                field_type="text",
                required=True,
                label="Placement Name*",
                placeholder="Enter placement name",
                help_text="Name of the placement"
            ),
            Field(
                name="type",
                field_type="dropdown",
                required=True,
                label="Placement Type*",
                options=[("Rewarded", "rewarded"), ("Interstitial", "interstitial"), ("Banner", "banner")],
                help_text="Type of placement: rewarded, interstitial, or banner"
            ),
        ]
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        required_fields = ["app_name"]
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                return False, f"Field '{field}' is required"
        
        # At least one platform must be provided
        android_store_id = data.get("androidStoreId", "").strip()
        ios_store_id = data.get("iosStoreId", "").strip()
        if not android_store_id and not ios_store_id:
            return False, "At least one Store ID (Android or iOS) must be provided"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        required_fields = ["application", "name", "type"]
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                return False, f"Field '{field}' is required"
        
        # Validate type
        valid_types = ["rewarded", "interstitial", "banner"]
        if data.get("type") not in valid_types:
            return False, f"Type must be one of: {', '.join(valid_types)}"
        
        return True, ""
    
    def build_app_payload(self, form_data: Dict, platform: Optional[str] = None) -> Dict:
        """Build API payload for app creation
        
        Args:
            form_data: Form data from UI
            platform: "Android" or "iOS" (optional, for dual-platform creation)
        """
        # Get category (shared for both platforms)
        category = form_data.get("category", "").strip()
        
        # Determine platform and store info based on platform parameter or form_data
        if platform == "Android":
            store_id = form_data.get("androidStoreId", "").strip()
            store_url = form_data.get("androidStoreUrl", "").strip()
            platform_str = "android"
        elif platform == "iOS":
            store_id = form_data.get("iosStoreId", "").strip()
            store_url = form_data.get("iosStoreUrl", "").strip()
            platform_str = "ios"
        else:
            # Legacy: use form_data directly (backward compatibility)
            # Try Android first, then iOS
            store_id = form_data.get("androidStoreId", "").strip()
            store_url = form_data.get("androidStoreUrl", "").strip()
            platform_str = "android"
            
            if not store_id:
                store_id = form_data.get("iosStoreId", "").strip()
                store_url = form_data.get("iosStoreUrl", "").strip()
                platform_str = "ios"
        
        # Build store object
        store_obj = {
            "id": store_id,
            "isPaid": False,  # Default to free app
            "isManual": True,  # Default to manual
            "url": store_url if store_url else "",
            "thumbnail": ""  # Optional, can be empty
        }

        # Only add category for Android platform (iOS should not have category)
        if platform_str == "android" and category:
            store_obj["category"] = category

        payload = {
            "platform": platform_str,
            "name": form_data.get("app_name", "").strip(),
            "store": store_obj,
            "isCoppa": form_data.get("isCoppa", False)
        }
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit (placement) creation"""
        payload = {
            "application": form_data.get("application", "").strip(),
            "name": form_data.get("name", "").strip(),
            "type": form_data.get("type", "").strip().lower(),
            "allowEndCards": True,  # Always true
            "isHBParticipation": True,  # Always true
        }
        
        return payload
    
    def supports_create_app(self) -> bool:
        """Vungle supports app creation via API"""
        return True
    
    def supports_create_unit(self) -> bool:
        """Vungle supports unit creation via API"""
        return True
