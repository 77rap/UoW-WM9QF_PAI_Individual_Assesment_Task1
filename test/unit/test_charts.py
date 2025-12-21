"""
Unit tests for chart generation module.

Tests for generate_chart, generate_multi_line_chart, and export_chart
functions covering normal operation, edge cases, and error handling.
"""

import unittest
import tempfile
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for testing
import matplotlib.pyplot as plt

from src.analysis.charts import generate_chart, generate_multi_line_chart, export_chart


class TestGenerateChart(unittest.TestCase):
    """Test suite for generate_chart function."""
    
    def setUp(self):
        """Set up test data."""
        self.df = pd.DataFrame({
            "country_code": ["GBR", "FRA", "DEU", "USA", "JPN"],
            "year": [2018, 2019, 2020, 2019, 2020],
            "life_expectancy": [81.2, 82.3, 80.9, 78.5, 84.5],
            "population": [67, 67, 83, 331, 126]
        })
    
    def tearDown(self):
        """Close all matplotlib figures."""
        plt.close('all')
    
    # Basic functionality tests
    def test_generate_line_chart(self):
        """Test generating basic line chart."""
        fig = generate_chart(
            self.df, 
            x_column="year", 
            y_column="life_expectancy",
            show=False
        )
        
        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, 'savefig'))
    
    def test_generate_bar_chart(self):
        """Test generating bar chart for categorical x-axis."""
        fig = generate_chart(
            self.df,
            x_column="country_code",
            y_column="life_expectancy",
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    def test_generate_chart_with_grouping(self):
        """Test chart with group_by parameter."""
        df = pd.DataFrame({
            "year": [2020, 2020, 2021, 2021],
            "region": ["Europe", "Asia", "Europe", "Asia"],
            "value": [10, 20, 15, 25]
        })
        
        fig = generate_chart(
            df,
            x_column="year",
            y_column="value",
            group_by="region",
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    # Aggregation tests
    def test_generate_chart_aggregation_sum(self):
        """Test chart with sum aggregation."""
        fig = generate_chart(
            self.df,
            x_column="year",
            y_column="population",
            aggregation="sum",
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    def test_generate_chart_aggregation_mean(self):
        """Test chart with mean aggregation."""
        fig = generate_chart(
            self.df,
            x_column="year",
            y_column="life_expectancy",
            aggregation="mean",
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    def test_generate_chart_aggregation_count(self):
        """Test chart with count aggregation."""
        fig = generate_chart(
            self.df,
            x_column="year",
            y_column="life_expectancy",
            aggregation="count",
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    # Error handling tests
    def test_generate_chart_empty_data(self):
        """Test chart with empty DataFrame raises error."""
        empty_df = pd.DataFrame(columns=["x", "y"])
        
        with self.assertRaises(ValueError) as context:
            generate_chart(empty_df, "x", "y", show=False)
        
        self.assertIn("No data", str(context.exception))
    
    def test_generate_chart_invalid_x_column(self):
        """Test chart with non-existent x column raises error."""
        with self.assertRaises(ValueError) as context:
            generate_chart(self.df, "nonexistent", "life_expectancy", show=False)
        
        self.assertIn("X column not found", str(context.exception))
    
    def test_generate_chart_invalid_y_column(self):
        """Test chart with non-existent y column raises error."""
        with self.assertRaises(ValueError) as context:
            generate_chart(self.df, "year", "nonexistent", show=False)
        
        self.assertIn("Y column not found", str(context.exception))
    
    def test_generate_chart_non_numeric_y(self):
        """Test chart with non-numeric y column raises error."""
        with self.assertRaises(ValueError) as context:
            generate_chart(self.df, "year", "country_code", show=False)
        
        self.assertIn("numeric", str(context.exception))
    
    def test_generate_chart_invalid_group_by(self):
        """Test chart with non-existent group_by raises error."""
        with self.assertRaises(ValueError) as context:
            generate_chart(
                self.df, "year", "life_expectancy", 
                group_by="nonexistent", show=False
            )
        
        self.assertIn("Group by column not found", str(context.exception))
    
    def test_generate_chart_invalid_aggregation(self):
        """Test chart with invalid aggregation raises error."""
        with self.assertRaises(ValueError) as context:
            generate_chart(
                self.df, "year", "life_expectancy",
                aggregation="invalid", show=False
            )
        
        self.assertIn("Aggregation", str(context.exception))


class TestGenerateMultiLineChart(unittest.TestCase):
    """Test suite for generate_multi_line_chart function."""
    
    def setUp(self):
        """Set up test data."""
        self.df = pd.DataFrame({
            "year": [2018, 2019, 2020, 2021],
            "vaccination_rate": [85.0, 87.5, 90.0, 92.0],
            "disease_cases": [1000, 800, 600, 400],
            "population": [67, 67, 68, 68]
        })
    
    def tearDown(self):
        """Close all matplotlib figures."""
        plt.close('all')
    
    def test_generate_multi_line_single_y(self):
        """Test multi-line chart with single Y column."""
        fig = generate_multi_line_chart(
            self.df,
            x_column="year",
            y_columns=["vaccination_rate"],
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    def test_generate_multi_line_multiple_y(self):
        """Test multi-line chart with multiple Y columns."""
        fig = generate_multi_line_chart(
            self.df,
            x_column="year",
            y_columns=["vaccination_rate", "disease_cases"],
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    def test_generate_multi_line_three_y(self):
        """Test multi-line chart with three Y columns."""
        fig = generate_multi_line_chart(
            self.df,
            x_column="year",
            y_columns=["vaccination_rate", "disease_cases", "population"],
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    def test_generate_multi_line_aggregation(self):
        """Test multi-line chart with aggregation."""
        df = pd.DataFrame({
            "year": [2020, 2020, 2021, 2021],
            "value1": [10, 20, 15, 25],
            "value2": [5, 10, 8, 12]
        })
        
        fig = generate_multi_line_chart(
            df,
            x_column="year",
            y_columns=["value1", "value2"],
            aggregation="mean",
            show=False
        )
        
        self.assertIsNotNone(fig)
    
    # Error handling tests
    def test_multi_line_empty_data(self):
        """Test multi-line with empty DataFrame raises error."""
        empty_df = pd.DataFrame(columns=["x", "y"])
        
        with self.assertRaises(ValueError):
            generate_multi_line_chart(empty_df, "x", ["y"], show=False)
    
    def test_multi_line_invalid_x_column(self):
        """Test multi-line with non-existent x column raises error."""
        with self.assertRaises(ValueError):
            generate_multi_line_chart(
                self.df, "nonexistent", ["vaccination_rate"], show=False
            )
    
    def test_multi_line_invalid_y_column(self):
        """Test multi-line with non-existent y column raises error."""
        with self.assertRaises(ValueError):
            generate_multi_line_chart(
                self.df, "year", ["nonexistent"], show=False
            )
    
    def test_multi_line_empty_y_columns(self):
        """Test multi-line with empty y_columns raises error."""
        with self.assertRaises(ValueError):
            generate_multi_line_chart(self.df, "year", [], show=False)
    
    def test_multi_line_non_numeric_y(self):
        """Test multi-line with non-numeric y column raises error."""
        df = pd.DataFrame({
            "year": [2020, 2021],
            "category": ["A", "B"]
        })
        
        with self.assertRaises(ValueError):
            generate_multi_line_chart(df, "year", ["category"], show=False)


class TestExportChart(unittest.TestCase):
    """Test suite for export_chart function."""
    
    def setUp(self):
        """Set up test data and create a figure."""
        self.df = pd.DataFrame({
            "year": [2020, 2021],
            "value": [10, 20]
        })
        self.figure = generate_chart(
            self.df, "year", "value", show=False
        )
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up figures and test files."""
        plt.close('all')
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_export_png(self):
        """Test exporting chart as PNG."""
        filepath = os.path.join(self.test_dir, "chart.png")
        
        result = export_chart(self.figure, filepath)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
    
    def test_export_creates_directory(self):
        """Test that export creates parent directory if needed."""
        filepath = os.path.join(self.test_dir, "subdir", "chart.png")
        
        result = export_chart(self.figure, filepath)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
    
    def test_export_none_figure(self):
        """Test exporting None figure raises error."""
        filepath = os.path.join(self.test_dir, "chart.png")
        
        with self.assertRaises(ValueError) as context:
            export_chart(None, filepath)
        
        self.assertIn("No chart", str(context.exception))
    
    def test_export_file_content(self):
        """Test that exported file has content."""
        filepath = os.path.join(self.test_dir, "chart.png")
        
        export_chart(self.figure, filepath)
        
        file_size = os.path.getsize(filepath)
        self.assertGreater(file_size, 0)


if __name__ == '__main__':
    unittest.main()
