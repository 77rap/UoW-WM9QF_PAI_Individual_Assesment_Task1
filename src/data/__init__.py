"""
Data Module - Public Health Data Insights Dashboard
====================================================

This module handles all data ingestion, storage, and retrieval operations.
It implements a two-stage storage pattern:
    1. Raw storage: Original data preserved as JSON in raw_records table
    2. Structured storage: Queryable SQL tables with proper columns

The adapter pattern is used to support multiple data sources (CSV, API)
through a common interface.

Usage:
    from src.data import DataStore, CSVAdapter, WHOAPIAdapter
    
    store = DataStore()
    adapter = CSVAdapter("data.csv")
    import_id = store.import_data(adapter)
"""

# Import main classes for public API
from .adapters import DataAdapter, CSVAdapter, WHOAPIAdapter
from .store import DataStore
from .database import get_connection, init_db
from .utils import clean_column_name, infer_sql_type


# Define what gets imported with "from src.data import *"
__all__ = [
    'DataStore',
    'DataAdapter',
    'CSVAdapter',
    'WHOAPIAdapter',
    'get_connection',
    'init_db',
    'clean_column_name',
    'infer_sql_type',
]
