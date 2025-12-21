"""
System Tests for UC8: Generate Charts
======================================

Tests the complete use case of generating charts/visualizations.
Validates the full workflow from selecting columns through chart generation.

Use Case: User creates visualizations
Precondition: User has selected a dataset
Flow:
1. User selects X-axis column
2. User selects Y-axis column(s)
3. User optionally selects Group By column
4. User selects aggregation method
5. System generates chart
6. User can export chart to file

Test Categories:
- Basic Chart Tests: Simple chart generation
- Grouped Chart Tests: Charts with grouping
- Multi-line Chart Tests: Charts with multiple Y columns
- Aggregation Tests: Different aggregation methods
- Export Tests: Exporting charts to files
"""

import unittest
import tempfile
import os
import csv

from unittest.mock import patch, MagicMock

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for testing
import matplotlib.pyplot as plt

from src.data.store import DataStore
from src.data.adapters import CSVAdapter
from src.analysis.session import AnalysisSession


# =============================================================================
# TEST FIXTURES
# =============================================================================

def create_test_csv_for_charts(temp_files_list):
    """Create a CSV file with data for chart testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['country', 'region', 'year', 'population', 'life_expectancy', 'gdp'])
    writer.writerow(['UK', 'Europe', '2018', '66000000', '81.0', '2800000'])
    writer.writerow(['UK', 'Europe', '2019', '66500000', '81.2', '2850000'])
    writer.writerow(['UK', 'Europe', '2020', '67000000', '80.5', '2700000'])
    writer.writerow(['France', 'Europe', '2018', '64000000', '82.3', '2700000'])
    writer.writerow(['France', 'Europe', '2019', '64500000', '82.5', '2750000'])
    writer.writerow(['France', 'Europe', '2020', '65000000', '82.0', '2600000'])
    writer.writerow(['Japan', 'Asia', '2018', '125000000', '84.0', '5000000'])
    writer.writerow(['Japan', 'Asia', '2019', '125500000', '84.2', '5100000'])
    writer.writerow(['Japan', 'Asia', '2020', '126000000', '84.5', '4900000'])
    
    temp_file.close()
    return temp_file.name


# =============================================================================
# BASIC CHART TESTS
# =============================================================================

class TestBasicCharts(unittest.TestCase):
    """System tests for basic chart generation."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files and close plots."""
        plt.close('all')
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_generate_chart_returns_figure(self):
        """UC8-BC1: Chart generation returns matplotlib figure."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            figure = session.generate_chart('year', 'population', show=False)
            
            self.assertIsNotNone(figure)
            self.assertIsInstance(figure, plt.Figure)
    
    def test_generate_chart_with_sum_aggregation(self):
        """UC8-BC2: Chart with sum aggregation."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Should not raise exception
            figure = session.generate_chart(
                'year', 'population', 
                aggregation='sum', 
                show=False
            )
            
            self.assertIsNotNone(figure)
    
    def test_generate_chart_with_mean_aggregation(self):
        """UC8-BC3: Chart with mean aggregation."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            figure = session.generate_chart(
                'year', 'life_expectancy',
                aggregation='mean',
                show=False
            )
            
            self.assertIsNotNone(figure)
    
    def test_generate_chart_with_count_aggregation(self):
        """UC8-BC4: Chart with count aggregation."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            figure = session.generate_chart(
                'region', 'population',
                aggregation='count',
                show=False
            )
            
            self.assertIsNotNone(figure)


# =============================================================================
# GROUPED CHART TESTS
# =============================================================================

class TestGroupedCharts(unittest.TestCase):
    """System tests for grouped chart generation."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files and close plots."""
        plt.close('all')
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_generate_grouped_chart(self):
        """UC8-GC1: Chart with group by column."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            figure = session.generate_chart(
                'year', 'population',
                group_by='country',
                show=False
            )
            
            self.assertIsNotNone(figure)
    
    def test_generate_grouped_chart_by_region(self):
        """UC8-GC2: Chart grouped by region."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            figure = session.generate_chart(
                'year', 'life_expectancy',
                group_by='region',
                aggregation='mean',
                show=False
            )
            
            self.assertIsNotNone(figure)


# =============================================================================
# MULTI-LINE CHART TESTS
# =============================================================================

class TestMultiLineCharts(unittest.TestCase):
    """System tests for multi-line chart generation."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files and close plots."""
        plt.close('all')
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_generate_multi_line_chart(self):
        """UC8-ML1: Multi-line chart with multiple Y columns."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            figure = session.generate_multi_line_chart(
                'year',
                ['population', 'gdp'],
                show=False
            )
            
            self.assertIsNotNone(figure)
    
    def test_multi_line_chart_with_aggregation(self):
        """UC8-ML2: Multi-line chart with mean aggregation."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            figure = session.generate_multi_line_chart(
                'year',
                ['life_expectancy', 'population'],
                aggregation='mean',
                show=False
            )
            
            self.assertIsNotNone(figure)


# =============================================================================
# CHART EXPORT TESTS
# =============================================================================

class TestChartExport(unittest.TestCase):
    """System tests for chart export functionality."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files and close plots."""
        plt.close('all')
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_export_chart_to_png(self):
        """UC8-EX1: Export chart to PNG file."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.generate_chart('year', 'population', show=False)
            
            # Export to temp file
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.png'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            result = session.export_chart(export_file.name)
            
            self.assertTrue(result)
            self.assertTrue(os.path.exists(export_file.name))
            self.assertGreater(os.path.getsize(export_file.name), 0)
    
    def test_export_chart_without_generating_first(self):
        """UC8-EX2: Export without generating chart raises ValueError."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Don't generate chart first
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.png'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            with self.assertRaises(ValueError):
                session.export_chart(export_file.name)


# =============================================================================
# CHART WITH OPERATIONS TESTS
# =============================================================================

class TestChartsWithOperations(unittest.TestCase):
    """System tests for charts with filters/clean/sort applied."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files and close plots."""
        plt.close('all')
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_chart_with_filter_applied(self):
        """UC8-OP1: Chart uses filtered data."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter to Europe only
            session.add_filter_text('region', ['Europe'])
            
            figure = session.generate_chart(
                'year', 'population',
                group_by='country',
                show=False
            )
            
            self.assertIsNotNone(figure)
    
    def test_chart_with_sort_applied(self):
        """UC8-OP2: Chart works with sorted data."""
        csv_path = create_test_csv_for_charts(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            session.set_sort('year', ascending=True)
            
            figure = session.generate_chart('year', 'gdp', show=False)
            
            self.assertIsNotNone(figure)


if __name__ == '__main__':
    unittest.main()
