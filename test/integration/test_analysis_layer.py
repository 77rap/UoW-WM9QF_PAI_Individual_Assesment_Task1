"""
Integration Tests for Analysis Layer
======================================

Tests the complete analysis flow from AnalysisSession through operations
to chart generation. Uses real DataStore with temporary database.

Test Categories:
- Session Creation Tests: Creating sessions from DataStore data
- Clean Operation Flow Tests: End-to-end cleaning workflows
- Filter Operation Flow Tests: End-to-end filtering workflows
- Sort Operation Flow Tests: End-to-end sorting workflows
- Combined Operations Tests: Multiple operations working together
- Chart Generation Flow Tests: Complete chart generation from session
- Export Tests: Chart export functionality
"""

import unittest
import tempfile
import os
import csv
import shutil

from unittest.mock import patch

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for testing
import matplotlib.pyplot as plt

from src.data.store import DataStore
from src.data.adapters import CSVAdapter
from src.analysis.session import AnalysisSession
from src.analysis.charts import generate_chart, generate_multi_line_chart, export_chart
from src.analysis.operations import CleanOperation, FilterOperation


# =============================================================================
# SESSION CREATION FROM DATASTORE TESTS
# =============================================================================

class TestSessionFromDataStore(unittest.TestCase):
    """Integration tests for creating AnalysisSession from DataStore data."""
    
    def setUp(self):
        """Set up temp database and health CSV file."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Create health data CSV
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country', 'year', 'life_expectancy', 'population'])
        writer.writerow(['United Kingdom', '2020', '81.2', '67886011'])
        writer.writerow(['France', '2020', '82.3', '65273511'])
        writer.writerow(['Germany', '2020', '81.0', '83783942'])
        writer.writerow(['Japan', '2020', '84.5', '126476461'])
        writer.writerow(['USA', '2020', '77.0', '331002651'])
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
        
        # Reset operation IDs for consistent testing
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
        plt.close('all')
    
    def test_create_session_from_imported_data(self):
        """Test creating AnalysisSession from DataStore imported data."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(self.test_csv_path)
            import_id = store.import_data(adapter)
            
            # Get data and create session
            data = store.get_structured_data(import_id)
            info = store.get_import_info(import_id)
            
            session = AnalysisSession(data, source_name=info['source_name'])
            
            self.assertEqual(session.get_row_count(), 5)
            self.assertEqual(session.get_original_row_count(), 5)
            self.assertIn('country', session.get_columns())
    
    def test_session_data_isolation_from_store(self):
        """Test that session data is isolated from DataStore."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(self.test_csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Modify original DataFrame
            data['life_expectancy'] = 0
            
            # Session data should be unchanged
            session_data = session.get_current_view()
            self.assertGreater(session_data['life_expectancy'].mean(), 0)
    
    def test_multiple_sessions_from_same_import(self):
        """Test creating multiple independent sessions from same import."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(self.test_csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            
            session1 = AnalysisSession(data)
            session2 = AnalysisSession(data)
            
            # Add operation to session1 only
            session1.add_filter_text('country', ['Japan'])
            
            # Session2 should be unaffected
            self.assertEqual(session1.get_row_count(), 1)
            self.assertEqual(session2.get_row_count(), 5)


# =============================================================================
# CLEAN OPERATION FLOW TESTS
# =============================================================================

class TestCleanOperationFlow(unittest.TestCase):
    """Integration tests for complete cleaning workflows."""
    
    def setUp(self):
        """Set up temp database and CSV with missing values."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Create health data CSV with missing values
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country', 'year', 'life_expectancy', 'infant_mortality'])
        writer.writerow(['United Kingdom', '2020', '81.2', '3.7'])
        writer.writerow(['France', '2020', '', '3.6'])  # Missing life_expectancy
        writer.writerow(['Germany', '2020', '81.0', 'N/A'])  # N/A infant_mortality
        writer.writerow(['Japan', '2020', '84.5', ''])  # Missing infant_mortality
        writer.writerow(['USA', '2020', 'Unknown', '5.4'])  # Unknown life_expectancy
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
        
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
        plt.close('all')
    
    def test_clean_removes_empty_values(self):
        """Test that clean operation removes rows with empty/null values."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_clean(['life_expectancy'])
            
            view = session.get_current_view()
            
            # Clean removes rows with null/empty in life_expectancy column
            # France (empty) and Germany (empty) are removed = 3 remaining
            self.assertEqual(len(view), 3)
    
    def test_clean_removes_custom_missing_values(self):
        """Test that clean operation removes custom missing value indicators."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_clean(['life_expectancy'], missing_values=['Unknown', 'N/A'])
            
            view = session.get_current_view()
            
            # Should remove France (empty) and USA (Unknown)
            self.assertEqual(len(view), 3)
    
    def test_multiple_clean_operations_stack(self):
        """Test that multiple clean operations are applied sequentially."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Clean life_expectancy first
            session.add_clean(['life_expectancy'])
            
            # Then clean infant_mortality
            session.add_clean(['infant_mortality'], missing_values=['N/A'])
            
            view = session.get_current_view()
            
            # Should only have UK (all others have missing data)
            self.assertEqual(len(view), 1)
            self.assertEqual(view.iloc[0]['country'], 'United Kingdom')
    
    def test_clean_then_filter_flow(self):
        """Test clean followed by filter operations."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # First clean
            session.add_clean(['infant_mortality'], missing_values=['N/A'])
            
            # Then filter - after cleaning, remaining: UK, France, USA
            session.add_filter_text( 'country', ['United Kingdom', 'France'])
            
            view = session.get_current_view()
            
            self.assertEqual(len(view), 2)
            countries = view['country'].tolist()
            self.assertIn('United Kingdom', countries)
            self.assertIn('France', countries)


# =============================================================================
# FILTER OPERATION FLOW TESTS
# =============================================================================

class TestFilterOperationFlow(unittest.TestCase):
    """Integration tests for complete filtering workflows."""
    
    def setUp(self):
        """Set up temp database and health CSV file."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Create health data CSV with various values
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country', 'region', 'year', 'life_expectancy', 'gdp_per_capita'])
        writer.writerow(['United Kingdom', 'Europe', '2018', '81.0', '42000'])
        writer.writerow(['United Kingdom', 'Europe', '2019', '81.1', '43000'])
        writer.writerow(['United Kingdom', 'Europe', '2020', '81.2', '40000'])
        writer.writerow(['France', 'Europe', '2018', '82.0', '41000'])
        writer.writerow(['France', 'Europe', '2019', '82.2', '42000'])
        writer.writerow(['France', 'Europe', '2020', '82.3', '39000'])
        writer.writerow(['Japan', 'Asia', '2018', '84.0', '39000'])
        writer.writerow(['Japan', 'Asia', '2019', '84.3', '40000'])
        writer.writerow(['Japan', 'Asia', '2020', '84.5', '38000'])
        writer.writerow(['USA', 'Americas', '2018', '78.5', '62000'])
        writer.writerow(['USA', 'Americas', '2019', '78.8', '65000'])
        writer.writerow(['USA', 'Americas', '2020', '77.0', '63000'])
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
        
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
        plt.close('all')
    
    def test_text_filter_single_value(self):
        """Test text filter with single value."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_filter_text( 'country', ['Japan'])
            
            view = session.get_current_view()
            
            self.assertEqual(len(view), 3)
            self.assertTrue(all(view['country'] == 'Japan'))
    
    def test_text_filter_multiple_values(self):
        """Test text filter with multiple values."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_filter_text( 'region', ['Europe', 'Asia'])
            
            view = session.get_current_view()
            
            self.assertEqual(len(view), 9)  # UK (3) + France (3) + Japan (3)
    
    def test_numeric_filter_range(self):
        """Test numeric filter with range."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_filter_numeric('life_expectancy', 82.0, 85.0)
            
            view = session.get_current_view()
            
            # France and Japan entries with life_expectancy >= 82
            self.assertEqual(len(view), 6)
    
    def test_multiple_filters_combine(self):
        """Test that multiple filters are applied together (AND logic)."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Filter by region
            session.add_filter_text( 'region', ['Europe'])
            
            # Then filter by life expectancy > 81.5
            session.add_filter_numeric('life_expectancy', 81.5, 100)
            
            view = session.get_current_view()
            
            # Only France entries >= 81.5
            self.assertEqual(len(view), 3)
            self.assertTrue(all(view['country'] == 'France'))
    
    def test_filter_preserves_all_columns(self):
        """Test that filtering preserves all data columns."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_filter_text( 'country', ['Japan'])
            
            view = session.get_current_view()
            
            original_columns = set(session.get_columns())
            view_columns = set(view.columns)
            
            self.assertEqual(original_columns, view_columns)
    
    def test_remove_filter_restores_data(self):
        """Test that removing a filter restores the data."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            filter_id = session.add_filter_text( 'country', ['Japan'])
            self.assertEqual(session.get_row_count(), 3)
            
            session.remove_filter(filter_id)
            self.assertEqual(session.get_row_count(), 12)


# =============================================================================
# SORT OPERATION FLOW TESTS
# =============================================================================

class TestSortOperationFlow(unittest.TestCase):
    """Integration tests for complete sorting workflows."""
    
    def setUp(self):
        """Set up temp database and health CSV file."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Create health data CSV
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country', 'year', 'life_expectancy'])
        writer.writerow(['USA', '2020', '77.0'])
        writer.writerow(['Japan', '2020', '84.5'])
        writer.writerow(['Germany', '2020', '81.0'])
        writer.writerow(['France', '2020', '82.3'])
        writer.writerow(['United Kingdom', '2020', '81.2'])
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
        
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
        plt.close('all')
    
    def test_sort_ascending_numeric(self):
        """Test ascending sort on numeric column."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.set_sort('life_expectancy', ascending=True)
            
            view = session.get_current_view()
            
            self.assertEqual(view.iloc[0]['country'], 'USA')  # Lowest
            self.assertEqual(view.iloc[-1]['country'], 'Japan')  # Highest
    
    def test_sort_descending_numeric(self):
        """Test descending sort on numeric column."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.set_sort('life_expectancy', ascending=False)
            
            view = session.get_current_view()
            
            self.assertEqual(view.iloc[0]['country'], 'Japan')  # Highest
            self.assertEqual(view.iloc[-1]['country'], 'USA')  # Lowest
    
    def test_sort_text_column(self):
        """Test sorting on text column."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.set_sort('country', ascending=True)
            
            view = session.get_current_view()
            
            self.assertEqual(view.iloc[0]['country'], 'France')  # Alphabetically first
            self.assertEqual(view.iloc[-1]['country'], 'USA')  # Alphabetically last
    
    def test_sort_after_filter(self):
        """Test that sort is applied after filter."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Filter to European countries (by life_expectancy range)
            session.add_filter_numeric('life_expectancy', 81.0, 83.0)
            
            # Sort remaining
            session.set_sort('life_expectancy', ascending=False)
            
            view = session.get_current_view()
            
            self.assertEqual(len(view), 3)  # Germany, UK, France
            self.assertEqual(view.iloc[0]['country'], 'France')  # Highest in range
    
    def test_clear_sort(self):
        """Test clearing sort operation."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Get original order
            original = session.get_current_view()['country'].tolist()
            
            # Sort
            session.set_sort('life_expectancy', ascending=True)
            sorted_order = session.get_current_view()['country'].tolist()
            
            # Clear sort
            session.clear_sort()
            cleared_order = session.get_current_view()['country'].tolist()
            
            self.assertNotEqual(original, sorted_order)
            self.assertEqual(original, cleared_order)


# =============================================================================
# COMBINED OPERATIONS TESTS
# =============================================================================

class TestCombinedOperationsFlow(unittest.TestCase):
    """Integration tests for combined clean, filter, and sort operations."""
    
    def setUp(self):
        """Set up temp database and comprehensive health CSV."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Create comprehensive health data CSV with issues
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country', 'region', 'year', 'life_expectancy', 'infant_mortality'])
        writer.writerow(['United Kingdom', 'Europe', '2020', '81.2', '3.7'])
        writer.writerow(['France', 'Europe', '2020', '82.3', ''])  # Missing IM
        writer.writerow(['Germany', 'Europe', '2020', '', '3.2'])  # Missing LE
        writer.writerow(['Japan', 'Asia', '2020', '84.5', '1.9'])
        writer.writerow(['USA', 'Americas', '2020', '77.0', '5.4'])
        writer.writerow(['Canada', 'Americas', '2020', 'N/A', '4.5'])  # N/A LE
        writer.writerow(['Australia', 'Oceania', '2020', '83.0', '3.1'])
        writer.writerow(['Brazil', 'Americas', '2020', '75.9', ''])  # Missing IM
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
        
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
        plt.close('all')
    
    def test_clean_filter_sort_sequence(self):
        """Test complete sequence: clean -> filter -> sort."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Step 1: Clean - remove missing life expectancy
            session.add_clean(['life_expectancy'], missing_values=['N/A'])
            # Remaining: UK, France, Japan, USA, Australia, Brazil (6)
            
            # Step 2: Filter - only life expectancy > 80
            session.add_filter_numeric('life_expectancy', 80.0, 100.0)
            # Remaining: UK, France, Japan, Australia (4)
            
            # Step 3: Sort - by life expectancy descending
            session.set_sort('life_expectancy', ascending=False)
            
            view = session.get_current_view()
            
            self.assertEqual(len(view), 4)
            self.assertEqual(view.iloc[0]['country'], 'Japan')  # Highest: 84.5
            self.assertEqual(view.iloc[-1]['country'], 'United Kingdom')  # Lowest of 4: 81.2
    
    def test_operations_order_matters(self):
        """Test that clean is applied before filter."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Add filter first (logically)
            session.add_filter_text( 'region', ['Americas'])
            # Would give: USA, Canada, Brazil (3)
            
            # Then add clean
            session.add_clean(['life_expectancy'], missing_values=['N/A'])
            # Clean removes Canada (N/A) -> USA, Brazil remain (2)
            
            view = session.get_current_view()
            
            # Clean is applied before filter, so:
            # After clean: removes Germany, Canada (missing LE)
            # Then filter for Americas: USA, Brazil
            self.assertEqual(len(view), 2)
            countries = view['country'].tolist()
            self.assertIn('USA', countries)
            self.assertIn('Brazil', countries)
    
    def test_remove_clean_reapplies_all(self):
        """Test that removing clean operation reapplies remaining operations."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            clean_id = session.add_clean(['life_expectancy'], missing_values=['N/A'])
            session.add_filter_text( 'region', ['Americas'])
            
            # With clean: USA, Brazil
            self.assertEqual(session.get_row_count(), 2)
            
            # Remove clean
            session.remove_clean(clean_id)
            
            # Without clean: USA, Canada, Brazil (all Americas)
            self.assertEqual(session.get_row_count(), 3)
    
    def test_clear_all_operations(self):
        """Test clearing all operations restores original data."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            original_count = session.get_row_count()
            
            # Add operations
            session.add_clean(['life_expectancy'])
            session.add_filter_text( 'region', ['Europe'])
            session.set_sort('life_expectancy', ascending=True)
            
            self.assertLess(session.get_row_count(), original_count)
            
            # Clear all
            session.clear_all_operations()
            
            self.assertEqual(session.get_row_count(), original_count)


# =============================================================================
# CHART GENERATION FLOW TESTS
# =============================================================================

class TestChartGenerationFlow(unittest.TestCase):
    """Integration tests for chart generation from analysis session."""
    
    def setUp(self):
        """Set up temp database and health CSV file."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Create multi-year health data CSV
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country', 'year', 'life_expectancy', 'infant_mortality', 'gdp'])
        writer.writerow(['Japan', '2018', '84.0', '1.9', '39000'])
        writer.writerow(['Japan', '2019', '84.3', '1.8', '40000'])
        writer.writerow(['Japan', '2020', '84.5', '1.7', '38000'])
        writer.writerow(['France', '2018', '82.0', '3.6', '41000'])
        writer.writerow(['France', '2019', '82.2', '3.5', '42000'])
        writer.writerow(['France', '2020', '82.3', '3.4', '39000'])
        writer.writerow(['USA', '2018', '78.5', '5.6', '62000'])
        writer.writerow(['USA', '2019', '78.8', '5.5', '65000'])
        writer.writerow(['USA', '2020', '77.0', '5.4', '63000'])
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
        
        self.temp_dir = tempfile.mkdtemp()
        
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files and figures."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        plt.close('all')
    
    def test_generate_chart_from_session_data(self):
        """Test generating chart from session's current view."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Generate chart from session data
            fig = generate_chart(
                session.get_current_view(),
                x_column='year',
                y_column='life_expectancy',
                show=False
            )
            
            self.assertIsNotNone(fig)
            self.assertIsInstance(fig, plt.Figure)
    
    def test_generate_chart_after_filter(self):
        """Test generating chart from filtered data."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_filter_text( 'country', ['Japan'])
            
            fig = generate_chart(
                session.get_current_view(),
                x_column='year',
                y_column='life_expectancy',
                show=False
            )
            
            self.assertIsNotNone(fig)
    
    def test_generate_grouped_chart(self):
        """Test generating grouped chart with multiple series."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            fig = generate_chart(
                session.get_current_view(),
                x_column='year',
                y_column='life_expectancy',
                group_by='country',
                show=False
            )
            
            self.assertIsNotNone(fig)
    
    def test_generate_multi_line_chart(self):
        """Test generating multi-line chart with multiple Y columns."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_filter_text( 'country', ['Japan'])
            
            fig = generate_multi_line_chart(
                session.get_current_view(),
                x_column='year',
                y_columns=['life_expectancy', 'infant_mortality'],
                show=False
            )
            
            self.assertIsNotNone(fig)
    
    def test_chart_with_aggregation(self):
        """Test chart generation with different aggregation methods."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Test mean aggregation
            fig = generate_chart(
                session.get_current_view(),
                x_column='country',
                y_column='life_expectancy',
                aggregation='mean',
                show=False
            )
            
            self.assertIsNotNone(fig)
    
    def test_export_chart_creates_file(self):
        """Test that chart export creates a file."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            fig = generate_chart(
                session.get_current_view(),
                x_column='year',
                y_column='life_expectancy',
                show=False
            )
            
            export_path = os.path.join(self.temp_dir, 'test_chart.png')
            result = export_chart(fig, export_path)
            
            self.assertTrue(result)
            self.assertTrue(os.path.exists(export_path))
            self.assertGreater(os.path.getsize(export_path), 0)


# =============================================================================
# SUMMARY STATISTICS FLOW TESTS
# =============================================================================

class TestSummaryStatisticsFlow(unittest.TestCase):
    """Integration tests for summary statistics from analysis session."""
    
    def setUp(self):
        """Set up temp database and health CSV file."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Create health data CSV
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country', 'region', 'year', 'life_expectancy', 'population'])
        writer.writerow(['Japan', 'Asia', '2020', '84.5', '126000000'])
        writer.writerow(['France', 'Europe', '2020', '82.3', '67000000'])
        writer.writerow(['Germany', 'Europe', '2020', '81.0', '83000000'])
        writer.writerow(['USA', 'Americas', '2020', '77.0', '331000000'])
        writer.writerow(['UK', 'Europe', '2020', '81.2', '68000000'])
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
        
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
        plt.close('all')
    
    def test_numeric_summary_statistics(self):
        """Test getting summary statistics for numeric column."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            summary = session.get_summary('life_expectancy')
            
            self.assertIn('count', summary)
            self.assertIn('mean', summary)
            self.assertIn('min', summary)
            self.assertIn('max', summary)
            self.assertEqual(summary['count'], 5)
    
    def test_text_summary_statistics(self):
        """Test getting summary statistics for text column."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            summary = session.get_summary('region')
            
            self.assertIn('count', summary)
            self.assertIn('unique_count', summary)
            self.assertIn('mode', summary)
            self.assertEqual(summary['mode'], 'Europe')  # Most common
    
    def test_summary_with_group_by(self):
        """Test summary statistics with group by."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            summary = session.get_summary('life_expectancy', group_by='region')
            
            self.assertIsInstance(summary, pd.DataFrame)
            # The group column contains region values
            self.assertIn('Europe', summary['group'].tolist())
    
    def test_summary_after_filter(self):
        """Test summary statistics after filtering."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            session.add_filter_text( 'region', ['Europe'])
            
            summary = session.get_summary('life_expectancy')
            
            self.assertEqual(summary['count'], 3)  # Only European countries


# =============================================================================
# END-TO-END WORKFLOW TESTS
# =============================================================================

class TestEndToEndWorkflow(unittest.TestCase):
    """Integration tests for complete end-to-end analysis workflows."""
    
    def setUp(self):
        """Set up temp database and health CSV file."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Create realistic health dataset
        self.test_csv = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        writer = csv.writer(self.test_csv)
        writer.writerow(['country', 'region', 'year', 'life_expectancy', 'infant_mortality', 'healthcare_spending'])
        # Add data with some missing values
        writer.writerow(['Japan', 'Asia', '2019', '84.3', '1.8', '4500'])
        writer.writerow(['Japan', 'Asia', '2020', '84.5', '1.7', '4600'])
        writer.writerow(['France', 'Europe', '2019', '82.2', '3.5', '4200'])
        writer.writerow(['France', 'Europe', '2020', '82.3', '', '4300'])  # Missing IM
        writer.writerow(['Germany', 'Europe', '2019', '81.1', '3.2', '5100'])
        writer.writerow(['Germany', 'Europe', '2020', '81.0', '3.1', '5200'])
        writer.writerow(['USA', 'Americas', '2019', '78.8', '5.5', '10500'])
        writer.writerow(['USA', 'Americas', '2020', '77.0', '5.4', '11000'])
        writer.writerow(['UK', 'Europe', '2019', '81.1', '3.8', '3900'])
        writer.writerow(['UK', 'Europe', '2020', '81.2', 'N/A', '4000'])  # N/A IM
        self.test_csv.close()
        self.test_csv_path = self.test_csv.name
        
        self.temp_dir = tempfile.mkdtemp()
        
        CleanOperation._next_id = 1
        FilterOperation._next_id = 1
    
    def tearDown(self):
        """Clean up temp files and figures."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        if os.path.exists(self.test_csv_path):
            os.unlink(self.test_csv_path)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        plt.close('all')
    
    def test_complete_analysis_workflow(self):
        """
        Test complete workflow:
        1. Import data from CSV
        2. Create analysis session
        3. Clean data (remove missing values)
        4. Filter to specific region
        5. Sort by metric
        6. Get summary statistics
        7. Generate and export chart
        """
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # Step 1: Import data
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            
            # Verify import
            info = store.get_import_info(import_id)
            self.assertEqual(info['record_count'], 10)
            
            # Step 2: Create analysis session
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data, source_name=info['source_name'])
            
            self.assertEqual(session.get_original_row_count(), 10)
            
            # Step 3: Clean data - remove missing infant mortality
            session.add_clean(['infant_mortality'], missing_values=['N/A'])
            
            # After clean: 8 rows (removed France 2020, UK 2020)
            self.assertEqual(session.get_row_count(), 8)
            
            # Step 4: Filter to Europe only
            session.add_filter_text( 'region', ['Europe'])
            
            # After filter: 4 rows (France 2019, Germany 2019, Germany 2020, UK 2019)
            self.assertEqual(session.get_row_count(), 4)
            
            # Step 5: Sort by life expectancy descending
            session.set_sort('life_expectancy', ascending=False)
            
            view = session.get_current_view()
            self.assertEqual(view.iloc[0]['country'], 'France')  # Highest LE in filtered set
            
            # Step 6: Get summary statistics
            summary = session.get_summary('life_expectancy')
            self.assertEqual(summary['count'], 4)
            self.assertAlmostEqual(summary['mean'], 81.35, places=1)
            
            # Step 7: Generate and export chart
            fig = generate_chart(
                session.get_current_view(),
                x_column='country',
                y_column='life_expectancy',
                aggregation='mean',
                show=False
            )
            
            export_path = os.path.join(self.temp_dir, 'europe_life_expectancy.png')
            result = export_chart(fig, export_path)
            
            self.assertTrue(result)
            self.assertTrue(os.path.exists(export_path))
    
    def test_comparative_analysis_workflow(self):
        """
        Test comparative analysis workflow:
        1. Import data
        2. Create two sessions for comparison
        3. Apply different filters to each
        4. Compare summary statistics
        """
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            # Create two sessions for comparison
            europe_session = AnalysisSession(data, source_name="Europe Analysis")
            americas_session = AnalysisSession(data, source_name="Americas Analysis")
            
            # Filter each to different regions
            europe_session.add_filter_text( 'region', ['Europe'])
            americas_session.add_filter_text( 'region', ['Americas'])
            
            # Get summaries
            europe_summary = europe_session.get_summary('life_expectancy')
            americas_summary = americas_session.get_summary('life_expectancy')
            
            # Compare - Europe should have higher life expectancy
            self.assertGreater(europe_summary['mean'], americas_summary['mean'])
    
    def test_time_series_analysis_workflow(self):
        """
        Test time series analysis workflow:
        1. Import data
        2. Filter to single country
        3. Sort by year
        4. Generate line chart
        """
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            import_id = store.import_data(CSVAdapter(self.test_csv_path))
            data = store.get_structured_data(import_id)
            
            session = AnalysisSession(data)
            
            # Filter to Japan only
            session.add_filter_text( 'country', ['Japan'])
            
            # Sort by year
            session.set_sort('year', ascending=True)
            
            view = session.get_current_view()
            
            # Verify time series order
            self.assertEqual(len(view), 2)
            # Year may be stored as int or string depending on import
            self.assertEqual(int(view.iloc[0]['year']), 2019)
            self.assertEqual(int(view.iloc[1]['year']), 2020)
            
            # Generate multi-metric chart
            fig = generate_multi_line_chart(
                view,
                x_column='year',
                y_columns=['life_expectancy', 'infant_mortality'],
                show=False
            )
            
            self.assertIsNotNone(fig)


if __name__ == '__main__':
    unittest.main()
