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
        
        # Valid categories for iOS (from user specification)
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
        ]
        
        if platform.lower() == "android":
            return android_categories
        else:
            return ios_categories
    
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
                options=self._get_categories("android"),  # Will be updated dynamically based on platform selection
                default="Games - Casual",
                help_text="App's first store category (platform-specific, updates based on platform selection)"
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

