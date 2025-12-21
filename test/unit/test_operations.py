"""
Unit tests for analysis operations module.

Tests for CleanOperation, FilterOperation, and SortOperation classes,
covering initialization, describe methods, and ID generation.
"""

import unittest
from src.analysis.operations import CleanOperation, FilterOperation, SortOperation


class TestCleanOperation(unittest.TestCase):
    """Test suite for CleanOperation class."""
    
    def setUp(self):
        """Reset operation ID counter for consistent testing."""
        CleanOperation._next_id = 1
    
    # Initialization tests
    def test_init_with_single_column(self):
        """Test initialization with single column."""
        op = CleanOperation(["country_code"])
        self.assertEqual(op.columns, ["country_code"])
    
    def test_init_with_multiple_columns(self):
        """Test initialization with multiple columns."""
        op = CleanOperation(["country_code", "year", "life_expectancy"])
        self.assertEqual(len(op.columns), 3)
        self.assertIn("life_expectancy", op.columns)
    
    def test_init_with_default_missing_values(self):
        """Test that default missing values are used when not specified."""
        op = CleanOperation(["country_code"])
        self.assertIsInstance(op.missing_values, list)
        self.assertIn("N/A", op.missing_values)
        self.assertIn("Unknown", op.missing_values)
    
    def test_init_with_custom_missing_values(self):
        """Test initialization with custom missing values."""
        custom = ["missing", "none", "-"]
        op = CleanOperation(["country_code"], missing_values=custom)
        self.assertEqual(op.missing_values, custom)
    
    def test_init_empty_missing_values_list(self):
        """Test with empty missing values list."""
        op = CleanOperation(["country_code"], missing_values=[])
        self.assertEqual(op.missing_values, [])
    
    # ID generation tests
    def test_operation_id_assigned(self):
        """Test that operation ID is assigned."""
        op = CleanOperation(["country_code"])
        self.assertIsInstance(op.operation_id, int)
        self.assertGreater(op.operation_id, 0)
    
    def test_operation_ids_increment(self):
        """Test that operation IDs increment for each new operation."""
        op1 = CleanOperation(["col1"])
        op2 = CleanOperation(["col2"])
        op3 = CleanOperation(["col3"])
        
        self.assertEqual(op2.operation_id, op1.operation_id + 1)
        self.assertEqual(op3.operation_id, op2.operation_id + 1)
    
    # Describe tests
    def test_describe_single_column(self):
        """Test describe with single column."""
        op = CleanOperation(["life_expectancy"])
        description = op.describe()
        
        self.assertIn("Clean", description)
        self.assertIn("life_expectancy", description)
    
    def test_describe_multiple_columns(self):
        """Test describe with multiple columns."""
        op = CleanOperation(["country_code", "year"])
        description = op.describe()
        
        self.assertIn("country_code", description)
        self.assertIn("year", description)
    
    # Edge cases
    def test_empty_columns_list(self):
        """Test with empty columns list."""
        op = CleanOperation([])
        self.assertEqual(op.columns, [])


class TestFilterOperation(unittest.TestCase):
    """Test suite for FilterOperation class."""
    
    def setUp(self):
        """Reset operation ID counter."""
        FilterOperation._next_id = 1
    
    # Text filter tests
    def test_init_text_filter(self):
        """Test initialization of text filter."""
        op = FilterOperation("country_code", "text", values=["GBR", "FRA", "DEU"])
        
        self.assertEqual(op.column, "country_code")
        self.assertEqual(op.filter_type, "text")
        self.assertEqual(op.values, ["GBR", "FRA", "DEU"])
        self.assertIsNone(op.min_value)
        self.assertIsNone(op.max_value)
    
    def test_text_filter_single_value(self):
        """Test text filter with single value."""
        op = FilterOperation("country_code", "text", values=["GBR"])
        self.assertEqual(len(op.values), 1)
    
    def test_text_filter_many_values(self):
        """Test text filter with many values."""
        countries = ["GBR", "FRA", "DEU", "USA", "JPN", "CHN", "IND", "BRA"]
        op = FilterOperation("country_code", "text", values=countries)
        self.assertEqual(len(op.values), 8)
    
    # Numeric filter tests
    def test_init_numeric_filter(self):
        """Test initialization of numeric filter."""
        op = FilterOperation("life_expectancy", "numeric", min_value=70.0, max_value=85.0)
        
        self.assertEqual(op.column, "life_expectancy")
        self.assertEqual(op.filter_type, "numeric")
        self.assertEqual(op.min_value, 70.0)
        self.assertEqual(op.max_value, 85.0)
        self.assertIsNone(op.values)
    
    def test_numeric_filter_integers(self):
        """Test numeric filter with integer values."""
        op = FilterOperation("year", "numeric", min_value=2000, max_value=2020)
        self.assertEqual(op.min_value, 2000)
        self.assertEqual(op.max_value, 2020)
    
    def test_numeric_filter_same_min_max(self):
        """Test numeric filter where min equals max."""
        op = FilterOperation("year", "numeric", min_value=2020, max_value=2020)
        self.assertEqual(op.min_value, op.max_value)
    
    def test_numeric_filter_negative_values(self):
        """Test numeric filter with negative values."""
        op = FilterOperation("temperature", "numeric", min_value=-40, max_value=50)
        self.assertEqual(op.min_value, -40)
    
    # Date filter tests
    def test_init_date_filter(self):
        """Test initialization of date filter."""
        op = FilterOperation("date", "date", min_value="2020-01-01", max_value="2020-12-31")
        
        self.assertEqual(op.filter_type, "date")
        self.assertEqual(op.min_value, "2020-01-01")
        self.assertEqual(op.max_value, "2020-12-31")
    
    # ID generation tests
    def test_operation_id_assigned(self):
        """Test that operation ID is assigned."""
        op = FilterOperation("col", "text", values=["a"])
        self.assertIsInstance(op.operation_id, int)
    
    def test_operation_ids_increment(self):
        """Test IDs increment across different filter types."""
        op1 = FilterOperation("col1", "text", values=["a"])
        op2 = FilterOperation("col2", "numeric", min_value=0, max_value=100)
        op3 = FilterOperation("col3", "date", min_value="2020-01-01", max_value="2020-12-31")
        
        self.assertEqual(op2.operation_id, op1.operation_id + 1)
        self.assertEqual(op3.operation_id, op2.operation_id + 1)
    
    # Describe tests
    def test_describe_text_filter_few_values(self):
        """Test describe for text filter with few values."""
        op = FilterOperation("country", "text", values=["GBR", "FRA"])
        description = op.describe()
        
        self.assertIn("Filter", description)
        self.assertIn("country", description)
        self.assertIn("GBR", description)
        self.assertIn("FRA", description)
    
    def test_describe_text_filter_many_values(self):
        """Test describe for text filter with many values shows count."""
        values = ["a", "b", "c", "d", "e"]
        op = FilterOperation("category", "text", values=values)
        description = op.describe()
        
        self.assertIn("5 values", description)
    
    def test_describe_numeric_filter(self):
        """Test describe for numeric filter."""
        op = FilterOperation("life_expectancy", "numeric", min_value=70, max_value=85)
        description = op.describe()
        
        self.assertIn("Filter", description)
        self.assertIn("life_expectancy", description)
        self.assertIn("70", description)
        self.assertIn("85", description)
    
    def test_describe_date_filter(self):
        """Test describe for date filter."""
        op = FilterOperation("date", "date", min_value="2020-01-01", max_value="2020-12-31")
        description = op.describe()
        
        self.assertIn("2020-01-01", description)
        self.assertIn("2020-12-31", description)


class TestSortOperation(unittest.TestCase):
    """Test suite for SortOperation class."""
    
    # Initialization tests
    def test_init_ascending(self):
        """Test initialization with ascending sort."""
        op = SortOperation("year", ascending=True)
        
        self.assertEqual(op.column, "year")
        self.assertTrue(op.ascending)
    
    def test_init_descending(self):
        """Test initialization with descending sort."""
        op = SortOperation("life_expectancy", ascending=False)
        
        self.assertEqual(op.column, "life_expectancy")
        self.assertFalse(op.ascending)
    
    def test_init_default_ascending(self):
        """Test that default is ascending."""
        op = SortOperation("country_code")
        self.assertTrue(op.ascending)
    
    # Describe tests
    def test_describe_ascending(self):
        """Test describe for ascending sort."""
        op = SortOperation("year", ascending=True)
        description = op.describe()
        
        self.assertIn("Sort", description)
        self.assertIn("year", description)
        self.assertIn("ascending", description)
    
    def test_describe_descending(self):
        """Test describe for descending sort."""
        op = SortOperation("life_expectancy", ascending=False)
        description = op.describe()
        
        self.assertIn("descending", description)


if __name__ == '__main__':
    unittest.main()
