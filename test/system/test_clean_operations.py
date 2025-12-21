"""
System Tests for UC4: Apply Clean Operations
=============================================

Tests the complete use case of cleaning data by removing rows with missing values.
Validates the full workflow from adding clean operations through data updates.

Use Case: User cleans data by removing missing values
Precondition: User has selected a dataset
Flow:
1. User clicks "Add Clean" button
2. User selects columns to check for missing values
3. User optionally customizes missing value indicators
4. System applies clean operation
5. System updates the data table to show cleaned data
6. System updates row count in status bar

Test Categories:
- Happy Path Tests: Successful clean operations
- Edge Case Tests: Multiple columns, custom missing values
- Undo/Redo Tests: Removing clean operations
- Data Integrity Tests: Verifying correct rows are removed
"""

import unittest
import tempfile
import os
import csv

from unittest.mock import patch

import pandas as pd
import numpy as np

from src.data.store import DataStore
from src.data.adapters import CSVAdapter
from src.analysis.session import AnalysisSession
from src.analysis.operations import CleanOperation


# =============================================================================
# TEST FIXTURES
# =============================================================================

def create_csv_with_missing_values(temp_files_list):
    """Create a CSV file with various missing value patterns."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['country', 'year', 'life_expectancy', 'population'])
    writer.writerow(['UK', '2020', '81.2', '67000000'])  # Complete
    writer.writerow(['France', '2020', '', '65000000'])  # Missing life_expectancy
    writer.writerow(['Germany', '2020', '81.0', ''])  # Missing population
    writer.writerow(['Japan', '', '84.5', '126000000'])  # Missing year
    writer.writerow(['USA', '2020', '77.0', '331000000'])  # Complete
    writer.writerow(['Canada', '2020', 'N/A', '38000000'])  # N/A value
    writer.writerow(['Australia', '2020', '83.0', 'Unknown'])  # Unknown value
    writer.writerow(['Brazil', '2020', '75.0', '212000000'])  # Complete
    
    temp_file.close()
    return temp_file.name


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================

class TestCleanOperationsHappyPath(unittest.TestCase):
    """System tests for successful clean operation scenarios."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        
        # Reset operation IDs
        CleanOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_clean_single_column_removes_empty_values(self):
        """UC4-HP1: Clean operation removes rows with empty values in specified column."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            # Apply clean on life_expectancy column
            session.add_clean(['life_expectancy'])
            
            cleaned_count = session.get_row_count()
            
            # Should have fewer rows after cleaning
            self.assertLess(cleaned_count, original_count)
            
            # Verify no empty/N/A values remain in cleaned column
            view = session.get_current_view()
            for val in view['life_expectancy']:
                self.assertIsNotNone(val)
                self.assertNotEqual(str(val).strip(), '')
                self.assertNotEqual(str(val).upper(), 'N/A')
    
    def test_clean_multiple_columns(self):
        """UC4-HP2: Clean operation can check multiple columns."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Apply clean on multiple columns
            session.add_clean(['life_expectancy', 'population'])
            
            view = session.get_current_view()
            
            # All remaining rows should have valid values in both columns
            for idx in range(len(view)):
                row = view.iloc[idx]
                self.assertIsNotNone(row['life_expectancy'])
                self.assertIsNotNone(row['population'])
    
    def test_clean_updates_row_count(self):
        """UC4-HP3: Clean operation updates row count correctly."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_original_row_count()
            
            session.add_clean(['life_expectancy'])
            
            current_count = session.get_row_count()
            
            # Current count should reflect cleaning
            self.assertLess(current_count, original_count)
            
            # Original count should remain unchanged
            self.assertEqual(session.get_original_row_count(), original_count)
    
    def test_clean_operation_appears_in_list(self):
        """UC4-HP4: Clean operation is listed in operations panel."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Initially no clean operations
            self.assertEqual(len(session.list_clean_operations()), 0)
            
            session.add_clean(['life_expectancy'])
            
            # Now should have one clean operation
            operations = session.list_clean_operations()
            self.assertEqual(len(operations), 1)
            
            # Description should mention the column
            op_id, description = operations[0]
            self.assertIn('life_expectancy', description)
    
    def test_multiple_clean_operations(self):
        """UC4-HP5: Multiple clean operations can be applied."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Add first clean operation
            session.add_clean(['year'])
            count_after_first = session.get_row_count()
            
            # Add second clean operation
            session.add_clean(['population'])
            count_after_second = session.get_row_count()
            
            # Each clean should potentially reduce rows further
            self.assertLessEqual(count_after_second, count_after_first)
            
            # Should have two operations listed
            self.assertEqual(len(session.list_clean_operations()), 2)


# =============================================================================
# CUSTOM MISSING VALUES TESTS
# =============================================================================

class TestCleanCustomMissingValues(unittest.TestCase):
    """System tests for clean operations with custom missing value indicators."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        CleanOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_clean_recognizes_na_value(self):
        """UC4-CM1: Clean operation recognizes 'N/A' as missing."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Clean with default missing values (includes N/A)
            session.add_clean(['life_expectancy'])
            
            view = session.get_current_view()
            
            # Should not contain 'N/A'
            for val in view['life_expectancy']:
                self.assertNotEqual(str(val).upper(), 'N/A')
    
    def test_clean_recognizes_unknown_value(self):
        """UC4-CM2: Clean operation recognizes 'Unknown' as missing."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Clean with default missing values (includes Unknown)
            session.add_clean(['population'])
            
            view = session.get_current_view()
            
            # Should not contain 'Unknown'
            for val in view['population']:
                self.assertNotEqual(str(val).lower(), 'unknown')
    
    def test_clean_with_custom_missing_values(self):
        """UC4-CM3: Clean operation works with custom missing value list."""
        # Create CSV with custom missing indicators
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        writer.writerow(['country', 'value'])
        writer.writerow(['UK', '100'])
        writer.writerow(['France', '-999'])  # Custom missing indicator
        writer.writerow(['Germany', '200'])
        writer.writerow(['Japan', 'MISSING'])  # Another custom indicator
        writer.writerow(['USA', '300'])
        temp_file.close()
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(temp_file.name)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Clean with custom missing values
            session.add_clean(['value'], missing_values=['-999', 'MISSING'])
            
            view = session.get_current_view()
            
            # Should have removed rows with -999 and MISSING
            self.assertEqual(len(view), 3)
            for val in view['value']:
                self.assertNotIn(str(val), ['-999', 'MISSING'])


# =============================================================================
# REMOVE CLEAN OPERATION TESTS
# =============================================================================

class TestRemoveCleanOperations(unittest.TestCase):
    """System tests for removing clean operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        CleanOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_remove_clean_restores_rows(self):
        """UC4-RC1: Removing clean operation restores previously hidden rows."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            # Apply clean
            session.add_clean(['life_expectancy'])
            cleaned_count = session.get_row_count()
            
            # Get operation ID
            operations = session.list_clean_operations()
            op_id = operations[0][0]
            
            # Remove clean
            session.remove_clean(op_id)
            restored_count = session.get_row_count()
            
            # Rows should be restored
            self.assertEqual(restored_count, original_count)
    
    def test_remove_specific_clean_operation(self):
        """UC4-RC2: Can remove specific clean operation when multiple exist."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Add two clean operations
            session.add_clean(['year'])
            session.add_clean(['population'])
            
            self.assertEqual(len(session.list_clean_operations()), 2)
            
            # Remove first operation
            operations = session.list_clean_operations()
            first_op_id = operations[0][0]
            session.remove_clean(first_op_id)
            
            # Should have one operation left
            remaining = session.list_clean_operations()
            self.assertEqual(len(remaining), 1)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestCleanOperationsEdgeCases(unittest.TestCase):
    """System tests for clean operation edge cases."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        CleanOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_clean_on_complete_data_no_change(self):
        """UC4-EC1: Clean on column with no missing values has no effect."""
        # Create CSV with complete data
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        writer.writerow(['country', 'value'])
        writer.writerow(['UK', '100'])
        writer.writerow(['France', '200'])
        writer.writerow(['Germany', '300'])
        temp_file.close()
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(temp_file.name)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            session.add_clean(['value'])
            
            # Count should remain the same
            self.assertEqual(session.get_row_count(), original_count)
    
    def test_clean_removes_all_rows_warning(self):
        """UC4-EC2: Clean that would remove all rows leaves zero rows."""
        # Create CSV where all rows have missing values in one column
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        writer.writerow(['country', 'value'])
        writer.writerow(['UK', ''])
        writer.writerow(['France', 'N/A'])
        writer.writerow(['Germany', ''])
        temp_file.close()
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(temp_file.name)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.add_clean(['value'])
            
            # All rows removed
            self.assertEqual(session.get_row_count(), 0)
    
    def test_clean_preserves_original_data(self):
        """UC4-EC3: Clean operation does not modify original data."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_data = session.get_original_data().copy()
            
            session.add_clean(['life_expectancy'])
            session.add_clean(['population'])
            
            # Original data should be unchanged
            current_original = session.get_original_data()
            self.assertEqual(len(current_original), len(original_data))


# =============================================================================
# DATA INTEGRITY TESTS
# =============================================================================

class TestCleanDataIntegrity(unittest.TestCase):
    """System tests verifying data integrity after clean operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        CleanOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_clean_only_removes_correct_rows(self):
        """UC4-DI1: Clean only removes rows with missing values in specified column."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Clean on year column - should only remove row with missing year
            session.add_clean(['year'])
            
            view = session.get_current_view()
            
            # Rows with complete year should remain
            countries = view['country'].tolist()
            self.assertIn('UK', countries)
            self.assertIn('France', countries)
            self.assertIn('USA', countries)
    
    def test_clean_preserves_column_values(self):
        """UC4-DI2: Clean preserves all values in remaining rows."""
        csv_path = create_csv_with_missing_values(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Get UK row before cleaning
            original = session.get_original_data()
            uk_original = original[original['country'] == 'UK'].iloc[0]
            
            session.add_clean(['life_expectancy'])
            
            view = session.get_current_view()
            uk_cleaned = view[view['country'] == 'UK'].iloc[0]
            
            # UK values should be preserved
            self.assertEqual(str(uk_original['year']), str(uk_cleaned['year']))
            self.assertEqual(str(uk_original['life_expectancy']), str(uk_cleaned['life_expectancy']))


if __name__ == '__main__':
    unittest.main()
