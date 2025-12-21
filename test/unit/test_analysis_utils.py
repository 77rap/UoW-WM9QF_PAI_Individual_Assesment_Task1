"""
Unit tests for analysis utility functions.

Tests for detect_column_type, get_unique_values_for_filter, search_values,
get_numeric_range, and get_date_range with edge cases and boundary conditions.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime

from src.analysis.utils import (
    detect_column_type,
    get_unique_values_for_filter,
    search_values,
    get_numeric_range,
    get_date_range
)


class TestDetectColumnType(unittest.TestCase):
    """Test suite for detect_column_type function."""
    
    # Numeric detection
    def test_detect_integer_column(self):
        """Test detection of integer column."""
        series = pd.Series([1, 2, 3, 4, 5])
        self.assertEqual(detect_column_type(series), "numeric")
    
    def test_detect_float_column(self):
        """Test detection of float column."""
        series = pd.Series([81.2, 82.3, 79.5, 84.1])
        self.assertEqual(detect_column_type(series), "numeric")
    
    def test_detect_numeric_strings(self):
        """Test detection of numeric values stored as strings."""
        series = pd.Series(["81.2", "82.3", "79.5"])
        self.assertEqual(detect_column_type(series), "numeric")
    
    def test_detect_integer_strings(self):
        """Test detection of integer values stored as strings."""
        series = pd.Series(["2018", "2019", "2020", "2021"])
        self.assertEqual(detect_column_type(series), "numeric")
    
    def test_detect_mixed_int_float(self):
        """Test detection with mixed integers and floats."""
        series = pd.Series([1, 2.5, 3, 4.7])
        self.assertEqual(detect_column_type(series), "numeric")
    
    def test_numeric_with_null(self):
        """Test numeric detection with null values."""
        series = pd.Series([1, 2, None, 4, 5])
        self.assertEqual(detect_column_type(series), "numeric")
    
    # Date detection
    def test_detect_datetime_column(self):
        """Test detection of datetime column."""
        series = pd.Series(pd.date_range("2020-01-01", periods=5))
        self.assertEqual(detect_column_type(series), "date")
    
    def test_detect_date_strings_iso(self):
        """Test detection of ISO date strings."""
        series = pd.Series(["2020-01-01", "2020-02-01", "2020-03-01"])
        self.assertEqual(detect_column_type(series), "date")
    
    def test_date_with_null(self):
        """Test date detection with null values."""
        series = pd.Series(["2020-01-01", None, "2020-03-01"])
        self.assertEqual(detect_column_type(series), "date")
    
    # Text detection
    def test_detect_text_column(self):
        """Test detection of pure text column."""
        series = pd.Series(["GBR", "FRA", "DEU", "USA"])
        self.assertEqual(detect_column_type(series), "text")
    
    def test_detect_mixed_text_numbers(self):
        """Test detection of mixed text and numbers as text."""
        series = pd.Series(["Code123", "ABC456", "XYZ789"])
        self.assertEqual(detect_column_type(series), "text")
    
    def test_detect_text_with_null(self):
        """Test text detection with null values."""
        series = pd.Series(["GBR", None, "DEU"])
        self.assertEqual(detect_column_type(series), "text")
    
    # Edge cases
    def test_empty_series(self):
        """Test with empty series."""
        series = pd.Series([], dtype=object)
        result = detect_column_type(series)
        self.assertEqual(result, "text")
    
    def test_all_null_series(self):
        """Test with all null values."""
        series = pd.Series([None, None, None])
        result = detect_column_type(series)
        self.assertEqual(result, "text")
    
    def test_single_value_numeric(self):
        """Test single numeric value."""
        series = pd.Series([42])
        self.assertEqual(detect_column_type(series), "numeric")
    
    def test_single_value_text(self):
        """Test single text value."""
        series = pd.Series(["hello"])
        self.assertEqual(detect_column_type(series), "text")


class TestGetUniqueValuesForFilter(unittest.TestCase):
    """Test suite for get_unique_values_for_filter function."""
    
    def test_basic_unique_values(self):
        """Test getting unique values from simple series."""
        series = pd.Series(["GBR", "FRA", "DEU", "GBR", "FRA"])
        values, total, truncated = get_unique_values_for_filter(series)
        
        self.assertEqual(total, 3)
        self.assertFalse(truncated)
        self.assertIn("GBR", values)
        self.assertIn("FRA", values)
        self.assertIn("DEU", values)
    
    def test_values_ordered_by_frequency(self):
        """Test that values are returned in order of frequency."""
        series = pd.Series(["A", "B", "B", "B", "C", "C"])
        values, total, truncated = get_unique_values_for_filter(series)
        
        self.assertEqual(values[0], "B")  # Most common
        self.assertEqual(values[1], "C")  # Second most common
    
    def test_truncation_when_many_values(self):
        """Test that values are truncated when exceeding max."""
        # Create series with many unique values
        series = pd.Series(["val_" + str(i) for i in range(50)])
        values, total, truncated = get_unique_values_for_filter(series, max_display=20)
        
        self.assertEqual(len(values), 20)
        self.assertEqual(total, 50)
        self.assertTrue(truncated)
    
    def test_no_truncation_at_boundary(self):
        """Test no truncation when values equal max."""
        series = pd.Series(["val_" + str(i) for i in range(20)])
        values, total, truncated = get_unique_values_for_filter(series, max_display=20)
        
        self.assertEqual(len(values), 20)
        self.assertFalse(truncated)
    
    def test_custom_max_display(self):
        """Test with custom max_display parameter."""
        series = pd.Series(["val_" + str(i) for i in range(10)])
        values, total, truncated = get_unique_values_for_filter(series, max_display=5)
        
        self.assertEqual(len(values), 5)
        self.assertTrue(truncated)
    
    def test_with_null_values(self):
        """Test that null values are handled."""
        series = pd.Series(["A", "B", None, "A"])
        values, total, truncated = get_unique_values_for_filter(series)
        
        # Null should not be in values
        self.assertEqual(total, 2)
    
    def test_empty_series(self):
        """Test with empty series."""
        series = pd.Series([], dtype=object)
        values, total, truncated = get_unique_values_for_filter(series)
        
        self.assertEqual(values, [])
        self.assertEqual(total, 0)
        self.assertFalse(truncated)


class TestSearchValues(unittest.TestCase):
    """Test suite for search_values function."""
    
    def test_basic_search(self):
        """Test basic search functionality."""
        series = pd.Series(["United Kingdom", "United States", "France", "Germany"])
        matches = search_values(series, "united")
        
        self.assertEqual(len(matches), 2)
        self.assertIn("United Kingdom", matches)
        self.assertIn("United States", matches)
    
    def test_case_insensitive(self):
        """Test that search is case-insensitive."""
        series = pd.Series(["ABC", "abc", "AbC", "xyz"])
        matches = search_values(series, "ABC")
        
        self.assertEqual(len(matches), 3)
    
    def test_partial_match(self):
        """Test partial string matching."""
        series = pd.Series(["vaccination_rate", "mortality_rate", "birth_rate"])
        matches = search_values(series, "rate")
        
        self.assertEqual(len(matches), 3)
    
    def test_no_matches(self):
        """Test when no matches found."""
        series = pd.Series(["apple", "banana", "cherry"])
        matches = search_values(series, "xyz")
        
        self.assertEqual(matches, [])
    
    def test_empty_search_term(self):
        """Test with empty search term matches all."""
        series = pd.Series(["a", "b", "c"])
        matches = search_values(series, "")
        
        self.assertEqual(len(matches), 3)
    
    def test_with_null_values(self):
        """Test search ignores null values."""
        series = pd.Series(["apple", None, "apricot"])
        matches = search_values(series, "ap")
        
        self.assertEqual(len(matches), 2)
    
    def test_search_with_special_characters(self):
        """Test search with special characters."""
        series = pd.Series(["test@email.com", "user@domain.org"])
        matches = search_values(series, "@")
        
        self.assertEqual(len(matches), 2)


class TestGetNumericRange(unittest.TestCase):
    """Test suite for get_numeric_range function."""
    
    def test_basic_range(self):
        """Test basic min/max calculation."""
        series = pd.Series([10, 20, 30, 40, 50])
        min_val, max_val = get_numeric_range(series)
        
        self.assertEqual(min_val, 10)
        self.assertEqual(max_val, 50)
    
    def test_float_range(self):
        """Test with float values."""
        series = pd.Series([81.2, 82.3, 79.5, 84.1])
        min_val, max_val = get_numeric_range(series)
        
        self.assertEqual(min_val, 79.5)
        self.assertEqual(max_val, 84.1)
    
    def test_negative_values(self):
        """Test with negative values."""
        series = pd.Series([-50, -20, 0, 20, 50])
        min_val, max_val = get_numeric_range(series)
        
        self.assertEqual(min_val, -50)
        self.assertEqual(max_val, 50)
    
    def test_single_value(self):
        """Test with single value."""
        series = pd.Series([42])
        min_val, max_val = get_numeric_range(series)
        
        self.assertEqual(min_val, 42)
        self.assertEqual(max_val, 42)
    
    def test_same_values(self):
        """Test when all values are the same."""
        series = pd.Series([5, 5, 5, 5])
        min_val, max_val = get_numeric_range(series)
        
        self.assertEqual(min_val, max_val)
    
    def test_with_null_values(self):
        """Test that null values are ignored."""
        series = pd.Series([10, None, 30, None, 50])
        min_val, max_val = get_numeric_range(series)
        
        self.assertEqual(min_val, 10)
        self.assertEqual(max_val, 50)
    
    def test_string_numbers_converted(self):
        """Test that string numbers are converted."""
        series = pd.Series(["10", "20", "30"])
        min_val, max_val = get_numeric_range(series)
        
        self.assertEqual(min_val, 10)
        self.assertEqual(max_val, 30)
    
    def test_invalid_values_ignored(self):
        """Test that non-numeric values are ignored."""
        series = pd.Series([10, "not a number", 30])
        min_val, max_val = get_numeric_range(series)
        
        self.assertEqual(min_val, 10)
        self.assertEqual(max_val, 30)


class TestGetDateRange(unittest.TestCase):
    """Test suite for get_date_range function."""
    
    def test_basic_date_range(self):
        """Test basic date range calculation."""
        series = pd.Series(["2020-01-01", "2020-06-15", "2020-12-31"])
        start, end = get_date_range(series)
        
        self.assertEqual(start.date(), datetime(2020, 1, 1).date())
        self.assertEqual(end.date(), datetime(2020, 12, 31).date())
    
    def test_datetime_series(self):
        """Test with actual datetime series."""
        dates = pd.date_range("2020-01-01", periods=10, freq="M")
        series = pd.Series(dates)
        start, end = get_date_range(series)
        
        self.assertTrue(start < end)
    
    def test_with_null_values(self):
        """Test that null values are ignored."""
        series = pd.Series(["2020-01-01", None, "2020-12-31"])
        start, end = get_date_range(series)
        
        self.assertEqual(start.date(), datetime(2020, 1, 1).date())
        self.assertEqual(end.date(), datetime(2020, 12, 31).date())
    
    def test_single_date(self):
        """Test with single date."""
        series = pd.Series(["2020-06-15"])
        start, end = get_date_range(series)
        
        self.assertEqual(start, end)
    
    def test_different_date_formats(self):
        """Test with various date formats."""
        series = pd.Series(["2020-01-01", "01/06/2020", "2020-12-31"])
        start, end = get_date_range(series)
        
        # Should still find the range
        self.assertIsNotNone(start)
        self.assertIsNotNone(end)


if __name__ == '__main__':
    unittest.main()
