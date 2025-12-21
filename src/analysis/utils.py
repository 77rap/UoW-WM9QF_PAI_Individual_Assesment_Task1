"""
Utility Functions for Analysis Layer
=====================================

This module provides helper functions for data type detection,
value extraction, and range calculations used by the analysis session.
"""

import pandas as pd

# Import from parent package config
try:
    from ..config import MAX_FILTER_DISPLAY_VALUES
    MAX_DISPLAY_VALUES = MAX_FILTER_DISPLAY_VALUES
except ImportError:
    # Fallback for direct module execution
    MAX_DISPLAY_VALUES = 20


def detect_column_type(series):
    """
    Detect the data type of a pandas Series for filtering purposes.
    
    This function examines the data to determine if it should be treated
    as text, numeric, or date for filtering purposes.
    
    Args:
        series (pd.Series): The column data to examine
        
    Returns:
        str: One of 'text', 'numeric', or 'date'
    """
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
    """
    Get unique values from a series for text filter selection.
    
    If there are more than max_display unique values, returns only
    the most common ones along with a warning flag.
    
    Args:
        series (pd.Series): The column data
        max_display (int): Maximum number of values to return
        
    Returns:
        tuple: (list of values, total count, bool indicating if truncated)
    """
    value_counts = series.value_counts()
    total_unique = len(value_counts)
    truncated = total_unique > max_display
    
    if truncated:
        display_values = list(value_counts.head(max_display).index)
    else:
        display_values = list(value_counts.index)
    
    return (display_values, total_unique, truncated)


def search_values(series, search_term):
    """
    Search for values in a series that contain the search term.
    
    Used when there are too many unique values to display all at once.
    
    Args:
        series (pd.Series): The column data
        search_term (str): Text to search for (case-insensitive)
        
    Returns:
        list: Values containing the search term
    """
    unique_values = series.dropna().unique()
    search_lower = search_term.lower()
    
    matches = []
    for value in unique_values:
        if search_lower in str(value).lower():
            matches.append(value)
    
    return matches


def get_numeric_range(series):
    """
    Get the minimum and maximum values from a numeric series.
    
    Args:
        series (pd.Series): Numeric column data
        
    Returns:
        tuple: (min_value, max_value)
    """
    numeric_series = pd.to_numeric(series, errors='coerce')
    min_val = numeric_series.min()
    max_val = numeric_series.max()
    return (min_val, max_val)


def get_date_range(series):
    """
    Get the earliest and latest dates from a date series.
    
    Args:
        series (pd.Series): Date column data
        
    Returns:
        tuple: (start_date, end_date)
    """
    date_series = pd.to_datetime(series, errors='coerce')
    start_date = date_series.min()
    end_date = date_series.max()
    return (start_date, end_date)
