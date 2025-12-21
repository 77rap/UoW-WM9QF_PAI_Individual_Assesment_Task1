"""
Analysis Session for Data Analysis
====================================

This module provides the AnalysisSession class which manages non-destructive
data transformations including cleaning, filtering, and sorting.

The core principle is NON-DESTRUCTIVE EDITING: the original data is never
modified. Instead, operations are stored and applied on-demand to produce views.

Operations are applied in a fixed sequence:
1. Clean operations (data quality first)
2. Filter operations (narrow to area of interest)
3. Sort operation (affects display order only)
"""

import pandas as pd

from .operations import CleanOperation, FilterOperation, SortOperation
from .utils import (
    detect_column_type,
    get_unique_values_for_filter,
    search_values,
    get_numeric_range,
    get_date_range
)
from . import charts


class AnalysisSession:
    """
    Main class for managing data analysis operations.
    
    The session maintains:
    - A reference to the original (immutable) data
    - Lists of active operations (clean, filter)
    - The current sort operation (if any)
    - The most recently generated chart (for export)
    
    Operations are applied in sequence: clean -> filter -> sort
    The original data is never modified.
    """
    
    def __init__(self, dataframe, source_name="Unknown"):
        """
        Initialize an analysis session with data.
        
        Args:
            dataframe (pd.DataFrame): The data to analyse
            source_name (str): Name of the data source (for display)
        """
        self._original_data = dataframe.copy()
        self.source_name = source_name
        self._clean_operations = []
        self._filter_operations = []
        self._sort_operation = None
        self._current_figure = None
    
    def get_original_data(self):
        """
        Get the original, unmodified data.
        
        Returns:
            pd.DataFrame: Copy of the original data
        """
        return self._original_data.copy()
    
    def get_current_view(self):
        """
        Get the current view with all operations applied.
        
        Operations are applied in order: clean -> filter -> sort
        
        Returns:
            pd.DataFrame: The transformed data
        """
        data = self._original_data.copy()
        
        for clean_op in self._clean_operations:
            data = self._apply_clean(data, clean_op)
        
        for filter_op in self._filter_operations:
            data = self._apply_filter(data, filter_op)
        
        if self._sort_operation is not None:
            data = self._apply_sort(data, self._sort_operation)
        
        return data
    
    def get_columns(self):
        """
        Get list of column names in the data.
        
        Returns:
            list: Column names
        """
        return list(self._original_data.columns)
    
    def get_column_type(self, column):
        """
        Get the detected type of a column.
        
        Args:
            column (str): Column name
            
        Returns:
            str: 'text', 'numeric', or 'date'
        """
        if column not in self._original_data.columns:
            raise ValueError("Column not found: " + column)
        
        return detect_column_type(self._original_data[column])
    
    def get_row_count(self):
        """
        Get the number of rows in the current view.
        
        Returns:
            int: Number of rows after all operations applied
        """
        return len(self.get_current_view())
    
    def get_original_row_count(self):
        """
        Get the number of rows in the original data.
        
        Returns:
            int: Original number of rows
        """
        return len(self._original_data)

    def add_clean(self, columns, missing_values=None):
        """
        Add a clean operation to remove rows with missing values.
        
        Args:
            columns (list): Column names to check for missing values
            missing_values (list, optional): Additional values to treat as missing
            
        Returns:
            int: The operation ID of the new clean operation
        """
        for col in columns:
            if col not in self._original_data.columns:
                raise ValueError("Column not found: " + col)
        
        operation = CleanOperation(columns, missing_values)
        self._clean_operations.append(operation)
        
        return operation.operation_id
    
    def remove_clean(self, operation_id):
        """
        Remove a clean operation by its ID.
        
        Args:
            operation_id (int): The ID of the operation to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        for i in range(len(self._clean_operations)):
            if self._clean_operations[i].operation_id == operation_id:
                self._clean_operations.pop(i)
                return True
        return False
    
    def list_clean_operations(self):
        """
        List all active clean operations.
        
        Returns:
            list: List of tuples (operation_id, description)
        """
        result = []
        for op in self._clean_operations:
            result.append((op.operation_id, op.describe()))
        return result
    
    def _apply_clean(self, data, clean_op):
        """
        Apply a clean operation to data.
        
        Removes rows where ANY of the specified columns contains
        a missing or invalid value.
        
        Args:
            data (pd.DataFrame): Data to clean
            clean_op (CleanOperation): The operation to apply
            
        Returns:
            pd.DataFrame: Cleaned data
        """
        if len(data) == 0:
            return data
        
        keep_mask = pd.Series([True] * len(data), index=data.index)
        
        for col in clean_op.columns:
            if col not in data.columns:
                continue
            
            column_data = data[col]
            is_null = column_data.isna()
            is_missing_value = column_data.isin(clean_op.missing_values)
            is_empty_string = column_data.apply(
                lambda x: str(x).strip() == "" if pd.notna(x) else False
            )
            should_remove = is_null | is_missing_value | is_empty_string
            keep_mask = keep_mask & (~should_remove)
        
        return data[keep_mask]

    def get_filter_options(self, column):
        """
        Get filter options for a column based on its type.
        
        This method helps the UI determine what filter interface to show.
        
        Args:
            column (str): Column name to get options for
            
        Returns:
            dict: Filter information including type and available options
        """
        if column not in self._original_data.columns:
            raise ValueError("Column not found: " + column)
        
        current_data = self.get_current_view()
        
        if len(current_data) == 0:
            return {
                "column": column,
                "type": "empty",
                "message": "No data available to filter"
            }
        
        column_data = current_data[column]
        col_type = detect_column_type(column_data)
        
        if col_type == "text":
            values, total, truncated = get_unique_values_for_filter(column_data)
            return {
                "column": column,
                "type": "text",
                "values": values,
                "total_unique": total,
                "truncated": truncated,
                "message": "Showing " + str(len(values)) + " of " + str(total) + " unique values" if truncated else None
            }
        
        elif col_type == "numeric":
            min_val, max_val = get_numeric_range(column_data)
            return {
                "column": column,
                "type": "numeric",
                "min": min_val,
                "max": max_val
            }
        
        elif col_type == "date":
            start_date, end_date = get_date_range(column_data)
            return {
                "column": column,
                "type": "date",
                "start": start_date,
                "end": end_date
            }
        
        return {"column": column, "type": "unknown"}
    
    def search_filter_values(self, column, search_term):
        """
        Search for filter values in a text column.
        
        Used when there are too many unique values to display all.
        
        Args:
            column (str): Column name
            search_term (str): Text to search for
            
        Returns:
            list: Matching values
        """
        current_data = self.get_current_view()
        return search_values(current_data[column], search_term)
    
    def add_filter_text(self, column, values):
        """
        Add a text filter to include only rows with specified values.
        
        Args:
            column (str): Column name to filter
            values (list): List of values to include
            
        Returns:
            int: The operation ID of the new filter
        """
        if column not in self._original_data.columns:
            raise ValueError("Column not found: " + column)
        
        if len(values) == 0:
            raise ValueError("At least one value must be selected")
        
        operation = FilterOperation(column, "text", values=values)
        self._filter_operations.append(operation)
        
        return operation.operation_id
    
    def add_filter_numeric(self, column, min_value, max_value):
        """
        Add a numeric range filter.
        
        Args:
            column (str): Column name to filter
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            
        Returns:
            int: The operation ID of the new filter
            
        Raises:
            ValueError: If column not found, min > max, or values out of data range
        """
        if column not in self._original_data.columns:
            raise ValueError("Column not found: " + column)
        
        if min_value > max_value:
            raise ValueError("Minimum value cannot be greater than maximum value")
        
        # Get actual data range for boundary validation
        col_data = pd.to_numeric(self._original_data[column], errors="coerce")
        data_min = col_data.min()
        data_max = col_data.max()
        
        # Validate that filter range overlaps with data range
        if min_value > data_max:
            raise ValueError(
                "Minimum value (" + str(min_value) + ") is greater than the maximum value in the data (" + 
                str(data_max) + "). No rows would match this filter."
            )
        
        if max_value < data_min:
            raise ValueError(
                "Maximum value (" + str(max_value) + ") is less than the minimum value in the data (" + 
                str(data_min) + "). No rows would match this filter."
            )
        
        operation = FilterOperation(column, "numeric", min_value=min_value, max_value=max_value)
        self._filter_operations.append(operation)
        
        return operation.operation_id
    
    def add_filter_date(self, column, start_date, end_date):
        """
        Add a date range filter.
        
        Args:
            column (str): Column name to filter
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            int: The operation ID of the new filter
            
        Raises:
            ValueError: If column not found, start > end, or dates out of data range
        """
        if column not in self._original_data.columns:
            raise ValueError("Column not found: " + column)
        
        if not isinstance(start_date, pd.Timestamp):
            start_date = pd.to_datetime(start_date)
        if not isinstance(end_date, pd.Timestamp):
            end_date = pd.to_datetime(end_date)
        
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        # Get actual data range for boundary validation
        col_data = pd.to_datetime(self._original_data[column], errors="coerce")
        data_min = col_data.min()
        data_max = col_data.max()
        
        # Validate that filter range overlaps with data range
        if pd.notna(data_max) and start_date > data_max:
            raise ValueError(
                "Start date (" + str(start_date.date()) + ") is after the latest date in the data (" + 
                str(data_max.date()) + "). No rows would match this filter."
            )
        
        if pd.notna(data_min) and end_date < data_min:
            raise ValueError(
                "End date (" + str(end_date.date()) + ") is before the earliest date in the data (" + 
                str(data_min.date()) + "). No rows would match this filter."
            )
        
        operation = FilterOperation(column, "date", min_value=start_date, max_value=end_date)
        self._filter_operations.append(operation)
        
        return operation.operation_id
    
    def remove_filter(self, operation_id):
        """
        Remove a filter operation by its ID.
        
        Args:
            operation_id (int): The ID of the filter to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        for i in range(len(self._filter_operations)):
            if self._filter_operations[i].operation_id == operation_id:
                self._filter_operations.pop(i)
                return True
        return False
    
    def list_filter_operations(self):
        """
        List all active filter operations.
        
        Returns:
            list: List of tuples (operation_id, description)
        """
        result = []
        for op in self._filter_operations:
            result.append((op.operation_id, op.describe()))
        return result
    
    def _apply_filter(self, data, filter_op):
        """
        Apply a filter operation to data.
        
        Args:
            data (pd.DataFrame): Data to filter
            filter_op (FilterOperation): The operation to apply
            
        Returns:
            pd.DataFrame: Filtered data
        """
        if len(data) == 0:
            return data
        
        if filter_op.column not in data.columns:
            return data
        
        column_data = data[filter_op.column]
        
        if filter_op.filter_type == "text":
            mask = column_data.isin(filter_op.values)
            return data[mask]
        
        elif filter_op.filter_type == "numeric":
            numeric_data = pd.to_numeric(column_data, errors='coerce')
            mask = (numeric_data >= filter_op.min_value) & (numeric_data <= filter_op.max_value)
            return data[mask]
        
        elif filter_op.filter_type == "date":
            date_data = pd.to_datetime(column_data, errors='coerce')
            mask = (date_data >= filter_op.min_value) & (date_data <= filter_op.max_value)
            return data[mask]
        
        return data

    def set_sort(self, column, ascending=True):
        """
        Set the sort operation (replaces any existing sort).
        
        Args:
            column (str): Column name to sort by
            ascending (bool): True for ascending, False for descending
        """
        if column not in self._original_data.columns:
            raise ValueError("Column not found: " + column)
        
        self._sort_operation = SortOperation(column, ascending)
    
    def clear_sort(self):
        """Clear the current sort operation."""
        self._sort_operation = None
    
    def get_sort_operation(self):
        """
        Get the current sort operation.
        
        Returns:
            tuple or None: (column, ascending) or None if no sort active
        """
        if self._sort_operation is None:
            return None
        return (self._sort_operation.column, self._sort_operation.ascending)
    
    def _apply_sort(self, data, sort_op):
        """
        Apply a sort operation to data.
        
        Null values are placed at the BEGINNING regardless of sort direction.
        
        Args:
            data (pd.DataFrame): Data to sort
            sort_op (SortOperation): The operation to apply
            
        Returns:
            pd.DataFrame: Sorted data
        """
        if len(data) == 0:
            return data
        
        if sort_op.column not in data.columns:
            return data
        
        column_data = data[sort_op.column]
        col_type = detect_column_type(column_data)
        
        sorted_data = data.copy()
        
        if col_type == "numeric":
            sorted_data["_sort_key"] = pd.to_numeric(sorted_data[sort_op.column], errors='coerce')
        elif col_type == "date":
            sorted_data["_sort_key"] = pd.to_datetime(sorted_data[sort_op.column], errors='coerce')
        else:
            sorted_data["_sort_key"] = sorted_data[sort_op.column].astype(str).str.lower()
        
        null_mask = sorted_data["_sort_key"].isna()
        null_rows = sorted_data[null_mask]
        non_null_rows = sorted_data[~null_mask]
        
        non_null_sorted = non_null_rows.sort_values(
            by="_sort_key",
            ascending=sort_op.ascending
        )
        
        result = pd.concat([null_rows, non_null_sorted], ignore_index=True)
        result = result.drop(columns=["_sort_key"])
        
        return result

    def list_all_operations(self):
        """
        List all active operations.
        
        Returns:
            dict: Dictionary with 'clean', 'filter', and 'sort' keys
        """
        result = {
            "clean": self.list_clean_operations(),
            "filter": self.list_filter_operations(),
            "sort": None
        }
        
        if self._sort_operation is not None:
            result["sort"] = self._sort_operation.describe()
        
        return result
    
    def clear_all_operations(self):
        """Remove all operations and return to original data."""
        self._clean_operations = []
        self._filter_operations = []
        self._sort_operation = None
    
    def has_empty_result(self):
        """
        Check if current operations produce empty results.
        
        Returns:
            bool: True if current view has no rows
        """
        return len(self.get_current_view()) == 0

    def get_summary(self, column, group_by=None):
        """
        Calculate summary statistics for a column (numeric or text).
        
        Args:
            column (str): Column to summarise
            group_by (str, optional): Column to group results by
            
        Returns:
            dict or pd.DataFrame: Summary statistics
        """
        data = self.get_current_view()
        
        if len(data) == 0:
            return {"error": "No data available for summary"}
        
        if column not in data.columns:
            raise ValueError("Column not found: " + column)
        
        col_type = detect_column_type(data[column])
        
        if group_by is None:
            if col_type == "numeric":
                numeric_data = pd.to_numeric(data[column], errors='coerce')
                return self._calculate_numeric_stats(numeric_data, column)
            else:
                return self._calculate_text_stats(data[column], column)
        else:
            if group_by not in data.columns:
                raise ValueError("Group by column not found: " + group_by)
            
            grouped_results = []
            
            for group_value in data[group_by].unique():
                group_mask = data[group_by] == group_value
                group_data = data[column][group_mask]
                
                if col_type == "numeric":
                    numeric_data = pd.to_numeric(group_data, errors='coerce')
                    stats = self._calculate_numeric_stats(numeric_data, column)
                else:
                    stats = self._calculate_text_stats(group_data, column)
                stats["group"] = group_value
                grouped_results.append(stats)
            
            return pd.DataFrame(grouped_results)
    
    def _calculate_numeric_stats(self, numeric_series, column_name):
        """
        Calculate statistics for a numeric series.
        
        Args:
            numeric_series (pd.Series): Numeric data
            column_name (str): Name of the column (for display)
            
        Returns:
            dict: Statistics dictionary
        """
        non_null = numeric_series.dropna()
        
        stats = {
            "column": column_name,
            "count": len(non_null),
            "missing": numeric_series.isna().sum(),
            "min": non_null.min() if len(non_null) > 0 else None,
            "max": non_null.max() if len(non_null) > 0 else None,
            "mean": non_null.mean() if len(non_null) > 0 else None,
            "median": non_null.median() if len(non_null) > 0 else None,
            "std": non_null.std() if len(non_null) > 1 else None
        }
        
        return stats
    
    def _calculate_text_stats(self, text_series, column_name):
        """
        Calculate statistics for a text/categorical series.
        
        Args:
            text_series (pd.Series): Text data
            column_name (str): Name of the column (for display)
            
        Returns:
            dict: Statistics dictionary with text-specific metrics
        """
        non_null = text_series.dropna()
        
        # Get value counts
        value_counts = non_null.value_counts()
        
        # Mode (most frequent value)
        mode_value = value_counts.index[0] if len(value_counts) > 0 else None
        mode_frequency = value_counts.iloc[0] if len(value_counts) > 0 else 0
        
        # Least frequent value
        least_frequent_value = value_counts.index[-1] if len(value_counts) > 0 else None
        least_frequency = value_counts.iloc[-1] if len(value_counts) > 0 else 0
        
        stats = {
            "column": column_name,
            "count": len(non_null),
            "missing": text_series.isna().sum(),
            "unique_count": non_null.nunique(),
            "mode": mode_value,
            "mode_frequency": mode_frequency,
            "least_frequent": least_frequent_value,
            "least_frequency": least_frequency,
        }
        
        # Add top 5 values if there are multiple unique values
        if len(value_counts) > 1:
            top_values = []
            for i in range(min(5, len(value_counts))):
                top_values.append(str(value_counts.index[i]) + " (" + str(value_counts.iloc[i]) + ")")
            stats["top_5_values"] = ", ".join(top_values)
        
        return stats
    
    def get_numeric_columns(self):
        """
        Get list of numeric columns (for summary/graphing).
        
        Returns:
            list: Names of numeric columns
        """
        result = []
        for col in self._original_data.columns:
            if detect_column_type(self._original_data[col]) == "numeric":
                result.append(col)
        return result
    
    def get_text_columns(self):
        """
        Get list of text/categorical columns.
        
        Returns:
            list: Names of text columns
        """
        result = []
        for col in self._original_data.columns:
            if detect_column_type(self._original_data[col]) == "text":
                result.append(col)
        return result

    def generate_chart(self, x_column, y_column, group_by=None, aggregation="sum", show=True):
        """
        Generate a chart from the current view.
        
        Args:
            x_column (str): Column for x-axis
            y_column (str): Column for y-axis (must be numeric)
            group_by (str, optional): Column to create multiple series
            aggregation (str): How to aggregate y values - 'sum', 'mean', or 'count'
            show (bool): Whether to display the chart immediately
            
        Returns:
            matplotlib.figure.Figure: The generated chart figure
        """
        data = self.get_current_view()
        self._current_figure = charts.generate_chart(
            data, x_column, y_column, group_by, aggregation, show
        )
        return self._current_figure
    
    def generate_multi_line_chart(self, x_column, y_columns, aggregation="sum", show=True):
        """
        Generate a multi-line chart with multiple Y columns.
        
        Args:
            x_column (str): Column for x-axis
            y_columns (list): List of column names for y-axis (all must be numeric)
            aggregation (str): How to aggregate y values - 'sum', 'mean', or 'count'
            show (bool): Whether to display the chart immediately
            
        Returns:
            matplotlib.figure.Figure: The generated chart figure
        """
        data = self.get_current_view()
        self._current_figure = charts.generate_multi_line_chart(
            data, x_column, y_columns, aggregation, show
        )
        return self._current_figure
    
    def export_chart(self, filepath):
        """
        Export the most recently generated chart to a file.
        
        Args:
            filepath (str): Path to save the chart (e.g., 'chart.png')
            
        Returns:
            bool: True if exported successfully
        """
        return charts.export_chart(self._current_figure, filepath)
