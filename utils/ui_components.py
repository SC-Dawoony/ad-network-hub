"""Reusable UI components for dynamic form rendering"""
from typing import Dict, List, Any, Optional
import streamlit as st
import re
from network_configs.base_config import Field, ConditionalField, NetworkConfig


class DynamicFormRenderer:
    """Render dynamic forms based on network configuration"""
    
    @staticmethod
    def render_field(field: Field, form_data: Dict, key_prefix: str = "", config: Optional[NetworkConfig] = None) -> Any:
        """Render a single field based on its type
        
        Args:
            field: Field definition
            form_data: Current form data dictionary
            key_prefix: Prefix for field key (e.g., "app", "unit")
            config: NetworkConfig instance (for dynamic options like Fyber categories)
        """
        field_key = f"{key_prefix}_{field.name}" if key_prefix else field.name
        
        # Add * to label if field is required
        label = field.label
        if field.required and not label.endswith("*"):
            label = f"{label}*"
        
        # Handle hidden fields (e.g., mediaType that's always 1)
        if field.field_type == "hidden":
            # Return default value without rendering UI
            return field.default
        
        if field.field_type == "text":
            # Get current value from form_data if exists, otherwise use default
            current_value = form_data.get(field.name, field.default if field.default else "")
            
            # Special handling for BigOAds iTunes ID: Check session state first
            # (in case storeUrl was filled after itunesId field was rendered)
            if field.name == "itunesId":
                itunes_id_key = f"app_itunesId"
                if itunes_id_key in st.session_state:
                    session_value = st.session_state[itunes_id_key]
                    if session_value and (not current_value or current_value == ""):
                        current_value = session_value
                        form_data[field.name] = current_value
                # Also check storeUrl in form_data (if storeUrl was rendered before itunesId)
                elif not current_value:
                    store_url = form_data.get("storeUrl", "")
                    if store_url and "apps.apple.com" in store_url:
                        match = re.search(r'/id(\d+)', store_url)
                        if match:
                            current_value = match.group(1)
                            form_data[field.name] = current_value
                            st.session_state[itunes_id_key] = current_value
            
            return st.text_input(
                label,
                value=str(current_value) if current_value is not None else "",
                help=field.help_text,
                placeholder=field.placeholder,
                key=field_key
            )
        
        elif field.field_type == "number":
            # Ensure all numeric values are the same type (int or float)
            min_val = field.min_value
            max_val = field.max_value
            default_val = field.default if field.default is not None else (min_val if min_val is not None else 0)
            
            # Determine if we should use int or float
            use_float = (
                isinstance(min_val, float) or 
                isinstance(max_val, float) or 
                isinstance(default_val, float) or
                (min_val is not None and min_val != int(min_val)) or
                (max_val is not None and max_val != int(max_val)) or
                (default_val != int(default_val))
            )
            
            if use_float:
                # Convert all to float
                min_val = float(min_val) if min_val is not None else None
                max_val = float(max_val) if max_val is not None else None
                default_val = float(default_val)
            else:
                # Convert all to int
                min_val = int(min_val) if min_val is not None else None
                max_val = int(max_val) if max_val is not None else None
                default_val = int(default_val)
            
            # itunesId is always enabled (validation will check if it's required for iOS)
            # No need to disable it based on platform selection
            
            return st.number_input(
                label,
                min_value=min_val,
                max_value=max_val,
                value=default_val,
                help=field.help_text,
                placeholder=field.placeholder,
                key=field_key
            )
        
        elif field.field_type == "radio":
            options = [opt[0] for opt in field.options] if field.options else []
            # Use current form_data value if exists, otherwise use default
            current_value = form_data.get(field.name, field.default)
            selected_index = 0
            if current_value is not None:
                # Find index of current value
                for idx, (opt_label, opt_value) in enumerate(field.options or []):
                    if opt_value == current_value:
                        selected_index = idx
                        break
            elif field.default is not None:
                # Fallback to default if no current value
                for idx, (opt_label, opt_value) in enumerate(field.options or []):
                    if opt_value == field.default:
                        selected_index = idx
                        break
            
            selected_label = st.radio(
                label,
                options=options,
                index=selected_index,
                help=field.help_text,
                key=field_key
            )
            # Return the value corresponding to the selected label
            for opt_label, opt_value in field.options or []:
                if opt_label == selected_label:
                    # Debug: Log radio selection
                    # print(f"DEBUG: Radio field '{field.name}' selected: label='{selected_label}', value={opt_value}")
                    return opt_value
            # If no match found, return None (should not happen)
            return None
        
        elif field.field_type == "dropdown":
            # Special handling for Fyber category1 and category2: Update options based on platform
            options = field.options or []
            if (field.name in ["category1", "category2"] and 
                hasattr(config, 'network_name') and config.network_name == "fyber" and
                hasattr(config, '_get_categories')):
                # Get current platform selection
                platform = form_data.get("platform", "android")
                # Get platform-specific categories
                options = config._get_categories(platform)
            
            option_labels = [opt[0] for opt in options]
            # Use current form_data value if exists, otherwise use default
            current_value = form_data.get(field.name, field.default)
            default_index = 0
            if current_value is not None:
                # Find index of current value in updated options
                for idx, (opt_label, opt_value) in enumerate(options):
                    if opt_value == current_value:
                        default_index = idx
                        break
                # If current value not found in new options (platform changed), reset to default
                if default_index == 0 and current_value not in [opt[1] for opt in options]:
                    current_value = None
            elif field.default is not None:
                # Fallback to default if no current value
                for idx, (opt_label, opt_value) in enumerate(options):
                    if opt_value == field.default:
                        default_index = idx
                        break
            
            selected_label = st.selectbox(
                label,
                options=option_labels,
                index=default_index,
                help=field.help_text,
                key=field_key
            )
            # Return the value corresponding to the selected label
            for opt_label, opt_value in options:
                if opt_label == selected_label:
                    return opt_value
            return None
        
        elif field.field_type == "multiselect":
            options = field.options or []
            option_labels = [opt[0] for opt in options]
            # Use current form_data value if exists, otherwise use default
            current_values = form_data.get(field.name, field.default)
            default_labels = []
            if current_values:
                for opt_label, opt_value in options:
                    if opt_value in current_values:
                        default_labels.append(opt_label)
            elif field.default:
                for opt_label, opt_value in options:
                    if opt_value in field.default:
                        default_labels.append(opt_label)
            
            selected_labels = st.multiselect(
                label,
                options=option_labels,
                default=default_labels,
                help=field.help_text,
                key=field_key
            )
            # Return values corresponding to selected labels
            selected_values = []
            for opt_label, opt_value in options:
                if opt_label in selected_labels:
                    selected_values.append(opt_value)
            return selected_values
        
        else:
            st.warning(f"Unknown field type: {field.field_type}")
            return None
    
    @staticmethod
    def render_form(config: NetworkConfig, form_type: str, existing_data: Optional[Dict] = None) -> Dict:
        """Render a complete form based on network configuration"""
        if existing_data is None:
            existing_data = {}
        
        if form_type == "app":
            fields = config.get_app_creation_fields()
        elif form_type == "unit":
            fields = config.get_unit_creation_fields()
        else:
            st.error(f"Unknown form type: {form_type}")
            return {}
        
        form_data = existing_data.copy()
        
        # Render fields in order, handling conditional fields at their correct position
        for field in fields:
            # Handle hidden fields (e.g., mediaType)
            if field.field_type == "hidden":
                form_data[field.name] = field.default
                continue
            
            # Handle conditional fields
            if isinstance(field, ConditionalField):
                if field.should_show(form_data):
                    # Render conditional field at its correct position in the form
                    rendered_value = DynamicFormRenderer.render_field(field, form_data, form_type, config=config)
                    if rendered_value is not None:
                        form_data[field.name] = rendered_value
                else:
                    # Clear conditional field if condition is not met
                    form_data.pop(field.name, None)
            else:
                # Render regular field
                rendered_value = DynamicFormRenderer.render_field(field, form_data, form_type, config=config)
                if rendered_value is not None:
                    form_data[field.name] = rendered_value
                
                # Special handling for BigOAds: Auto-extract iTunes ID from Store URL
                # Note: storeUrl is rendered after itunesId, so we update form_data
                # and session_state for the next rerun
                if (form_type == "app" and 
                    field.name == "storeUrl" and 
                    config.network_name == "bigoads" and
                    rendered_value):
                    store_url = str(rendered_value).strip()
                    if store_url and "apps.apple.com" in store_url:
                        # Extract iTunes ID from URL pattern: .../id{number} or .../id{number}?
                        match = re.search(r'/id(\d+)', store_url)
                        if match:
                            itunes_id = match.group(1)
                            # Update form_data for current form processing
                            form_data["itunesId"] = itunes_id
                            # Update session state key for itunesId field
                            itunes_id_key = f"app_itunesId"
                            st.session_state[itunes_id_key] = itunes_id
        
        return form_data
    
    @staticmethod
    def render_form_with_sections(config: NetworkConfig, form_type: str) -> Dict:
        """Render form with common and network-specific sections"""
        form_data = {}
        
        if form_type == "app":
            fields = config.get_app_creation_fields()
            
            # Common fields section
            st.subheader("Common Fields")
            common_field_names = ["name", "pkgName", "platform", "storeUrl"]
            common_fields = [f for f in fields if f.name in common_field_names]
            other_fields = [f for f in fields if f.name not in common_field_names]
            
            for field in common_fields:
                if isinstance(field, ConditionalField):
                    if field.should_show(form_data):
                        form_data[field.name] = DynamicFormRenderer.render_field(field, form_data, form_type, config=config)
                else:
                    form_data[field.name] = DynamicFormRenderer.render_field(field, form_data, form_type, config=config)
            
            # Network-specific fields section
            st.subheader("Network-Specific Fields")
            for field in other_fields:
                if isinstance(field, ConditionalField):
                    if field.should_show(form_data):
                        form_data[field.name] = DynamicFormRenderer.render_field(field, form_data, form_type, config=config)
                else:
                    form_data[field.name] = DynamicFormRenderer.render_field(field, form_data, form_type, config=config)
        
        else:
            # For unit creation, render all fields
            form_data = DynamicFormRenderer.render_form(config, form_type)
        
        return form_data

