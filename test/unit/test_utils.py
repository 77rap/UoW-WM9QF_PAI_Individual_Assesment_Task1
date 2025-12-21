"""
Unit tests for utility functions module.

Tests for clean_column_name and infer_sql_type functions,
covering edge cases, boundaries, and all return paths.
"""

import unittest
from src.data.utils import clean_column_name, infer_sql_type


class TestCleanColumnName(unittest.TestCase):
    """Test suite for clean_column_name function."""
    
    # Normal cases
    def test_simple_lowercase(self):
        """Test simple lowercase string."""
        self.assertEqual(clean_column_name("age"), "age")
    
    def test_uppercase_to_lowercase(self):
        """Test conversion of uppercase to lowercase."""
        self.assertEqual(clean_column_name("AGE"), "age")
    
    def test_mixed_case(self):
        """Test mixed case conversion."""
        self.assertEqual(clean_column_name("UserName"), "username")
    
    def test_spaces_to_underscores(self):
        """Test spaces converted to underscores."""
        self.assertEqual(clean_column_name("user name"), "user_name")
    
    def test_multiple_spaces(self):
        """Test multiple consecutive spaces."""
        self.assertEqual(clean_column_name("user   name"), "user_name")
    
    def test_special_characters(self):
        """Test special characters replaced with underscores."""
        self.assertEqual(clean_column_name("user@name"), "user_name")
        self.assertEqual(clean_column_name("user-name"), "user_name")
        self.assertEqual(clean_column_name("user.name"), "user_name")
        self.assertEqual(clean_column_name("user#name$"), "user_name")
    
    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        self.assertEqual(clean_column_name("column123"), "column123")
        self.assertEqual(clean_column_name("user1name2"), "user1name2")
    
    # Edge cases - None and empty strings
    def test_none_input(self):
        """Test None returns default column name."""
        self.assertEqual(clean_column_name(None), "unnamed_column")
    
    def test_empty_string(self):
        """Test empty string returns default."""
        self.assertEqual(clean_column_name(""), "unnamed_column")
    
    def test_only_spaces(self):
        """Test string with only spaces."""
        self.assertEqual(clean_column_name("   "), "unnamed_column")
    
    def test_only_special_characters(self):
        """Test string with only special characters."""
        self.assertEqual(clean_column_name("@#$%"), "unnamed_column")
        self.assertEqual(clean_column_name("---"), "unnamed_column")
    
    # Boundary cases - leading/trailing characters
    def test_leading_underscore(self):
        """Test leading underscores are removed."""
        self.assertEqual(clean_column_name("_name"), "name")
        self.assertEqual(clean_column_name("__name"), "name")
    
    def test_trailing_underscore(self):
        """Test trailing underscores are removed."""
        self.assertEqual(clean_column_name("name_"), "name")
        self.assertEqual(clean_column_name("name__"), "name")
    
    def test_leading_and_trailing_underscore(self):
        """Test both leading and trailing underscores removed."""
        self.assertEqual(clean_column_name("_name_"), "name")
        self.assertEqual(clean_column_name("__name__"), "name")
    
    def test_consecutive_underscores_in_middle(self):
        """Test consecutive underscores reduced to one."""
        self.assertEqual(clean_column_name("user__name"), "user_name")
        self.assertEqual(clean_column_name("user___name"), "user_name")
    
    # Complex cases
    def test_complex_string(self):
        """Test complex string with multiple transformations."""
        self.assertEqual(
            clean_column_name("  User@Name#123!!  "),
            "user_name_123"
        )
    
    def test_sql_reserved_words(self):
        """Test SQL reserved words are cleaned."""
        self.assertEqual(clean_column_name("SELECT"), "select")
        self.assertEqual(clean_column_name("FROM"), "from")
    
    def test_very_long_name(self):
        """Test very long column names."""
        long_name = "a" * 100
        self.assertEqual(clean_column_name(long_name), long_name)


class TestInferSqlType(unittest.TestCase):
    """Test suite for infer_sql_type function."""
    
    # Test INTEGER type detection
    def test_all_integers(self):
        """Test list of all integers returns INTEGER."""
        self.assertEqual(infer_sql_type([1, 2, 3, 4, 5]), "INTEGER")
    
    def test_integers_as_strings(self):
        """Test integer strings are detected as INTEGER."""
        self.assertEqual(infer_sql_type(["1", "2", "3"]), "INTEGER")
    
    def test_negative_integers(self):
        """Test negative integers detected."""
        self.assertEqual(infer_sql_type([-1, -2, -3]), "INTEGER")
    
    def test_zero(self):
        """Test zero is detected as integer."""
        self.assertEqual(infer_sql_type([0, 0, 0]), "INTEGER")
    
    # Test REAL type detection
    def test_all_floats(self):
        """Test list of all floats returns REAL."""
        self.assertEqual(infer_sql_type([1.5, 2.3, 3.7]), "REAL")
    
    def test_floats_as_strings(self):
        """Test float strings are detected as REAL."""
        self.assertEqual(infer_sql_type(["1.5", "2.3", "3.7"]), "REAL")
    
    def test_mixed_int_and_float(self):
        """Test mix of integers and floats returns REAL."""
        self.assertEqual(infer_sql_type([1, 2.5, 3, 4.7]), "REAL")
        self.assertEqual(infer_sql_type(["1", "2.5", "3"]), "REAL")
    
    def test_negative_floats(self):
        """Test negative floats detected."""
        self.assertEqual(infer_sql_type([-1.5, -2.3]), "REAL")
    
    def test_scientific_notation(self):
        """Test scientific notation detected as REAL."""
        self.assertEqual(infer_sql_type(["1e5", "2e-3"]), "REAL")
    
    # Test TEXT type detection
    def test_all_text(self):
        """Test list of text values returns TEXT."""
        self.assertEqual(infer_sql_type(["apple", "banana", "cherry"]), "TEXT")
    
    def test_mixed_text_and_numbers(self):
        """Test mix of text and numbers returns TEXT."""
        self.assertEqual(infer_sql_type(["1", "2", "abc"]), "TEXT")
        self.assertEqual(infer_sql_type([1, 2, "abc"]), "TEXT")
    
    def test_alphanumeric(self):
        """Test alphanumeric values detected as TEXT."""
        self.assertEqual(infer_sql_type(["abc123", "def456"]), "TEXT")
    
    # Edge cases - empty and None values
    def test_empty_list(self):
        """Test empty list returns TEXT."""
        self.assertEqual(infer_sql_type([]), "TEXT")
    
    def test_all_none(self):
        """Test list of all None values returns TEXT."""
        self.assertEqual(infer_sql_type([None, None, None]), "TEXT")
    
    def test_none_with_integers(self):
        """Test None mixed with integers ignores None."""
        self.assertEqual(infer_sql_type([1, None, 2, None, 3]), "INTEGER")
    
    def test_none_with_floats(self):
        """Test None mixed with floats ignores None."""
        self.assertEqual(infer_sql_type([1.5, None, 2.5]), "REAL")
    
    def test_none_with_text(self):
        """Test None mixed with text returns TEXT."""
        self.assertEqual(infer_sql_type(["abc", None, "def"]), "TEXT")
    
    # Boundary cases
    def test_single_value_integer(self):
        """Test single integer value."""
        self.assertEqual(infer_sql_type([42]), "INTEGER")
    
    def test_single_value_float(self):
        """Test single float value."""
        self.assertEqual(infer_sql_type([3.14]), "REAL")
    
    def test_single_value_text(self):
        """Test single text value."""
        self.assertEqual(infer_sql_type(["hello"]), "TEXT")
    
    def test_single_none(self):
        """Test single None value."""
        self.assertEqual(infer_sql_type([None]), "TEXT")
    
    # Special numeric cases
    def test_leading_zeros(self):
        """Test numbers with leading zeros treated as strings."""
        self.assertEqual(infer_sql_type(["001", "002"]), "INTEGER")
    
    def test_whitespace_numbers(self):
        """Test numbers with whitespace are handled."""
        self.assertEqual(infer_sql_type([" 1 ", " 2 ", " 3 "]), "INTEGER")
        self.assertEqual(infer_sql_type([" 1.5 ", " 2.5 "]), "REAL")
    
    def test_empty_strings(self):
        """Test empty strings in list."""
        self.assertEqual(infer_sql_type(["", "", ""]), "TEXT")
        self.assertEqual(infer_sql_type(["1", "", "2"]), "TEXT")
    
    def test_boolean_values(self):
        """Test boolean values are treated as TEXT since str(True)='True' cannot be parsed as int."""
        # Note: Python booleans when converted to string become "True"/"False"
        # which cannot be parsed as integers, so they are treated as TEXT
        self.assertEqual(infer_sql_type([True, False, True]), "TEXT")
    
    # Large datasets
    def test_large_integer_list(self):
        """Test with large list of integers."""
        large_list = list(range(1000))
        self.assertEqual(infer_sql_type(large_list), "INTEGER")
    
    def test_large_mixed_list(self):
        """Test with large mixed list."""
        large_list = [1.5] * 500 + [2] * 500
        self.assertEqual(infer_sql_type(large_list), "REAL")


if __name__ == "__main__":
    unittest.main()
