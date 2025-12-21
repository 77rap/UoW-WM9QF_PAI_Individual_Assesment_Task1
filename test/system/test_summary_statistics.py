"""
System Tests for UC7: Generate Summary Statistics
==================================================

Tests the complete use case of generating statistical summaries for data.
Validates the full workflow from selecting columns through summary display.

Use Case: User generates statistical summaries
Precondition: User has selected a dataset
Flow:
1. User selects a column for summary
2. User optionally selects a Group By column
3. System calculates summary statistics
4. System displays the summary (numeric or text statistics)

Test Categories:
- Numeric Summary Tests: Statistics for numeric columns
- Text Summary Tests: Statistics for text/categorical columns
- Group By Tests: Grouped summary statistics
- Edge Case Tests: Empty data, missing values
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

def create_test_csv_for_summary(temp_files_list):
    """Create a CSV file with various data types for summary testing."""
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
    writer.writerow(['China', 'Asia', '2020', '1400000000', '77.0'])
    writer.writerow(['India', 'Asia', '2020', '1380000000', '69.5'])
    writer.writerow(['Australia', 'Oceania', '2020', '25000000', '83.0'])
    writer.writerow(['Brazil', 'Americas', '2018', '212000000', '75.0'])
    writer.writerow(['Canada', 'Americas', '2019', '38000000', '82.0'])
    writer.writerow(['USA', 'Americas', '2020', '331000000', '77.0'])
    
    temp_file.close()
    return temp_file.name


# =============================================================================
# NUMERIC SUMMARY TESTS
# =============================================================================

class TestNumericSummary(unittest.TestCase):
    """System tests for numeric column summary statistics."""
    
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
    
    def test_numeric_summary_contains_count(self):
        """UC7-NS1: Numeric summary includes count."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy')
            
            self.assertIn('count', summary)
            self.assertEqual(summary['count'], 10)
    
    def test_numeric_summary_contains_min_max(self):
        """UC7-NS2: Numeric summary includes min and max."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy')
            
            self.assertIn('min', summary)
            self.assertIn('max', summary)
            self.assertEqual(summary['min'], 69.5)  # India
            self.assertEqual(summary['max'], 84.5)  # Japan
    
    def test_numeric_summary_contains_mean(self):
        """UC7-NS3: Numeric summary includes mean."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy')
            
            self.assertIn('mean', summary)
            self.assertIsNotNone(summary['mean'])
    
    def test_numeric_summary_contains_median(self):
        """UC7-NS4: Numeric summary includes median."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy')
            
            self.assertIn('median', summary)
            self.assertIsNotNone(summary['median'])
    
    def test_numeric_summary_contains_std(self):
        """UC7-NS5: Numeric summary includes standard deviation."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy')
            
            self.assertIn('std', summary)
            self.assertIsNotNone(summary['std'])
    
    def test_numeric_summary_missing_count(self):
        """UC7-NS6: Numeric summary includes missing value count."""
        # Create CSV with missing values
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        self.temp_files.append(temp_file.name)
        
        writer = csv.writer(temp_file)
        writer.writerow(['name', 'value'])
        writer.writerow(['A', '100'])
        writer.writerow(['B', ''])
        writer.writerow(['C', '300'])
        writer.writerow(['D', ''])
        writer.writerow(['E', '500'])
        temp_file.close()
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(temp_file.name)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('value')
            
            self.assertIn('missing', summary)
            self.assertEqual(summary['missing'], 2)


# =============================================================================
# TEXT SUMMARY TESTS
# =============================================================================

class TestTextSummary(unittest.TestCase):
    """System tests for text/categorical column summary statistics."""
    
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
    
    def test_text_summary_contains_count(self):
        """UC7-TS1: Text summary includes count."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('region')
            
            self.assertIn('count', summary)
            self.assertEqual(summary['count'], 10)
    
    def test_text_summary_contains_unique_count(self):
        """UC7-TS2: Text summary includes unique value count."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('region')
            
            self.assertIn('unique_count', summary)
            self.assertEqual(summary['unique_count'], 4)  # Europe, Asia, Oceania, Americas
    
    def test_text_summary_contains_mode(self):
        """UC7-TS3: Text summary includes mode (most frequent value)."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('region')
            
            self.assertIn('mode', summary)
            self.assertIn('mode_frequency', summary)
            # Either Europe or Americas or Asia should be mode (3 each)
            self.assertEqual(summary['mode_frequency'], 3)
    
    def test_text_summary_contains_least_frequent(self):
        """UC7-TS4: Text summary includes least frequent value."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('region')
            
            self.assertIn('least_frequent', summary)
            self.assertIn('least_frequency', summary)
            self.assertEqual(summary['least_frequent'], 'Oceania')
            self.assertEqual(summary['least_frequency'], 1)


# =============================================================================
# GROUP BY TESTS
# =============================================================================

class TestGroupBySummary(unittest.TestCase):
    """System tests for grouped summary statistics."""
    
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
    
    def test_group_by_returns_dataframe(self):
        """UC7-GB1: Grouped summary returns DataFrame."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy', group_by='region')
            
            self.assertIsInstance(summary, pd.DataFrame)
    
    def test_group_by_has_group_column(self):
        """UC7-GB2: Grouped summary includes group column."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy', group_by='region')
            
            self.assertIn('group', summary.columns)
    
    def test_group_by_one_row_per_group(self):
        """UC7-GB3: Grouped summary has one row per group."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy', group_by='region')
            
            # Should have 4 rows (Europe, Asia, Oceania, Americas)
            self.assertEqual(len(summary), 4)
    
    def test_group_by_includes_stats(self):
        """UC7-GB4: Each group has complete statistics."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            summary = session.get_summary('life_expectancy', group_by='region')
            
            # Each group should have mean, min, max, etc.
            self.assertIn('mean', summary.columns)
            self.assertIn('min', summary.columns)
            self.assertIn('max', summary.columns)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestSummaryEdgeCases(unittest.TestCase):
    """System tests for summary edge cases."""
    
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
    
    def test_summary_nonexistent_column_raises(self):
        """UC7-EC1: Summary on non-existent column raises error."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            with self.assertRaises(ValueError):
                session.get_summary('nonexistent')
    
    def test_group_by_nonexistent_column_raises(self):
        """UC7-EC2: Group by non-existent column raises error."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            with self.assertRaises(ValueError):
                session.get_summary('life_expectancy', group_by='nonexistent')
    
    def test_summary_with_filtered_data(self):
        """UC7-EC3: Summary works on filtered data."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            # Filter to Europe only
            session.add_filter_text('region', ['Europe'])
            
            summary = session.get_summary('life_expectancy')
            
            # Should only count 3 European countries
            self.assertEqual(summary['count'], 3)
    
    def test_get_numeric_columns(self):
        """UC7-EC4: Can get list of numeric columns."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            numeric_cols = session.get_numeric_columns()
            
            self.assertIn('year', numeric_cols)
            self.assertIn('population', numeric_cols)
            self.assertIn('life_expectancy', numeric_cols)
    
    def test_get_text_columns(self):
        """UC7-EC5: Can get list of text columns."""
        csv_path = create_test_csv_for_summary(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            data = store.get_structured_data(import_id)
            session = AnalysisSession(data)
            
            text_cols = session.get_text_columns()
            
            self.assertIn('country', text_cols)
            self.assertIn('region', text_cols)


if __name__ == '__main__':
    unittest.main()
