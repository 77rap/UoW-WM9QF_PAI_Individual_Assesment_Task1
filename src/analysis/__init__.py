"""
Analysis Layer Package for Public Health Data Insights Dashboard
=================================================================

This package provides data analysis capabilities including:
- Non-destructive data cleaning (remove rows with missing values)
- Filtering by column values (text selection, numeric/date ranges)
- Sorting with null handling
- Statistical summaries with optional grouping
- Chart generation with automatic type detection

The core principle is NON-DESTRUCTIVE EDITING: the original data is never
modified. Instead, operations are stored as data objects and applied
on-demand to produce views.

Usage:
    from src.analysis import AnalysisSession
    
    session = AnalysisSession(dataframe, "source_name")
    session.add_clean(["column_name"])
    session.add_filter_text("region", ["Europe"])
    view = session.get_current_view()
"""

from .operations import CleanOperation, FilterOperation, SortOperation
from .utils import (
    detect_column_type,
    get_unique_values_for_filter,
    search_values,
    get_numeric_range,
    get_date_range,
    MAX_DISPLAY_VALUES
)
from .session import AnalysisSession
from . import charts

# Re-export config values used by this package
try:
    from ..config import DEFAULT_MISSING_VALUES, MAX_FILTER_DISPLAY_VALUES
except ImportError:
    DEFAULT_MISSING_VALUES = ["N/A", "Unknown", "n/a", "unknown", "NA", ""]
    MAX_FILTER_DISPLAY_VALUES = 20


__all__ = [
    "AnalysisSession",
    "CleanOperation",
    "FilterOperation",
    "SortOperation",
    "DEFAULT_MISSING_VALUES",
    "MAX_FILTER_DISPLAY_VALUES",
    "detect_column_type",
    "get_unique_values_for_filter",
    "search_values",
    "get_numeric_range",
    "get_date_range",
    "MAX_DISPLAY_VALUES",
    "charts"
]
