"""
Unit tests for AnalysisSession class.

Comprehensive tests for session initialization, clean operations,
filter operations, sort operations, and summary statistics.
"""

import unittest
import pandas as pd
import numpy as np

from src.analysis.session import AnalysisSession
from src.analysis.operations import CleanOperation, FilterOperation


class TestAnalysisSessionInit(unittest.TestCase):
    """Test suite for AnalysisSession initialization."""
    
    def test_init_with_dataframe(self):
        """Test basic initialization with DataFrame."""
        df = pd.DataFrame({
            "country_code": ["GBR", "FRA", "DEU"],
            "life_expectancy": [81.2, 82.3, 80.9]
        })
        session = AnalysisSession(df)
        
        self.assertIsInstance(session, AnalysisSession)
    
    def test_init_stores_copy_of_data(self):
        """Test that session stores a copy, not reference."""
        df = pd.DataFrame({"col": [1, 2, 3]})
        session = AnalysisSession(df)
        
        # Modify original
        df.loc[0, "col"] = 999
        
        # Session should have original value
        original = session.get_original_data()
        self.assertEqual(original.loc[0, "col"], 1)
    
    def test_init_with_source_name(self):
        """Test initialization with source name."""
        df = pd.DataFrame({"col": [1]})
        session = AnalysisSession(df, source_name="test_data.csv")
        
        self.assertEqual(session.source_name, "test_data.csv")
    
    def test_init_default_source_name(self):
        """Test default source name is 'Unknown'."""
        df = pd.DataFrame({"col": [1]})
        session = AnalysisSession(df)
        
        self.assertEqual(session.source_name, "Unknown")
    
    def test_init_empty_operations(self):
        """Test that operations lists are empty on init."""
        df = pd.DataFrame({"col": [1]})
        session = AnalysisSession(df)
        
        self.assertEqual(session.list_clean_operations(), [])
        self.assertEqual(session.list_filter_operations(), [])
        self.assertIsNone(session.get_sort_operation())


class TestAnalysisSessionDataAccess(unittest.TestCase):
    """Test suite for data access methods."""
    
    def setUp(self):
        """Set up test session with health data."""
        self.df = pd.DataFrame({
            "country_code": ["GBR", "FRA", "DEU", "USA", "JPN"],
            "year": [2020, 2020, 2020, 2020, 2020],
            "life_expectancy": [81.2, 82.3, 80.9, 78.5, 84.5]
        })
        self.session = AnalysisSession(self.df)
    
    def test_get_original_data(self):
        """Test getting original data."""
        data = self.session.get_original_data()
        
        self.assertEqual(len(data), 5)
        self.assertIn("country_code", data.columns)
    
    def test_get_original_data_returns_copy(self):
        """Test that get_original_data returns a copy."""
        data1 = self.session.get_original_data()
        data2 = self.session.get_original_data()
        
        data1.loc[0, "country_code"] = "XXX"
        self.assertNotEqual(data2.loc[0, "country_code"], "XXX")
    
    def test_get_current_view_no_operations(self):
        """Test current view with no operations equals original."""
        view = self.session.get_current_view()
        
        self.assertEqual(len(view), len(self.df))
    
    def test_get_columns(self):
        """Test getting column names."""
        columns = self.session.get_columns()
        
        self.assertEqual(columns, ["country_code", "year", "life_expectancy"])
    
    def test_get_row_count(self):
        """Test getting row count."""
        count = self.session.get_row_count()
        
        self.assertEqual(count, 5)
    
    def test_get_original_row_count(self):
        """Test getting original row count."""
        count = self.session.get_original_row_count()
        
        self.assertEqual(count, 5)
    
    def test_get_column_type_numeric(self):
        """Test column type detection for numeric."""
        col_type = self.session.get_column_type("life_expectancy")
        
        self.assertEqual(col_type, "numeric")
    
    def test_get_column_type_text(self):
        """Test column type detection for text."""
        col_type = self.session.get_column_type("country_code")
        
        self.assertEqual(col_type, "text")
    
    def test_get_column_type_invalid_column(self):
        """Test column type detection for non-existent column."""
        with self.assertRaises(ValueError) as context:
            self.session.get_column_type("nonexistent")
        
        self.assertIn("not found", str(context.exception))


class TestAnalysisSessionCleanOperations(unittest.TestCase):
    """Test suite for clean operations."""
    
    def setUp(self):
        """Set up test session with data containing missing values."""
        CleanOperation._next_id = 1
        self.df = pd.DataFrame({
            "country_code": ["GBR", "FRA", None, "USA", "N/A"],
            "life_expectancy": [81.2, None, 80.9, 78.5, 84.5],
            "mortality_rate": [9.4, 9.1, "Unknown", 8.8, 8.2]
        })
        self.session = AnalysisSession(self.df)
    
    def test_add_clean_single_column(self):
        """Test adding clean operation for single column."""
        op_id = self.session.add_clean(["country_code"])
        
        self.assertIsInstance(op_id, int)
        self.assertEqual(len(self.session.list_clean_operations()), 1)
    
    def test_add_clean_multiple_columns(self):
        """Test adding clean operation for multiple columns."""
        op_id = self.session.add_clean(["country_code", "life_expectancy"])
        
        view = self.session.get_current_view()
        # Should remove rows with None in either column
        self.assertLess(len(view), 5)
    
    def test_add_clean_removes_null_values(self):
        """Test that clean removes rows with null values."""
        self.session.add_clean(["life_expectancy"])
        view = self.session.get_current_view()
        
        # Row with None life_expectancy should be removed
        self.assertEqual(len(view), 4)
    
    def test_add_clean_removes_missing_indicators(self):
        """Test that clean removes rows with missing indicators."""
        self.session.add_clean(["country_code"])
        view = self.session.get_current_view()
        
        # Rows with None and "N/A" should be removed
        self.assertEqual(len(view), 3)
    
    def test_add_clean_with_custom_missing_values(self):
        """Test clean with custom missing value indicators."""
        self.session.add_clean(["mortality_rate"], missing_values=["Unknown"])
        view = self.session.get_current_view()
        
        self.assertEqual(len(view), 4)
    
    def test_add_clean_invalid_column(self):
        """Test adding clean for non-existent column raises error."""
        with self.assertRaises(ValueError) as context:
            self.session.add_clean(["nonexistent"])
        
        self.assertIn("not found", str(context.exception))
    
    def test_remove_clean(self):
        """Test removing a clean operation."""
        op_id = self.session.add_clean(["country_code"])
        
        result = self.session.remove_clean(op_id)
        
        self.assertTrue(result)
        self.assertEqual(len(self.session.list_clean_operations()), 0)
    
    def test_remove_clean_restores_data(self):
        """Test that removing clean restores data."""
        original_count = self.session.get_row_count()
        
        op_id = self.session.add_clean(["country_code"])
        cleaned_count = self.session.get_row_count()
        
        self.session.remove_clean(op_id)
        restored_count = self.session.get_row_count()
        
        self.assertLess(cleaned_count, original_count)
        self.assertEqual(restored_count, original_count)
    
    def test_remove_clean_invalid_id(self):
        """Test removing non-existent clean operation."""
        result = self.session.remove_clean(9999)
        
        self.assertFalse(result)
    
    def test_list_clean_operations(self):
        """Test listing clean operations."""
        self.session.add_clean(["country_code"])
        self.session.add_clean(["life_expectancy"])
        
        ops = self.session.list_clean_operations()
        
        self.assertEqual(len(ops), 2)
        self.assertIsInstance(ops[0], tuple)
        self.assertEqual(len(ops[0]), 2)  # (id, description)
    
    def test_multiple_clean_operations_stack(self):
        """Test that multiple clean operations stack (AND logic)."""
        self.session.add_clean(["country_code"])  # Removes 2 rows
        self.session.add_clean(["life_expectancy"])  # Removes 1 more row
        
        view = self.session.get_current_view()
        
        # Should have removed rows from both operations
        self.assertLess(len(view), 5)


class TestAnalysisSessionFilterOperations(unittest.TestCase):
    """Test suite for filter operations."""
    
    def setUp(self):
        """Set up test session with health data."""
        FilterOperation._next_id = 1
        self.df = pd.DataFrame({
            "country_code": ["GBR", "FRA", "DEU", "USA", "JPN"],
            "year": [2018, 2019, 2020, 2019, 2020],
            "life_expectancy": [81.2, 82.3, 80.9, 78.5, 84.5]
        })
        self.session = AnalysisSession(self.df)
    
    # Text filter tests
    def test_add_filter_text_single_value(self):
        """Test text filter with single value."""
        self.session.add_filter_text("country_code", ["GBR"])
        view = self.session.get_current_view()
        
        self.assertEqual(len(view), 1)
        self.assertEqual(view.iloc[0]["country_code"], "GBR")
    
    def test_add_filter_text_multiple_values(self):
        """Test text filter with multiple values."""
        self.session.add_filter_text("country_code", ["GBR", "FRA"])
        view = self.session.get_current_view()
        
        self.assertEqual(len(view), 2)
    
    def test_add_filter_text_invalid_column(self):
        """Test text filter with non-existent column raises error."""
        with self.assertRaises(ValueError):
            self.session.add_filter_text("nonexistent", ["value"])
    
    def test_add_filter_text_empty_values(self):
        """Test text filter with empty values list raises error."""
        with self.assertRaises(ValueError):
            self.session.add_filter_text("country_code", [])
    
    # Numeric filter tests
    def test_add_filter_numeric_range(self):
        """Test numeric range filter."""
        self.session.add_filter_numeric("life_expectancy", 80.0, 82.0)
        view = self.session.get_current_view()
        
        for _, row in view.iterrows():
            self.assertGreaterEqual(row["life_expectancy"], 80.0)
            self.assertLessEqual(row["life_expectancy"], 82.0)
    
    def test_add_filter_numeric_exact_value(self):
        """Test numeric filter where min equals max."""
        self.session.add_filter_numeric("year", 2020, 2020)
        view = self.session.get_current_view()
        
        for _, row in view.iterrows():
            self.assertEqual(row["year"], 2020)
    
    def test_add_filter_numeric_invalid_range(self):
        """Test numeric filter with min > max raises error."""
        with self.assertRaises(ValueError) as context:
            self.session.add_filter_numeric("life_expectancy", 90.0, 70.0)
        
        self.assertIn("greater than maximum", str(context.exception))
    
    def test_add_filter_numeric_out_of_data_range_min(self):
        """Test numeric filter with min > data max raises error."""
        with self.assertRaises(ValueError):
            self.session.add_filter_numeric("life_expectancy", 100.0, 110.0)
    
    def test_add_filter_numeric_out_of_data_range_max(self):
        """Test numeric filter with max < data min raises error."""
        with self.assertRaises(ValueError):
            self.session.add_filter_numeric("life_expectancy", 10.0, 50.0)
    
    # Date filter tests  
    def test_add_filter_date(self):
        """Test date range filter."""
        df = pd.DataFrame({
            "date": ["2020-01-01", "2020-06-15", "2020-12-31"],
            "value": [1, 2, 3]
        })
        session = AnalysisSession(df)
        
        session.add_filter_date("date", "2020-01-01", "2020-06-30")
        view = session.get_current_view()
        
        self.assertEqual(len(view), 2)
    
    def test_add_filter_date_invalid_range(self):
        """Test date filter with start > end raises error."""
        df = pd.DataFrame({"date": ["2020-01-01", "2020-12-31"]})
        session = AnalysisSession(df)
        
        with self.assertRaises(ValueError):
            session.add_filter_date("date", "2020-12-31", "2020-01-01")
    
    # Remove and list operations
    def test_remove_filter(self):
        """Test removing a filter operation."""
        op_id = self.session.add_filter_text("country_code", ["GBR"])
        
        result = self.session.remove_filter(op_id)
        
        self.assertTrue(result)
        self.assertEqual(len(self.session.list_filter_operations()), 0)
    
    def test_remove_filter_restores_data(self):
        """Test that removing filter restores data."""
        original_count = self.session.get_row_count()
        
        op_id = self.session.add_filter_text("country_code", ["GBR"])
        self.assertEqual(self.session.get_row_count(), 1)
        
        self.session.remove_filter(op_id)
        self.assertEqual(self.session.get_row_count(), original_count)
    
    def test_remove_filter_invalid_id(self):
        """Test removing non-existent filter."""
        result = self.session.remove_filter(9999)
        
        self.assertFalse(result)
    
    def test_multiple_filters_stack(self):
        """Test that multiple filters stack (AND logic)."""
        self.session.add_filter_text("country_code", ["GBR", "FRA", "DEU"])
        self.session.add_filter_numeric("year", 2020, 2020)
        
        view = self.session.get_current_view()
        
        # Only DEU has both matching country and year 2020
        self.assertEqual(len(view), 1)


class TestAnalysisSessionSortOperations(unittest.TestCase):
    """Test suite for sort operations."""
    
    def setUp(self):
        """Set up test session with unsorted data."""
        self.df = pd.DataFrame({
            "country_code": ["GBR", "FRA", "DEU", "USA", "JPN"],
            "life_expectancy": [81.2, 82.3, 80.9, 78.5, 84.5]
        })
        self.session = AnalysisSession(self.df)
    
    def test_set_sort_ascending(self):
        """Test ascending sort."""
        self.session.set_sort("life_expectancy", ascending=True)
        view = self.session.get_current_view()
        
        # First row should have lowest life expectancy
        self.assertEqual(view.iloc[0]["country_code"], "USA")  # 78.5
    
    def test_set_sort_descending(self):
        """Test descending sort."""
        self.session.set_sort("life_expectancy", ascending=False)
        view = self.session.get_current_view()
        
        # First row should have highest life expectancy
        self.assertEqual(view.iloc[0]["country_code"], "JPN")  # 84.5
    
    def test_set_sort_text_column(self):
        """Test sorting by text column."""
        self.session.set_sort("country_code", ascending=True)
        view = self.session.get_current_view()
        
        # Should be alphabetical
        self.assertEqual(view.iloc[0]["country_code"], "DEU")
    
    def test_set_sort_replaces_previous(self):
        """Test that new sort replaces previous sort."""
        self.session.set_sort("country_code", ascending=True)
        self.session.set_sort("life_expectancy", ascending=False)
        
        sort = self.session.get_sort_operation()
        
        self.assertEqual(sort[0], "life_expectancy")
    
    def test_set_sort_invalid_column(self):
        """Test sort with non-existent column raises error."""
        with self.assertRaises(ValueError):
            self.session.set_sort("nonexistent")
    
    def test_clear_sort(self):
        """Test clearing sort operation."""
        self.session.set_sort("life_expectancy")
        self.session.clear_sort()
        
        self.assertIsNone(self.session.get_sort_operation())
    
    def test_get_sort_operation(self):
        """Test getting current sort operation."""
        self.session.set_sort("country_code", ascending=False)
        sort = self.session.get_sort_operation()
        
        self.assertEqual(sort, ("country_code", False))
    
    def test_get_sort_operation_none(self):
        """Test get_sort_operation when no sort set."""
        sort = self.session.get_sort_operation()
        
        self.assertIsNone(sort)
    
    def test_sort_with_null_values(self):
        """Test that null values are placed at beginning."""
        df = pd.DataFrame({
            "col": [3, None, 1, None, 2]
        })
        session = AnalysisSession(df)
        session.set_sort("col", ascending=True)
        
        view = session.get_current_view()
        
        # Nulls should be at the beginning
        self.assertTrue(pd.isna(view.iloc[0]["col"]))
        self.assertTrue(pd.isna(view.iloc[1]["col"]))


class TestAnalysisSessionOperationsOrder(unittest.TestCase):
    """Test suite for operations order (clean -> filter -> sort)."""
    
    def setUp(self):
        """Set up test session."""
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
        self.df = pd.DataFrame({
            "country_code": ["GBR", "FRA", "N/A", "USA", "JPN"],
            "region": ["Europe", "Europe", "Unknown", "Americas", "Asia"],
            "life_expectancy": [81.2, 82.3, None, 78.5, 84.5]
        })
        self.session = AnalysisSession(self.df)
    
    def test_clean_applied_before_filter(self):
        """Test that clean is applied before filter."""
        # Clean removes the row with N/A country_code
        self.session.add_clean(["country_code"])
        
        # Filter by region - the Unknown row should already be gone
        self.session.add_filter_text("region", ["Europe", "Unknown"])
        
        view = self.session.get_current_view()
        
        # Should only have 2 Europe rows (N/A row was cleaned)
        self.assertEqual(len(view), 2)
    
    def test_filter_applied_before_sort(self):
        """Test that filter is applied before sort."""
        self.session.add_filter_text("region", ["Europe"])
        self.session.set_sort("life_expectancy", ascending=True)
        
        view = self.session.get_current_view()
        
        # Should only have Europe rows, sorted
        self.assertEqual(len(view), 2)
        self.assertEqual(view.iloc[0]["country_code"], "GBR")  # Lower life exp in Europe
    
    def test_all_operations_applied_in_order(self):
        """Test clean -> filter -> sort order."""
        # 1. Clean removes N/A row
        self.session.add_clean(["country_code"])
        
        # 2. Filter to high life expectancy
        self.session.add_filter_numeric("life_expectancy", 80.0, 90.0)
        
        # 3. Sort by life expectancy descending
        self.session.set_sort("life_expectancy", ascending=False)
        
        view = self.session.get_current_view()
        
        # Should have 3 rows (GBR, FRA, JPN), sorted descending
        self.assertEqual(len(view), 3)
        self.assertEqual(view.iloc[0]["country_code"], "JPN")  # Highest
        self.assertEqual(view.iloc[2]["country_code"], "GBR")  # Lowest of remaining


class TestAnalysisSessionSummary(unittest.TestCase):
    """Test suite for summary statistics."""
    
    def setUp(self):
        """Set up test session with mixed data types."""
        self.df = pd.DataFrame({
            "country_code": ["GBR", "FRA", "DEU", "USA", "JPN", "GBR", "FRA"],
            "region": ["Europe", "Europe", "Europe", "Americas", "Asia", "Europe", "Europe"],
            "life_expectancy": [81.2, 82.3, 80.9, 78.5, 84.5, 81.5, 82.1]
        })
        self.session = AnalysisSession(self.df)
    
    def test_get_summary_numeric(self):
        """Test summary for numeric column."""
        summary = self.session.get_summary("life_expectancy")
        
        self.assertIn("count", summary)
        self.assertIn("mean", summary)
        self.assertIn("min", summary)
        self.assertIn("max", summary)
        self.assertIn("std", summary)
        self.assertIn("median", summary)
    
    def test_get_summary_numeric_values(self):
        """Test summary values are correct."""
        summary = self.session.get_summary("life_expectancy")
        
        self.assertEqual(summary["count"], 7)
        self.assertEqual(summary["min"], 78.5)
        self.assertEqual(summary["max"], 84.5)
    
    def test_get_summary_text(self):
        """Test summary for text column."""
        summary = self.session.get_summary("country_code")
        
        self.assertIn("count", summary)
        self.assertIn("unique_count", summary)
        self.assertIn("mode", summary)
        self.assertIn("mode_frequency", summary)
    
    def test_get_summary_text_mode(self):
        """Test text summary mode is correct."""
        summary = self.session.get_summary("country_code")
        
        # GBR and FRA both appear twice
        self.assertIn(summary["mode"], ["GBR", "FRA"])
        self.assertEqual(summary["mode_frequency"], 2)
    
    def test_get_summary_with_group_by(self):
        """Test summary with group by."""
        summary = self.session.get_summary("life_expectancy", group_by="region")
        
        self.assertIsInstance(summary, pd.DataFrame)
        self.assertGreater(len(summary), 0)
    
    def test_get_summary_invalid_column(self):
        """Test summary with non-existent column raises error."""
        with self.assertRaises(ValueError):
            self.session.get_summary("nonexistent")
    
    def test_get_summary_invalid_group_by(self):
        """Test summary with non-existent group by raises error."""
        with self.assertRaises(ValueError):
            self.session.get_summary("life_expectancy", group_by="nonexistent")


class TestAnalysisSessionColumnMethods(unittest.TestCase):
    """Test suite for column utility methods."""
    
    def setUp(self):
        """Set up test session with mixed types."""
        self.df = pd.DataFrame({
            "country_code": ["GBR", "FRA", "DEU"],
            "region": ["Europe", "Europe", "Europe"],
            "year": [2020, 2020, 2020],
            "life_expectancy": [81.2, 82.3, 80.9]
        })
        self.session = AnalysisSession(self.df)
    
    def test_get_numeric_columns(self):
        """Test getting numeric columns."""
        numeric = self.session.get_numeric_columns()
        
        self.assertIn("year", numeric)
        self.assertIn("life_expectancy", numeric)
        self.assertNotIn("country_code", numeric)
    
    def test_get_text_columns(self):
        """Test getting text columns."""
        text = self.session.get_text_columns()
        
        self.assertIn("country_code", text)
        self.assertIn("region", text)
        self.assertNotIn("year", text)


class TestAnalysisSessionEdgeCases(unittest.TestCase):
    """Test suite for edge cases."""
    
    def test_empty_dataframe(self):
        """Test session with empty DataFrame."""
        df = pd.DataFrame(columns=["col1", "col2"])
        session = AnalysisSession(df)
        
        self.assertEqual(session.get_row_count(), 0)
        self.assertEqual(session.get_columns(), ["col1", "col2"])
    
    def test_single_row_dataframe(self):
        """Test session with single row."""
        df = pd.DataFrame({"col": [42]})
        session = AnalysisSession(df)
        
        self.assertEqual(session.get_row_count(), 1)
    
    def test_filter_results_in_empty(self):
        """Test that filtering to empty result works."""
        df = pd.DataFrame({"col": ["a", "b", "c"]})
        session = AnalysisSession(df)
        
        session.add_filter_text("col", ["z"])  # No match
        
        self.assertEqual(session.get_row_count(), 0)
    
    def test_has_empty_result(self):
        """Test has_empty_result method."""
        df = pd.DataFrame({"col": ["a", "b"]})
        session = AnalysisSession(df)
        
        self.assertFalse(session.has_empty_result())
        
        session.add_filter_text("col", ["z"])
        
        self.assertTrue(session.has_empty_result())
    
    def test_clear_all_operations(self):
        """Test clearing all operations."""
        df = pd.DataFrame({
            "col1": ["a", "b", "c"],
            "col2": [1, 2, 3]
        })
        session = AnalysisSession(df)
        
        session.add_clean(["col1"])
        session.add_filter_numeric("col2", 1, 2)
        session.set_sort("col2")
        
        session.clear_all_operations()
        
        self.assertEqual(session.list_clean_operations(), [])
        self.assertEqual(session.list_filter_operations(), [])
        self.assertIsNone(session.get_sort_operation())


if __name__ == '__main__':
    unittest.main()
