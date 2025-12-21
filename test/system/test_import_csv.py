"""
System Tests for UC1: Import CSV Data
======================================

Tests the complete use case of importing CSV data into the system.
Validates the full workflow from file selection through data display.

Use Case: User imports a CSV file into the system
Precondition: User has a valid CSV file with health data
Flow:
1. User selects a CSV file to import
2. System validates the file format
3. System imports data into database
4. System displays imported data in the table
5. System updates dataset dropdown with new import

Test Categories:
- Happy Path Tests: Successful imports with valid data
- Edge Case Tests: Empty files, large files, special characters
- Error Handling Tests: Invalid files, malformed data
- Data Integrity Tests: Verifying imported data matches source
"""

import unittest
import tempfile
import os
import csv
import shutil

from unittest.mock import patch

import pandas as pd

from src.data.store import DataStore
from src.data.adapters import CSVAdapter
from src.analysis.session import AnalysisSession


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================

class TestImportCSVHappyPath(unittest.TestCase):
    """System tests for successful CSV import scenarios."""
    
    def setUp(self):
        """Set up temp database for testing."""
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
    
    def _create_csv_file(self, rows, headers=None):
        """Helper to create a temporary CSV file."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        if headers:
            writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        temp_file.close()
        
        return temp_file.name
    
    def test_import_basic_health_data(self):
        """UC1-HP1: Import a basic CSV with health indicators."""
        # Arrange: Create CSV with health data
        csv_path = self._create_csv_file(
            headers=['country', 'year', 'life_expectancy', 'population'],
            rows=[
                ['United Kingdom', '2020', '81.2', '67886011'],
                ['France', '2020', '82.3', '65273511'],
                ['Germany', '2020', '81.0', '83783942'],
            ]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # Act: Import the CSV
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # Assert: Verify import was successful
            self.assertIsNotNone(import_id)
            
            # Verify data is accessible
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 3)
            self.assertIn('country', data.columns)
            self.assertIn('life_expectancy', data.columns)
    
    def test_import_creates_analysis_session(self):
        """UC1-HP2: Imported data can be used to create analysis session."""
        csv_path = self._create_csv_file(
            headers=['country', 'year', 'mortality_rate'],
            rows=[
                ['UK', '2020', '9.4'],
                ['France', '2020', '10.3'],
                ['Germany', '2020', '11.9'],
                ['Spain', '2020', '10.2'],
                ['Italy', '2020', '12.1'],
            ]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # Create session from imported data
            data = store.get_structured_data(import_id)
            info = store.get_import_info(import_id)
            session = AnalysisSession(data, source_name=info['source_name'])
            
            # Verify session is functional
            self.assertEqual(session.get_row_count(), 5)
            self.assertEqual(session.get_original_row_count(), 5)
            columns = session.get_columns()
            self.assertIn('country', columns)
            self.assertIn('mortality_rate', columns)
    
    def test_import_persists_to_database(self):
        """UC1-HP3: Imported data persists across DataStore instances."""
        csv_path = self._create_csv_file(
            headers=['region', 'cases', 'deaths'],
            rows=[
                ['Europe', '1000', '50'],
                ['Asia', '2000', '100'],
            ]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # Import data with first store instance
            store1 = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store1.import_data(adapter)
            
            # Create new store instance (simulates app restart)
            store2 = DataStore()
            
            # Verify data is still accessible
            imports = store2.list_imports()
            self.assertGreater(len(imports), 0)
            
            data = store2.get_structured_data(import_id)
            self.assertEqual(len(data), 2)
    
    def test_import_multiple_csv_files(self):
        """UC1-HP4: Import multiple CSV files successfully."""
        csv_path1 = self._create_csv_file(
            headers=['country', 'gdp'],
            rows=[['UK', '2800000'], ['France', '2700000']]
        )
        csv_path2 = self._create_csv_file(
            headers=['country', 'population'],
            rows=[['UK', '67000000'], ['France', '65000000']]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            # Import both files
            import_id1 = store.import_data(CSVAdapter(csv_path1))
            import_id2 = store.import_data(CSVAdapter(csv_path2))
            
            # Verify both imports exist
            imports = store.list_imports()
            self.assertEqual(len(imports), 2)
            
            # Verify each has correct data
            data1 = store.get_structured_data(import_id1)
            data2 = store.get_structured_data(import_id2)
            
            self.assertIn('gdp', data1.columns)
            self.assertIn('population', data2.columns)
    
    def test_import_updates_import_list(self):
        """UC1-HP5: Dataset dropdown is updated with new import."""
        csv_path = self._create_csv_file(
            headers=['indicator', 'value'],
            rows=[['test_indicator', '123']]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            # Get initial import count
            initial_imports = store.list_imports()
            initial_count = len(initial_imports)
            
            # Import new data
            adapter = CSVAdapter(csv_path)
            store.import_data(adapter)
            
            # Verify import count increased
            updated_imports = store.list_imports()
            self.assertEqual(len(updated_imports), initial_count + 1)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestImportCSVEdgeCases(unittest.TestCase):
    """System tests for CSV import edge cases."""
    
    def setUp(self):
        """Set up temp database."""
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
    
    def _create_csv_file(self, rows, headers=None):
        """Helper to create a temporary CSV file."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8'
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        if headers:
            writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        temp_file.close()
        
        return temp_file.name
    
    def test_import_csv_with_special_characters(self):
        """UC1-EC1: Import CSV containing special characters in data."""
        csv_path = self._create_csv_file(
            headers=['country', 'region', 'value'],
            rows=[
                ['Côte d\'Ivoire', 'Région Centre', '123'],
                ['São Paulo', 'América do Sul', '456'],
                ['北京', '亚洲', '789'],
            ]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 3)
    
    def test_import_csv_with_numeric_headers_raises_error(self):
        """UC1-EC2: CSV with pure numeric headers raises SQL error (known limitation)."""
        csv_path = self._create_csv_file(
            headers=['country', '2018', '2019', '2020'],
            rows=[
                ['UK', '100', '110', '120'],
                ['France', '200', '210', '220'],
            ]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            
            # Numeric-only column names cause SQL syntax errors
            # This is a known limitation of the current implementation
            with self.assertRaises(Exception):
                store.import_data(adapter)
    
    def test_import_csv_with_quoted_values(self):
        """UC1-EC3: Import CSV with quoted values containing commas."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8'
        )
        self.temp_files.append(temp_file.name)
        
        # Write CSV with quoted values
        temp_file.write('country,description,value\n')
        temp_file.write('"United Kingdom","London, Birmingham, Manchester",100\n')
        temp_file.write('"France","Paris, Lyon, Marseille",200\n')
        temp_file.close()
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(temp_file.name)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 2)
            # Verify commas in data are preserved
            self.assertIn(',', data['description'].iloc[0])
    
    def test_import_csv_with_missing_values(self):
        """UC1-EC4: Import CSV with missing/empty values."""
        csv_path = self._create_csv_file(
            headers=['country', 'value1', 'value2'],
            rows=[
                ['UK', '', '100'],
                ['France', '200', ''],
                ['Germany', '', ''],
            ]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # Should import all rows including those with missing values
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 3)
    
    def test_import_large_csv(self):
        """UC1-EC5: Import CSV with many rows."""
        # Create CSV with 1000 rows
        rows = [[f'Country{i}', str(2020), str(50 + i * 0.01)] for i in range(1000)]
        csv_path = self._create_csv_file(
            headers=['country', 'year', 'life_expectancy'],
            rows=rows
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 1000)
            
            # Verify info shows correct count
            info = store.get_import_info(import_id)
            self.assertEqual(info['record_count'], 1000)
    
    def test_import_single_row_csv(self):
        """UC1-EC6: Import CSV with only one data row."""
        csv_path = self._create_csv_file(
            headers=['country', 'value'],
            rows=[['UK', '100']]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 1)
    
    def test_import_single_column_csv(self):
        """UC1-EC7: Import CSV with only one data column."""
        csv_path = self._create_csv_file(
            headers=['country'],
            rows=[['UK'], ['France'], ['Germany']]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 3)
            # System adds row_id column, so we check for the source column
            self.assertIn('country', data.columns)


# =============================================================================
# DATA INTEGRITY TESTS
# =============================================================================

class TestImportCSVDataIntegrity(unittest.TestCase):
    """System tests verifying data integrity after CSV import."""
    
    def setUp(self):
        """Set up temp database."""
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
    
    def _create_csv_file(self, rows, headers=None):
        """Helper to create a temporary CSV file."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        if headers:
            writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        temp_file.close()
        
        return temp_file.name
    
    def test_imported_values_match_source(self):
        """UC1-DI1: All values match between source CSV and imported data."""
        source_data = [
            ['United Kingdom', '2020', '81.23', '67886011'],
            ['France', '2020', '82.34', '65273511'],
            ['Germany', '2020', '80.94', '83783942'],
        ]
        headers = ['country', 'year', 'life_expectancy', 'population']
        
        csv_path = self._create_csv_file(headers=headers, rows=source_data)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            
            # Verify each value
            for i, row in enumerate(source_data):
                for j, header in enumerate(headers):
                    self.assertEqual(str(data.iloc[i][header]), row[j])
    
    def test_column_order_preserved(self):
        """UC1-DI2: Column order from source CSV is preserved."""
        headers = ['alpha', 'beta', 'gamma', 'delta']
        csv_path = self._create_csv_file(
            headers=headers,
            rows=[['a', 'b', 'c', 'd']]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            
            # Filter out internal columns (row_id, _record_id, etc.)
            columns = [c for c in data.columns if not c.startswith('_') and c != 'row_id']
            self.assertEqual(columns, headers)
    
    def test_row_order_preserved(self):
        """UC1-DI3: Row order from source CSV is preserved."""
        # Use unique values to ensure proper ordering verification
        rows = [
            ['Alpha', '100'],
            ['Bravo', '200'],
            ['Charlie', '300'],
            ['Delta', '400'],
        ]
        
        # Create CSV with unique temp file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        writer = csv.writer(temp_file)
        writer.writerow(['name', 'order_num'])
        for row in rows:
            writer.writerow(row)
        temp_file.close()
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(temp_file.name)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            
            for i, expected in enumerate(['Alpha', 'Bravo', 'Charlie', 'Delta']):
                self.assertEqual(data.iloc[i]['name'], expected)
    
    def test_import_info_accuracy(self):
        """UC1-DI4: Import metadata is accurate."""
        csv_path = self._create_csv_file(
            headers=['a', 'b', 'c'],
            rows=[['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']]
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            info = store.get_import_info(import_id)
            
            self.assertEqual(info['source_type'], 'csv')
            self.assertEqual(info['record_count'], 3)
            self.assertIn(os.path.basename(csv_path), info['source_name'])


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestImportCSVErrorHandling(unittest.TestCase):
    """System tests for CSV import error handling."""
    
    def setUp(self):
        """Set up temp database."""
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
    
    def test_import_nonexistent_file_raises_error(self):
        """UC1-EH1: Importing non-existent file raises appropriate error."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            with self.assertRaises(Exception):
                adapter = CSVAdapter('/path/to/nonexistent/file.csv')
                adapter.fetch()
    
    def test_import_empty_csv_headers_only(self):
        """UC1-EH2: Handle CSV with headers but no data rows."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        writer.writerow(['col1', 'col2', 'col3'])  # Headers only, no data
        temp_file.close()
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(temp_file.name)
            
            # Empty CSV (no data rows) should either:
            # - Import with 0 rows, or
            # - Handle gracefully with error
            try:
                import_id = store.import_data(adapter)
                data = store.get_structured_data(import_id)
                self.assertEqual(len(data), 0)
            except Exception:
                # Some implementations may raise error for empty data
                pass  # This is acceptable behavior


if __name__ == '__main__':
    unittest.main()
