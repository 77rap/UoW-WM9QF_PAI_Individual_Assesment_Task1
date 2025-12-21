"""
Operation Data Classes for Analysis Layer
==========================================

This module defines the data classes that represent analysis operations.
Each operation is immutable after creation and has a unique ID.

Operations:
- CleanOperation: Remove rows with missing values
- FilterOperation: Filter rows by column values
- SortOperation: Sort rows by a column
"""

# Import from parent package config
try:
    from ..config import DEFAULT_MISSING_VALUES
except ImportError:
    # Fallback for direct module execution
    DEFAULT_MISSING_VALUES = ["N/A", "Unknown", "n/a", "unknown", "NA", ""]


class CleanOperation:
    """
    Represents a single clean operation.
    
    A clean operation removes rows where specified columns contain
    missing or invalid values.
    
    Attributes:
        columns (list): Column names to check for missing values
        missing_values (list): Values to treat as missing (in addition to null)
        operation_id (int): Unique identifier for this operation
    """
    
    _next_id = 1
    
    def __init__(self, columns, missing_values=None):
        """
        Initialize a clean operation.
        
        Args:
            columns (list): Column names to check
            missing_values (list, optional): Custom values to treat as missing.
                                            If None, uses DEFAULT_MISSING_VALUES.
        """
        self.columns = columns
        
        if missing_values is None:
            self.missing_values = DEFAULT_MISSING_VALUES.copy()
        else:
            self.missing_values = missing_values
        
        self.operation_id = CleanOperation._next_id
        CleanOperation._next_id = CleanOperation._next_id + 1
    
    def describe(self):
        """Return a human-readable description of this operation."""
        columns_str = ", ".join(self.columns)
        return "Clean: Remove rows with missing values in [" + columns_str + "]"


class FilterOperation:
    """
    Represents a single filter operation.
    
    A filter operation narrows the dataset to rows matching specified criteria.
    The filter type is determined by the column data type.
    
    Attributes:
        column (str): Column name to filter by
        filter_type (str): One of 'text', 'numeric', 'date'
        values (list): For text filters, the allowed values
        min_value: For numeric/date filters, the minimum (inclusive)
        max_value: For numeric/date filters, the maximum (inclusive)
        operation_id (int): Unique identifier for this operation
    """
    
    _next_id = 1
    
    def __init__(self, column, filter_type, values=None, min_value=None, max_value=None):
        """
        Initialize a filter operation.
        
        Args:
            column (str): Column name to filter
            filter_type (str): 'text', 'numeric', or 'date'
            values (list, optional): For text filters, list of allowed values
            min_value (optional): For range filters, minimum value
            max_value (optional): For range filters, maximum value
        """
        self.column = column
        self.filter_type = filter_type
        self.values = values
        self.min_value = min_value
        self.max_value = max_value
        
        self.operation_id = FilterOperation._next_id
        FilterOperation._next_id = FilterOperation._next_id + 1
    
    def describe(self):
        """Return a human-readable description of this operation."""
        if self.filter_type == "text":
            if len(self.values) <= 3:
                values_str = ", ".join(str(v) for v in self.values)
            else:
                values_str = str(len(self.values)) + " values"
            return "Filter: " + self.column + " in [" + values_str + "]"
        else:
            return "Filter: " + self.column + " from " + str(self.min_value) + " to " + str(self.max_value)


class SortOperation:
    """
    Represents a sort operation.
    
    Only one sort operation can be active at a time.
    
    Attributes:
        column (str): Column name to sort by
        ascending (bool): True for ascending, False for descending
    """
    
    def __init__(self, column, ascending=True):
        """
        Initialize a sort operation.
        
        Args:
            column (str): Column name to sort by
            ascending (bool): Sort direction (default True = ascending)
        """
        self.column = column
        self.ascending = ascending
    
    def describe(self):
        """Return a human-readable description of this operation."""
        direction = "ascending" if self.ascending else "descending"
        return "Sort: " + self.column + " (" + direction + ")"
