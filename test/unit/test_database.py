"""
Unit tests for database module.

Tests for database connection and initialization functions,
covering normal operation, edge cases, and all return paths.
"""

import unittest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from src.data.database import get_connection, init_db, DB_PATH


class TestGetConnection(unittest.TestCase):
    """Test suite for get_connection function."""
    
    def setUp(self):
        """Set up test database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    @patch('src.data.database.DB_PATH')
    def test_connection_returns_connection_object(self, mock_path):
        """Test that get_connection returns a connection object."""
        mock_path.__str__ = lambda x: self.test_db_path
        mock_path.__fspath__ = lambda x: self.test_db_path
        
        with patch('src.data.database.sqlite3.connect') as mock_connect:
            mock_conn = unittest.mock.MagicMock()
            mock_connect.return_value = mock_conn
            
            conn = get_connection()
            
            self.assertIsNotNone(conn)
            mock_connect.assert_called_once()
    
    @patch('src.data.database.DB_PATH')
    def test_foreign_keys_enabled(self, mock_path):
        """Test that foreign keys are enabled on connection."""
        mock_path.__str__ = lambda x: self.test_db_path
        mock_path.__fspath__ = lambda x: self.test_db_path
        
        with patch('src.data.database.sqlite3.connect') as mock_connect:
            mock_conn = unittest.mock.MagicMock()
            mock_connect.return_value = mock_conn
            
            get_connection()
            
            mock_conn.execute.assert_called_once_with("PRAGMA foreign_keys = ON")
    
    @patch('src.data.database.DB_PATH')
    def test_row_factory_set(self, mock_path):
        """Test that row_factory is set to sqlite3.Row."""
        mock_path.__str__ = lambda x: self.test_db_path
        mock_path.__fspath__ = lambda x: self.test_db_path
        
        with patch('src.data.database.sqlite3.connect') as mock_connect:
            mock_conn = unittest.mock.MagicMock()
            mock_connect.return_value = mock_conn
            
            get_connection()
            
            self.assertEqual(mock_conn.row_factory, sqlite3.Row)
    
    def test_connection_can_execute_queries(self):
        """Test that returned connection can execute queries."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()
            
            self.assertIsNotNone(result)
    
    def test_multiple_connections(self):
        """Test that multiple connections can be created."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            conn1 = get_connection()
            conn2 = get_connection()
            
            self.assertIsNotNone(conn1)
            self.assertIsNotNone(conn2)
            self.assertIsNot(conn1, conn2)
            
            conn1.close()
            conn2.close()


class TestInitDb(unittest.TestCase):
    """Test suite for init_db function."""
    
    def setUp(self):
        """Set up test database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    def test_init_db_creates_imports_table(self):
        """Test that init_db creates imports table."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='imports'"
            )
            result = cursor.fetchone()
            conn.close()
            
            self.assertIsNotNone(result)
            self.assertEqual(result[0], "imports")
    
    def test_init_db_creates_raw_records_table(self):
        """Test that init_db creates raw_records table."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'"
            )
            result = cursor.fetchone()
            conn.close()
            
            self.assertIsNotNone(result)
    
    def test_init_db_creates_data_tables_table(self):
        """Test that init_db creates data_tables table."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='data_tables'"
            )
            result = cursor.fetchone()
            conn.close()
            
            self.assertIsNotNone(result)
    
    def test_init_db_creates_index(self):
        """Test that init_db creates index on raw_records."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_raw_records_import'"
            )
            result = cursor.fetchone()
            conn.close()
            
            self.assertIsNotNone(result)
    
    def test_imports_table_structure(self):
        """Test imports table has correct columns."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(imports)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()
            
            expected_columns = {'id', 'source_name', 'source_type', 'record_count', 'imported_at'}
            self.assertEqual(columns, expected_columns)
    
    def test_raw_records_table_structure(self):
        """Test raw_records table has correct columns."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(raw_records)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()
            
            expected_columns = {'id', 'import_id', 'row_data'}
            self.assertEqual(columns, expected_columns)
    
    def test_data_tables_table_structure(self):
        """Test data_tables table has correct columns."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(data_tables)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()
            
            expected_columns = {'id', 'import_id', 'table_name', 'created_at'}
            self.assertEqual(columns, expected_columns)
    
    def test_source_type_constraint(self):
        """Test that source_type has CHECK constraint."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            # Valid values should work
            cursor.execute(
                "INSERT INTO imports (source_name, source_type) VALUES (?, ?)",
                ("test", "csv")
            )
            cursor.execute(
                "INSERT INTO imports (source_name, source_type) VALUES (?, ?)",
                ("test2", "api")
            )
            
            # Invalid value should fail
            with self.assertRaises(sqlite3.IntegrityError):
                cursor.execute(
                    "INSERT INTO imports (source_name, source_type) VALUES (?, ?)",
                    ("test3", "invalid")
                )
            
            conn.close()
    
    def test_foreign_key_constraint(self):
        """Test foreign key constraint on raw_records."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Try to insert raw_record without valid import_id
            with self.assertRaises(sqlite3.IntegrityError):
                cursor.execute(
                    "INSERT INTO raw_records (import_id, row_data) VALUES (?, ?)",
                    (9999, "{}")
                )
            
            conn.close()
    
    def test_cascade_delete(self):
        """Test cascade delete on foreign key."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Insert import
            cursor.execute(
                "INSERT INTO imports (source_name, source_type) VALUES (?, ?)",
                ("test", "csv")
            )
            import_id = cursor.lastrowid
            
            # Insert raw_record
            cursor.execute(
                "INSERT INTO raw_records (import_id, row_data) VALUES (?, ?)",
                (import_id, "{}")
            )
            
            # Delete import
            cursor.execute("DELETE FROM imports WHERE id = ?", (import_id,))
            
            # Check raw_record is also deleted
            cursor.execute(
                "SELECT COUNT(*) FROM raw_records WHERE import_id = ?",
                (import_id,)
            )
            count = cursor.fetchone()[0]
            
            conn.close()
            
            self.assertEqual(count, 0)
    
    def test_init_db_idempotent(self):
        """Test that init_db can be called multiple times safely."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            init_db()  # Should not raise error
            init_db()
            
            # Verify tables still exist
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            count = cursor.fetchone()[0]
            conn.close()
            
            self.assertEqual(count, 3)  # 3 tables (imports, raw_records, data_tables)
    
    def test_default_values(self):
        """Test default values in imports table."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            # Insert minimal record
            cursor.execute(
                "INSERT INTO imports (source_name, source_type) VALUES (?, ?)",
                ("test", "csv")
            )
            
            # Retrieve and check defaults
            cursor.execute("SELECT record_count, imported_at FROM imports WHERE source_name = 'test'")
            row = cursor.fetchone()
            
            conn.close()
            
            self.assertEqual(row[0], 0)  # record_count default
            self.assertIsNotNone(row[1])  # imported_at should be set
    
    def test_auto_increment_ids(self):
        """Test that IDs auto-increment correctly."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO imports (source_name, source_type) VALUES (?, ?)",
                ("test1", "csv")
            )
            id1 = cursor.lastrowid
            
            cursor.execute(
                "INSERT INTO imports (source_name, source_type) VALUES (?, ?)",
                ("test2", "csv")
            )
            id2 = cursor.lastrowid
            
            conn.close()
            
            self.assertEqual(id2, id1 + 1)
    
    # Edge cases
    def test_init_db_empty_database(self):
        """Test init_db on completely empty database."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            # Ensure file exists but is empty
            open(self.test_db_path, 'w').close()
            
            init_db()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            conn.close()
            
            self.assertEqual(len(tables), 3)  # imports, raw_records, data_tables
    
    def test_init_db_connection_closes(self):
        """Test that init_db closes connection properly."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            init_db()
            
            # Try to open connection after init_db
            # Should work if previous connection was closed
            conn = sqlite3.connect(self.test_db_path)
            self.assertIsNotNone(conn)
            conn.close()


if __name__ == "__main__":
    unittest.main()
