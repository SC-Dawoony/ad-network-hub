"""IronSource network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField


class IronSourceConfig(NetworkConfig):
    """IronSource network configuration"""
    
    @property
    def network_name(self) -> str:
        return "ironsource"
    
    @property
    def display_name(self) -> str:
        return "IronSource"
    
    def _get_taxonomies(self) -> List[Tuple[str, str]]:
        """Get taxonomy (sub-genre) options"""
        # Convert display name to API value (lowercase, replace spaces/special chars with underscores)
        def to_api_value(display: str) -> str:
            # Convert to lowercase and replace spaces/special chars
            value = display.lower()
            value = value.replace(" ", "_")
            value = value.replace("/", "_")
            value = value.replace("'", "")
            value = value.replace(".", "")
            value = value.replace("-", "_")
            return value
        
        taxonomy_list = [
            "Bingo", "Blackjack", "Non-Poker Cards", "Poker", "Slots", "Sports Betting", "Other Casino",
            "AR/Location Based", "Endless Runner", "Idler", "Other Arcade", "Platformer", "Shoot 'em Up", "Tower Defense", ".io",
            "Ball", "Dexterity", "Idle", "Merge", "Other", "Puzzle", "Rising/Falling", "Stacking", "Swerve", "Tap / Timing", "Turning",
            "Kids & Family", "Customization", "Interactive Story", "Music/Band", "Other Lifestyle",
            "Lucky Casino", "Lucky Game Discovery", "Lucky Puzzle", "Other Casual",
            "Action Puzzle", "Board", "Bubble Shooter", "Coloring Games", "Crossword", "Hidden Objects", "Jigsaw", "Match 3", "Non Casino Card Game", "Other Puzzle", "Solitaire", "Trivia", "Word",
            "Adventures", "Breeding", "Cooking/Time Management", "Farming", "Idle Simulation", "Other Simulation", "Sandbox", "Tycoon/Crafting",
            "Card Battler", "Other Mid-Core",
            "Action RPG", "Fighting", "Idle RPG", "MMORPG", "Other RPG", "Puzzle RPG", "Survival", "Turn-based RPG",
            "Battle Royale", "Classic FPS", "Other Shooter", "Snipers", "Tactical Shooter",
            "4X Strategy", "Build & Battle", "Idle Strategy", "MOBA", "Other Strategy", "Sync. Battler",
            "Books & Reference", "Comics", "Communications", "Dating", "Education", "Entertainment", "Events & Tickets", "Finance", "Food & Drink", "Health & Fitness", "Lifestyle", "Maps & Navigation", "Medical", "Music & Audio", "News & Magazines", "Other Non-Gaming", "Parenting", "Personalization", "Photography", "Real Estate & Home", "Marketplace", "Shopping", "Social", "Sports",
            "Bike", "Car Sharing", "Taxi/Ride Sharing", "Travel & Local", "Travel Air & Hotel", "Other Sports & Racing",
            "Casual Racing", "Other Racing", "Simulation Racing", "Casual Sports", "Licensed Sports"
        ]
        
        return [(display, to_api_value(display)) for display in taxonomy_list]
    
    def _get_ad_formats(self) -> List[Tuple[str, str]]:
        """Get ad format options for placements"""
        return [
            ("Rewarded Video", "rewarded"),
            ("Interstitial", "interstitial"),
            ("Banner", "banner"),
            ("Native Ad", "native"),
        ]
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation
        
        Note: For IronSource, we support creating apps for both iOS and Android simultaneously.
        Store URLs are separated by platform.
        """
        return [
            Field(
                name="appName",
                field_type="text",
                required=True,
                label="App Name",
                placeholder="Enter application name"
            ),
            Field(
                name="iosStoreUrl",
                field_type="text",
                required=False,
                label="iOS Store URL (Optional)",
                placeholder="https://apps.apple.com/us/app/...",
                help_text="iOS App Store URL. Leave empty if iOS app is not needed."
            ),
            Field(
                name="androidStoreUrl",
                field_type="text",
                required=False,
                label="Android Store URL (Optional)",
                placeholder="https://play.google.com/store/apps/details?id=...",
                help_text="Google Play Store URL. Leave empty if Android app is not needed."
            ),
            Field(
                name="taxonomy",
                field_type="dropdown",
                required=True,
                label="Taxonomy (Sub-genre)",
                options=self._get_taxonomies(),
                help_text="Application sub-genre (applies to both platforms)"
            ),
            Field(
                name="coppa",
                field_type="radio",
                required=True,
                label="COPPA",
                options=[("No", 0), ("Yes", 1)],
                default=0,
                help_text="Applies to both platforms"
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit (placement) creation"""
        # Note: IronSource Create Placements API accepts an array of ad units
        # This form allows creating multiple ad units at once
        base_fields = [
            Field(
                name="appKey",
                field_type="text",
                required=True,
                label="App Key",
                placeholder="Enter app key from IronSource platform",
                help_text="Application key from IronSource platform"
            ),
        ]
        
        # Ad unit fields (can create multiple)
        ad_unit_fields = [
            Field(
                name="mediationAdUnitName",
                field_type="text",
                required=True,
                label="Ad Unit Name",
                placeholder="e.g., interstitial-1, banner-1, rewarded-1"
            ),
            Field(
                name="adFormat",
                field_type="dropdown",
                required=True,
                label="Ad Format",
                options=self._get_ad_formats()
            ),
        ]
        
        # Conditional fields for rewarded format
        conditional_fields = [
            ConditionalField(
                name="rewardItemName",
                field_type="text",
                required=True,
                label="Reward Item Name",
                condition=lambda data: data.get("adFormat") == "rewarded",
                placeholder="e.g., Virtual Item",
                help_text="Required for rewarded ad format"
            ),
            ConditionalField(
                name="rewardAmount",
                field_type="number",
                required=True,
                label="Reward Amount",
                condition=lambda data: data.get("adFormat") == "rewarded",
                min_value=1,
                default=1,
                help_text="Required for rewarded ad format"
            ),
        ]
        
        # Settings fields (optional)
        settings_fields = [
            Field(
                name="testGroup",
                field_type="text",
                required=False,
                label="Test Group",
                placeholder="null or test group name"
            ),
            Field(
                name="cappingEnabled",
                field_type="radio",
                required=False,
                label="Capping Enabled",
                options=[("No", False), ("Yes", True)],
                help_text="Relevant for rewarded and interstitial"
            ),
            Field(
                name="cappingLimit",
                field_type="number",
                required=False,
                label="Capping Limit",
                min_value=1,
                help_text="Maximum cap value"
            ),
            Field(
                name="cappingInterval",
                field_type="radio",
                required=False,
                label="Capping Interval",
                options=[("Day", "d"), ("Hour", "h")],
                help_text="Time interval for capping"
            ),
            Field(
                name="pacingEnabled",
                field_type="radio",
                required=False,
                label="Pacing Enabled",
                options=[("No", False), ("Yes", True)],
                help_text="Relevant for rewarded and interstitial"
            ),
            Field(
                name="pacingMinutes",
                field_type="number",
                required=False,
                label="Pacing Minutes",
                min_value=0.1,
                max_value=1000,
                help_text="Pacing interval in minutes (float, max 1000)"
            ),
            Field(
                name="bannerRefreshRate",
                field_type="number",
                required=False,
                label="Banner Refresh Rate (seconds)",
                options=[(str(x), x) for x in [0, 10, 15, 20, 25, 30, 45, 60, 120, 240]],
                default=25,
                help_text="Relevant only for banner. Default: 25"
            ),
        ]
        
        return base_fields + ad_unit_fields + conditional_fields + settings_fields
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        # At least one Store URL must be provided
        ios_store_url = data.get("iosStoreUrl", "").strip()
        android_store_url = data.get("androidStoreUrl", "").strip()
        
        if not ios_store_url and not android_store_url:
            return False, "At least one Store URL (iOS or Android) must be provided"
        
        # Validate iOS Store URL format if provided
        if ios_store_url:
            if not (ios_store_url.startswith("https://") or ios_store_url.startswith("http://")):
                return False, "iOS Store URL must start with http:// or https://"
            if "apps.apple.com" not in ios_store_url:
                return False, "iOS Store URL must be from apps.apple.com"
        
        # Validate Android Store URL format if provided
        if android_store_url:
            if not (android_store_url.startswith("https://") or android_store_url.startswith("http://")):
                return False, "Android Store URL must start with http:// or https://"
            if "play.google.com" not in android_store_url:
                return False, "Android Store URL must be from play.google.com"
        
        # Validate taxonomy
        if not data.get("taxonomy"):
            return False, "Taxonomy (Sub-genre) is required"
        
        # Validate coppa value
        coppa = data.get("coppa")
        if coppa not in [0, 1]:
            return False, "COPPA must be 0 (false) or 1 (true)"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        required_fields = ["appKey", "mediationAdUnitName", "adFormat"]
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                return False, f"Field '{field}' is required"
        
        # Validate adFormat
        ad_format = data.get("adFormat")
        valid_formats = ["rewarded", "interstitial", "banner", "native"]
        if ad_format not in valid_formats:
            return False, f"Ad format must be one of: {', '.join(valid_formats)}"
        
        # Validate rewarded format requirements
        if ad_format == "rewarded":
            if not data.get("rewardItemName") or not data.get("rewardAmount"):
                return False, "Reward item name and amount are required for rewarded ad format"
            if data.get("rewardAmount", 0) < 1:
                return False, "Reward amount must be at least 1"
        
        # Validate banner refresh rate
        if ad_format == "banner" and data.get("bannerRefreshRate"):
            valid_rates = [0, 10, 15, 20, 25, 30, 45, 60, 120, 240]
            if data["bannerRefreshRate"] not in valid_rates:
                return False, f"Banner refresh rate must be one of: {', '.join(map(str, valid_rates))}"
        
        # Validate pacing minutes
        if data.get("pacingMinutes"):
            if data["pacingMinutes"] < 0.1 or data["pacingMinutes"] > 1000:
                return False, "Pacing minutes must be between 0.1 and 1000"
        
        return True, ""
    
    def build_app_payload(self, form_data: Dict, platform: str = "android") -> Dict:
        """Build API payload for app creation
        
        Args:
            form_data: Form data containing app information
            platform: "iOS" or "Android" to build payload for specific platform
        
        Returns:
            Payload dict for the specified platform
        """
        if platform.lower() == "ios":
            store_url = form_data.get("iosStoreUrl", "").strip()
        else:
            store_url = form_data.get("androidStoreUrl", "").strip()
        
        payload = {
            "appName": form_data.get("appName"),
            "platform": platform,  # "iOS" or "Android"
            "storeUrl": store_url,
            "taxonomy": form_data.get("taxonomy"),
            "coppa": form_data.get("coppa", 0),
        }
        
        if form_data.get("ccpa") is not None:
            payload["ccpa"] = form_data.get("ccpa", 0)
        
        # Optional: adUnits configuration
        # If not specified, all ad units are created with 'Off' status by default
        # User can optionally configure this in the future
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit creation
        
        Note: IronSource Create Placements API accepts an array of ad units.
        This method builds a single ad unit object. Multiple calls or array handling
        should be done at the API call level.
        """
        ad_unit = {
            "mediationAdUnitName": form_data.get("mediationAdUnitName"),
            "adFormat": form_data.get("adFormat"),
        }
        
        # Add reward for rewarded format
        if form_data.get("adFormat") == "rewarded":
            ad_unit["reward"] = {
                "rewardItemName": form_data.get("rewardItemName"),
                "rewardAmount": form_data.get("rewardAmount", 1)
            }
        
        # Build settings array
        settings = {}
        
        if form_data.get("testGroup") is not None:
            test_group = form_data.get("testGroup")
            settings["testGroup"] = None if test_group == "" or test_group.lower() == "null" else test_group
        
        # Capping settings (for rewarded and interstitial)
        if form_data.get("adFormat") in ["rewarded", "interstitial"]:
            if form_data.get("cappingEnabled") is not None:
                settings["cappingEnabled"] = form_data.get("cappingEnabled")
            if form_data.get("cappingLimit"):
                settings["cappingLimit"] = form_data.get("cappingLimit")
            if form_data.get("cappingInterval"):
                settings["cappingInterval"] = form_data.get("cappingInterval")
        
        # Pacing settings (for rewarded and interstitial)
        if form_data.get("adFormat") in ["rewarded", "interstitial"]:
            if form_data.get("pacingEnabled") is not None:
                settings["pacingEnabled"] = form_data.get("pacingEnabled")
            if form_data.get("pacingMinutes"):
                settings["pacingMinutes"] = form_data.get("pacingMinutes")
        
        # Banner refresh rate
        if form_data.get("adFormat") == "banner" and form_data.get("bannerRefreshRate") is not None:
            settings["bannerRefreshRate"] = form_data.get("bannerRefreshRate")
        
        # Add settings if any were set
        if settings:
            ad_unit["settings"] = [settings]
        
        return ad_unit

