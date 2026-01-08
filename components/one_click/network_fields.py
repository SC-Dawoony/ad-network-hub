"""Network-specific required fields rendering for one-click workflow"""
import streamlit as st
from typing import Dict, List, Tuple
from components.one_click.category_matchers import (
    match_ironsource_taxonomy,
    match_fyber_android_category,
    match_fyber_ios_category
)


def render_network_required_fields(network: str, config, fetched_info: Dict, key_prefix: str = "one_click") -> Dict:
    """Render network-specific required fields that can't be fetched from store
    
    Args:
        network: Network identifier
        config: Network configuration object
        fetched_info: Fetched store information
        key_prefix: Prefix for Streamlit widget keys (to avoid duplicates in multi-network mode)
    """
    settings = {}
    
    if network == "ironsource":
        settings = _render_ironsource_fields(config, fetched_info, key_prefix)
    elif network == "mintegral":
        settings = _render_mintegral_fields(key_prefix)
    elif network == "fyber":
        settings = _render_fyber_fields(config, fetched_info, key_prefix)
    elif network == "inmobi":
        settings = _render_inmobi_fields(config, key_prefix)
    elif network == "bigoads":
        settings = _render_bigoads_fields(config, key_prefix)
    elif network == "unity":
        settings = _render_unity_fields(config, key_prefix)
    
    return settings


def _render_ironsource_fields(config, fetched_info: Dict, key_prefix: str = "one_click") -> Dict:
    """Render IronSource required fields"""
    settings = {}
    
    # Taxonomy with auto-matching
    taxonomy_options = config._get_taxonomies()
    taxonomy_labels = [opt[0] for opt in taxonomy_options]
    
    category = fetched_info.get("_ios_category") or fetched_info.get("_android_category")
    default_index = 0
    
    if category:
        matched_taxonomy = match_ironsource_taxonomy(category, taxonomy_options)
        if matched_taxonomy:
            try:
                default_index = taxonomy_labels.index(matched_taxonomy)
                st.info(f"💡 Store category '{category}' → Taxonomy '{matched_taxonomy}' 자동 매칭")
            except ValueError:
                pass
    
    selected_taxonomy = st.selectbox(
        "Taxonomy (Sub-genre)*",
        options=taxonomy_labels,
        index=default_index,
        key=f"{key_prefix}_taxonomy"
    )
    for label, value in taxonomy_options:
        if label == selected_taxonomy:
            settings["taxonomy"] = value
            break
    
    # COPPA
    coppa = st.radio(
        "COPPA*",
        options=[("No", False), ("Yes", True)],
        index=0,
        key=f"{key_prefix}_coppa"
    )
    settings["coppa"] = coppa
    
    return settings


def _render_mintegral_fields(key_prefix: str = "one_click") -> Dict:
    """Render Mintegral required fields"""
    settings = {}
    
    is_live = st.radio(
        "Live in App Store*",
        options=[("No", 0), ("Yes", 1)],
        index=1,
        key=f"{key_prefix}_is_live"
    )
    settings["is_live_in_store"] = is_live
    
    return settings


def _render_fyber_fields(config, fetched_info: Dict, key_prefix: str = "one_click") -> Dict:
    """Render Fyber required fields"""
    settings = {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        android_category_options = config._get_categories("android")
        android_category_labels = [opt[0] for opt in android_category_options]
        
        android_category = fetched_info.get("_android_category")
        android_default_index = 0
        
        if android_category:
            matched_category = match_fyber_android_category(android_category, android_category_options)
            if matched_category:
                try:
                    android_default_index = android_category_labels.index(matched_category)
                    st.info(f"💡 Android category '{android_category}' → '{matched_category}' 자동 매칭")
                except ValueError:
                    pass
        
        selected_android_category = st.selectbox(
            "Android Category1*",
            options=android_category_labels,
            index=android_default_index,
            key=f"{key_prefix}_android_category1"
        )
        for label, value in android_category_options:
            if label == selected_android_category:
                settings["androidCategory1"] = value
                break
    
    with col2:
        ios_category_options = config._get_categories("ios")
        ios_category_labels = [opt[0] for opt in ios_category_options]
        
        ios_category = fetched_info.get("_ios_category")
        android_category = fetched_info.get("_android_category")
        ios_default_index = 0
        
        if ios_category:
            if ios_category.lower() in ["games", "game"] and android_category:
                matched_category = match_fyber_ios_category(ios_category, android_category, ios_category_options)
            else:
                # Use iOS category directly (fallback to simple matching)
                matched_category = match_fyber_android_category(ios_category, ios_category_options)
            
            if matched_category:
                try:
                    ios_default_index = ios_category_labels.index(matched_category)
                    if ios_category.lower() in ["games", "game"] and android_category:
                        st.info(f"💡 iOS: '{ios_category}' + Android: '{android_category}' → '{matched_category}' 자동 매칭")
                    else:
                        st.info(f"💡 iOS category '{ios_category}' → '{matched_category}' 자동 매칭")
                except ValueError:
                    pass
        
        selected_ios_category = st.selectbox(
            "iOS Category1*",
            options=ios_category_labels,
            index=ios_default_index,
            key=f"{key_prefix}_ios_category1"
        )
        for label, value in ios_category_options:
            if label == selected_ios_category:
                settings["iosCategory1"] = value
                break
    
    # COPPA
    coppa = st.radio(
        "COPPA*",
        options=[("No", False), ("Yes", True)],
        index=0,
        key=f"{key_prefix}_coppa"
    )
    settings["coppa"] = coppa
    
    return settings


def _render_inmobi_fields(config, key_prefix: str = "one_click") -> Dict:
    """Render InMobi required fields"""
    settings = {}
    
    child_directed_options = config._get_child_directed_options()
    child_directed_labels = [opt[0] for opt in child_directed_options]
    selected_child_directed = st.selectbox(
        "Child Directed*",
        options=child_directed_labels,
        index=1,  # Default: "Directed towards children (requires parental consent)" = 2
        key=f"{key_prefix}_child_directed"
    )
    for label, value in child_directed_options:
        if label == selected_child_directed:
            settings["childDirected"] = value
            break
    
    location_access = st.radio(
        "Location Access*",
        options=[("Yes", True), ("No", False)],
        index=0,
        key=f"{key_prefix}_location_access"
    )
    settings["locationAccess"] = location_access
    
    return settings


def _render_bigoads_fields(config, key_prefix: str = "one_click") -> Dict:
    """Render BigOAds required fields"""
    settings = {}
    
    # Mediation Platform
    mediation_options = config._get_mediation_platforms()
    mediation_labels = [opt[0] for opt in mediation_options]
    selected_mediation = st.selectbox(
        "Mediation Platform*",
        options=mediation_labels,
        key=f"{key_prefix}_mediation"
    )
    for label, value in mediation_options:
        if label == selected_mediation:
            settings["mediationPlatform"] = value
            break
    
    # Category
    category_options = config._get_categories()
    category_labels = [opt[0] for opt in category_options]
    selected_category = st.selectbox(
        "Category*",
        options=category_labels,
        key=f"{key_prefix}_category"
    )
    for label, value in category_options:
        if label == selected_category:
            settings["category"] = value
            break
    
    # COPPA Option
    coppa_options = [("No", 1), ("Yes", 2)]
    coppa_labels = [opt[0] for opt in coppa_options]
    selected_coppa = st.selectbox(
        "COPPA Option*",
        options=coppa_labels,
        index=0,
        key=f"{key_prefix}_coppa_option"
    )
    for label, value in coppa_options:
        if label == selected_coppa:
            settings["coppaOption"] = value
            break
    
    # Screen Direction
    screen_direction_options = [("Vertical", 0), ("Horizontal", 1)]
    screen_direction_labels = [opt[0] for opt in screen_direction_options]
    selected_screen_direction = st.selectbox(
        "Screen Direction*",
        options=screen_direction_labels,
        index=0,
        key=f"{key_prefix}_screen_direction"
    )
    for label, value in screen_direction_options:
        if label == selected_screen_direction:
            settings["screenDirection"] = value
            break
    
    return settings


def _render_unity_fields(config, key_prefix: str = "one_click") -> Dict:
    """Render Unity required fields"""
    settings = {}
    
    # Ads Provider
    ads_provider_options = config._get_ads_provider_options()
    ads_provider_labels = [opt[0] for opt in ads_provider_options]
    selected_ads_providers = st.multiselect(
        "Ads Provider*",
        options=ads_provider_labels,
        default=["MAX"],
        key=f"{key_prefix}_ads_provider"
    )
    selected_values = []
    for label, value in ads_provider_options:
        if label in selected_ads_providers:
            selected_values.append(value)
    settings["adsProvider"] = selected_values if selected_values else ["max"]
    
    # COPPA Compliance
    coppa_options = config._get_coppa_options()
    coppa_labels = [opt[0] for opt in coppa_options]
    selected_coppa = st.selectbox(
        "COPPA Compliance*",
        options=coppa_labels,
        index=0,
        key=f"{key_prefix}_coppa_unity"
    )
    for label, value in coppa_options:
        if label == selected_coppa:
            settings["coppa"] = value
            break
    
    return settings

