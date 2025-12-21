"""
Integration Tests for Data Layer
=================================

Tests the complete data flow from adapters through DataStore to database.
Uses real temporary database and files.

Test Categories:
- CSV Import Tests: Test real CSV file imports (no mocking)
- API Import Tests: Test WHO API imports (mocked HTTP requests)
- Real API Tests: Optional tests hitting real WHO API (skip by default)
"""

import unittest
import tempfile
import os
import csv

from unittest.mock import patch

from src.data.store import DataStore
from src.data.adapters import CSVAdapter, WHOAPIAdapter


# =============================================================================
# CSV IMPORT INTEGRATION TESTS
# =============================================================================

class TestCSVImportFlow(unittest.TestCase):
    """Integration tests for CSV import workflow."""
    
    def setUp(self):
        """Set up temp database and health CSV file."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country_code', 'year', 'life_expectancy'])
        writer.writerow(['GBR', '2020', '81.2'])
        writer.writerow(['FRA', '2020', '82.3'])
        writer.writerow(['DEU', '2020', '81.0'])
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
    
    def test_complete_csv_import_flow(self):
        """Test full CSV import: file → adapter → store → database → query."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(self.test_csv_path)
            
            import_id = store.import_data(adapter)
            
            self.assertIsNotNone(import_id)
            
            info = store.get_import_info(import_id)
            self.assertEqual(info['source_type'], 'csv')
            self.assertEqual(info['record_count'], 3)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 3)
            self.assertIn('country_code', data.columns)
            self.assertIn('year', data.columns)
            self.assertIn('life_expectancy', data.columns)
    
    def test_csv_import_preserves_data(self):
        """Test that imported data matches original CSV values."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(self.test_csv_path)
            
            import_id = store.import_data(adapter)
            data = store.get_structured_data(import_id)
            
            countries = data['country_code'].tolist()
            self.assertIn('GBR', countries)
            self.assertIn('FRA', countries)
            self.assertIn('DEU', countries)
    
    def test_csv_import_with_filtering(self):
        """Test querying imported health data with WHERE clause."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(self.test_csv_path)
            
            import_id = store.import_data(adapter)
            
            filtered = store.get_structured_data(
                import_id,
                where_clause="life_expectancy > ?",
                params=(81.5,)
            )
            
            self.assertEqual(len(filtered), 1)
            countries = filtered['country_code'].tolist()
            self.assertIn('FRA', countries)
    
    def test_raw_data_contains_record_ids(self):
        """Test that raw data includes _record_id for each row."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(self.test_csv_path)
            
            import_id = store.import_data(adapter)
            raw_data = store.get_raw_data(import_id)
            
            self.assertIn('_record_id', raw_data.columns)
            self.assertEqual(len(raw_data), 3)


# =============================================================================
# API IMPORT INTEGRATION TESTS (MOCKED)
# =============================================================================
# These tests mock the HTTP requests to WHO API but test real database
# operations. They verify that:
# - DataStore correctly processes API adapter output
# - Database correctly stores API-sourced data with source_type='api'
# - Filtering and querying works on API-imported data
#
# LIMITATIONS: These tests do NOT verify:
# - Real WHO API is reachable
# - API response format hasn't changed
# - Network timeout handling in real conditions
#
# For real API testing, see TestRealAPIImport class below.
# =============================================================================

class TestAPIImportFlow(unittest.TestCase):
    """Integration tests for WHO API import workflow."""
    
    def setUp(self):
        """Set up temp database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Mock WHO API response data
        self.mock_api_response = {
            "value": [
                {
                    "IndicatorCode": "WHOSIS_000001",
                    "SpatialDim": "GBR",
                    "TimeDim": 2020,
                    "NumericValue": 81.2,
                    "Dim1": "BTSX",
                    "Dim2": None
                },
                {
                    "IndicatorCode": "WHOSIS_000001",
                    "SpatialDim": "FRA",
                    "TimeDim": 2020,
                    "NumericValue": 82.3,
                    "Dim1": "BTSX",
                    "Dim2": None
                },
                {
                    "IndicatorCode": "WHOSIS_000001",
                    "SpatialDim": "JPN",
                    "TimeDim": 2020,
                    "NumericValue": 84.5,
                    "Dim1": "BTSX",
                    "Dim2": None
                }
            ]
        }
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    @patch('requests.get')
    def test_complete_api_import_flow(self, mock_get):
        """Test full API import: WHO API → adapter → store → database → query."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = self.mock_api_response
        mock_response.raise_for_status = unittest.mock.MagicMock()
        mock_get.return_value = mock_response
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter("life_expectancy", limit=100)
            
            import_id = store.import_data(adapter)
            
            self.assertIsNotNone(import_id)
            
            info = store.get_import_info(import_id)
            self.assertEqual(info['source_type'], 'api')
            self.assertEqual(info['record_count'], 3)
            self.assertIn('WHO_GHO', info['source_name'])
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 3)
            self.assertIn('country_code', data.columns)
            self.assertIn('year', data.columns)
            self.assertIn('value', data.columns)
    
    @patch('requests.get')
    def test_api_import_preserves_data(self, mock_get):
        """Test that API imported data matches expected values."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = self.mock_api_response
        mock_response.raise_for_status = unittest.mock.MagicMock()
        mock_get.return_value = mock_response
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter("life_expectancy")
            
            import_id = store.import_data(adapter)
            data = store.get_structured_data(import_id)
            
            countries = data['country_code'].tolist()
            self.assertIn('GBR', countries)
            self.assertIn('FRA', countries)
            self.assertIn('JPN', countries)
    
    @patch('requests.get')
    def test_api_import_with_filtering(self, mock_get):
        """Test filtering API imported health data."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = self.mock_api_response
        mock_response.raise_for_status = unittest.mock.MagicMock()
        mock_get.return_value = mock_response
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter("life_expectancy")
            
            import_id = store.import_data(adapter)
            
            # Filter for life expectancy > 83
            filtered = store.get_structured_data(
                import_id,
                where_clause="value > ?",
                params=(83.0,)
            )
            
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered.iloc[0]['country_code'], 'JPN')
    
    @patch('requests.get')
    def test_api_import_different_indicators(self, mock_get):
        """Test importing different health indicators."""
        mortality_response = {
            "value": [
                {
                    "IndicatorCode": "MDG_0000000001",
                    "SpatialDim": "USA",
                    "TimeDim": 2020,
                    "NumericValue": 5.4,
                    "Dim1": "BTSX",
                    "Dim2": None
                }
            ]
        }
        
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = mortality_response
        mock_response.raise_for_status = unittest.mock.MagicMock()
        mock_get.return_value = mock_response
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter("infant_mortality")
            
            import_id = store.import_data(adapter)
            
            info = store.get_import_info(import_id)
            self.assertIn('infant_mortality', info['source_name'])
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 1)
    
    @patch('requests.get')
    def test_mixed_csv_and_api_imports(self, mock_get):
        """Test that CSV and API imports coexist correctly."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = self.mock_api_response
        mock_response.raise_for_status = unittest.mock.MagicMock()
        mock_get.return_value = mock_response
        
        # Create a CSV file
        csv_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(csv_file)
        writer.writerow(['country_code', 'vaccination_rate'])
        writer.writerow(['GBR', '92.5'])
        csv_file.close()
        
        try:
            with patch('src.data.database.DB_PATH', self.test_db_path):
                store = DataStore()
                
                # Import from CSV
                csv_id = store.import_data(CSVAdapter(csv_file.name))
                
                # Import from API
                api_id = store.import_data(WHOAPIAdapter("life_expectancy"))
                
                # Verify both exist
                imports = store.list_imports()
                self.assertEqual(len(imports), 2)
                
                # Verify different source types
                csv_info = store.get_import_info(csv_id)
                api_info = store.get_import_info(api_id)
                
                self.assertEqual(csv_info['source_type'], 'csv')
                self.assertEqual(api_info['source_type'], 'api')
                
                # Verify data isolation
                csv_data = store.get_structured_data(csv_id)
                api_data = store.get_structured_data(api_id)
                
                self.assertIn('vaccination_rate', csv_data.columns)
                self.assertIn('value', api_data.columns)
        finally:
            os.unlink(csv_file.name)


# =============================================================================
# MULTIPLE IMPORTS TESTS
# =============================================================================

class TestMultipleImportsFlow(unittest.TestCase):
    """Integration tests for multiple health data imports."""
    
    def setUp(self):
        """Set up temp database and multiple health CSV files."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        self.csv1 = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.csv1)
        writer.writerow(['country_code', 'life_expectancy'])
        writer.writerow(['GBR', '81.2'])
        writer.writerow(['FRA', '82.3'])
        self.csv1.close()
        
        self.csv2 = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.csv2)
        writer.writerow(['country_code', 'infant_mortality'])
        writer.writerow(['USA', '5.6'])
        writer.writerow(['CAN', '4.3'])
        self.csv2.close()
    
    def tearDown(self):
        """Clean up temp files."""
        for path in [self.test_db_path, self.csv1.name, self.csv2.name]:
            if os.path.exists(path):
                os.unlink(path)
    
    def test_multiple_imports_isolated(self):
        """Test that multiple health imports create separate tables."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            id1 = store.import_data(CSVAdapter(self.csv1.name))
            id2 = store.import_data(CSVAdapter(self.csv2.name))
            
            self.assertNotEqual(id1, id2)
            
            data1 = store.get_structured_data(id1)
            data2 = store.get_structured_data(id2)
            
            self.assertIn('life_expectancy', data1.columns)
            self.assertIn('infant_mortality', data2.columns)
            
            self.assertNotIn('infant_mortality', data1.columns)
            self.assertNotIn('life_expectancy', data2.columns)
    
    def test_list_imports_shows_all(self):
        """Test that list_imports returns all imports."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            store.import_data(CSVAdapter(self.csv1.name))
            store.import_data(CSVAdapter(self.csv2.name))
            
            imports = store.list_imports()
            
            self.assertEqual(len(imports), 2)
    
    def test_list_data_tables_shows_all(self):
        """Test that list_data_tables returns all structured tables."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            store.import_data(CSVAdapter(self.csv1.name))
            store.import_data(CSVAdapter(self.csv2.name))
            
            tables = store.list_data_tables()
            
            self.assertEqual(len(tables), 2)


# =============================================================================
# CRUD OPERATIONS TESTS
# =============================================================================

class TestCRUDFlow(unittest.TestCase):
    """Integration tests for CRUD operations on health data."""
    
    def setUp(self):
        """Set up temp database with initial health data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country_code', 'vaccination_rate'])
        writer.writerow(['GBR', '92.5'])
        writer.writerow(['FRA', '88.3'])
        self.test_csv.close()
    
    def tearDown(self):
        """Clean up temp files."""
        for path in [self.test_db_path, self.test_csv.name]:
            if os.path.exists(path):
                os.unlink(path)
    
    def test_add_record_flow(self):
        """Test adding a health record updates both raw and count."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv.name))
            
            initial_info = store.get_import_info(import_id)
            initial_count = initial_info['record_count']
            
            store.add_record(import_id, {'country_code': 'DEU', 'vaccination_rate': 90.1})
            
            updated_info = store.get_import_info(import_id)
            self.assertEqual(updated_info['record_count'], initial_count + 1)
            
            raw_data = store.get_raw_data(import_id)
            countries = [row['country_code'] for _, row in raw_data.iterrows()]
            self.assertIn('DEU', countries)
    
    def test_delete_record_flow(self):
        """Test deleting a record updates count."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv.name))
            
            raw_data = store.get_raw_data(import_id)
            record_id = int(raw_data.iloc[0]['_record_id'])
            
            initial_count = store.get_import_info(import_id)['record_count']
            
            result = store.delete_record(record_id)
            
            self.assertTrue(result)
            
            updated_count = store.get_import_info(import_id)['record_count']
            self.assertEqual(updated_count, initial_count - 1)
    
    def test_update_record_flow(self):
        """Test updating a health record persists changes."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv.name))
            
            raw_data = store.get_raw_data(import_id)
            record_id = int(raw_data.iloc[0]['_record_id'])
            
            result = store.update_record(record_id, {'country_code': 'GBR', 'vaccination_rate': 94.0})
            
            self.assertTrue(result)
            
            updated_data = store.get_raw_data(import_id)
            updated_record = updated_data[updated_data['_record_id'] == record_id].iloc[0]
            self.assertEqual(updated_record['vaccination_rate'], 94.0)


# =============================================================================
# DELETE/CASCADE TESTS
# =============================================================================

class TestDeleteImportFlow(unittest.TestCase):
    """Integration tests for import deletion cascade."""
    
    def setUp(self):
        """Set up temp database with health data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country_code', 'mortality_rate'])
        writer.writerow(['GBR', '9.4'])
        self.test_csv.close()
    
    def tearDown(self):
        """Clean up temp files."""
        for path in [self.test_db_path, self.test_csv.name]:
            if os.path.exists(path):
                os.unlink(path)
    
    def test_delete_import_cascade(self):
        """Test that deleting import removes all associated data."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv.name))
            
            self.assertIsNotNone(store.get_import_info(import_id))
            self.assertGreater(len(store.get_raw_data(import_id)), 0)
            
            result = store.delete_import(import_id)
            
            self.assertTrue(result)
            
            self.assertIsNone(store.get_import_info(import_id))
            
            raw_data = store.get_raw_data(import_id)
            self.assertEqual(len(raw_data), 0)
    
    def test_delete_one_import_preserves_others(self):
        """Test that deleting one import doesn't affect others."""
        csv2 = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(csv2)
        writer.writerow(['country_code', 'life_expectancy'])
        writer.writerow(['JPN', '84.5'])
        csv2.close()
        
        try:
            with patch('src.data.database.DB_PATH', self.test_db_path):
                store = DataStore()
                id1 = store.import_data(CSVAdapter(self.test_csv.name))
                id2 = store.import_data(CSVAdapter(csv2.name))
                
                store.delete_import(id1)
                
                self.assertIsNone(store.get_import_info(id1))
                self.assertIsNotNone(store.get_import_info(id2))
                
                data2 = store.get_structured_data(id2)
                self.assertEqual(len(data2), 1)
        finally:
            os.unlink(csv2.name)


# =============================================================================
# EDGE CASES TESTS
# =============================================================================

class TestEdgeCases(unittest.TestCase):
    """Integration tests for edge cases."""
    
    def setUp(self):
        """Set up temp database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    def test_csv_with_empty_values(self):
        """Test importing health CSV with empty cells."""
        csv_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(csv_file)
        writer.writerow(['country_code', 'life_expectancy'])
        writer.writerow(['GBR', ''])
        writer.writerow(['', '82.3'])
        csv_file.close()
        
        try:
            with patch('src.data.database.DB_PATH', self.test_db_path):
                store = DataStore()
                import_id = store.import_data(CSVAdapter(csv_file.name))
                
                data = store.get_raw_data(import_id)
                self.assertEqual(len(data), 2)
        finally:
            os.unlink(csv_file.name)
    
    def test_csv_with_special_characters(self):
        """Test importing CSV with special characters in country names."""
        csv_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8'
        )
        writer = csv.writer(csv_file)
        writer.writerow(['country', 'life_expectancy'])
        writer.writerow(['Côte d\'Ivoire', '57.8'])
        writer.writerow(['São Tomé', '66.5'])
        csv_file.close()
        
        try:
            with patch('src.data.database.DB_PATH', self.test_db_path):
                store = DataStore()
                import_id = store.import_data(CSVAdapter(csv_file.name))
                
                data = store.get_raw_data(import_id)
                countries = [row['country'] for _, row in data.iterrows()]
                self.assertIn('Côte d\'Ivoire', countries)
                self.assertIn('São Tomé', countries)
        finally:
            os.unlink(csv_file.name)
    
    def test_large_import(self):
        """Test importing larger health dataset."""
        csv_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(csv_file)
        writer.writerow(['year', 'life_expectancy'])
        for i in range(500):
            writer.writerow([1900 + i, 50 + i * 0.06])
        csv_file.close()
        
        try:
            with patch('src.data.database.DB_PATH', self.test_db_path):
                store = DataStore()
                import_id = store.import_data(CSVAdapter(csv_file.name))
                
                info = store.get_import_info(import_id)
                self.assertEqual(info['record_count'], 500)
                
                data = store.get_structured_data(import_id)
                self.assertEqual(len(data), 500)
        finally:
            os.unlink(csv_file.name)


# =============================================================================
# REAL API INTEGRATION TESTS (SKIPPED BY DEFAULT)
# =============================================================================
# These tests hit the REAL WHO API - they require internet connection.
# They are skipped by default to avoid slow/flaky CI builds.
#
# To run these tests manually:
#   python -m unittest test.integration.test_data_layer.TestRealAPIImport
#
# These tests verify:
# - Real WHO API is reachable and returns expected format
# - Full end-to-end flow with actual network requests
# - API response parsing works with real data
# =============================================================================

# Uncomment @unittest.skip below to skip these tests in automated runs
# @unittest.skip("Skipped by default - requires internet. Run manually to test real API.")
class TestRealAPIImport(unittest.TestCase):
    """Integration tests using REAL WHO API calls."""
    
    def setUp(self):
        """Set up temp database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    def test_real_who_api_life_expectancy(self):
        """Test fetching real life expectancy data from WHO API."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            # Limit to 10 records to keep test fast
            adapter = WHOAPIAdapter("life_expectancy", limit=10)
            
            import_id = store.import_data(adapter)
            
            self.assertIsNotNone(import_id)
            
            info = store.get_import_info(import_id)
            self.assertEqual(info['source_type'], 'api')
            self.assertGreater(info['record_count'], 0)
            
            data = store.get_structured_data(import_id)
            self.assertIn('country_code', data.columns)
            self.assertIn('value', data.columns)
    
    def test_real_who_api_infant_mortality(self):
        """Test fetching real infant mortality data from WHO API."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter("infant_mortality", limit=10)
            
            import_id = store.import_data(adapter)
            
            info = store.get_import_info(import_id)
            self.assertEqual(info['source_type'], 'api')
            self.assertIn('infant_mortality', info['source_name'])
    
    def test_real_who_api_vaccination(self):
        """Test fetching real vaccination data from WHO API."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter("vaccination_dtp3", limit=10)
            
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            self.assertGreater(len(data), 0)


if __name__ == "__main__":
    unittest.main()
