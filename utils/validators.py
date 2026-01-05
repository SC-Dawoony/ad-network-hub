"""Common validation utilities"""
from typing import Tuple
import re


def validate_package_name(package_name: str) -> Tuple[bool, str]:
    """Validate package name format (Android/iOS)
    
    Supports both lowercase and mixed case package names:
    - com.example.app (lowercase)
    - com.TornadoBear.DinoKing (mixed case)
    """
    if not package_name:
        return False, "Package name is required"
    
    # Package name validation - allows uppercase letters
    # Format: com.example.app or com.TornadoBear.DinoKing
    # Each segment must start with a letter (a-z, A-Z) and can contain letters, numbers, and underscores
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$'
    if not re.match(pattern, package_name):
        return False, "Invalid package name format (e.g., com.example.app or com.TornadoBear.DinoKing)"
    
    return True, ""


def validate_url(url: str) -> Tuple[bool, str]:
    """Validate URL format"""
    if not url:
        return True, ""  # Optional field
    
    pattern = r'^https?://.+'
    if not re.match(pattern, url):
        return False, "Invalid URL format (must start with http:// or https://)"
    
    return True, ""


def validate_app_name(name: str) -> Tuple[bool, str]:
    """Validate app name"""
    if not name or len(name.strip()) == 0:
        return False, "App name is required"
    
    if len(name) > 100:
        return False, "App name must be less than 100 characters"
    
    return True, ""


def validate_slot_name(name: str) -> Tuple[bool, str]:
    """Validate slot name"""
    if not name or len(name.strip()) == 0:
        return False, "Slot name is required"
    
    if len(name) > 100:
        return False, "Slot name must be less than 100 characters"
    
    return True, ""

