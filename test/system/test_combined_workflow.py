"""
System Tests for UC11: Combined Workflow
=========================================

Tests end-to-end workflows combining multiple operations.
Validates the complete user journey from import through analysis to export.

Use Case: End-to-end workflow combining multiple operations
Flow Examples:
1. Import → Clean → Filter → Sort → Summary → Chart → Export
2. Import CSV → Apply operations → Generate insights
3. Import WHO API → Process → Visualize → Export

Test Categories:
- Full Pipeline Tests: Import to export with all operations
- Analysis Pipeline Tests: Import through summary/charts
- Data Processing Tests: Import with clean, filter, sort combinations
- Multi-Session Tests: Operations across multiple analysis sessions
"""

import unittest
import tempfile
import os
import csv

from unittest.mock import patch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import pandas as pd

from src.data.store import DataStore
from src.data.adapters import CSVAdapter
from src.analysis.session import AnalysisSession


# =============================================================================
# TEST FIXTURES
# =============================================================================

def create_comprehensive_csv(temp_files_list):
    """Create a comprehensive CSV for full workflow testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['country', 'region', 'year', 'population', 'life_expectancy', 'gdp_per_capita'])
    writer.writerow(['United Kingdom', 'Europe', '2020', '67000000', '81.2', '40000'])
    writer.writerow(['France', 'Europe', '2020', '65000000', '82.5', '42000'])
    writer.writerow(['Germany', 'Europe', '2019', '83000000', '81.0', '46000'])
    writer.writerow(['Japan', 'Asia', '2020', '126000000', '84.5', '40000'])
    writer.writerow(['Australia', 'Oceania', '2020', '25000000', '83.0', '55000'])
    writer.writerow(['Brazil', 'Americas', '2018', '212000000', '75.0', '9000'])
    writer.writerow(['India', 'Asia', '2020', '1380000000', '69.5', '2000'])
    writer.writerow(['Canada', 'Americas', '2019', '38000000', '82.0', '46000'])
    writer.writerow(['Nigeria', 'Africa', '2020', '206000000', '54.5', '2200'])
    writer.writerow(['South Africa', 'Africa', '2019', '59000000', '64.0', '6000'])
    
    temp_file.close()
    return temp_file.name


def create_csv_with_issues(temp_files_list):
    """Create a CSV with missing values and data quality issues."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['name', 'category', 'value', 'date'])
    writer.writerow(['Item1', 'A', '100', '2020-01-15'])
    writer.writerow(['Item2', 'B', '', '2020-02-20'])  # Missing value
    writer.writerow(['Item3', 'A', '300', '2020-03-25'])
    writer.writerow(['Item4', '', '400', '2020-04-30'])  # Missing category
    writer.writerow(['Item5', 'B', '500', '2020-05-05'])
    writer.writerow(['Item6', 'A', '600', ''])  # Missing date
    writer.writerow(['Item7', 'C', '700', '2020-07-15'])
    writer.writerow(['Item8', 'C', '800', '2020-08-20'])
    
    temp_file.close()
    return temp_file.name


# =============================================================================
# FULL PIPELINE TESTS
# =============================================================================

class TestFullPipeline(unittest.TestCase):
    """System tests for complete import-to-export workflows."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files and matplotlib figures."""
        plt.close('all')
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_import_filter_sort_export(self):
        """UC11-FP1: Import → Filter → Sort → Export workflow."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # 1. Import
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            self.assertIsNotNone(import_id)
            
            # 2. Create session
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # 3. Filter to Europe only
            session.add_filter_text('region', ['Europe'])
            
            # 4. Sort by life expectancy descending
            session.set_sort('life_expectancy', ascending=False)
            
            # 5. Export
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            export_data = session.get_current_view()
            export_data.to_csv(export_file.name, index=False)
            
            # Verify export
            imported = pd.read_csv(export_file.name)
            
            # Only European countries
            self.assertEqual(len(imported), 3)
            
            # All Europe
            for region in imported['region']:
                self.assertEqual(region, 'Europe')
            
            # Sorted by life expectancy descending
            life_exp = imported['life_expectancy'].tolist()
            self.assertEqual(life_exp, sorted(life_exp, reverse=True))
    
    def test_import_clean_filter_summary_chart(self):
        """UC11-FP2: Import → Clean → Filter → Summary → Chart workflow."""
        csv_path = create_csv_with_issues(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # 1. Import
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # 2. Create session
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            # 3. Clean - remove rows with missing values
            session.add_clean(['value'])
            
            # Verify cleaning worked
            self.assertLess(session.get_row_count(), original_count)
            
            # 4. Filter to category A
            session.add_filter_text('category', ['A'])
            
            # 5. Get summary
            summary = session.get_summary('value')
            
            self.assertIn('count', summary)
            self.assertIn('mean', summary)
            
            # 6. Generate chart
            fig = session.generate_chart(
                x_column='name',
                y_column='value',
                aggregation='sum',
                show=False
            )
            
            self.assertIsInstance(fig, plt.Figure)
    
    def test_complete_analysis_workflow(self):
        """UC11-FP3: Complete analysis from import to insights."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # 1. Import data
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # 2. Verify import
            info = store.get_import_info(import_id)
            self.assertIsNotNone(info)
            
            # 3. Start analysis session
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # 4. Explore data
            columns = session.get_columns()
            self.assertIn('country', columns)
            self.assertIn('life_expectancy', columns)
            
            # 5. Get summary of key metric
            life_summary = session.get_summary('life_expectancy')
            self.assertIn('mean', life_summary)
            self.assertIn('min', life_summary)
            self.assertIn('max', life_summary)
            
            # 6. Filter for analysis
            session.add_filter_numeric('life_expectancy', 70, 100)
            
            # 7. Generate grouped summary
            grouped_summary = session.get_summary('life_expectancy', group_by='region')
            self.assertIsInstance(grouped_summary, pd.DataFrame)
            
            # 8. Create visualization
            fig = session.generate_chart(
                x_column='region',
                y_column='life_expectancy',
                aggregation='mean',
                show=False
            )
            self.assertIsInstance(fig, plt.Figure)
            
            # 9. Export processed data
            export_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv'
            )
            export_file.close()
            self.temp_files.append(export_file.name)
            
            session.get_current_view().to_csv(export_file.name, index=False)
            
            exported = pd.read_csv(export_file.name)
            # All exported rows have life_expectancy >= 70
            for le in exported['life_expectancy']:
                self.assertGreaterEqual(float(le), 70)


# =============================================================================
# ANALYSIS PIPELINE TESTS
# =============================================================================

class TestAnalysisPipeline(unittest.TestCase):
    """System tests for analysis-focused workflows."""
    
    def setUp(self):
        """Set up temp database and test data."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
        self.temp_files = []
    
    def tearDown(self):
        """Clean up temp files and matplotlib figures."""
        plt.close('all')
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
        for f in self.temp_files:
            if os.path.exists(f):
                os.unlink(f)
    
    def test_regional_comparison_workflow(self):
        """UC11-AP1: Compare regions with summary and charts."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Get grouped summary by region
            summary_by_region = session.get_summary('life_expectancy', group_by='region')
            
            # Should have multiple regions
            self.assertIsInstance(summary_by_region, pd.DataFrame)
            self.assertGreater(len(summary_by_region), 1)
            
            # Create comparison chart
            fig = session.generate_chart(
                x_column='region',
                y_column='life_expectancy',
                aggregation='mean',
                show=False
            )
            
            self.assertIsInstance(fig, plt.Figure)
    
    def test_trend_analysis_workflow(self):
        """UC11-AP2: Analyze trends over time."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Sort by year to see trend
            session.set_sort('year', ascending=True)
            
            # Get summary by year
            summary_by_year = session.get_summary('population', group_by='year')
            
            self.assertIsInstance(summary_by_year, pd.DataFrame)
    
    def test_multiple_metrics_workflow(self):
        """UC11-AP3: Analyze multiple metrics for same dimension."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Get multiple summaries
            pop_summary = session.get_summary('population')
            life_summary = session.get_summary('life_expectancy')
            gdp_summary = session.get_summary('gdp_per_capita')
            
            # All should have statistics
            self.assertIn('mean', pop_summary)
            self.assertIn('mean', life_summary)
            self.assertIn('mean', gdp_summary)
            
            # Generate multi-line chart
            fig = session.generate_multi_line_chart(
                x_column='country',
                y_columns=['life_expectancy', 'gdp_per_capita'],
                aggregation='sum',
                show=False
            )
            
            self.assertIsInstance(fig, plt.Figure)


# =============================================================================
# DATA PROCESSING TESTS
# =============================================================================

class TestDataProcessing(unittest.TestCase):
    """System tests for data processing combinations."""
    
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
    
    def test_clean_then_filter(self):
        """UC11-DP1: Clean data then apply filter."""
        csv_path = create_csv_with_issues(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original = session.get_row_count()
            
            # Clean first
            session.add_clean(['value'])
            after_clean = session.get_row_count()
            
            # Then filter
            session.add_filter_text('category', ['A'])
            after_filter = session.get_row_count()
            
            # Each operation reduces rows
            self.assertLess(after_clean, original)
            self.assertLessEqual(after_filter, after_clean)
    
    def test_filter_then_sort(self):
        """UC11-DP2: Filter data then sort."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter to high life expectancy
            session.add_filter_numeric('life_expectancy', 80, 100)
            
            # Sort by life expectancy
            session.set_sort('life_expectancy', ascending=False)
            
            view = session.get_current_view()
            
            # All filtered
            for le in view['life_expectancy']:
                self.assertGreaterEqual(float(le), 80)
            
            # All sorted
            life_exp = view['life_expectancy'].tolist()
            self.assertEqual(life_exp, sorted(life_exp, reverse=True))
    
    def test_multiple_filters_then_clean(self):
        """UC11-DP3: Apply multiple filters then clean."""
        csv_path = create_csv_with_issues(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Multiple filters
            session.add_filter_text('category', ['A', 'B'])
            session.add_filter_numeric('value', 100, 600)
            
            # Then clean
            session.add_clean(['date'])
            
            view = session.get_current_view()
            
            # All should meet filter criteria
            for idx in range(len(view)):
                row = view.iloc[idx]
                self.assertIn(row['category'], ['A', 'B'])


# =============================================================================
# OPERATIONS MODIFICATION TESTS
# =============================================================================

class TestOperationsModification(unittest.TestCase):
    """System tests for modifying operations during workflow."""
    
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
    
    def test_add_then_remove_filter(self):
        """UC11-OM1: Add filter, analyze, remove filter."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            # Add filter
            filter_id = session.add_filter_text('region', ['Europe'])
            filtered_count = session.get_row_count()
            
            self.assertLess(filtered_count, original_count)
            
            # Remove filter
            session.remove_filter(filter_id)
            restored_count = session.get_row_count()
            
            self.assertEqual(restored_count, original_count)
    
    def test_change_sort_order(self):
        """UC11-OM2: Change sort order during analysis."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Sort ascending
            session.set_sort('life_expectancy', ascending=True)
            asc_view = session.get_current_view()
            asc_order = asc_view['life_expectancy'].tolist()
            
            # Change to descending
            session.set_sort('life_expectancy', ascending=False)
            desc_view = session.get_current_view()
            desc_order = desc_view['life_expectancy'].tolist()
            
            # Orders should be reversed
            self.assertEqual(asc_order, list(reversed(desc_order)))
    
    def test_remove_clean_operation(self):
        """UC11-OM3: Add then remove clean operation."""
        csv_path = create_csv_with_issues(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            original_count = session.get_row_count()
            
            # Add clean
            clean_id = session.add_clean(['value'])
            cleaned_count = session.get_row_count()
            
            self.assertLess(cleaned_count, original_count)
            
            # Remove clean
            session.remove_clean(clean_id)
            restored_count = session.get_row_count()
            
            self.assertEqual(restored_count, original_count)


# =============================================================================
# IMPORT AND DELETE WORKFLOW TESTS
# =============================================================================

class TestImportDeleteWorkflow(unittest.TestCase):
    """System tests for import and delete combined workflows."""
    
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
    
    def test_import_analyze_delete_reimport(self):
        """UC11-ID1: Full lifecycle - import, analyze, delete, reimport."""
        csv_path = create_comprehensive_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            # First import
            adapter1 = CSVAdapter(csv_path)
            id1 = store.import_data(adapter1)
            
            # Analyze
            data1 = store.get_structured_data(id1)
            session1 = AnalysisSession(data1)
            summary1 = session1.get_summary('life_expectancy')
            
            self.assertIn('mean', summary1)
            
            # Delete
            store.delete_import(id1)
            
            # Reimport
            adapter2 = CSVAdapter(csv_path)
            id2 = store.import_data(adapter2)
            
            # Analyze again
            data2 = store.get_structured_data(id2)
            session2 = AnalysisSession(data2)
            summary2 = session2.get_summary('life_expectancy')
            
            # Same data, same summary
            self.assertEqual(summary1['mean'], summary2['mean'])
    
    def test_work_with_multiple_datasets(self):
        """UC11-ID2: Work with multiple datasets simultaneously."""
        csv_path1 = create_comprehensive_csv(self.temp_files)
        csv_path2 = create_csv_with_issues(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            # Import both
            adapter1 = CSVAdapter(csv_path1)
            adapter2 = CSVAdapter(csv_path2)
            
            id1 = store.import_data(adapter1)
            id2 = store.import_data(adapter2)
            
            # Create sessions for both
            data1 = store.get_structured_data(id1)
            data2 = store.get_structured_data(id2)
            
            session1 = AnalysisSession(data1)
            session2 = AnalysisSession(data2)
            
            # Work with both
            session1.add_filter_text('region', ['Europe'])
            session2.add_clean(['value'])
            
            # Each session maintains its own state
            view1 = session1.get_current_view()
            view2 = session2.get_current_view()
            
            # Different column sets
            self.assertIn('region', view1.columns)
            self.assertIn('category', view2.columns)


if __name__ == '__main__':
    unittest.main()
