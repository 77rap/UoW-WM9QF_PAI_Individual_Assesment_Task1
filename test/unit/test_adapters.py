"""
Unit tests for data adapters module.

Tests for DataAdapter base class, CSVAdapter, and WHOAPIAdapter,
covering normal operation, edge cases, and failure modes.
"""

import unittest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import tempfile
import os

from src.data.adapters import DataAdapter, CSVAdapter, WHOAPIAdapter


class TestDataAdapter(unittest.TestCase):
    """Test suite for DataAdapter base class."""
    
    def test_abstract_methods_exist(self):
        """Test that abstract methods are defined."""
        adapter = DataAdapter()
        self.assertTrue(hasattr(adapter, 'fetch'))
        self.assertTrue(hasattr(adapter, 'source_name'))
        self.assertTrue(hasattr(adapter, 'source_type'))
    
    def test_fetch_returns_none(self):
        """Test fetch method returns None by default."""
        adapter = DataAdapter()
        result = adapter.fetch()
        self.assertIsNone(result)
    
    def test_source_name_returns_none(self):
        """Test source_name property returns None by default."""
        adapter = DataAdapter()
        self.assertIsNone(adapter.source_name)
    
    def test_source_type_returns_none(self):
        """Test source_type property returns None by default."""
        adapter = DataAdapter()
        self.assertIsNone(adapter.source_type)


class TestCSVAdapter(unittest.TestCase):
    """Test suite for CSVAdapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_csv(self, filename, content):
        """Helper to create a test CSV file."""
        filepath = os.path.join(self.test_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    # Normal operation tests
    def test_init_with_valid_file(self):
        """Test initialization with existing file."""
        filepath = self._create_test_csv("health_data.csv", "country_code,life_expectancy\nGBR,81.2")
        adapter = CSVAdapter(filepath)
        self.assertIsInstance(adapter.filepath, Path)
        self.assertEqual(adapter.filepath.name, "health_data.csv")
    
    def test_init_with_path_object(self):
        """Test initialization with Path object."""
        filepath = self._create_test_csv("mortality.csv", "country_code,mortality_rate\nUSA,8.3")
        adapter = CSVAdapter(Path(filepath))
        self.assertIsInstance(adapter.filepath, Path)
    
    def test_fetch_basic_csv(self):
        """Test fetching data from basic health CSV."""
        filepath = self._create_test_csv("health.csv", "country_code,year,life_expectancy\nGBR,2020,81.2\nFRA,2020,82.3")
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["country_code"], "GBR")
        self.assertEqual(records[0]["life_expectancy"], "81.2")
        self.assertEqual(records[1]["country_code"], "FRA")
        self.assertEqual(records[1]["life_expectancy"], "82.3")
    
    def test_fetch_empty_strings_to_none(self):
        """Test that empty strings are converted to None."""
        filepath = self._create_test_csv("health.csv", "country_code,mortality_rate\nGBR,\nFRA,7.5")
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        
        self.assertIsNone(records[0]["mortality_rate"])
        self.assertEqual(records[1]["mortality_rate"], "7.5")
    
    def test_source_name_property(self):
        """Test source_name returns filename."""
        filepath = self._create_test_csv("vaccination_data.csv", "country_code\nGBR")
        adapter = CSVAdapter(filepath)
        self.assertEqual(adapter.source_name, "vaccination_data.csv")
    
    def test_source_type_property(self):
        """Test source_type returns 'csv'."""
        filepath = self._create_test_csv("mortality.csv", "country_code\nUSA")
        adapter = CSVAdapter(filepath)
        self.assertEqual(adapter.source_type, "csv")
    
    # Edge cases
    def test_empty_csv_file(self):
        """Test fetching from empty CSV returns empty list."""
        filepath = self._create_test_csv("empty_health.csv", "")
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        self.assertEqual(records, [])
    
    def test_csv_with_only_headers(self):
        """Test CSV with headers but no data."""
        filepath = self._create_test_csv("headers_only.csv", "country_code,life_expectancy\n")
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        self.assertEqual(records, [])
    
    def test_csv_with_single_row(self):
        """Test CSV with single health record."""
        filepath = self._create_test_csv("single.csv", "country_code,life_expectancy\nGBR,81.2")
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        self.assertEqual(len(records), 1)
    
    def test_csv_with_special_characters(self):
        """Test CSV with special characters in health data."""
        filepath = self._create_test_csv(
            "special.csv", 
            "country,health_note\nUK,Has comma, in note\nUSA,Has \"quotes\""
        )
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        self.assertTrue(len(records) > 0)
    
    def test_csv_with_unicode_characters(self):
        """Test CSV with unicode characters in country names."""
        filepath = self._create_test_csv(
            "unicode.csv",
            "country,life_expectancy\nSão Tomé,66.5\nCôte d'Ivoire,57.8"
        )
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        self.assertEqual(records[0]["country"], "São Tomé")
        self.assertEqual(records[1]["country"], "Côte d'Ivoire")
    
    def test_csv_with_bom(self):
        """Test CSV with BOM (Byte Order Mark)."""
        filepath = os.path.join(self.test_dir, "bom_health.csv")
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write("country_code,life_expectancy\nGBR,81.2")
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        self.assertIn("country_code", records[0].keys())
    
    def test_csv_with_whitespace(self):
        """Test CSV with whitespace in values."""
        filepath = self._create_test_csv(
            "whitespace.csv",
            "country_code,life_expectancy\n GBR ,81.2\n FRA ,82.3"
        )
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        self.assertEqual(records[0]["country_code"], " GBR ")
    
    def test_csv_with_all_empty_values(self):
        """Test CSV where all values are empty."""
        filepath = self._create_test_csv("all_empty.csv", "col1,col2\n,\n,")
        adapter = CSVAdapter(filepath)
        records = adapter.fetch()
        self.assertIsNone(records[0]["col1"])
        self.assertIsNone(records[0]["col2"])
    
    # Failure cases
    def test_file_not_found(self):
        """Test FileNotFoundError raised for non-existent file."""
        with self.assertRaises(FileNotFoundError):
            CSVAdapter("nonexistent.csv")
    
    def test_file_not_found_with_message(self):
        """Test FileNotFoundError contains filename."""
        try:
            CSVAdapter("missing.csv")
        except FileNotFoundError as e:
            self.assertIn("missing.csv", str(e))
    
    def test_directory_instead_of_file(self):
        """Test fetch with directory path fails with PermissionError."""
        adapter = CSVAdapter(self.test_dir)
        with self.assertRaises(PermissionError):
            adapter.fetch()


class TestWHOAPIAdapter(unittest.TestCase):
    """Test suite for WHOAPIAdapter."""
    
    # Normal operation tests
    def test_init_with_default_indicator(self):
        """Test initialization with default indicator."""
        adapter = WHOAPIAdapter()
        self.assertEqual(adapter.indicator_name, "life_expectancy")
        self.assertEqual(adapter.indicator_code, "WHOSIS_000001")
        self.assertEqual(adapter.limit, 1000)
    
    def test_init_with_known_indicator(self):
        """Test initialization with known indicator name."""
        adapter = WHOAPIAdapter(indicator="infant_mortality")
        self.assertEqual(adapter.indicator_name, "infant_mortality")
        self.assertEqual(adapter.indicator_code, "MDG_0000000001")
    
    def test_init_with_raw_indicator_code(self):
        """Test initialization with raw WHO code."""
        adapter = WHOAPIAdapter(indicator="CUSTOM_CODE_123")
        self.assertEqual(adapter.indicator_name, "CUSTOM_CODE_123")
        self.assertEqual(adapter.indicator_code, "CUSTOM_CODE_123")
    
    def test_init_with_custom_limit(self):
        """Test initialization with custom limit."""
        adapter = WHOAPIAdapter(limit=500)
        self.assertEqual(adapter.limit, 500)
    
    def test_source_name_property(self):
        """Test source_name property format."""
        adapter = WHOAPIAdapter(indicator="life_expectancy")
        self.assertEqual(adapter.source_name, "WHO_GHO_life_expectancy")
    
    def test_source_type_property(self):
        """Test source_type returns 'api'."""
        adapter = WHOAPIAdapter()
        self.assertEqual(adapter.source_type, "api")
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_successful_response(self, mock_get):
        """Test fetch with successful API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "IndicatorCode": "WHOSIS_000001",
                    "SpatialDim": "USA",
                    "TimeDim": 2020,
                    "NumericValue": 78.5,
                    "Dim1": "BTSX",
                    "Dim2": None
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter()
        records = adapter.fetch()
        
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["indicator_code"], "WHOSIS_000001")
        self.assertEqual(records[0]["country_code"], "USA")
        self.assertEqual(records[0]["year"], 2020)
        self.assertEqual(records[0]["value"], 78.5)
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_empty_response(self, mock_get):
        """Test fetch with empty API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter()
        records = adapter.fetch()
        
        self.assertEqual(records, [])
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_missing_value_key(self, mock_get):
        """Test fetch when 'value' key is missing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter()
        records = adapter.fetch()
        
        self.assertEqual(records, [])
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_with_missing_fields(self, mock_get):
        """Test fetch handles missing fields in records."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [{"IndicatorCode": "TEST"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter()
        records = adapter.fetch()
        
        self.assertEqual(records[0]["indicator_code"], "TEST")
        self.assertIsNone(records[0]["country_code"])
        self.assertIsNone(records[0]["value"])
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_multiple_records(self, mock_get):
        """Test fetch with multiple records."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"IndicatorCode": "A", "SpatialDim": "USA"},
                {"IndicatorCode": "B", "SpatialDim": "CAN"},
                {"IndicatorCode": "C", "SpatialDim": "MEX"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter()
        records = adapter.fetch()
        
        self.assertEqual(len(records), 3)
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_calls_api_with_correct_params(self, mock_get):
        """Test fetch calls API with correct URL and parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter(limit=100)
        adapter.fetch()
        
        expected_url = "https://ghoapi.azureedge.net/api/WHOSIS_000001"
        mock_get.assert_called_once_with(
            expected_url,
            params={"$top": 100},
            timeout=30
        )
    
    # Edge cases
    @patch('src.data.adapters.requests.get')
    def test_fetch_with_zero_limit(self, mock_get):
        """Test fetch with limit=0."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter(limit=0)
        adapter.fetch()
        
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]["params"]["$top"], 0)
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_with_very_large_limit(self, mock_get):
        """Test fetch with very large limit."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter(limit=999999)
        adapter.fetch()
        
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]["params"]["$top"], 999999)
    
    def test_all_predefined_indicators(self):
        """Test all predefined indicator mappings."""
        indicators = {
            "life_expectancy": "WHOSIS_000001",
            "infant_mortality": "MDG_0000000001",
            "vaccination_dtp3": "WHS4_100",
            "vaccination_measles": "WHS8_110",
            "neonatal_mortality": "MDG_0000000003",
        }
        
        for name, code in indicators.items():
            adapter = WHOAPIAdapter(indicator=name)
            self.assertEqual(adapter.indicator_code, code)
    
    # Failure cases
    @patch('src.data.adapters.requests.get')
    def test_fetch_http_error(self, mock_get):
        """Test fetch raises error on HTTP failure."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter()
        with self.assertRaises(Exception):
            adapter.fetch()
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_timeout(self, mock_get):
        """Test fetch with timeout error."""
        import requests
        mock_get.side_effect = requests.Timeout("Request timed out")
        
        adapter = WHOAPIAdapter()
        with self.assertRaises(requests.Timeout):
            adapter.fetch()
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_connection_error(self, mock_get):
        """Test fetch with connection error."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        
        adapter = WHOAPIAdapter()
        with self.assertRaises(requests.ConnectionError):
            adapter.fetch()
    
    @patch('src.data.adapters.requests.get')
    def test_fetch_invalid_json(self, mock_get):
        """Test fetch with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        adapter = WHOAPIAdapter()
        with self.assertRaises(ValueError):
            adapter.fetch()


if __name__ == "__main__":
    unittest.main()
