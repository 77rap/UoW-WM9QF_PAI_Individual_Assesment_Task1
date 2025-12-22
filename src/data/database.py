"""SQLite database connection and initialization."""

import sqlite3
from pathlib import Path

try:
    from ..config import DATABASE_PATH
    DB_PATH = DATABASE_PATH
except ImportError:
    DB_PATH = Path(__file__).parent.parent / "health_data.db"


def get_connection():
    """Return SQLite connection with foreign keys enabled."""
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create required tables if they don't exist."""
    connection = get_connection()
    cursor = connection.cursor()
    
    # imports: tracks import operations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK(source_type IN ('csv', 'api')),
            record_count INTEGER DEFAULT 0,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # raw_records: stores original data as JSON
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            row_data TEXT NOT NULL,
            FOREIGN KEY (import_id) REFERENCES imports(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_raw_records_import 
        ON raw_records(import_id)
    """)
    
    # data_tables table: registry of structured tables created from imports
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            table_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (import_id) REFERENCES imports(id) ON DELETE CASCADE
        )
    """)
    
    connection.commit()
    connection.close()
