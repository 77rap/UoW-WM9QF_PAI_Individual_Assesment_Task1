"""
System Tests for UC2: Import WHO API Data
==========================================

Tests the complete use case of importing data from WHO Global Health Observatory API.
Validates the full workflow from API selection through data display.

Use Case: User imports data from WHO API
Precondition: User has network connectivity (tests use mocking for reliability)
Flow:
1. User clicks "Import WHO API" button
2. User selects health indicator from dropdown
3. User specifies number of records to fetch
4. System fetches data from WHO API
5. System imports data into database
6. System displays imported data in the table

Test Categories:
- Happy Path Tests: Successful API imports with mocked responses
- Edge Case Tests: Various indicator types, record limits
- Error Handling Tests: Network errors, API errors
- Data Integrity Tests: Verifying API data is correctly stored
"""

import unittest
import tempfile
import os
import json

from unittest.mock import patch, MagicMock

import pandas as pd

from src.data.store import DataStore
from src.data.adapters import WHOAPIAdapter
from src.analysis.session import AnalysisSession


# =============================================================================
# SAMPLE API RESPONSES
# =============================================================================

def create_mock_who_response(indicator_code, num_records=5):
    """Create a mock WHO API response with health data."""
    records = []
    countries = ['GBR', 'FRA', 'DEU', 'JPN', 'USA', 'CAN', 'AUS', 'BRA', 'IND', 'CHN']
    
    for i in range(num_records):
        records.append({
            'IndicatorCode': indicator_code,
            'SpatialDim': countries[i % len(countries)],
            'TimeDim': str(2015 + (i % 6)),
            'Dim1': 'BTSX',
            'Dim2': None,
            'NumericValue': 75.0 + i * 0.5,
            'Value': str(75.0 + i * 0.5)
        })
    
    return {'value': records}


def create_mock_requests_response(data_dict, status_code=200):
    """Create a mock requests.Response object."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = data_dict
    mock_response.raise_for_status = MagicMock()
    return mock_response


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================

class TestImportWHOAPIHappyPath(unittest.TestCase):
    """System tests for successful WHO API import scenarios."""
    
    def setUp(self):
        """Set up temp database for testing."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    @patch('src.data.adapters.requests.get')
    def test_import_life_expectancy_indicator(self, mock_get):
        """UC2-HP1: Import life expectancy data from WHO API."""
        # Arrange: Mock API response
        mock_get.return_value = create_mock_requests_response(
            create_mock_who_response('WHOSIS_000001', 10)
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # Act: Import from WHO API
            store = DataStore()
            adapter = WHOAPIAdapter(indicator='life_expectancy', limit=10)
            import_id = store.import_data(adapter)
            
            # Assert: Verify import was successful
            self.assertIsNotNone(import_id)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 10)
            
            # Verify expected columns exist (adapter transforms the data)
            self.assertIn('country_code', data.columns)
            self.assertIn('year', data.columns)
            self.assertIn('value', data.columns)
    
    @patch('src.data.adapters.requests.get')
    def test_import_infant_mortality_indicator(self, mock_get):
        """UC2-HP2: Import infant mortality data from WHO API."""
        mock_get.return_value = create_mock_requests_response(
            create_mock_who_response('MDG_0000000001', 5)
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter(indicator='infant_mortality', limit=5)
            import_id = store.import_data(adapter)
            
            self.assertIsNotNone(import_id)
            
            info = store.get_import_info(import_id)
            self.assertEqual(info['source_type'], 'api')
            self.assertEqual(info['record_count'], 5)
    
    @patch('src.data.adapters.requests.get')
    def test_import_creates_analysis_session(self, mock_get):
        """UC2-HP3: Imported WHO data can be used for analysis."""
        mock_get.return_value = create_mock_requests_response(
            create_mock_who_response('WHOSIS_000001', 20)
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter(indicator='life_expectancy', limit=20)
            import_id = store.import_data(adapter)
            
            # Create session from imported data
            data = store.get_structured_data(import_id)
            info = store.get_import_info(import_id)
            session = AnalysisSession(data, source_name=info['source_name'])
            
            # Verify session is functional
            self.assertEqual(session.get_row_count(), 20)
            # value column should be numeric
            self.assertIn('value', session.get_numeric_columns())
    
    @patch('src.data.adapters.requests.get')
    def test_import_persists_to_database(self, mock_get):
        """UC2-HP4: WHO API data persists across DataStore instances."""
        mock_get.return_value = create_mock_requests_response(
            create_mock_who_response('WHOSIS_000001', 5)
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # Import with first store instance
            store1 = DataStore()
            adapter = WHOAPIAdapter(indicator='life_expectancy', limit=5)
            import_id = store1.import_data(adapter)
            
            # Create new store instance
            store2 = DataStore()
            
            # Verify data is accessible
            data = store2.get_structured_data(import_id)
            self.assertEqual(len(data), 5)
    
    @patch('src.data.adapters.requests.get')
    def test_import_multiple_indicators(self, mock_get):
        """UC2-HP5: Import multiple different indicators."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_ids = []
            
            # Import life expectancy
            mock_get.return_value = create_mock_requests_response(
                create_mock_who_response('WHOSIS_000001', 3)
            )
            adapter1 = WHOAPIAdapter(indicator='life_expectancy', limit=3)
            import_ids.append(store.import_data(adapter1))
            
            # Import infant mortality
            mock_get.return_value = create_mock_requests_response(
                create_mock_who_response('MDG_0000000001', 4)
            )
            adapter2 = WHOAPIAdapter(indicator='infant_mortality', limit=4)
            import_ids.append(store.import_data(adapter2))
            
            # Verify both imports exist
            imports = store.list_imports()
            self.assertEqual(len(imports), 2)
            
            # Verify correct record counts
            info1 = store.get_import_info(import_ids[0])
            info2 = store.get_import_info(import_ids[1])
            
            self.assertEqual(info1['record_count'], 3)
            self.assertEqual(info2['record_count'], 4)


# =============================================================================
# INDICATOR TYPE TESTS
# =============================================================================

class TestImportWHOAPIIndicators(unittest.TestCase):
    """System tests for different WHO API indicators."""
    
    def setUp(self):
        """Set up temp database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    @patch('src.data.adapters.requests.get')
    def test_all_supported_indicators_import(self, mock_get):
        """UC2-IND1: All supported indicators can be imported."""
        indicators = [
            'life_expectancy',
            'infant_mortality',
            'neonatal_mortality',
            'vaccination_dtp3',
            'vaccination_measles',
        ]
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            for indicator in indicators:
                # Set up mock for each indicator
                mock_get.return_value = create_mock_requests_response(
                    create_mock_who_response('TEST_CODE', 2)
                )
                
                with self.subTest(indicator=indicator):
                    adapter = WHOAPIAdapter(indicator=indicator, limit=2)
                    import_id = store.import_data(adapter)
                    
                    self.assertIsNotNone(import_id)
                    data = store.get_structured_data(import_id)
                    self.assertEqual(len(data), 2)
    
    def test_indicator_code_mapping(self):
        """UC2-IND2: Verify indicator names map to correct API codes."""
        # These are the expected mappings
        expected_mappings = {
            'life_expectancy': 'WHOSIS_000001',
            'infant_mortality': 'MDG_0000000001',
            'neonatal_mortality': 'MDG_0000000003',
            'vaccination_dtp3': 'WHS4_100',
            'vaccination_measles': 'WHS8_110',
        }
        
        for indicator_name, expected_code in expected_mappings.items():
            with self.subTest(indicator=indicator_name):
                adapter = WHOAPIAdapter(indicator=indicator_name, limit=1)
                self.assertEqual(adapter.indicator_code, expected_code)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestImportWHOAPIEdgeCases(unittest.TestCase):
    """System tests for WHO API import edge cases."""
    
    def setUp(self):
        """Set up temp database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    @patch('src.data.adapters.requests.get')
    def test_import_with_minimum_records(self, mock_get):
        """UC2-EC1: Import with minimum record limit."""
        mock_get.return_value = create_mock_requests_response(
            create_mock_who_response('WHOSIS_000001', 1)
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter(indicator='life_expectancy', limit=1)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 1)
    
    @patch('src.data.adapters.requests.get')
    def test_import_with_large_record_limit(self, mock_get):
        """UC2-EC2: Import with large record limit."""
        mock_get.return_value = create_mock_requests_response(
            create_mock_who_response('WHOSIS_000001', 500)
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter(indicator='life_expectancy', limit=500)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            self.assertEqual(len(data), 500)
    
    @patch('src.data.adapters.requests.get')
    def test_import_empty_api_response(self, mock_get):
        """UC2-EC3: Handle API returning no records."""
        mock_get.return_value = create_mock_requests_response({'value': []})
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter(indicator='life_expectancy', limit=10)
            
            # System raises ValueError for empty data
            with self.assertRaises(ValueError) as context:
                store.import_data(adapter)
            
            self.assertIn('No records', str(context.exception))
    
    def test_unknown_indicator_uses_raw_code(self):
        """UC2-EC4: Unknown indicator name uses value as raw API code."""
        # If indicator is not in INDICATORS dict, it should be used as raw code
        adapter = WHOAPIAdapter(indicator='CUSTOM_CODE_123', limit=10)
        self.assertEqual(adapter.indicator_code, 'CUSTOM_CODE_123')


# =============================================================================
# DATA INTEGRITY TESTS
# =============================================================================

class TestImportWHOAPIDataIntegrity(unittest.TestCase):
    """System tests verifying data integrity after WHO API import."""
    
    def setUp(self):
        """Set up temp database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    @patch('src.data.adapters.requests.get')
    def test_api_values_preserved(self, mock_get):
        """UC2-DI1: API values are correctly stored in database."""
        api_response = {
            'value': [
                {
                    'IndicatorCode': 'WHOSIS_000001',
                    'SpatialDim': 'GBR',
                    'TimeDim': '2020',
                    'Dim1': 'BTSX',
                    'Dim2': None,
                    'NumericValue': 81.2,
                    'Value': '81.2'
                },
                {
                    'IndicatorCode': 'WHOSIS_000001',
                    'SpatialDim': 'FRA',
                    'TimeDim': '2020',
                    'Dim1': 'BTSX',
                    'Dim2': None,
                    'NumericValue': 82.5,
                    'Value': '82.5'
                }
            ]
        }
        
        mock_get.return_value = create_mock_requests_response(api_response)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter(indicator='life_expectancy', limit=2)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            
            # Verify values match API response (adapter transforms to cleaned format)
            gbr_row = data[data['country_code'] == 'GBR'].iloc[0]
            # Year may be stored as int or string depending on database type inference
            self.assertEqual(str(gbr_row['year']), '2020')
            self.assertAlmostEqual(float(gbr_row['value']), 81.2, places=1)
    
    @patch('src.data.adapters.requests.get')
    def test_import_info_shows_api_source(self, mock_get):
        """UC2-DI2: Import metadata correctly shows API as source."""
        mock_get.return_value = create_mock_requests_response(
            create_mock_who_response('WHOSIS_000001', 5)
        )
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = WHOAPIAdapter(indicator='life_expectancy', limit=5)
            import_id = store.import_data(adapter)
            
            info = store.get_import_info(import_id)
            
            self.assertEqual(info['source_type'], 'api')
            self.assertIn('WHO', info['source_name'])


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestImportWHOAPIErrorHandling(unittest.TestCase):
    """System tests for WHO API import error handling."""
    
    def setUp(self):
        """Set up temp database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    @patch('src.data.adapters.requests.get')
    def test_network_error_handling(self, mock_get):
        """UC2-EH1: Network errors are handled gracefully."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError('Network unavailable')
        
        adapter = WHOAPIAdapter(indicator='life_expectancy', limit=10)
        
        with self.assertRaises(requests.exceptions.ConnectionError):
            adapter.fetch()
    
    @patch('src.data.adapters.requests.get')
    def test_timeout_error_handling(self, mock_get):
        """UC2-EH2: Timeout errors are handled."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout('Request timed out')
        
        adapter = WHOAPIAdapter(indicator='life_expectancy', limit=10)
        
        with self.assertRaises(requests.exceptions.Timeout):
            adapter.fetch()
    
    @patch('src.data.adapters.requests.get')
    def test_http_error_handling(self, mock_get):
        """UC2-EH3: HTTP errors (4xx, 5xx) are handled."""
        import requests
        
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('404 Not Found')
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter(indicator='life_expectancy', limit=10)
        
        with self.assertRaises(requests.exceptions.HTTPError):
            adapter.fetch()


if __name__ == '__main__':
    unittest.main()
