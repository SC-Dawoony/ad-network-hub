"""Common validation utilities"""
from typing import Tuple
import re


def validate_package_name(package_name: str) -> Tuple[bool, str]:
    """Validate Android package name format"""
    if not package_name:
        return False, "Package name is required"
    
    # Basic package name validation (com.example.app)
    pattern = r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'
    if not re.match(pattern, package_name):
        return False, "Invalid package name format (e.g., com.example.app)"
    
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

