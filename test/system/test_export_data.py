"""
System Tests for UC9: Export Data
==================================

Tests the complete use case of exporting filtered/processed data to CSV.
Validates the full workflow from data processing through export.

Use Case: User exports filtered/processed data to CSV
Precondition: User has selected a dataset and optionally applied operations
Flow:
1. User applies filters, cleans, sorts (optional)
2. User clicks Export CSV button
3. User selects destination file
4. System exports current view to CSV
5. System confirms successful export

Test Categories:
- Basic Export Tests: Exporting unprocessed data
- Filtered Export Tests: Exporting after filtering
- Cleaned Export Tests: Exporting after cleaning
- Sorted Export Tests: Exporting sorted data
- Combined Operations Tests: Exporting after multiple operations
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


# =============================================================================
# TEST FIXTURES
# =============================================================================

def create_test_csv_for_export(temp_files_list):
    """Create a CSV file for export testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['country', 'region', 'year', 'population', 'life_expectancy'])
    writer.writerow(['United Kingdom', 'Europe', '2020', '67000000', '81.2'])
    writer.writerow(['France', 'Europe', '2020', '65000000', '82.5'])
    writer.writerow(['Germany', 'Europe', '2019', '83000000', '81.0'])
    writer.writerow(['Japan', 'Asia', '2020', '126000000', '84.5'])
    writer.writerow(['Australia', 'Oceania', '2020', '25000000', '83.0'])
    writer.writerow(['Brazil', 'Americas', '2018', '212000000', '75.0'])
    writer.writerow(['India', 'Asia', '2020', '1380000000', '69.5'])
    writer.writerow(['Canada', 'Americas', '2019', '38000000', '82.0'])
    
    temp_file.close()
    return temp_file.name


def create_csv_with_missing(temp_files_list):
    """Create a CSV file with missing values for clean+export testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['name', 'value', 'category'])
    writer.writerow(['Alpha', '100', 'A'])
    writer.writerow(['Beta', '', 'B'])  # Missing value
    writer.writerow(['Gamma', '300', 'A'])
    writer.writerow(['Delta', '400', ''])  # Missing category
    writer.writerow(['Epsilon', '500', 'B'])
    
    temp_file.close()
    return temp_file.name


# =============================================================================
# BASIC EXPORT TESTS
# =============================================================================

class TestBasicExport(unittest.TestCase):
    """System tests for basic data export."""
    
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
    
    def test_export_creates_file(self):
        """UC9-BE1: Export creates a CSV file."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Get current view for export
            export_data = session.get_current_view()
            
            # Export to temp file
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            self.assertTrue(os.path.exists(export_file.name))
            self.assertGreater(os.path.getsize(export_file.name), 0)
    
    def test_export_preserves_row_count(self):
        """UC9-BE2: Exported file has same row count as view."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            # Read back and check
            imported = pd.read_csv(export_file.name)
            self.assertEqual(len(imported), original_count)
    
    def test_export_preserves_columns(self):
        """UC9-BE3: Exported file has same columns as view."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            export_data = session.get_current_view()
            original_columns = list(export_data.columns)
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            imported_columns = list(imported.columns)
            
            self.assertEqual(original_columns, imported_columns)
    
    def test_export_preserves_data_values(self):
        """UC9-BE4: Exported file has same data values."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # Check specific values
            uk_row = imported[imported['country'] == 'United Kingdom'].iloc[0]
            self.assertEqual(int(uk_row['year']), 2020)


# =============================================================================
# FILTERED EXPORT TESTS
# =============================================================================

class TestFilteredExport(unittest.TestCase):
    """System tests for exporting filtered data."""
    
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
    
    def test_export_filtered_by_text(self):
        """UC9-FE1: Export respects text filter."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter to Europe only
            session.add_filter_text('region', ['Europe'])
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # Should only have European countries
            self.assertEqual(len(imported), 3)
            for region in imported['region']:
                self.assertEqual(region, 'Europe')
    
    def test_export_filtered_by_numeric(self):
        """UC9-FE2: Export respects numeric filter."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter life_expectancy > 80
            session.add_filter_numeric('life_expectancy', 80, 100)
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # All exported rows should have life_expectancy >= 80
            for le in imported['life_expectancy']:
                self.assertGreaterEqual(float(le), 80)
    
    def test_export_with_multiple_filters(self):
        """UC9-FE3: Export respects multiple filters."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Multiple filters
            session.add_filter_text('region', ['Europe', 'Asia'])
            session.add_filter_numeric('year', 2020, 2020)
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # All rows should match both filters
            for idx in range(len(imported)):
                row = imported.iloc[idx]
                self.assertIn(row['region'], ['Europe', 'Asia'])
                self.assertEqual(int(row['year']), 2020)


# =============================================================================
# CLEANED EXPORT TESTS
# =============================================================================

class TestCleanedExport(unittest.TestCase):
    """System tests for exporting cleaned data."""
    
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
    
    def test_export_cleaned_data(self):
        """UC9-CE1: Export respects clean operation."""
        csv_path = create_csv_with_missing(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Clean rows with missing values
            session.add_clean(['value'])
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # Should have fewer rows (Beta removed)
            self.assertEqual(len(imported), 4)
            
            # No empty values in value column
            for val in imported['value']:
                self.assertIsNotNone(val)
                self.assertTrue(pd.notna(val))


# =============================================================================
# SORTED EXPORT TESTS
# =============================================================================

class TestSortedExport(unittest.TestCase):
    """System tests for exporting sorted data."""
    
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
    
    def test_export_sorted_ascending(self):
        """UC9-SE1: Export preserves ascending sort order."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('country', ascending=True)
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # Countries should be alphabetically sorted
            countries = imported['country'].tolist()
            self.assertEqual(countries, sorted(countries))
    
    def test_export_sorted_descending(self):
        """UC9-SE2: Export preserves descending sort order."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('population', ascending=False)
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # Populations should be in descending order
            populations = imported['population'].tolist()
            self.assertEqual(populations, sorted(populations, reverse=True))


# =============================================================================
# COMBINED OPERATIONS TESTS
# =============================================================================

class TestCombinedOperationsExport(unittest.TestCase):
    """System tests for exporting with multiple operations."""
    
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
    
    def test_export_filter_and_sort(self):
        """UC9-CO1: Export with filter and sort applied."""
        csv_path = create_test_csv_for_export(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter and sort
            session.add_filter_text('region', ['Europe'])
            session.set_sort('country', ascending=True)
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # Only Europe
            self.assertEqual(len(imported), 3)
            
            # Sorted alphabetically
            countries = imported['country'].tolist()
            self.assertEqual(countries, sorted(countries))
    
    def test_export_clean_filter_sort(self):
        """UC9-CO2: Export with clean, filter, and sort."""
        csv_path = create_csv_with_missing(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Clean, filter, and sort
            session.add_clean(['value'])
            session.add_filter_text('category', ['A'])
            session.set_sort('value', ascending=True)
            
            export_data = session.get_current_view()
            
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data.to_csv(export_file.name, index=False)
            
            imported = pd.read_csv(export_file.name)
            
            # Only category A with non-missing values
            self.assertEqual(len(imported), 2)  # Alpha and Gamma
            
            # All category A
            for cat in imported['category']:
                self.assertEqual(cat, 'A')
            
            # Sorted by value
            values = imported['value'].tolist()
            self.assertEqual(values, sorted(values))


if __name__ == '__main__':
    unittest.main()
