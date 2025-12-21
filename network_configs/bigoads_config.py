"""BigOAds network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField


class BigOAdsConfig(NetworkConfig):
    """BigOAds network configuration"""
    
    @property
    def network_name(self) -> str:
        return "bigoads"
    
    @property
    def display_name(self) -> str:
        return "BigOAds"
    
    def _get_categories(self) -> List[Tuple[str, int]]:
        """Get category options"""
        return [
            ("Action", 1),
            ("Adventure", 2),
            ("Arcade", 3),
            ("Board", 4),
            ("Card", 5),
            ("Casino", 6),
            ("Casual", 7),
            ("Educational", 8),
            ("Music", 9),
            ("Puzzle", 10),
            ("Racing", 11),
            ("Role Playing", 12),
            ("Simulation", 13),
            ("Sports", 14),
            ("Strategy", 15),
            ("Trivia", 16),
            ("Word", 17),
            ("Other", 18),
        ]
    
    def _get_mediation_platforms(self) -> List[Tuple[str, int]]:
        """Get mediation platform options
        
        API 순서: 1:MAX, 2:Yandex, 3:AdMob, 4:ironSource, 5:TopOn, 6:TradePlus, 7:in-house Mediation, 99:others
        """
        return [
            ("MAX", 1),
            ("Yandex", 2),
            ("AdMob", 3),
            ("ironSource", 4),
            ("TopOn", 5),
            ("TradePlus", 6),
            ("In-house Mediation", 7),
            ("Others", 99),
        ]
    
    def _get_ad_types(self) -> List[Tuple[str, int]]:
        """Get ad type options"""
        return [
            ("Native", 1),
            ("Banner", 2),
            ("Interstitial", 3),
            ("Reward Video", 4),
            ("Splash Ad", 5),
            ("Pop Up", 6),
        ]
    
    def _get_auction_types(self) -> List[Tuple[str, int]]:
        """Get auction type options"""
        return [
            ("Waterfall", 1),
            ("Client Bidding", 2),
            ("Server Bidding", 3),
        ]
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation
        
        API 순서 (storeUrl 제외 모두 필수):
        1. name*
        2. mediaType* (항상 1로 고정, 숨김)
        3. platform*
        4. pkgName*
        5. itunesId* (iOS일 때만 활성화)
        6. storeUrl (선택)
        7. mediationPlatform*
        8. category*
        9. coppaOption*
        10. screenDirection*
        """
        return [
            # 1. name*
            Field(
                name="name",
                field_type="text",
                required=True,
                label="App Name",
                placeholder="Enter app name"
            ),
            # 2. mediaType* (항상 1로 고정, 숨김 처리)
            Field(
                name="mediaType",
                field_type="hidden",
                required=True,
                label="Media Type",
                default=1  # 항상 Application (1)
            ),
            # 3. platform*
            Field(
                name="platform",
                field_type="radio",
                required=True,
                label="Platform",
                options=[("Android", 1), ("iOS", 2)],
                default=1
            ),
            # 4. pkgName*
            Field(
                name="pkgName",
                field_type="text",
                required=True,
                label="Package Name",
                placeholder="com.example.app"
            ),
            # 5. itunesId* (항상 활성화, validation에서 iOS일 때만 체크)
            Field(
                name="itunesId",
                field_type="text",
                required=True,
                label="iTunes ID (iOS)",
                placeholder="Enter iTunes ID",
                help_text="Required for iOS apps. Enter iTunes ID (e.g., 1234567890)"
            ),
            # 6. storeUrl (선택, * 없음)
            Field(
                name="storeUrl",
                field_type="text",
                required=False,
                label="Store URL",
                placeholder="https://play.google.com/store/apps/details?id=..."
            ),
            # 7. mediationPlatform*
            Field(
                name="mediationPlatform",
                field_type="multiselect",
                required=True,
                label="Mediation Platform",
                options=self._get_mediation_platforms(),
                default=[1]  # MAX
            ),
            # mediationPlatformName (조건부, Others 선택 시)
            ConditionalField(
                name="mediationPlatformName",
                field_type="text",
                required=True,
                label="Mediation Platform Name",
                condition=lambda data: data.get("mediationPlatform") and 99 in data.get("mediationPlatform", []),
                placeholder="Enter mediation platform name (required when 'Others' is selected)",
                help_text="Required when 'Others' (99) is selected in Mediation Platform"
            ),
            # 8. category*
            Field(
                name="category",
                field_type="dropdown",
                required=True,
                label="Category",
                options=self._get_categories(),
                default=7  # Casual
            ),
            # 9. coppaOption*
            Field(
                name="coppaOption",
                field_type="radio",
                required=True,
                label="COPPA",
                options=[("No", 1), ("Yes", 2)],
                default=1
            ),
            # 10. screenDirection*
            Field(
                name="screenDirection",
                field_type="radio",
                required=True,
                label="Orientation",
                options=[("Vertical", 0), ("Horizontal", 1)],
                default=0
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit creation"""
        base_fields = [
            Field(
                name="appCode",
                field_type="dropdown",
                required=True,
                label="App Code",
                help_text="Select the app for this slot"
            ),
            Field(
                name="name",
                field_type="text",
                required=True,
                label="Slot Name",
                placeholder="Enter slot name"
            ),
            Field(
                name="adType",
                field_type="dropdown",
                required=True,
                label="Ad Type",
                options=self._get_ad_types()
            ),
            Field(
                name="auctionType",
                field_type="dropdown",
                required=True,
                label="Auction Type",
                options=self._get_auction_types()
            ),
        ]
        
        # Conditional fields based on ad_type and auction_type
        conditional_fields = [
            ConditionalField(
                name="reservePrice",
                field_type="number",
                required=False,
                label="Reserve Price (cents)",
                condition=lambda data: data.get("auctionType") == 1,  # Waterfall
                default=1,
                min_value=0.01,
                help_text="Minimum price in cents (default: 0.01)"
            ),
            ConditionalField(
                name="musicSwitch",
                field_type="radio",
                required=True,
                label="Music",
                condition=lambda data: data.get("adType") in [1, 3, 4, 6],  # Native, Interstitial, Reward, PopUp
                options=[("On", 1), ("Off", 0)],
                default=1
            ),
            ConditionalField(
                name="adSpecification",
                field_type="multiselect",
                required=True,
                label="Creative Type",
                condition=lambda data: data.get("adType") == 1,  # Native
                options=[("Image", 1), ("Video", 2)]
            ),
            ConditionalField(
                name="videoAutoReplay",
                field_type="radio",
                required=True,
                label="Video Auto Replay",
                condition=lambda data: data.get("adType") == 1 and 2 in data.get("adSpecification", []),  # Native with Video
                options=[("Yes", 1), ("No", 0)],
                default=0
            ),
            ConditionalField(
                name="autoRefresh",
                field_type="radio",
                required=True,
                label="Auto Refresh",
                condition=lambda data: data.get("adType") == 2,  # Banner
                options=[("Yes", 1), ("No", 0)],
                default=0
            ),
            ConditionalField(
                name="refreshSec",
                field_type="number",
                required=False,
                label="Refresh Seconds",
                condition=lambda data: data.get("adType") == 2 and data.get("autoRefresh") == 1,  # Banner with auto refresh
                min_value=1,
                placeholder="Seconds"
            ),
            ConditionalField(
                name="bannerSize",
                field_type="multiselect",
                required=True,
                label="Banner Size",
                condition=lambda data: data.get("adType") == 2,  # Banner
                options=[("300x250", "300x250"), ("320x50", "320x50")]
            ),
            ConditionalField(
                name="fullScreen",
                field_type="radio",
                required=True,
                label="Full Screen",
                condition=lambda data: data.get("adType") == 5,  # Splash
                options=[("Full", 1), ("Half", 0)],
                default=1
            ),
            ConditionalField(
                name="showDuration",
                field_type="number",
                required=True,
                label="Show Duration (seconds)",
                condition=lambda data: data.get("adType") == 5,  # Splash
                min_value=3,
                max_value=10,
                default=5
            ),
            ConditionalField(
                name="turnOff",
                field_type="number",
                required=True,
                label="Turn Off (seconds)",
                condition=lambda data: data.get("adType") == 5,  # Splash
                min_value=0,
                max_value=5,
                default=0
            ),
            ConditionalField(
                name="showCountMax",
                field_type="number",
                required=True,
                label="Show Count Max (0=unlimited)",
                condition=lambda data: data.get("adType") == 5,  # Splash
                min_value=0,
                default=0
            ),
            ConditionalField(
                name="interactive",
                field_type="radio",
                required=True,
                label="Interactive",
                condition=lambda data: data.get("adType") == 5,  # Splash
                options=[("No", 0), ("Yes", 1)],
                default=0
            ),
        ]
        
        return base_fields + conditional_fields
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data - returns (is_valid, error_message)"""
        error_messages = []
        
        # iOS requires iTunes ID (validation only, field is always enabled)
        # Check platform value first to validate itunesId if iOS is selected
        platform = data.get("platform")
        try:
            # Try to convert platform to int, handling various input types
            if platform is None:
                platform_int = None
            elif isinstance(platform, int):
                platform_int = platform
            elif isinstance(platform, str):
                platform_int = int(platform.strip())
            else:
                platform_int = int(platform)
        except (ValueError, TypeError):
            platform_int = None
        
        # Check if platform is iOS (2) - validate itunesId first
        if platform_int == 2:  # iOS
            itunes_id = data.get("itunesId")
            
            # Check if itunesId is missing, empty, or "0"
            # Handle various empty cases: None, empty string, whitespace-only, "0"
            itunes_id_str = str(itunes_id).strip() if itunes_id is not None else ""
            is_empty = (itunes_id is None or 
                       itunes_id == "" or 
                       itunes_id_str == "" or 
                       itunes_id_str == "0")
            
            if is_empty:
                error_messages.append("iTunes ID is required for iOS apps")
            else:
                # Validate that itunesId contains only digits (must be numeric)
                if not itunes_id_str.isdigit():
                    error_messages.append("iTunes ID must be a valid integer (numbers only, no letters or special characters)")
                else:
                    # Additional check: try to convert to int
                    try:
                        int(itunes_id_str)
                    except (ValueError, TypeError):
                        error_messages.append("iTunes ID must be a valid integer")
        
        # Check required fields (after itunesId validation for iOS)
        # Note: 'name' and 'pkgName' are validated separately in common validations
        required_fields = ["platform", "mediaType", "category", "mediationPlatform", "coppaOption", "screenDirection"]
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                # Map field names to user-friendly labels
                field_labels = {
                    "platform": "Platform",
                    "mediaType": "Media Type",
                    "category": "Category",
                    "mediationPlatform": "Mediation Platform",
                    "coppaOption": "COPPA",
                    "screenDirection": "Screen Direction"
                }
                field_label = field_labels.get(field, field)
                error_messages.append(f"{field_label} is required")
        
        # Return first error message if any, otherwise return success
        if error_messages:
            return False, error_messages[0]  # Return first error for backward compatibility
        return True, ""
        
        # Mediation platform must be selected
        if not data.get("mediationPlatform") or len(data["mediationPlatform"]) == 0:
            return False, "At least one mediation platform must be selected"
        
        # Validate mediationPlatformName if 99 (others) is selected
        if 99 in data.get("mediationPlatform", []):
            if not data.get("mediationPlatformName") or data.get("mediationPlatformName") == "":
                return False, "Mediation Platform Name is required when 'Others' (99) is selected"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        required_fields = ["appCode", "name", "adType", "auctionType"]
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                return False, f"Field '{field}' is required"
        
        # Ad type specific validations
        ad_type = data.get("adType")
        
        if ad_type == 1:  # Native
            if not data.get("adSpecification") or len(data["adSpecification"]) == 0:
                return False, "Creative type is required for Native ads"
            if "musicSwitch" not in data:
                return False, "Music switch is required for Native ads"
        
        if ad_type == 2:  # Banner
            if "autoRefresh" not in data:
                return False, "Auto refresh is required for Banner ads"
            if data.get("autoRefresh") == 1 and (not data.get("refreshSec") or data["refreshSec"] < 1):
                return False, "Refresh seconds must be at least 1 when auto refresh is enabled"
            if not data.get("bannerSize") or len(data["bannerSize"]) == 0:
                return False, "Banner size is required"
        
        if ad_type == 5:  # Splash
            if "fullScreen" not in data:
                return False, "Full screen option is required for Splash ads"
            if not data.get("showDuration") or data["showDuration"] < 3 or data["showDuration"] > 10:
                return False, "Show duration must be between 3 and 10 seconds"
            if "turnOff" not in data or data["turnOff"] < 0 or data["turnOff"] > 5:
                return False, "Turn off must be between 0 and 5 seconds"
            if "showCountMax" not in data or data["showCountMax"] < 0:
                return False, "Show count max must be 0 or greater"
            if "interactive" not in data:
                return False, "Interactive option is required for Splash ads"
        
        return True, ""
    
    def build_app_payload(self, form_data: Dict) -> Dict:
        """Build API payload for app creation
        
        API Parameters:
        - name: string, Yes
        - mediaType: int, Yes (항상 1:application)
        - platform: int, Yes (1:Android, 2:iOS)
        - pkgName: string, Yes
        - itunesId: int, iOS app required
        - storeUrl: string, No
        - mediationPlatform: int[], Yes (배열)
        - mediationPlatformName: string, No (required when mediationPlatform includes 99)
        - category: string, Yes (value from API /open/app/dict/category)
        - coppaOption: int, Yes (1=no, 2=yes)
        - screenDirection: int, Yes (0:Vertical, 1:Horizontal)
        """
        payload = {
            "name": form_data.get("name"),
            "pkgName": form_data.get("pkgName"),
            "platform": form_data.get("platform"),
            "mediaType": form_data.get("mediaType", 1),  # 항상 1 (Application)
            "category": str(form_data.get("category")),  # API 문서에 따르면 string
            "mediationPlatform": form_data.get("mediationPlatform"),  # int[] 배열
            "coppaOption": form_data.get("coppaOption"),
            "screenDirection": form_data.get("screenDirection"),
        }
        
        if form_data.get("storeUrl"):
            payload["storeUrl"] = form_data.get("storeUrl")
        
        if form_data.get("platform") == 2 and form_data.get("itunesId"):
            # API requires int, so convert from string if needed
            itunes_id = form_data.get("itunesId")
            try:
                payload["itunesId"] = int(itunes_id) if isinstance(itunes_id, str) else itunes_id
            except (ValueError, TypeError):
                # If conversion fails, still include it (validation should catch this)
                payload["itunesId"] = itunes_id
        
        # mediationPlatform에 99(others)가 포함되어 있으면 mediationPlatformName 필수
        mediation_platforms = form_data.get("mediationPlatform", [])
        if 99 in mediation_platforms and form_data.get("mediationPlatformName"):
            payload["mediationPlatformName"] = form_data.get("mediationPlatformName")
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit creation"""
        payload = {
            "appCode": form_data.get("appCode"),
            "name": form_data.get("name"),
            "adType": form_data.get("adType"),
            "auctionType": form_data.get("auctionType"),
        }
        
        # Waterfall reserve price
        if form_data.get("auctionType") == 1 and form_data.get("reservePrice"):
            payload["reservePrice"] = form_data.get("reservePrice")
        
        # Music switch for Native, Interstitial, Reward, PopUp
        if form_data.get("adType") in [1, 3, 4, 6] and "musicSwitch" in form_data:
            payload["musicSwitch"] = form_data.get("musicSwitch")
        
        # Native specific
        if form_data.get("adType") == 1:
            if form_data.get("adSpecification"):
                payload["adSpecification"] = form_data.get("adSpecification")
            if form_data.get("videoAutoReplay") is not None:
                payload["videoAutoReplay"] = form_data.get("videoAutoReplay")
        
        # Banner specific
        if form_data.get("adType") == 2:
            if "autoRefresh" in form_data:
                payload["autoRefresh"] = form_data.get("autoRefresh")
            if form_data.get("autoRefresh") == 1 and form_data.get("refreshSec"):
                payload["refreshSec"] = form_data.get("refreshSec")
            if form_data.get("bannerSize"):
                payload["bannerSize"] = form_data.get("bannerSize")
        
        # Splash specific
        if form_data.get("adType") == 5:
            if "fullScreen" in form_data:
                payload["fullScreen"] = form_data.get("fullScreen")
            if form_data.get("showDuration"):
                payload["showDuration"] = form_data.get("showDuration")
            if "turnOff" in form_data:
                payload["turnOff"] = form_data.get("turnOff")
            if "showCountMax" in form_data:
                payload["showCountMax"] = form_data.get("showCountMax")
            if "interactive" in form_data:
                payload["interactive"] = form_data.get("interactive")
        
        return payload

