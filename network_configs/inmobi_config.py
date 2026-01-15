"""InMobi network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField


class InMobiConfig(NetworkConfig):
    """InMobi network configuration"""
    
    @property
    def network_name(self) -> str:
        return "inmobi"
    
    @property
    def display_name(self) -> str:
        return "InMobi"
    
    def _get_child_directed_options(self) -> List[Tuple[str, int]]:
        """Get child directed options"""
        return [
            ("Not directed towards children", 2),  # 값 1 → 2로 변경
            ("Directed towards children (requires parental consent)", 1),  # 값 2 → 1로 변경
            ("Partially directed towards children and adults", 3),
        ]
    
    def _get_placement_type_options(self) -> List[Tuple[str, str]]:
        """Get placement type options"""
        return [
            ("Interstitial", "INTERSTITIAL"),
            ("Banner", "BANNER"),
            ("Rewarded Video", "REWARDED_VIDEO"),
            ("Native", "NATIVE"),
        ]
    
    def _get_audience_bidding_partner_options(self) -> List[Tuple[str, str]]:
        """Get audience bidding partner options"""
        return [
            ("MAX", "MAX"),
            ("Amazon TAM", "AMAZON_TAM"),
            ("Google Open Bidding", "GOOGLE_OPEN_BIDDING"),
            ("Custom Mediation", "CUSTOM_MEDIATION"),
            ("IronSource", "IRONSOURCE"),
            ("SpringServe", "SPRINGSERVE"),
            ("Prebid", "PREBID"),
            ("Fyber", "FYBER"),
            ("AdMost", "ADMOST"),
            ("Aequus", "AEQUUS"),
            ("GameAnalytics HyperBid", "GAMEANALYTICS_HYPERBID"),
            ("Chartboost", "CHARTBOOST"),
            ("Google SDK Bidding", "GOOGLE_SDK_BIDDING"),
        ]
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation
        
        Note: For InMobi, we support creating apps for both iOS and Android simultaneously.
        Store URLs are separated by platform.
        Order: iosStoreUrl, androidStoreUrl, childDirected, locationAccess, appName (as per API documentation)
        """
        return [
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
                name="childDirected",
                field_type="radio",
                required=True,
                label="Child Directed*",
                options=self._get_child_directed_options(),
                default=2,
                help_text="Specify the audience type of the app"
            ),
            Field(
                name="locationAccess",
                field_type="radio",
                required=True,
                label="Location Access*",
                options=[("Yes", True), ("No", False)],
                default=True,
                help_text="Specify if InMobi can access the location details"
            ),
            Field(
                name="appName",
                field_type="text",
                required=False,
                label="App Name",
                placeholder="Enter app name (optional)",
                help_text="Name of the app (optional)"
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit (placement) creation"""
        base_fields = [
            Field(
                name="appId",
                field_type="number",
                required=True,
                label="App ID*",
                placeholder="Enter app ID from InMobi platform",
                help_text="App key on InMobi platform",
                min_value=1
            ),
            Field(
                name="placementName",
                field_type="text",
                required=True,
                label="Placement Name*",
                placeholder="Enter placement name",
                help_text="Placement name as on InMobi platform"
            ),
            Field(
                name="placementType",
                field_type="dropdown",
                required=True,
                label="Placement Type*",
                options=self._get_placement_type_options(),
                default="INTERSTITIAL",
                help_text="Type of placement"
            ),
            Field(
                name="isAudienceBiddingEnabled",
                field_type="radio",
                required=True,
                label="Audience Bidding Enabled*",
                options=[("Yes", True), ("No", False)],
                default=False,
                help_text="Determines if Audience Bidding is enabled for this placement"
            ),
        ]
        
        # Conditional fields
        conditional_fields = [
            # audienceBiddingPartner: Required if isAudienceBiddingEnabled is true
            ConditionalField(
                name="audienceBiddingPartner",
                field_type="dropdown",
                required=True,
                label="Audience Bidding Partner*",
                options=self._get_audience_bidding_partner_options(),
                help_text="Audience Bidding Partner (required if Audience Bidding is enabled)",
                condition=lambda data: data.get("isAudienceBiddingEnabled") is True
            ),
            # a9TagId: Required if Amazon TAM
            ConditionalField(
                name="a9TagId",
                field_type="text",
                required=True,
                label="A9 Tag ID*",
                placeholder="Enter Amazon TAM Tag ID",
                help_text="Tag ID of Amazon TAM placement (required if Amazon TAM is selected as Audience Bidding partner)",
                condition=lambda data: data.get("audienceBiddingPartner") == "AMAZON_TAM"
            ),
            # a9AppId: Required if Amazon TAM
            ConditionalField(
                name="a9AppId",
                field_type="text",
                required=True,
                label="A9 App ID*",
                placeholder="Enter Amazon TAM App ID",
                help_text="App ID of Amazon TAM placement (required if Amazon TAM is selected as Audience Bidding partner)",
                condition=lambda data: data.get("audienceBiddingPartner") == "AMAZON_TAM"
            ),
            # cpmFloor: Optional, not applicable if isAudienceBiddingEnabled is true
            ConditionalField(
                name="cpmFloor",
                field_type="number",
                required=False,
                label="CPM Floor",
                placeholder="0.00",
                help_text="eCPM floor set on the InMobi platform (not applicable if Audience Bidding is enabled)",
                min_value=0,
                condition=lambda data: data.get("isAudienceBiddingEnabled") is False
            ),
            # isFallbackPlacement: Optional
            Field(
                name="isFallbackPlacement",
                field_type="radio",
                required=False,
                label="Is Fallback Placement",
                options=[("No", False), ("Yes", True)],
                default=False,
                help_text="Determines if this is a fallback placement"
            ),
        ]
        
        return base_fields + conditional_fields
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        # At least one Store URL must be provided
        ios_store_url = data.get("iosStoreUrl", "").strip()
        android_store_url = data.get("androidStoreUrl", "").strip()
        
        if not ios_store_url and not android_store_url:
            return False, "At least one Store URL (iOS or Android) must be provided"
        
        # Validate iOS Store URL format if provided
        if ios_store_url:
            if not (ios_store_url.startswith("http://") or ios_store_url.startswith("https://")):
                return False, "iOS Store URL must be a valid URL starting with http:// or https://"
        
        # Validate Android Store URL format if provided
        if android_store_url:
            if not (android_store_url.startswith("http://") or android_store_url.startswith("https://")):
                return False, "Android Store URL must be a valid URL starting with http:// or https://"
        
        if "childDirected" not in data:
            return False, "Child Directed is required"
        
        if data.get("childDirected") not in [1, 2, 3]:
            return False, "Child Directed must be 1, 2, or 3"
        
        if "locationAccess" not in data:
            return False, "Location Access is required"
        
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        # Required fields
        if not data.get("appId"):
            return False, "App ID is required"
        
        if not data.get("placementName"):
            return False, "Placement Name is required"
        
        if not data.get("placementType"):
            return False, "Placement Type is required"
        
        valid_placement_types = ["INTERSTITIAL", "BANNER", "REWARDED_VIDEO", "NATIVE"]
        if data.get("placementType") not in valid_placement_types:
            return False, f"Placement Type must be one of: {', '.join(valid_placement_types)}"
        
        if "isAudienceBiddingEnabled" not in data:
            return False, "Audience Bidding Enabled is required"
        
        # Conditional validation: audienceBiddingPartner required if isAudienceBiddingEnabled is true
        if data.get("isAudienceBiddingEnabled") is True:
            if not data.get("audienceBiddingPartner"):
                return False, "Audience Bidding Partner is required when Audience Bidding is enabled"
            
            # If Amazon TAM, a9TagId and a9AppId are required
            if data.get("audienceBiddingPartner") == "AMAZON_TAM":
                if not data.get("a9TagId"):
                    return False, "A9 Tag ID is required when Amazon TAM is selected as Audience Bidding partner"
                if not data.get("a9AppId"):
                    return False, "A9 App ID is required when Amazon TAM is selected as Audience Bidding partner"
        
        # cpmFloor should not be set if isAudienceBiddingEnabled is true
        if data.get("isAudienceBiddingEnabled") is True and data.get("cpmFloor") is not None:
            return False, "CPM Floor is not applicable when Audience Bidding is enabled"
        
        return True, ""
    
    def build_app_payload(self, form_data: Dict, platform: Optional[str] = None) -> Dict:
        """Build API payload for app creation
        
        Args:
            form_data: Form data from UI
            platform: Optional platform string ("iOS" or "Android") to select the appropriate store URL
        """
        # Select store URL based on platform
        if platform == "iOS":
            store_url = form_data.get("iosStoreUrl", "").strip()
        elif platform == "Android":
            store_url = form_data.get("androidStoreUrl", "").strip()
        else:
            # Fallback: use storeUrl if provided (for backward compatibility)
            store_url = form_data.get("storeUrl", "").strip()
            if not store_url:
                # Try to get from platform-specific fields
                store_url = form_data.get("iosStoreUrl", "").strip() or form_data.get("androidStoreUrl", "").strip()
        
        if not store_url:
            raise ValueError(f"Store URL is required for {platform or 'the selected platform'}")
        
        # Get childDirected value and ensure it's an integer
        child_directed_value = form_data.get("childDirected", 1)
        # Handle case where value might be a string representation
        if isinstance(child_directed_value, str):
            try:
                child_directed_value = int(child_directed_value)
            except (ValueError, TypeError):
                child_directed_value = 1
        else:
            child_directed_value = int(child_directed_value) if child_directed_value is not None else 1
        
        # Log the childDirected value for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[InMobi] childDirected value: {child_directed_value} (type: {type(child_directed_value)})")
        logger.info(f"[InMobi] childDirected from form_data: {form_data.get('childDirected')} (type: {type(form_data.get('childDirected'))})")
        
        payload = {
            "storeUrl": store_url,
            "childDirected": child_directed_value,
            "locationAccess": bool(form_data.get("locationAccess", True)),
        }
        
        # appName is optional, only include if provided and not empty
        app_name = form_data.get("appName", "").strip()
        if app_name:
            payload["appName"] = app_name
        
        # Remove any None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit creation"""
        payload = {
            "appId": int(form_data.get("appId", 0)),
            "placementName": form_data.get("placementName", "").strip(),
            "placementType": form_data.get("placementType", "INTERSTITIAL"),
            "isAudienceBiddingEnabled": bool(form_data.get("isAudienceBiddingEnabled", False)),
        }
        
        # Conditional fields
        if payload["isAudienceBiddingEnabled"]:
            payload["audienceBiddingPartner"] = form_data.get("audienceBiddingPartner", "")
            
            # Amazon TAM specific fields
            if payload.get("audienceBiddingPartner") == "AMAZON_TAM":
                if form_data.get("a9TagId"):
                    payload["a9TagId"] = form_data.get("a9TagId", "").strip()
                if form_data.get("a9AppId"):
                    payload["a9AppId"] = form_data.get("a9AppId", "").strip()
        else:
            # cpmFloor only applicable if Audience Bidding is disabled
            if form_data.get("cpmFloor") is not None:
                try:
                    payload["cpmFloor"] = float(form_data.get("cpmFloor", 0))
                except (ValueError, TypeError):
                    payload["cpmFloor"] = 0
        
        # Optional field
        if "isFallbackPlacement" in form_data:
            payload["isFallbackPlacement"] = bool(form_data.get("isFallbackPlacement", False))
        
        return payload

