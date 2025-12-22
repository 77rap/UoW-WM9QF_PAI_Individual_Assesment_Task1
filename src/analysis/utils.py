"""Utility functions for data type detection, value extraction, and range calculations."""

import pandas as pd

# Import from parent package config
try:
    from ..config import MAX_FILTER_DISPLAY_VALUES
    MAX_DISPLAY_VALUES = MAX_FILTER_DISPLAY_VALUES
except ImportError:
    # Fallback for direct module execution
    MAX_DISPLAY_VALUES = 20


def detect_column_type(series):
    """Detect column type for filtering: returns 'text', 'numeric', or 'date'."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    
    non_null = series.dropna()
    if len(non_null) > 0:
        try:
            numeric_converted = pd.to_numeric(non_null, errors='raise')
            return "numeric"
        except (ValueError, TypeError):
            pass
        
        try:
            date_converted = pd.to_datetime(non_null, errors='raise')
            return "date"
        except (ValueError, TypeError):
            pass
    
    return "text"


def get_unique_values_for_filter(series, max_display=MAX_DISPLAY_VALUES):
    """Get unique values for text filter. Returns (values, total_count, truncated)."""
    value_counts = series.value_counts()
    total_unique = len(value_counts)
    truncated = total_unique > max_display
    
    if truncated:
        display_values = list(value_counts.head(max_display).index)
    else:
        display_values = list(value_counts.index)
    
    return (display_values, total_unique, truncated)


def search_values(series, search_term):
    """Search for values containing search_term (case-insensitive)."""
    unique_values = series.dropna().unique()
    search_lower = search_term.lower()
    
    matches = []
    for value in unique_values:
        if search_lower in str(value).lower():
            matches.append(value)
    
    return matches


def get_numeric_range(series):
    """Return (min_value, max_value) for numeric series."""
    numeric_series = pd.to_numeric(series, errors='coerce')
    min_val = numeric_series.min()
    max_val = numeric_series.max()
    return (min_val, max_val)


def get_date_range(series):
    """Return (start_date, end_date) for date series."""
    date_series = pd.to_datetime(series, errors='coerce')
    start_date = date_series.min()
    end_date = date_series.max()
    return (start_date, end_date)
