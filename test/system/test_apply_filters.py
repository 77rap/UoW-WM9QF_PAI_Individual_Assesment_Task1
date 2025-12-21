"""
System Tests for UC5: Apply Filters
====================================

Tests the complete use case of filtering data with text, numeric, and date filters.
Validates the full workflow from adding filters through data updates.

Use Case: User filters data (text, numeric, date filters)
Precondition: User has selected a dataset
Flow:
1. User clicks "Add Filter" button
2. User selects column to filter
3. User selects filter type and enters value(s)
4. System applies filter
5. System updates the data table to show filtered data
6. System updates row count in status bar

Test Categories:
- Text Filter Tests: Filtering by specific text values
- Numeric Filter Tests: Filtering by numeric range
- Date Filter Tests: Filtering by date range
- Multiple Filter Tests: Combining filters
- Remove Filter Tests: Removing individual filters
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
from src.analysis.operations import FilterOperation


# =============================================================================
# TEST FIXTURES
# =============================================================================

def create_test_csv_for_filtering(temp_files_list):
    """Create a CSV file with various data types for filter testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['country', 'region', 'year', 'population', 'life_expectancy', 'date_recorded'])
    writer.writerow(['United Kingdom', 'Europe', '2020', '67000000', '81.2', '2020-06-15'])
    writer.writerow(['France', 'Europe', '2020', '65000000', '82.5', '2020-06-16'])
    writer.writerow(['Germany', 'Europe', '2019', '83000000', '81.0', '2019-12-31'])
    writer.writerow(['Japan', 'Asia', '2020', '126000000', '84.5', '2020-03-20'])
    writer.writerow(['United States', 'Americas', '2020', '331000000', '77.0', '2020-07-04'])
    writer.writerow(['Canada', 'Americas', '2019', '38000000', '82.0', '2019-07-01'])
    writer.writerow(['Australia', 'Oceania', '2020', '25000000', '83.0', '2020-01-26'])
    writer.writerow(['Brazil', 'Americas', '2018', '212000000', '75.0', '2018-09-07'])
    writer.writerow(['India', 'Asia', '2020', '1380000000', '69.5', '2020-08-15'])
    writer.writerow(['South Africa', 'Africa', '2019', '59000000', '64.0', '2019-04-27'])
    
    temp_file.close()
    return temp_file.name


# =============================================================================
# TEXT FILTER TESTS
# =============================================================================

class TestTextFilters(unittest.TestCase):
    """System tests for text-based filter operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_filter_text_single_value(self):
        """UC5-TF1: Filter by single text value."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter region to Europe only
            session.add_filter_text('region', ['Europe'])
            
            view = session.get_current_view()
            
            # Should match only European countries
            self.assertEqual(len(view), 3)
            for region in view['region']:
                self.assertEqual(region, 'Europe')
    
    def test_filter_text_multiple_values(self):
        """UC5-TF2: Filter by multiple text values."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter region to Europe and Asia
            session.add_filter_text('region', ['Europe', 'Asia'])
            
            view = session.get_current_view()
            
            # Should match European and Asian countries
            self.assertEqual(len(view), 5)  # 3 Europe + 2 Asia
            for region in view['region']:
                self.assertIn(region, ['Europe', 'Asia'])
    
    def test_filter_text_exact_match(self):
        """UC5-TF3: Text filter matches exact values only."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter for specific country
            session.add_filter_text('country', ['Japan'])
            
            view = session.get_current_view()
            
            # Should match exactly Japan
            self.assertEqual(len(view), 1)
            self.assertEqual(view.iloc[0]['country'], 'Japan')
    
    def test_filter_text_get_options(self):
        """UC5-TF4: Can get available text filter options."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            options = session.get_filter_options('region')
            
            self.assertEqual(options['type'], 'text')
            self.assertIn('values', options)
            # Should have unique regions
            self.assertGreaterEqual(options['total_unique'], 5)
    
    def test_filter_text_search_values(self):
        """UC5-TF5: Can search for text filter values."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Search for countries containing "United"
            matches = session.search_filter_values('country', 'United')
            
            # Should find United Kingdom and United States
            self.assertGreaterEqual(len(matches), 2)


# =============================================================================
# NUMERIC FILTER TESTS
# =============================================================================

class TestNumericFilters(unittest.TestCase):
    """System tests for numeric filter operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_filter_numeric_range(self):
        """UC5-NF1: Filter by numeric range includes values in range."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter life_expectancy between 75 and 82
            session.add_filter_numeric('life_expectancy', 75, 82)
            
            view = session.get_current_view()
            
            for le in view['life_expectancy']:
                value = float(le)
                self.assertGreaterEqual(value, 75)
                self.assertLessEqual(value, 82)
    
    def test_filter_numeric_includes_boundaries(self):
        """UC5-NF2: Numeric filter is inclusive of boundaries."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter life_expectancy from 81.0 to 82.5 (exact boundary values)
            session.add_filter_numeric('life_expectancy', 81.0, 82.5)
            
            view = session.get_current_view()
            
            # Should include UK (81.2), France (82.5), Germany (81.0), Canada (82.0)
            life_exp_values = [float(le) for le in view['life_expectancy']]
            self.assertIn(81.0, life_exp_values)  # Germany - lower boundary
            self.assertIn(82.5, life_exp_values)  # France - upper boundary
    
    def test_filter_numeric_get_options(self):
        """UC5-NF3: Can get numeric range options for column."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            options = session.get_filter_options('life_expectancy')
            
            self.assertEqual(options['type'], 'numeric')
            self.assertIn('min', options)
            self.assertIn('max', options)
            self.assertLessEqual(options['min'], options['max'])
    
    def test_filter_numeric_validation_min_greater_max(self):
        """UC5-NF4: Numeric filter validates min <= max."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Min > max should raise error
            with self.assertRaises(ValueError):
                session.add_filter_numeric('life_expectancy', 90, 50)
    
    def test_filter_numeric_validation_out_of_range(self):
        """UC5-NF5: Numeric filter validates range overlaps with data."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter completely above data range should raise error
            with self.assertRaises(ValueError):
                session.add_filter_numeric('life_expectancy', 100, 150)
    
    def test_filter_numeric_year_column(self):
        """UC5-NF6: Numeric filter works on year column."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter for year 2020 only
            session.add_filter_numeric('year', 2020, 2020)
            
            view = session.get_current_view()
            
            for year in view['year']:
                self.assertEqual(int(year), 2020)


# =============================================================================
# DATE FILTER TESTS
# =============================================================================

class TestDateFilters(unittest.TestCase):
    """System tests for date filter operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_filter_date_range(self):
        """UC5-DF1: Filter by date range includes dates in range."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter dates between 2020-01-01 and 2020-06-30
            session.add_filter_date('date_recorded', '2020-01-01', '2020-06-30')
            
            view = session.get_current_view()
            
            for date_str in view['date_recorded']:
                date_val = pd.to_datetime(date_str)
                self.assertGreaterEqual(date_val, pd.to_datetime('2020-01-01'))
                self.assertLessEqual(date_val, pd.to_datetime('2020-06-30'))
    
    def test_filter_date_get_options(self):
        """UC5-DF2: Can get date range options for column."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            options = session.get_filter_options('date_recorded')
            
            self.assertEqual(options['type'], 'date')
            self.assertIn('start', options)
            self.assertIn('end', options)
    
    def test_filter_date_validation_start_after_end(self):
        """UC5-DF3: Date filter validates start <= end."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Start after end should raise error
            with self.assertRaises(ValueError):
                session.add_filter_date('date_recorded', '2020-12-31', '2020-01-01')
    
    def test_filter_date_validation_out_of_range(self):
        """UC5-DF4: Date filter validates range overlaps with data."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter dates completely after data range should raise error
            with self.assertRaises(ValueError):
                session.add_filter_date('date_recorded', '2025-01-01', '2025-12-31')


# =============================================================================
# MULTIPLE FILTER TESTS
# =============================================================================

class TestMultipleFilters(unittest.TestCase):
    """System tests for combining multiple filters."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_multiple_filters_and_logic(self):
        """UC5-MF1: Multiple filters combine with AND logic."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter Europe AND year 2020
            session.add_filter_text('region', ['Europe'])
            session.add_filter_numeric('year', 2020, 2020)
            
            view = session.get_current_view()
            
            # Should match only European countries from 2020
            for idx in range(len(view)):
                row = view.iloc[idx]
                self.assertEqual(row['region'], 'Europe')
                self.assertEqual(int(row['year']), 2020)
    
    def test_filters_on_different_types(self):
        """UC5-MF2: Filters can combine text, numeric, and date types."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Text + numeric + date filters
            session.add_filter_text('region', ['Europe', 'Asia'])
            session.add_filter_numeric('life_expectancy', 80, 85)
            session.add_filter_date('date_recorded', '2019-01-01', '2020-12-31')
            
            view = session.get_current_view()
            
            for idx in range(len(view)):
                row = view.iloc[idx]
                self.assertIn(row['region'], ['Europe', 'Asia'])
                self.assertGreaterEqual(float(row['life_expectancy']), 80)
                self.assertLessEqual(float(row['life_expectancy']), 85)
    
    def test_filter_updates_row_count(self):
        """UC5-MF3: Each filter updates the row count."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            session.add_filter_text('region', ['Europe'])
            count_after_first = session.get_row_count()
            
            session.add_filter_numeric('year', 2020, 2020)
            count_after_second = session.get_row_count()
            
            # Each filter should reduce or maintain count
            self.assertLessEqual(count_after_first, original_count)
            self.assertLessEqual(count_after_second, count_after_first)
    
    def test_filters_listed_in_operations(self):
        """UC5-MF4: All applied filters appear in operations list."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.add_filter_text('region', ['Europe'])
            session.add_filter_numeric('year', 2020, 2020)
            session.add_filter_numeric('life_expectancy', 80, 85)
            
            operations = session.list_filter_operations()
            
            self.assertEqual(len(operations), 3)


# =============================================================================
# REMOVE FILTER TESTS
# =============================================================================

class TestRemoveFilters(unittest.TestCase):
    """System tests for removing filter operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_remove_filter_restores_rows(self):
        """UC5-RF1: Removing filter restores previously filtered rows."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            session.add_filter_text('region', ['Europe'])
            
            operations = session.list_filter_operations()
            op_id = operations[0][0]
            
            session.remove_filter(op_id)
            
            restored_count = session.get_row_count()
            
            self.assertEqual(restored_count, original_count)
    
    def test_remove_specific_filter(self):
        """UC5-RF2: Can remove specific filter when multiple exist."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.add_filter_text('region', ['Europe'])
            session.add_filter_numeric('year', 2020, 2020)
            
            # Remove first filter
            operations = session.list_filter_operations()
            first_op_id = operations[0][0]
            session.remove_filter(first_op_id)
            
            remaining = session.list_filter_operations()
            self.assertEqual(len(remaining), 1)
    
    def test_remove_filter_keeps_other_filters(self):
        """UC5-RF3: Removing one filter doesn't affect others."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Add filter for year 2020
            session.add_filter_numeric('year', 2020, 2020)
            
            # Add filter for Europe
            session.add_filter_text('region', ['Europe'])
            
            # Remove year filter (first added)
            operations = session.list_filter_operations()
            year_filter_id = operations[0][0]  # First filter is year
            session.remove_filter(year_filter_id)
            
            # Europe filter should still be active
            view = session.get_current_view()
            for region in view['region']:
                self.assertEqual(region, 'Europe')


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestFilterEdgeCases(unittest.TestCase):
    """System tests for filter edge cases."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_filter_no_matches_returns_empty(self):
        """UC5-EC1: Filter with no matches returns empty dataset."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter for non-existent region
            session.add_filter_text('region', ['Antarctica'])
            
            view = session.get_current_view()
            self.assertEqual(len(view), 0)
    
    def test_filter_all_values_selected(self):
        """UC5-EC2: Filter with all values selected returns full dataset."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            # Select all regions
            all_regions = ['Europe', 'Asia', 'Americas', 'Oceania', 'Africa']
            session.add_filter_text('region', all_regions)
            
            filtered_count = session.get_row_count()
            self.assertEqual(filtered_count, original_count)
    
    def test_filter_empty_values_list_raises(self):
        """UC5-EC3: Filter with empty values list raises error."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            with self.assertRaises(ValueError):
                session.add_filter_text('region', [])
    
    def test_filter_nonexistent_column_raises(self):
        """UC5-EC4: Filter on non-existent column raises error."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            with self.assertRaises(ValueError):
                session.add_filter_text('nonexistent', ['value'])
    
    def test_filter_preserves_original_data(self):
        """UC5-EC5: Filtering does not modify original data."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_data = session.get_original_data().copy()
            
            session.add_filter_text('region', ['Europe'])
            session.add_filter_numeric('year', 2020, 2020)
            
            # Original data should be unchanged
            current_original = session.get_original_data()
            self.assertEqual(len(current_original), len(original_data))


# =============================================================================
# DATA INTEGRITY TESTS
# =============================================================================

class TestFilterDataIntegrity(unittest.TestCase):
    """System tests verifying data integrity after filter operations."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_filter_preserves_row_values(self):
        """UC5-DI1: Filtered rows retain their original values."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Get Japan's original data
            original = session.get_original_data()
            japan_original = original[original['country'] == 'Japan'].iloc[0]
            
            # Apply filter that includes Japan
            session.add_filter_text('region', ['Asia'])
            
            view = session.get_current_view()
            japan_filtered = view[view['country'] == 'Japan'].iloc[0]
            
            # Values should match
            self.assertEqual(
                str(japan_original['life_expectancy']),
                str(japan_filtered['life_expectancy'])
            )
    
    def test_filter_maintains_column_order(self):
        """UC5-DI2: Filtering maintains column order."""
        csv_path = create_test_csv_for_filtering(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_columns = list(session.get_original_data().columns)
            
            session.add_filter_text('region', ['Europe'])
            
            filtered_columns = list(session.get_current_view().columns)
            
            # Columns should be in same order
            self.assertEqual(original_columns, filtered_columns)


if __name__ == '__main__':
    unittest.main()
