"""Mintegral network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField


class MintegralConfig(NetworkConfig):
    """Mintegral network configuration"""
    
    @property
    def network_name(self) -> str:
        return "mintegral"
    
    @property
    def display_name(self) -> str:
        return "Mintegral"
    
    def _get_os_options(self) -> List[Tuple[str, str]]:
        """Get OS options (refer to appendix 3)"""
        # Common OS values: "android", "ios"
        return [
            ("Android", "android"),
            ("iOS", "ios"),
        ]
    
    def _get_mediation_platforms(self) -> List[Tuple[str, int]]:
        """Get mediation platform options (refer to appendix 5)"""
        return [
            ("MAX", 1),
            ("DT FairBid", 4),
            ("TopOn", 6),
            ("TradPlus", 7),
            ("GroMore", 8),
            ("Helium", 9),
            ("Unity", 11),
            ("IronSource", 12),
            ("Yandex", 13),
            ("Google AdMob/AdManager", 14),
            ("ToBid", 15),
            ("Others", 0),
        ]
    
    def _get_stores(self) -> List[Tuple[str, str]]:
        """Get store options (refer to appendix 8)"""
        return [
            ("Google Play", "google_play"),
            ("App Store", "app_store"),
        ]
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation - ordered as per API requirements"""
        return [
            # Required fields (with * indicator)
            Field(
                name="app_name",
                field_type="text",
                required=True,
                label="App Name*",
                placeholder="Enter app name (must be unique)",
                help_text="Media name intended to be unique among all media names in the same publisher account"
            ),
            Field(
                name="os",
                field_type="radio",
                required=True,
                label="Operating System*",
                options=self._get_os_options(),
                default="android",
                help_text="Operating system"
            ),
            Field(
                name="package",
                field_type="text",
                required=True,
                label="Package Name*",
                placeholder="com.example.app (Android) or id1364356863 (iOS)",
                help_text="Media's respective package name intended to be unique. iOS sample: id1364356863, Android sample: com.talkingtom"
            ),
            Field(
                name="is_live_in_store",
                field_type="radio",
                required=True,
                label="Live in App Store*",
                options=[("No", 0), ("Yes", 1)],
                default=1,
                help_text="Whether live in app store(s). If Yes, store_url is required."
            ),
            ConditionalField(
                name="store_url",
                field_type="text",
                required=True,
                label="Store URL*",
                placeholder="https://play.google.com/store/apps/details?id=... or https://apps.apple.com/...",
                help_text="App store link (required if live in app store)",
                condition=lambda data: data.get("is_live_in_store") == 1
            ),
            Field(
                name="coppa",
                field_type="radio",
                required=True,
                label="COPPA*",
                options=[("No", 0), ("Yes", 1)],
                default=0,
                help_text="Whether abides to COPPA"
            ),
            # Optional fields (in order)
            Field(
                name="campaign_black_rule",
                field_type="radio",
                required=False,
                label="Campaign Blacklist Rule",
                options=[("Not setting up blacklist", 0), ("Inherit publisher level blacklist", 1), ("Set up individually", 2)],
                default=1,
                help_text="Ad blacklist rule. Default: Inherit publisher level blacklist"
            ),
            Field(
                name="mediation_platform",
                field_type="multiselect",
                required=False,
                label="Mediation Platform",
                options=self._get_mediation_platforms(),
                default=[1],  # MAX
                help_text="Mediation Platform. Default: MAX (1)"
            ),
            Field(
                name="video_orientation",
                field_type="dropdown",
                required=False,
                label="Video Orientation",
                options=[("Portrait", "portrait"), ("Landscape", "landscape"), ("Both", "both")],
                default="both",
                help_text="Orientation of returned video. Default: Both"
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit creation"""
        # Base fields (always required)
        base_fields = [
            Field(
                name="app_id",
                field_type="number",
                required=True,
                label="App ID*",
                help_text="Media ID from created app",
                min_value=1
            ),
            Field(
                name="placement_name",
                field_type="text",
                required=True,
                label="Placement Name*",
                placeholder="Enter placement name",
                help_text="Ad Placement name"
            ),
            Field(
                name="ad_type",
                field_type="dropdown",
                required=True,
                label="Ad Type*",
                options=[
                    ("Rewarded Video", "rewarded_video"),
                    ("New Interstitial", "new_interstitial"),
                    ("Banner", "banner"),
                    ("Native", "native"),
                    ("Static Interstitial", "static_interstitial"),
                    ("Automatic Rendering Native", "automatic_rendering_native"),
                    ("Splash Ad", "splash_ad"),
                ],
                default="rewarded_video",
                help_text="Ad unit ad format"
            ),
            Field(
                name="integrate_type",
                field_type="hidden",
                required=True,
                default="sdk",
                help_text="Integration type (always SDK)"
            ),
            Field(
                name="unit_names",
                field_type="text",
                required=False,
                label="Unit Names",
                placeholder="unit_name1,unit_name2",
                help_text='Traditional units (non-bidding units). Separate with commas. One of "unit_names" or "hb_unit_name" is required.'
            ),
            Field(
                name="hb_unit_name",
                field_type="text",
                required=False,
                label="HB Unit Name",
                placeholder="Enter header bidding unit name",
                help_text='Header bidding unit name. One of "unit_names" or "hb_unit_name" is required.'
            ),
            Field(
                name="skip_time",
                field_type="number",
                required=False,
                label="Skip Time (seconds)",
                help_text="Close button appears after this many seconds. -1 for non-skippable, 0-30 for skippable.",
                min_value=-1,
                max_value=30,
                default=-1
            ),
        ]
        
        # Conditional fields based on ad_type
        conditional_fields = [
            # content_type: for native, automatic_rendering_native, new_interstitial
            ConditionalField(
                name="content_type",
                field_type="dropdown",
                required=False,
                label="Content Type",
                options=[("Image", "image"), ("Video", "video"), ("Both", "both")],
                default="both",
                help_text="Content type. Default: Both",
                condition=lambda data: data.get("ad_type") in ["native", "automatic_rendering_native", "new_interstitial"]
            ),
            # ad_space_type: for new_interstitial
            ConditionalField(
                name="ad_space_type",
                field_type="radio",
                required=False,
                label="Ad Space Type",
                options=[("Full Screen Interstitial", 1), ("Half Screen Interstitial", 2)],
                default=1,
                help_text="Ad Size. Default: Full Screen Interstitial",
                condition=lambda data: data.get("ad_type") == "new_interstitial"
            ),
            # show_close_button: for banner
            ConditionalField(
                name="show_close_button",
                field_type="radio",
                required=False,
                label="Show Close Button",
                options=[("No", 0), ("Yes", 1)],
                default=0,
                help_text="Whether to show close button. Default: No",
                condition=lambda data: data.get("ad_type") == "banner"
            ),
            # auto_fresh: for banner
            ConditionalField(
                name="auto_fresh",
                field_type="radio",
                required=False,
                label="Auto Refresh",
                options=[("Turn Off", 0), ("Turn On", 1)],
                default=0,
                help_text="Auto refresh for banner ads. Default: Turn Off",
                condition=lambda data: data.get("ad_type") == "banner"
            ),
        ]
        
        return base_fields + conditional_fields
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        required_fields = ["app_name", "os", "package", "is_live_in_store", "coppa"]
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                return False, f"Field '{field}' is required"
        
        # Validate is_live_in_store = 1 requires store_url
        if data.get("is_live_in_store") == 1:
            if not data.get("store_url") or data["store_url"] == "":
                return False, "Store URL is required when 'Live in App Store' is Yes"
        
        # Validate os value
        valid_os = ["android", "ios"]
        if data.get("os") not in valid_os:
            return False, f"OS must be one of: {', '.join(valid_os)}"
        
        # Validate coppa value
        if data.get("coppa") not in [0, 1]:
            return False, "COPPA must be 0 (No) or 1 (Yes)"
        
        # Validate is_live_in_store value
        if data.get("is_live_in_store") not in [0, 1]:
            return False, "Live in App Store must be 0 (No) or 1 (Yes)"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data - not implemented yet"""
        # TODO: Implement when Create Unit is needed
        return True, ""
    
    def build_app_payload(self, form_data: Dict) -> Dict:
        """Build API payload for app creation - only send specified fields"""
        # Required fields
        # os must be uppercase: "ANDROID" or "IOS"
        os_value = form_data.get("os", "").upper() if form_data.get("os") else ""
        
        payload = {
            "app_name": form_data.get("app_name"),
            "os": os_value,
            "package": form_data.get("package"),
            "is_live_in_store": form_data.get("is_live_in_store", 1),
            "coppa": form_data.get("coppa", 0),
        }
        
        # Add store_url if is_live_in_store = 1
        if form_data.get("is_live_in_store") == 1 and form_data.get("store_url"):
            payload["store_url"] = form_data.get("store_url")
        
        # Optional fields (only if provided)
        if form_data.get("campaign_black_rule") is not None:
            payload["campaign_black_rule"] = form_data.get("campaign_black_rule")
        
        # mediation_platform: multiselect returns list, but API expects single int
        # Take first value if list, otherwise use as-is
        mediation_platform = form_data.get("mediation_platform")
        if mediation_platform is not None:
            if isinstance(mediation_platform, list) and len(mediation_platform) > 0:
                payload["mediation_platform"] = mediation_platform[0]
            elif not isinstance(mediation_platform, list):
                payload["mediation_platform"] = mediation_platform
        
        if form_data.get("video_orientation"):
            payload["video_orientation"] = form_data.get("video_orientation")
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit creation"""
        # Required fields
        payload = {
            "app_id": int(form_data.get("app_id")),
            "placement_name": form_data.get("placement_name"),
            "ad_type": form_data.get("ad_type"),
            "integrate_type": form_data.get("integrate_type", "sdk"),
        }
        
        # unit_names or hb_unit_name (at least one required)
        unit_names = form_data.get("unit_names", "").strip() if form_data.get("unit_names") else ""
        hb_unit_name = form_data.get("hb_unit_name", "").strip() if form_data.get("hb_unit_name") else ""
        
        if unit_names:
            payload["unit_names"] = unit_names
        if hb_unit_name:
            payload["hb_unit_name"] = hb_unit_name
        
        # Optional fields
        if form_data.get("skip_time") is not None:
            payload["skip_time"] = int(form_data.get("skip_time"))
        
        # Conditional fields based on ad_type
        ad_type = form_data.get("ad_type")
        
        # content_type: for native, automatic_rendering_native, new_interstitial
        if ad_type in ["native", "automatic_rendering_native", "new_interstitial"]:
            if form_data.get("content_type"):
                payload["content_type"] = form_data.get("content_type")
            else:
                payload["content_type"] = "both"  # Default
        
        # ad_space_type: for new_interstitial
        if ad_type == "new_interstitial":
            if form_data.get("ad_space_type") is not None:
                payload["ad_space_type"] = int(form_data.get("ad_space_type"))
            else:
                payload["ad_space_type"] = 1  # Default: Full Screen
        
        # show_close_button: for banner
        if ad_type == "banner":
            if form_data.get("show_close_button") is not None:
                payload["show_close_button"] = int(form_data.get("show_close_button"))
            else:
                payload["show_close_button"] = 0  # Default: No
        
        # auto_fresh: for banner
        if ad_type == "banner":
            if form_data.get("auto_fresh") is not None:
                payload["auto_fresh"] = int(form_data.get("auto_fresh"))
            else:
                payload["auto_fresh"] = 0  # Default: Turn Off
        
        return payload

