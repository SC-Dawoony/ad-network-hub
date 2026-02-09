"""Base configuration interface for ad networks"""
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class Field:
    """Field definition for dynamic form rendering"""
    name: str
    field_type: str  # text, radio, dropdown, multiselect, number, etc.
    required: bool = False
    label: Optional[str] = None
    help_text: Optional[str] = None
    options: Optional[List[Tuple[str, Any]]] = None  # For radio, dropdown, multiselect
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    placeholder: Optional[str] = None
    disabled: bool = False
    
    def __post_init__(self):
        if self.label is None:
            self.label = self.name.replace('_', ' ').title()


@dataclass
class ConditionalField(Field):
    """Field that is conditionally shown based on form data"""
    condition: Optional[Callable[[Dict], bool]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.condition is None:
            raise ValueError("ConditionalField requires a 'condition' callable")
    
    def should_show(self, form_data: Dict) -> bool:
        """Check if field should be displayed"""
        if self.condition is None:
            return True  # Fallback (should not happen due to __post_init__)
        return self.condition(form_data)


class NetworkConfig(ABC):
    """Base class for all network configurations"""
    
    @property
    @abstractmethod
    def network_name(self) -> str:
        """Network identifier (lowercase)"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable network name"""
        pass
    
    @abstractmethod
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields required for app creation"""
        pass
    
    @abstractmethod
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields required for unit creation"""
        pass
    
    @abstractmethod
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        pass
    
    @abstractmethod
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        pass
    
    @abstractmethod
    def build_app_payload(self, form_data: Dict) -> Dict:
        """Build API payload for app creation"""
        pass
    
    @abstractmethod
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit creation"""
        pass
    
    def supports_create_app(self) -> bool:
        """Check if network supports app creation via API"""
        return True
    
    def supports_create_unit(self) -> bool:
        """Check if network supports unit creation via API"""
        return True

