"""Fyber (DT) network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField


class FyberConfig(NetworkConfig):
    """Fyber (DT) network configuration"""
    
    @property
    def network_name(self) -> str:
        return "fyber"
    
    @property
    def display_name(self) -> str:
        return "Fyber (DT)"
    
    def _get_categories(self) -> List[Tuple[str, str]]:
        """Get category options for Fyber
        
        Common app store categories
        """
        return [
            ("Books", "Books"),
            ("Business", "Business"),
            ("Education", "Education"),
            ("Entertainment", "Entertainment"),
            ("Finance", "Finance"),
            ("Food & Drink", "Food & Drink"),
            ("Games", "Games"),
            ("Health & Fitness", "Health & Fitness"),
            ("Lifestyle", "Lifestyle"),
            ("Medical", "Medical"),
            ("Music", "Music"),
            ("News", "News"),
            ("Photo & Video", "Photo & Video"),
            ("Productivity", "Productivity"),
            ("Reference", "Reference"),
            ("Shopping", "Shopping"),
            ("Social Networking", "Social Networking"),
            ("Sports", "Sports"),
            ("Travel", "Travel"),
            ("Utilities", "Utilities"),
            ("Weather", "Weather"),
        ]
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation
        
        Order: name, bundle, platform, category1, coppa, rewardedAdUrl (optional), category2 (optional)
        """
        return [
            Field(
                name="name",
                field_type="text",
                required=True,
                label="App Name*",
                placeholder="Enter app name",
                help_text="The name of the app"
            ),
            Field(
                name="bundle",
                field_type="text",
                required=True,
                label="Bundle/Store ID*",
                placeholder="com.example.app (Android) or id1234567890 (iOS)",
                help_text="App's Android bundle or iOS Store ID"
            ),
            Field(
                name="platform",
                field_type="radio",
                required=True,
                label="Platform*",
                options=[("Android", "android"), ("iOS", "ios")],
                default="android",
                help_text="App's platform"
            ),
            Field(
                name="category1",
                field_type="dropdown",
                required=True,
                label="Category 1*",
                options=self._get_categories(),
                default="Games",
                help_text="App's first store category"
            ),
            Field(
                name="coppa",
                field_type="radio",
                required=True,
                label="COPPA*",
                options=[("No", "false"), ("Yes", "true")],
                default="false",
                help_text="Is the app directed to children under 13 years of age?"
            ),
            Field(
                name="rewardedAdUrl",
                field_type="text",
                required=False,
                label="Rewarded Ad URL",
                placeholder="https://example.com/callbacks.aspx?user_id={{USER_ID}}&reward_amount={{AMOUNT}}&signature={{SIG}}",
                help_text="URL to be used for server side call back on app's rewarded placements"
            ),
            Field(
                name="category2",
                field_type="dropdown",
                required=False,
                label="Category 2",
                options=self._get_categories(),
                help_text="App's second store category (optional)"
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit creation
        
        To be implemented when API documentation is provided.
        """
        return [
            Field(
                name="appId",
                field_type="text",
                required=True,
                label="App ID*",
                placeholder="Enter app ID from Fyber platform",
                help_text="Application ID from Fyber platform"
            ),
        ]
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        # Required fields
        if not data.get("name"):
            return False, "App Name is required"
        
        if not data.get("bundle"):
            return False, "Bundle/Store ID is required"
        
        if not data.get("platform"):
            return False, "Platform is required"
        
        valid_platforms = ["android", "ios"]
        if data.get("platform") not in valid_platforms:
            return False, f"Platform must be one of: {', '.join(valid_platforms)}"
        
        if not data.get("category1"):
            return False, "Category 1 is required"
        
        if "coppa" not in data:
            return False, "COPPA is required"
        
        valid_coppa = ["true", "false"]
        if data.get("coppa") not in valid_coppa:
            return False, f"COPPA must be one of: {', '.join(valid_coppa)}"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        # To be implemented when API documentation is provided
        if not data.get("appId"):
            return False, "App ID is required"
        return True, ""
    
    def build_app_payload(self, form_data: Dict) -> Dict:
        """Build API payload for app creation"""
        payload = {
            "name": form_data.get("name", "").strip(),
            "bundle": form_data.get("bundle", "").strip(),
            "platform": form_data.get("platform", "android"),
            "category1": form_data.get("category1", "").strip(),
            "coppa": form_data.get("coppa", "false"),
        }
        
        # Optional fields
        if form_data.get("rewardedAdUrl"):
            payload["rewardedAdUrl"] = form_data.get("rewardedAdUrl", "").strip()
        
        if form_data.get("category2"):
            payload["category2"] = form_data.get("category2", "").strip()
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit creation"""
        # To be implemented when API documentation is provided
        return {
            "appId": form_data.get("appId", "").strip(),
        }

