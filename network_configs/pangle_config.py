"""Pangle (TikTok) network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField
from utils.session_manager import SessionManager


class PangleConfig(NetworkConfig):
    """Pangle (TikTok) network configuration"""
    
    @property
    def network_name(self) -> str:
        return "pangle"
    
    @property
    def display_name(self) -> str:
        return "TikTok (Pangle)"
    
    def _get_app_category_codes(self) -> List[Tuple[str, int]]:
        """Get app category code options (Industry Code and English Name)"""
        return [
            ("Games-Game Center (121315)", 121315),
            ("Games-Role Playing Game (121319)", 121319),
            ("Games-Hardcore-Strategy Game (121320)", 121320),
            ("Games-Social Game (121322)", 121322),
            ("Games-Shooting Game (121323)", 121323),
            ("Games-Racing Game (121324)", 121324),
            ("Games-Sports Game (121325)", 121325),
            ("Games-Simulation Game (121326)", 121326),
            ("Games-Action Game (121327)", 121327),
            ("Games-Strategy Tower Defense Game (121328)", 121328),
            ("Games-Merge Game (121329)", 121329),
            ("Games-Match 3 (121330)", 121330),
            ("Games-Idle Game (121331)", 121331),
            ("Games-Quiz Game (121332)", 121332),
            ("Games-Puzzle Game (121333)", 121333),
            ("Games-Music Game (121334)", 121334),
            ("Games-Arcade Runner (121335)", 121335),
            ("Games-Casual-Card Game (121336)", 121336),
            ("Games-Word (121337)", 121337),
            ("Games-Female Orientated (121338)", 121338),
            ("Games-MOBA (121339)", 121339),
            ("Games-Chinese Fantasy (121340)", 121340),
            ("Games-Adventure (121341)", 121341),
            ("Games-Sandbox (121342)", 121342),
            ("Games-Card (121343)", 121343),
            ("Games-Others (121344)", 121344),
        ]
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation - supports dual-platform creation"""
        # Note: user_id and role_id are shown separately in Create App page as read-only
        # They are not included here to avoid rendering them as input fields
        return [
            # User input fields
            Field(
                name="app_name",
                field_type="text",
                required=True,
                label="App Name*",
                placeholder="Enter app name (1-60 characters)",
                help_text="Length must be between 1 to 60 characters"
            ),
            # Android fields
            Field(
                name="androidDownloadUrl",
                field_type="text",
                required=False,
                label="Android Download URL",
                placeholder="https://play.google.com/store/apps/details?id=...",
                help_text="Google Play Store URL for Android app (optional)"
            ),
            # iOS fields
            Field(
                name="iosDownloadUrl",
                field_type="text",
                required=False,
                label="iOS Download URL",
                placeholder="https://apps.apple.com/.../id1234567890",
                help_text="Apple App Store URL for iOS app (optional)"
            ),
            Field(
                name="app_category_code",
                field_type="dropdown",
                required=True,
                label="App Category Code*",
                options=self._get_app_category_codes(),
                help_text="Second-level industry code"
            ),
            Field(
                name="mask_rule_ids",
                field_type="text",
                required=False,
                label="Mask Rule IDs",
                placeholder="Enter blocking rule IDs separated by commas (e.g., 1, 2, 3)",
                help_text="List of blocking rule IDs that can be bound to the app. Separate multiple IDs with commas."
            ),
            Field(
                name="coppa_value",
                field_type="radio",
                required=False,
                label="COPPA Value",
                options=[("Configured by client", -1), ("For users aged 13 and above", 0), ("For users aged 12 and below", 1)],
                default=0,
                help_text="Child Privacy Protection. Default: 0 (for users aged 13 and above)"
            ),
        ]
    
    def _get_ad_placement_types(self) -> List[Tuple[str, int]]:
        """Get ad placement type options"""
        return [
            ("Banner (Type 2)", 2),
            ("Rewarded Video (Type 5)", 5),
            ("Interstitial (Type 6)", 6),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit (ad placement) creation
        
        Args:
            ad_type: Ad placement type (2=Banner, 5=Rewarded Video, 6=Interstitial)
        """
        base_fields = [
            Field(
                name="site_id",
                field_type="text",
                required=True,
                label="Site ID*",
                placeholder="Enter site ID from Pangle platform",
                help_text="Site ID from Pangle platform (from Create App response)",
                default=SessionManager.get_last_created_app_info("pangle").get("siteId") if SessionManager.get_last_created_app_info("pangle") else ""
            ),
            Field(
                name="ad_placement_type",
                field_type="dropdown",
                required=True,
                label="Ad Placement Type*",
                options=self._get_ad_placement_types(),
                help_text="Select ad placement type: Banner (2), Rewarded Video (5), or Interstitial (6)"
            ),
        ]
        
        # Type-specific fields will be handled conditionally in the UI
        # For now, return base fields
        return base_fields
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        required_fields = ["app_name", "app_category_code"]
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                return False, f"Field '{field}' is required"
        
        # At least one download URL must be provided
        android_url = data.get("androidDownloadUrl", "").strip()
        ios_url = data.get("iosDownloadUrl", "").strip()
        if not android_url and not ios_url:
            return False, "At least one Download URL (Android or iOS) must be provided"
        
        # Validate app_name length (1-60 characters)
        app_name = data.get("app_name", "")
        if len(app_name) < 1 or len(app_name) > 60:
            return False, "App name must be between 1 to 60 characters"
        
        # Validate download_url format if provided
        if android_url and not (android_url.startswith("https://") or android_url.startswith("http://")):
            return False, "Android Download URL must start with http:// or https://"
        if ios_url and not (ios_url.startswith("https://") or ios_url.startswith("http://")):
            return False, "iOS Download URL must start with http:// or https://"
        
        # Validate app_category_code
        valid_codes = [code for _, code in self._get_app_category_codes()]
        if data.get("app_category_code") not in valid_codes:
            return False, "Invalid app category code"
        
        # Validate coppa_value if provided
        if "coppa_value" in data and data["coppa_value"] is not None:
            if data["coppa_value"] not in [-1, 0, 1]:
                return False, "COPPA value must be -1, 0, or 1"
        
        # Validate mask_rule_ids if provided (should be comma-separated integers)
        mask_rule_ids_str = data.get("mask_rule_ids", "")
        if mask_rule_ids_str and mask_rule_ids_str.strip():
            try:
                # Try to parse comma-separated string to list of integers
                ids = [int(id.strip()) for id in mask_rule_ids_str.split(",") if id.strip()]
                # All IDs should be positive integers
                if any(id <= 0 for id in ids):
                    return False, "Mask Rule IDs must be positive integers"
            except ValueError:
                return False, "Mask Rule IDs must be comma-separated integers (e.g., 1, 2, 3)"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        required_fields = ["app_id", "ad_placement_type"]
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                return False, f"Field '{field}' is required"
        
        ad_placement_type = data.get("ad_placement_type")
        
        # Validate type-specific fields
        if ad_placement_type == 2:  # Banner
            # Use defaults if not provided
            width = data.get("width", 640)
            height = data.get("height", 100)
            # Validate width and height values
            valid_sizes = [(600, 500), (640, 100)]  # (300*250), (320*50) in px
            if (width, height) not in valid_sizes:
                return False, f"Invalid banner size. Valid sizes: 600x500 (300*250) or 640x100 (320*50)"
        
        elif ad_placement_type == 5:  # Rewarded Video
            # reward_name and reward_count are required (no defaults)
            if not data.get("reward_name"):
                return False, "Field 'reward_name' is required for Rewarded Video ad placement"
            if data.get("reward_count") is None:
                return False, "Field 'reward_count' is required for Rewarded Video ad placement"
            # Validate reward_name length
            reward_name = data.get("reward_name", "")
            if len(reward_name) < 1 or len(reward_name) > 60:
                return False, "Reward name must be between 1 to 60 characters"
            # Validate reward_count
            reward_count = data.get("reward_count", 0)
            if reward_count < 0 or reward_count > 9007199254740991:
                return False, "Reward count must be between 0 and 9,007,199,254,740,991"
            # Validate reward_callback_url if reward_is_callback is 1
            reward_is_callback = data.get("reward_is_callback", 0)
            if reward_is_callback == 1:
                callback_url = data.get("reward_callback_url", "")
                if not callback_url or not (callback_url.startswith("http://") or callback_url.startswith("https://")):
                    return False, "Reward callback URL is required when reward delivery is verified by server"
        
        elif ad_placement_type == 6:  # Interstitial
            # All fields have defaults, no additional validation needed
            pass
        
        return True, ""
    
    def build_app_payload(self, form_data: Dict, platform: Optional[str] = None) -> Dict:
        """Build API payload for app creation
        
        Args:
            form_data: Form data from UI
            platform: "Android" or "iOS" (optional, for dual-platform creation)
        
        Note: timestamp, nonce, sign, version, status
        will be added by network_manager automatically
        user_id and role_id are included from form_data (set from .env in Create App page)
        """
        # Determine download_url based on platform parameter or form_data
        if platform == "Android":
            download_url = form_data.get("androidDownloadUrl", "").strip()
        elif platform == "iOS":
            download_url = form_data.get("iosDownloadUrl", "").strip()
        else:
            # Legacy: use form_data directly (backward compatibility)
            download_url = form_data.get("download_url", "").strip()
            if not download_url:
                # Try to get from platform-specific fields
                download_url = form_data.get("androidDownloadUrl", "").strip() or form_data.get("iosDownloadUrl", "").strip()
        
        payload = {
            "app_name": form_data.get("app_name"),
            "download_url": download_url,
            "app_category_code": form_data.get("app_category_code"),
        }
        
        # Include user_id and role_id if present (from .env, shown as read-only in form)
        if form_data.get("user_id"):
            payload["user_id"] = form_data.get("user_id")
        if form_data.get("role_id"):
            payload["role_id"] = form_data.get("role_id")
        
        # Include mask_rule_ids if provided (parse comma-separated string to list)
        mask_rule_ids_str = form_data.get("mask_rule_ids", "")
        if mask_rule_ids_str and mask_rule_ids_str.strip():
            try:
                # Parse comma-separated string to list of integers
                mask_rule_ids = [int(id.strip()) for id in mask_rule_ids_str.split(",") if id.strip()]
                if mask_rule_ids:
                    payload["mask_rule_ids"] = mask_rule_ids
            except ValueError:
                # If parsing fails, skip it (validation should catch this)
                pass
        
        # Include coppa_value if provided (default is 0)
        coppa_value = form_data.get("coppa_value", 0)
        if coppa_value is not None:
            payload["coppa_value"] = coppa_value
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit (ad placement) creation
        
        Note: timestamp, nonce, sign, version, user_id, role_id
        will be added by network_manager automatically
        """
        ad_slot_type = form_data.get("ad_placement_type")  # This is ad_slot_type in API
        
        # app_id is required and must be int
        app_id = form_data.get("app_id")
        if app_id is not None:
            try:
                app_id = int(app_id)
            except (ValueError, TypeError):
                pass  # Will be caught by validation
        
        payload = {
            "app_id": app_id,
            "bidding_type": form_data.get("bidding_type", 1),  # Default: 1
            "ad_slot_type": ad_slot_type,
        }
        
        # Type 2: Banner
        if ad_slot_type == 2:
            payload.update({
                "render_type": form_data.get("render_type", 1),  # Default: 1 (template render)
                "slide_banner": form_data.get("slide_banner", 1),  # Default: 1 (no)
                "width": form_data.get("width", 640),  # Default: 640
                "height": form_data.get("height", 100),  # Default: 100
            })
        
        # Type 5: Rewarded Video
        elif ad_slot_type == 5:
            payload.update({
                "render_type": form_data.get("render_type", 1),  # Default: 1 (template render)
                "orientation": form_data.get("orientation", 1),  # Default: 1 (vertical)
                "reward_is_callback": form_data.get("reward_is_callback", 0),  # Default: 0 (No Server Callback)
            })
            # reward_name and reward_count are required but no defaults provided
            if form_data.get("reward_name"):
                payload["reward_name"] = form_data.get("reward_name")
            if form_data.get("reward_count") is not None:
                payload["reward_count"] = form_data.get("reward_count")
            # reward_callback_url is optional, but required if reward_is_callback is 1
            if form_data.get("reward_is_callback") == 1 and form_data.get("reward_callback_url"):
                payload["reward_callback_url"] = form_data.get("reward_callback_url")
        
        # Type 6: Interstitial
        elif ad_slot_type == 6:
            payload.update({
                "render_type": form_data.get("render_type", 1),  # Default: 1 (template render)
                "orientation": form_data.get("orientation", 1),  # Default: 1 (vertical)
            })
            # accept_material_type is optional (default: 2)
            if form_data.get("accept_material_type"):
                payload["accept_material_type"] = form_data.get("accept_material_type")
        
        return payload

