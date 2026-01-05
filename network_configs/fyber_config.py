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
    
    def _get_categories(self, platform: str = "android") -> List[Tuple[str, str]]:
        """Get category options for Fyber
        
        Categories are platform-specific. Based on API error messages:
        - Android has specific categories like "Games - Arcade & Action", "Games - Casual", etc.
        - iOS may have different categories
        
        Args:
            platform: Platform name ("android" or "ios")
        """
        # Valid categories from API error message for Android
        android_categories = [
            ("Books & Reference", "Books & Reference"),
            ("Business", "Business"),
            ("Comics", "Comics"),
            ("Communication", "Communication"),
            ("Education", "Education"),
            ("Entertainment", "Entertainment"),
            ("Finance", "Finance"),
            ("Games - Arcade & Action", "Games - Arcade & Action"),
            ("Games - Brain & Puzzle", "Games - Brain & Puzzle"),
            ("Games - Cards & Casino", "Games - Cards & Casino"),
            ("Games - Casual", "Games - Casual"),
            ("Games - Live Wallpaper", "Games - Live Wallpaper"),
            ("Games - Racing", "Games - Racing"),
            ("Games - Sports Games", "Games - Sports Games"),
            ("Games - Widgets", "Games - Widgets"),
            ("Health & Fitness", "Health & Fitness"),
            ("Libraries & Demo", "Libraries & Demo"),
            ("Lifestyle", "Lifestyle"),
            ("Live Wallpaper", "Live Wallpaper"),
            ("Media & Video", "Media & Video"),
            ("Medical", "Medical"),
            ("Music & Audio", "Music & Audio"),
            ("News & Magazines", "News & Magazines"),
            ("Personalization", "Personalization"),
            ("Photography", "Photography"),
            ("Productivity", "Productivity"),
            ("Shopping", "Shopping"),
            ("Social", "Social"),
            ("Sports", "Sports"),
            ("Tools", "Tools"),
            ("Transportation", "Transportation"),
            ("Travel & Local", "Travel & Local"),
            ("Weather", "Weather"),
            ("Widgets", "Widgets"),
            ("Casual", "Casual"),
            ("Android Wear", "Android Wear"),
            ("Art & Design", "Art & Design"),
            ("Auto & Vehicles", "Auto & Vehicles"),
            ("Beauty", "Beauty"),
            ("Dating", "Dating"),
            ("Events", "Events"),
            ("Action", "Action"),
            ("Adventure", "Adventure"),
            ("Arcade", "Arcade"),
            ("Board", "Board"),
            ("Games - Cards", "Games - Cards"),
            ("Casino", "Casino"),
            ("Educational", "Educational"),
            ("Family", "Family"),
            ("Music Games", "Music Games"),
            ("Puzzle", "Puzzle"),
            ("Role Playing", "Role Playing"),
            ("Simulation", "Simulation"),
            ("Strategy", "Strategy"),
            ("Trivia", "Trivia"),
            ("Word Games", "Word Games"),
            ("House & Home", "House & Home"),
            ("Maps & Navigation", "Maps & Navigation"),
            ("Overall", "Overall"),
            ("Parenting", "Parenting"),
            ("Video Players & Editors", "Video Players & Editors"),
            ("Word", "Word"),
            ("Card", "Card"),
        ]
        
        # Valid categories for iOS (from API error message)
        ios_categories = [
            ("Books", "Books"),
            ("Business", "Business"),
            ("Catalogs", "Catalogs"),
            ("Education", "Education"),
            ("Entertainment", "Entertainment"),
            ("Finance", "Finance"),
            ("Food & Drink", "Food & Drink"),
            ("Games - Action", "Games - Action"),
            ("Games - Adventure", "Games - Adventure"),
            ("Games - Arcade", "Games - Arcade"),
            ("Games - Board", "Games - Board"),
            ("Games - Card", "Games - Card"),
            ("Games - Casino", "Games - Casino"),
            ("Games - Dice", "Games - Dice"),
            ("Games - Educational", "Games - Educational"),
            ("Games - Family", "Games - Family"),
            ("Games - Kids", "Games - Kids"),
            ("Games - Music", "Games - Music"),
            ("Games - Puzzle", "Games - Puzzle"),
            ("Games - Racing", "Games - Racing"),
            ("Games - Role Playing", "Games - Role Playing"),
            ("Games - Simulation", "Games - Simulation"),
            ("Games - Sports", "Games - Sports"),
            ("Games - Strategy", "Games - Strategy"),
            ("Games - Trivia", "Games - Trivia"),
            ("Games - Word", "Games - Word"),
            ("Health & Fitness", "Health & Fitness"),
            ("Lifestyle", "Lifestyle"),
            ("Medical", "Medical"),
            ("Music", "Music"),
            ("Navigation", "Navigation"),
            ("News", "News"),
            ("Newsstand", "Newsstand"),
            ("Photo & video", "Photo & video"),
            ("Productivity", "Productivity"),
            ("Reference", "Reference"),
            ("Social Networking", "Social Networking"),
            ("Sports", "Sports"),
            ("Travel", "Travel"),
            ("Utilities", "Utilities"),
            ("Weather", "Weather"),
            ("Games", "Games"),
            ("Shopping", "Shopping"),
        ]
        
        if platform.lower() == "android":
            return android_categories
        else:
            return ios_categories
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation
        
        Now supports simultaneous Android and iOS app creation (like IronSource/InMobi/BigOAds)
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
            # Android fields
            Field(
                name="androidStoreUrl",
                field_type="text",
                required=False,
                label="Android Store URL",
                placeholder="https://play.google.com/store/apps/details?id=...",
                help_text="Google Play Store URL for Android app (optional)"
            ),
            Field(
                name="androidBundle",
                field_type="text",
                required=False,
                label="Android Bundle ID",
                placeholder="com.example.app",
                help_text="Android package name (required if Android Store URL is provided)"
            ),
            # iOS fields
            Field(
                name="iosStoreUrl",
                field_type="text",
                required=False,
                label="iOS Store URL",
                placeholder="https://apps.apple.com/.../id1234567890",
                help_text="Apple App Store URL for iOS app (optional)"
            ),
            Field(
                name="iosBundle",
                field_type="text",
                required=False,
                label="iOS Bundle/Store ID",
                placeholder="com.example.app (recommended)",
                help_text="iOS Bundle ID (recommended) or iTunes Store ID (required if iOS Store URL is provided)"
            ),
            # Legacy fields for backward compatibility (hidden, will be populated from platform-specific fields)
            Field(
                name="bundle",
                field_type="hidden",
                required=False,
                label="Bundle (Legacy)",
                default=""
            ),
            Field(
                name="platform",
                field_type="hidden",
                required=False,
                label="Platform (Legacy)",
                default="android"
            ),
            # Android Category
            Field(
                name="androidCategory1",
                field_type="dropdown",
                required=False,
                label="Category 1 (Android)*",
                options=self._get_categories("android"),
                default="Games - Casual",
                help_text="App's first store category for Android (required if Android Store URL is provided)"
            ),
            # iOS Category
            Field(
                name="iosCategory1",
                field_type="dropdown",
                required=False,
                label="Category 1 (iOS)*",
                options=self._get_categories("ios"),
                default="Games",
                help_text="App's first store category for iOS (required if iOS Store URL is provided)"
            ),
            # Legacy field for backward compatibility
            Field(
                name="category1",
                field_type="hidden",
                required=False,
                label="Category 1 (Legacy)",
                default="Games - Casual"
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
            # Rewarded Ad URL is optional, so hide it from UI
            Field(
                name="rewardedAdUrl",
                field_type="hidden",
                required=False,
                label="Rewarded Ad URL",
                default=""
            ),
            # category2 is optional and hidden from UI
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit (placement) creation
        
        API: POST https://console.fyber.com/api/management/v1/placement
        """
        return [
            Field(
                name="name",
                field_type="text",
                required=True,
                label="Placement Name*",
                placeholder="Enter placement name (e.g., int_13)",
                help_text="The name of the placement"
            ),
            Field(
                name="appId",
                field_type="number",
                required=True,
                label="App ID*",
                placeholder="12345",
                help_text="The ID of the placement's app",
                min_value=1
            ),
            Field(
                name="placementType",
                field_type="dropdown",
                required=True,
                label="Placement Type*",
                options=[
                    ("Banner", "Banner"),
                    ("Rewarded", "Rewarded"),
                    ("Interstitial", "Interstitial"),
                    ("MREC", "MREC")
                ],
                default="Rewarded",
                help_text="The placement type"
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
            # Optional fields will be added based on placementType
            # creativeTypes (Interstitial only)
            # bannerRefresh (Banner only)
            # floorPrices
            # targetingEnabled
            # geo (only if targetingEnabled=true)
            # connectivity (only if targetingEnabled=true)
            # capping (only if enabled=true)
            # pacing (only if enabled=true)
            # ssrConfig (Rewarded only, only if enabled=true)
            # skipability (Interstitial only)
        ]
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        error_messages = []
        
        # Required fields
        if not data.get("name"):
            error_messages.append("App Name is required")
        
        # Check that at least one platform (Android or iOS) is provided
        android_store_url = data.get("androidStoreUrl", "").strip()
        ios_store_url = data.get("iosStoreUrl", "").strip()
        
        if not android_store_url and not ios_store_url:
            error_messages.append("At least one Store URL (Android or iOS) must be provided")
        
        # Validate Android fields if Android Store URL is provided
        if android_store_url:
            android_bundle = data.get("androidBundle", "").strip()
            if not android_bundle:
                error_messages.append("Android Bundle ID is required when Android Store URL is provided")
            android_category1 = data.get("androidCategory1", "").strip()
            if not android_category1:
                error_messages.append("Category 1 (Android) is required when Android Store URL is provided")
        
        # Validate iOS fields if iOS Store URL is provided
        if ios_store_url:
            ios_bundle = data.get("iosBundle", "").strip()
            if not ios_bundle:
                error_messages.append("iOS Bundle/Store ID is required when iOS Store URL is provided")
            ios_category1 = data.get("iosCategory1", "").strip()
            if not ios_category1:
                error_messages.append("Category 1 (iOS) is required when iOS Store URL is provided")
        
        # COPPA is required
        if "coppa" not in data:
            error_messages.append("COPPA is required")
        else:
            valid_coppa = ["true", "false"]
            if data.get("coppa") not in valid_coppa:
                error_messages.append(f"COPPA must be one of: {', '.join(valid_coppa)}")
        
        # Return first error message if any, otherwise return success
        if error_messages:
            return False, error_messages[0]
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit (placement) creation data"""
        # Required fields
        if not data.get("name"):
            return False, "Placement Name is required"
        
        if not data.get("appId"):
            return False, "App ID is required"
        
        try:
            app_id = int(data.get("appId"))
            if app_id <= 0:
                return False, "App ID must be a positive number"
        except (ValueError, TypeError):
            return False, "App ID must be a valid number"
        
        if not data.get("placementType"):
            return False, "Placement Type is required"
        
        valid_placement_types = ["Banner", "Rewarded", "Interstitial", "MREC"]
        if data.get("placementType") not in valid_placement_types:
            return False, f"Placement Type must be one of: {', '.join(valid_placement_types)}"
        
        if "coppa" not in data:
            return False, "COPPA is required"
        
        valid_coppa = ["true", "false"]
        if data.get("coppa") not in valid_coppa:
            return False, f"COPPA must be one of: {', '.join(valid_coppa)}"
        
        return True, ""
    
    def build_app_payload(self, form_data: Dict, platform: Optional[str] = None) -> Dict:
        """Build API payload for app creation
        
        Args:
            form_data: Form data from UI
            platform: "Android" or "iOS" (optional, for dual-platform creation)
        """
        # Determine platform and bundle based on platform parameter or form_data
        if platform == "Android":
            platform_str = "android"
            bundle = form_data.get("androidBundle", "").strip()
            category1 = form_data.get("androidCategory1", "").strip()
        elif platform == "iOS":
            platform_str = "ios"
            bundle = form_data.get("iosBundle", "").strip()
            category1 = form_data.get("iosCategory1", "").strip()
        else:
            # Legacy: use form_data directly (backward compatibility)
            platform_str = form_data.get("platform", "android")
            bundle = form_data.get("bundle", "").strip()
            category1 = form_data.get("category1", "").strip()
            if not bundle:
                # Try to get from platform-specific fields
                if platform_str == "android":
                    bundle = form_data.get("androidBundle", "").strip()
                    if not category1:
                        category1 = form_data.get("androidCategory1", "").strip()
                elif platform_str == "ios":
                    bundle = form_data.get("iosBundle", "").strip()
                    if not category1:
                        category1 = form_data.get("iosCategory1", "").strip()
        
        # Get COPPA value, ensure it defaults to "false" if not provided or invalid
        coppa_value = form_data.get("coppa")
        # Explicitly check: if coppa is None, empty, or not a valid value, default to "false"
        # Also handle boolean values (True/False) and convert to string
        if coppa_value is None or coppa_value == "":
            coppa_value = "false"
        elif isinstance(coppa_value, bool):
            coppa_value = "true" if coppa_value else "false"
        elif str(coppa_value).lower() not in ["true", "false"]:
            coppa_value = "false"
        else:
            # Ensure it's lowercase string
            coppa_value = str(coppa_value).lower()
        
        # Convert coppa string to boolean for API (Fyber API expects boolean)
        coppa_bool = coppa_value == "true"
        
        payload = {
            "name": form_data.get("name", "").strip(),
            "bundle": bundle,
            "platform": platform_str,
            "category1": category1,
            "coppa": coppa_bool,  # Convert to boolean (defaults to false)
        }
        
        # Optional fields
        if form_data.get("rewardedAdUrl"):
            payload["rewardedAdUrl"] = form_data.get("rewardedAdUrl", "").strip()
        
        if form_data.get("category2"):
            payload["category2"] = form_data.get("category2", "").strip()
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit (placement) creation
        
        API: POST https://console.fyber.com/api/management/v1/placement
        """
        # Required fields
        # Note: API expects appId as string, not integer
        app_id_value = form_data.get("appId", "0")
        if isinstance(app_id_value, int):
            app_id_value = str(app_id_value)
        
        payload = {
            "name": form_data.get("name", "").strip(),
            "appId": str(app_id_value).strip(),  # Must be string, not integer
            "placementType": form_data.get("placementType", "Rewarded"),
            "coppa": form_data.get("coppa", "false") == "true",  # Convert to boolean
        }
        
        # Optional fields based on placement type
        placement_type = form_data.get("placementType", "")
        
        # creativeTypes (Interstitial only)
        if placement_type == "Interstitial" and form_data.get("creativeTypes"):
            creative_types = form_data.get("creativeTypes")
            if isinstance(creative_types, str):
                # If string, try to parse as JSON array or comma-separated
                try:
                    import json
                    creative_types = json.loads(creative_types)
                except:
                    creative_types = [t.strip() for t in creative_types.split(",")]
            if isinstance(creative_types, list):
                payload["creativeTypes"] = creative_types
        
        # bannerRefresh (Banner only)
        if placement_type == "Banner" and form_data.get("bannerRefresh"):
            try:
                payload["bannerRefresh"] = int(form_data.get("bannerRefresh"))
            except (ValueError, TypeError):
                pass
        
        # floorPrices (optional)
        if form_data.get("floorPrices"):
            floor_prices = form_data.get("floorPrices")
            if isinstance(floor_prices, str):
                try:
                    import json
                    floor_prices = json.loads(floor_prices)
                except:
                    pass
            if isinstance(floor_prices, list):
                payload["floorPrices"] = floor_prices
        
        # targetingEnabled (optional)
        if "targetingEnabled" in form_data:
            payload["targetingEnabled"] = form_data.get("targetingEnabled") == "true" if isinstance(form_data.get("targetingEnabled"), str) else bool(form_data.get("targetingEnabled"))
            
            # geo (only if targetingEnabled=true)
            if payload.get("targetingEnabled") and form_data.get("geo"):
                geo = form_data.get("geo")
                if isinstance(geo, str):
                    try:
                        import json
                        geo = json.loads(geo)
                    except:
                        pass
                if isinstance(geo, dict):
                    payload["geo"] = geo
            
            # connectivity (only if targetingEnabled=true)
            if payload.get("targetingEnabled") and form_data.get("connectivity"):
                connectivity = form_data.get("connectivity")
                if isinstance(connectivity, str):
                    try:
                        import json
                        connectivity = json.loads(connectivity)
                    except:
                        connectivity = [c.strip() for c in connectivity.split(",")]
                if isinstance(connectivity, list):
                    payload["connectivity"] = connectivity
        
        # capping (only if enabled=true)
        if form_data.get("capping"):
            capping = form_data.get("capping")
            if isinstance(capping, str):
                try:
                    import json
                    capping = json.loads(capping)
                except:
                    pass
            if isinstance(capping, dict) and capping.get("enabled"):
                payload["capping"] = capping
        
        # pacing (only if enabled=true)
        if form_data.get("pacing"):
            pacing = form_data.get("pacing")
            if isinstance(pacing, str):
                try:
                    import json
                    pacing = json.loads(pacing)
                except:
                    pass
            if isinstance(pacing, dict) and pacing.get("enabled"):
                payload["pacing"] = pacing
        
        # ssrConfig (Rewarded only, only if enabled=true)
        if placement_type == "Rewarded" and form_data.get("ssrConfig"):
            ssr_config = form_data.get("ssrConfig")
            if isinstance(ssr_config, str):
                try:
                    import json
                    ssr_config = json.loads(ssr_config)
                except:
                    pass
            if isinstance(ssr_config, dict) and ssr_config.get("enabled"):
                payload["ssrConfig"] = ssr_config
        
        # skipability (Interstitial only)
        if placement_type == "Interstitial" and form_data.get("skipability"):
            payload["skipability"] = form_data.get("skipability")
        
        return payload

