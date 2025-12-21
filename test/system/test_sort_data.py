"""
System Tests for UC6: Sort Data
================================

Tests the complete use case of sorting data by a column.
Validates the full workflow from setting sort through data updates.

Use Case: User sorts data by a column
Precondition: User has selected a dataset
Flow:
1. User clicks on column header or uses sort controls
2. User selects sort direction (ascending/descending)
3. System applies sort operation
4. System updates the data table to show sorted data
5. System indicates current sort column and direction

Test Categories:
- Happy Path Tests: Basic sorting operations
- Ascending/Descending Tests: Both directions work correctly
- Data Type Tests: Sorting different column types (text, numeric, date)
- Clear Sort Tests: Removing sort operations
- Edge Case Tests: Empty data, null values
"""

import unittest
import tempfile
import os
import csv

from unittest.mock import patch

import pandas as pd

from src.data.store import DataStore
from src.data.adapters import CSVAdapter
from src.analysis.session import AnalysisSession
from src.analysis.operations import SortOperation


# =============================================================================
# TEST FIXTURES
# =============================================================================

def create_test_csv_for_sorting(temp_files_list):
    """Create a CSV file with various data types for sort testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['country', 'year', 'population', 'life_expectancy', 'date_recorded'])
    writer.writerow(['United Kingdom', '2020', '67000000', '81.2', '2020-06-15'])
    writer.writerow(['France', '2020', '65000000', '82.5', '2020-06-16'])
    writer.writerow(['Germany', '2019', '83000000', '81.0', '2019-12-31'])
    writer.writerow(['Japan', '2020', '126000000', '84.5', '2020-03-20'])
    writer.writerow(['Australia', '2020', '25000000', '83.0', '2020-01-26'])
    writer.writerow(['Brazil', '2018', '212000000', '75.0', '2018-09-07'])
    writer.writerow(['India', '2020', '1380000000', '69.5', '2020-08-15'])
    writer.writerow(['Canada', '2019', '38000000', '82.0', '2019-07-01'])
    
    temp_file.close()
    return temp_file.name


def create_csv_with_nulls(temp_files_list):
    """Create a CSV file with null values for null handling tests."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['name', 'value', 'date'])
    writer.writerow(['Alpha', '100', '2020-01-01'])
    writer.writerow(['Beta', '', '2020-02-01'])  # Missing value
    writer.writerow(['Gamma', '300', ''])  # Missing date
    writer.writerow(['Delta', '50', '2020-04-01'])
    writer.writerow(['Epsilon', '200', '2020-05-01'])
    
    temp_file.close()
    return temp_file.name


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================

class TestSortHappyPath(unittest.TestCase):
    """System tests for successful sort operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_sort_basic_ascending(self):
        """UC6-HP1: Sort column in ascending order."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('country', ascending=True)
            
            view = session.get_current_view()
            countries = view['country'].tolist()
            
            # Should be alphabetically sorted
            self.assertEqual(countries, sorted(countries))
    
    def test_sort_basic_descending(self):
        """UC6-HP2: Sort column in descending order."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('country', ascending=False)
            
            view = session.get_current_view()
            countries = view['country'].tolist()
            
            # Should be reverse alphabetically sorted
            self.assertEqual(countries, sorted(countries, reverse=True))
    
    def test_sort_returns_operation_info(self):
        """UC6-HP3: Can retrieve current sort operation."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('population', ascending=False)
            
            sort_info = session.get_sort_operation()
            
            self.assertIsNotNone(sort_info)
            self.assertEqual(sort_info[0], 'population')
            self.assertEqual(sort_info[1], False)
    
    def test_sort_replaces_previous_sort(self):
        """UC6-HP4: New sort replaces previous sort."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # First sort
            session.set_sort('country', ascending=True)
            
            # Second sort replaces first
            session.set_sort('population', ascending=False)
            
            sort_info = session.get_sort_operation()
            self.assertEqual(sort_info[0], 'population')
            
            # Data should be sorted by population
            view = session.get_current_view()
            populations = [int(p) for p in view['population']]
            self.assertEqual(populations, sorted(populations, reverse=True))
    
    def test_sort_preserves_row_count(self):
        """UC6-HP5: Sort does not change row count."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            session.set_sort('year', ascending=True)
            
            sorted_count = session.get_row_count()
            
            self.assertEqual(sorted_count, original_count)


# =============================================================================
# DATA TYPE TESTS
# =============================================================================

class TestSortDataTypes(unittest.TestCase):
    """System tests for sorting different data types."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_sort_text_column(self):
        """UC6-DT1: Sort text column alphabetically."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('country', ascending=True)
            
            view = session.get_current_view()
            first_country = view.iloc[0]['country']
            last_country = view.iloc[-1]['country']
            
            # Australia should come before United Kingdom alphabetically
            self.assertEqual(first_country, 'Australia')
            self.assertEqual(last_country, 'United Kingdom')
    
    def test_sort_numeric_column(self):
        """UC6-DT2: Sort numeric column by value."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('population', ascending=True)
            
            view = session.get_current_view()
            populations = [int(p) for p in view['population']]
            
            # Each population should be <= the next
            for i in range(len(populations) - 1):
                self.assertLessEqual(populations[i], populations[i + 1])
    
    def test_sort_numeric_descending(self):
        """UC6-DT3: Sort numeric column descending."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('life_expectancy', ascending=False)
            
            view = session.get_current_view()
            life_exp = [float(le) for le in view['life_expectancy']]
            
            # Each value should be >= the next
            for i in range(len(life_exp) - 1):
                self.assertGreaterEqual(life_exp[i], life_exp[i + 1])
    
    def test_sort_date_column(self):
        """UC6-DT4: Sort date column chronologically."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('date_recorded', ascending=True)
            
            view = session.get_current_view()
            dates = [pd.to_datetime(d) for d in view['date_recorded']]
            
            # Each date should be <= the next
            for i in range(len(dates) - 1):
                self.assertLessEqual(dates[i], dates[i + 1])
    
    def test_sort_year_column_numeric(self):
        """UC6-DT5: Sort year column as numeric values."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('year', ascending=True)
            
            view = session.get_current_view()
            years = [int(y) for y in view['year']]
            
            # Years should be in ascending order
            for i in range(len(years) - 1):
                self.assertLessEqual(years[i], years[i + 1])


# =============================================================================
# CLEAR SORT TESTS
# =============================================================================

class TestClearSort(unittest.TestCase):
    """System tests for clearing sort operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_clear_sort_removes_operation(self):
        """UC6-CS1: Clear sort removes the sort operation."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('country', ascending=True)
            self.assertIsNotNone(session.get_sort_operation())
            
            session.clear_sort()
            
            self.assertIsNone(session.get_sort_operation())
    
    def test_clear_sort_restores_original_order(self):
        """UC6-CS2: Clear sort restores original row order."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_order = session.get_current_view()['country'].tolist()
            
            session.set_sort('country', ascending=True)
            session.clear_sort()
            
            restored_order = session.get_current_view()['country'].tolist()
            
            self.assertEqual(original_order, restored_order)
    
    def test_no_sort_initially(self):
        """UC6-CS3: No sort operation active initially."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            self.assertIsNone(session.get_sort_operation())


# =============================================================================
# NULL VALUE TESTS
# =============================================================================

class TestSortNullValues(unittest.TestCase):
    """System tests for sorting with null/missing values."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_sort_with_null_values_ascending(self):
        """UC6-NV1: Null values appear at beginning when sorting ascending."""
        csv_path = create_csv_with_nulls(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('value', ascending=True)
            
            view = session.get_current_view()
            values = view['value'].tolist()
            
            # Row with empty value should be first (nulls at beginning)
            # Find Beta's position - it has empty value
            names = view['name'].tolist()
            beta_idx = names.index('Beta')
            self.assertEqual(beta_idx, 0)  # Beta with null value should be first
    
    def test_sort_with_null_values_descending(self):
        """UC6-NV2: Null values appear at beginning when sorting descending."""
        csv_path = create_csv_with_nulls(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('value', ascending=False)
            
            view = session.get_current_view()
            names = view['name'].tolist()
            
            # Beta with null value should still be at beginning
            beta_idx = names.index('Beta')
            self.assertEqual(beta_idx, 0)
    
    def test_sort_preserves_all_rows_with_nulls(self):
        """UC6-NV3: Sort preserves all rows including those with null values."""
        csv_path = create_csv_with_nulls(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            session.set_sort('value', ascending=True)
            
            sorted_count = session.get_row_count()
            
            self.assertEqual(sorted_count, original_count)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestSortEdgeCases(unittest.TestCase):
    """System tests for sort edge cases."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_sort_nonexistent_column_raises(self):
        """UC6-EC1: Sort on non-existent column raises error."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            with self.assertRaises(ValueError):
                session.set_sort('nonexistent_column', ascending=True)
    
    def test_sort_single_row(self):
        """UC6-EC2: Sort works with single row dataset."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        writer.writerow(['name', 'value'])
        writer.writerow(['Only', '100'])
        temp_file.close()
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(temp_file.name)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('name', ascending=True)
            
            view = session.get_current_view()
            self.assertEqual(len(view), 1)
            self.assertEqual(view.iloc[0]['name'], 'Only')
    
    def test_sort_preserves_data_values(self):
        """UC6-EC3: Sort preserves all data values in rows."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Get Japan's original data
            original = session.get_original_data()
            japan_row = original[original['country'] == 'Japan'].iloc[0]
            original_pop = japan_row['population']
            original_le = japan_row['life_expectancy']
            
            session.set_sort('country', ascending=True)
            
            view = session.get_current_view()
            japan_sorted = view[view['country'] == 'Japan'].iloc[0]
            
            # All values should match
            self.assertEqual(str(japan_sorted['population']), str(original_pop))
            self.assertEqual(str(japan_sorted['life_expectancy']), str(original_le))
    
    def test_sort_with_filters_applied(self):
        """UC6-EC4: Sort works with filtered data."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Apply filter first
            session.add_filter_numeric('year', 2020, 2020)
            filtered_count = session.get_row_count()
            
            # Then sort
            session.set_sort('country', ascending=True)
            
            view = session.get_current_view()
            
            # Should still have same filtered count
            self.assertEqual(len(view), filtered_count)
            
            # Should be sorted alphabetically
            countries = view['country'].tolist()
            self.assertEqual(countries, sorted(countries))
    
    def test_sort_with_clean_applied(self):
        """UC6-EC5: Sort works with cleaned data."""
        csv_path = create_csv_with_nulls(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Apply clean first to remove rows with missing values
            session.add_clean(['value'])
            cleaned_count = session.get_row_count()
            
            # Then sort
            session.set_sort('value', ascending=True)
            
            view = session.get_current_view()
            
            # Should still have same cleaned count
            self.assertEqual(len(view), cleaned_count)
            
            # Values should be sorted
            values = [int(v) for v in view['value']]
            self.assertEqual(values, sorted(values))


# =============================================================================
# DATA INTEGRITY TESTS
# =============================================================================

class TestSortDataIntegrity(unittest.TestCase):
    """System tests verifying data integrity after sort operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_sort_maintains_row_associations(self):
        """UC6-DI1: Sort keeps row data together (no column shuffling)."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Get original Japan row
            original = session.get_original_data()
            japan_orig = original[original['country'] == 'Japan'].iloc[0]
            
            session.set_sort('population', ascending=False)
            
            view = session.get_current_view()
            japan_sorted = view[view['country'] == 'Japan'].iloc[0]
            
            # All columns should match for Japan row
            for col in ['year', 'population', 'life_expectancy', 'date_recorded']:
                self.assertEqual(
                    str(japan_orig[col]),
                    str(japan_sorted[col]),
                    f"Column {col} mismatch after sort"
                )
    
    def test_sort_preserves_original_data(self):
        """UC6-DI2: Sort does not modify original data."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_order = session.get_original_data()['country'].tolist()
            
            session.set_sort('country', ascending=True)
            session.set_sort('population', ascending=False)
            
            # Original data should still be in original order
            current_original = session.get_original_data()['country'].tolist()
            self.assertEqual(original_order, current_original)
    
    def test_sort_maintains_column_order(self):
        """UC6-DI3: Sort maintains column order."""
        csv_path = create_test_csv_for_sorting(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_columns = list(session.get_original_data().columns)
            
            session.set_sort('population', ascending=True)
            
            sorted_columns = list(session.get_current_view().columns)
            
            self.assertEqual(original_columns, sorted_columns)


if __name__ == '__main__':
    unittest.main()
