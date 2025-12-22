"""Operation data classes: CleanOperation, FilterOperation, SortOperation. Immutable with unique IDs."""

# Import from parent package config
try:
    from ..config import DEFAULT_MISSING_VALUES
except ImportError:
    # Fallback for direct module execution
    DEFAULT_MISSING_VALUES = ["N/A", "Unknown", "n/a", "unknown", "NA", ""]


class CleanOperation:
    """Remove rows with missing/invalid values in specified columns."""
    
    _next_id = 1
    
    def __init__(self, columns, missing_values=None):
        """Init with columns to check. Uses DEFAULT_MISSING_VALUES if none provided."""
        self.columns = columns
        
        if missing_values is None:
            self.missing_values = DEFAULT_MISSING_VALUES.copy()
        else:
            self.missing_values = missing_values
        
        self.operation_id = CleanOperation._next_id
        CleanOperation._next_id = CleanOperation._next_id + 1
    
    def describe(self):
        """Return human-readable description."""
        columns_str = ", ".join(self.columns)
        return "Clean: Remove rows with missing values in [" + columns_str + "]"


class FilterOperation:
    """Filter rows by column values (text/numeric/date range)."""
    
    _next_id = 1
    
    def __init__(self, column, filter_type, values=None, min_value=None, max_value=None):
        """Init filter. text: use values list. numeric/date: use min_value, max_value."""
        self.column = column
        self.filter_type = filter_type
        self.values = values
        self.min_value = min_value
        self.max_value = max_value
        
        self.operation_id = FilterOperation._next_id
        FilterOperation._next_id = FilterOperation._next_id + 1
    
    def describe(self):
        """Return human-readable description."""
        if self.filter_type == "text":
            if len(self.values) <= 3:
                values_str = ", ".join(str(v) for v in self.values)
            else:
                values_str = str(len(self.values)) + " values"
            return "Filter: " + self.column + " in [" + values_str + "]"
        else:
            return "Filter: " + self.column + " from " + str(self.min_value) + " to " + str(self.max_value)


class SortOperation:
    """Sort rows by column (only one active at a time)."""
    
    def __init__(self, column, ascending=True):
        """Init with column name and direction."""
        self.column = column
        self.ascending = ascending
    
    def describe(self):
        """Return human-readable description."""
        direction = "ascending" if self.ascending else "descending"
        return "Sort: " + self.column + " (" + direction + ")"
