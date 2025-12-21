"""
System Tests for UC10: Delete Dataset
======================================

Tests the complete use case of deleting a dataset from the system.
Validates data removal, cascading deletes, and error handling.

Use Case: User deletes a dataset from the system
Precondition: User has one or more datasets imported
Flow:
1. User views list of imported datasets
2. User selects a dataset to delete
3. User confirms deletion
4. System removes all data associated with the import
5. System updates the imports list

Test Categories:
- Basic Delete Tests: Deleting a single import
- Cascade Delete Tests: Verifying all related data is removed
- Multiple Import Tests: Deleting one of several imports
- Error Handling Tests: Invalid import IDs
- Post-Delete State Tests: Verifying system state after deletion
"""

import unittest
import tempfile
import os
import csv

from unittest.mock import patch

from src.data.store import DataStore
from src.data.adapters import CSVAdapter
from src.data.database import get_connection


# =============================================================================
# TEST FIXTURES
# =============================================================================

def create_test_csv(temp_files_list, name='test'):
    """Create a CSV file for delete testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix=f'_{name}.csv', newline=''
    )
    temp_files_list.append(temp_file.name)
    
    writer = csv.writer(temp_file)
    writer.writerow(['id', 'name', 'value'])
    writer.writerow(['1', 'Alpha', '100'])
    writer.writerow(['2', 'Beta', '200'])
    writer.writerow(['3', 'Gamma', '300'])
    
    temp_file.close()
    return temp_file.name


# =============================================================================
# BASIC DELETE TESTS
# =============================================================================

class TestBasicDelete(unittest.TestCase):
    """System tests for basic dataset deletion."""
    
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
    
    def test_delete_import_returns_true(self):
        """UC10-BD1: delete_import returns True on success."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            result = store.delete_import(import_id)
            
            self.assertTrue(result)
    
    def test_delete_removes_from_list(self):
        """UC10-BD2: Deleted import no longer appears in list."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # Verify it exists
            imports_before = store.list_imports()
            self.assertEqual(len(imports_before), 1)
            
            store.delete_import(import_id)
            
            # Verify it's gone
            imports_after = store.list_imports()
            self.assertEqual(len(imports_after), 0)
    
    def test_delete_makes_get_info_fail(self):
        """UC10-BD3: get_import_info returns None after deletion."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # Verify info exists
            info_before = store.get_import_info(import_id)
            self.assertIsNotNone(info_before)
            
            store.delete_import(import_id)
            
            # Verify info is gone
            info_after = store.get_import_info(import_id)
            self.assertIsNone(info_after)


# =============================================================================
# CASCADE DELETE TESTS
# =============================================================================

class TestCascadeDelete(unittest.TestCase):
    """System tests for cascading deletes."""
    
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
    
    def test_delete_removes_structured_table(self):
        """UC10-CD1: Deletion removes the structured data table."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            table_name = f"data_{import_id}"
            
            # Verify table exists
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            self.assertIsNotNone(cursor.fetchone())
            conn.close()
            
            store.delete_import(import_id)
            
            # Verify table is gone
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            self.assertIsNone(cursor.fetchone())
            conn.close()
    
    def test_delete_removes_raw_records(self):
        """UC10-CD2: Deletion removes raw records."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # Verify raw records exist
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM raw_records WHERE import_id = ?",
                (import_id,)
            )
            count_before = cursor.fetchone()[0]
            conn.close()
            self.assertGreater(count_before, 0)
            
            store.delete_import(import_id)
            
            # Verify raw records are gone
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM raw_records WHERE import_id = ?",
                (import_id,)
            )
            count_after = cursor.fetchone()[0]
            conn.close()
            self.assertEqual(count_after, 0)
    
    def test_delete_removes_data_tables_entry(self):
        """UC10-CD3: Deletion removes data_tables registry entry."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # Verify entry exists
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM data_tables WHERE import_id = ?",
                (import_id,)
            )
            count_before = cursor.fetchone()[0]
            conn.close()
            self.assertGreater(count_before, 0)
            
            store.delete_import(import_id)
            
            # Verify entry is gone
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM data_tables WHERE import_id = ?",
                (import_id,)
            )
            count_after = cursor.fetchone()[0]
            conn.close()
            self.assertEqual(count_after, 0)


# =============================================================================
# MULTIPLE IMPORT TESTS
# =============================================================================

class TestMultipleImportDelete(unittest.TestCase):
    """System tests for deleting one of multiple imports."""
    
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
    
    def test_delete_one_of_many(self):
        """UC10-MI1: Deleting one import leaves others intact."""
        csv_path1 = create_test_csv(self.temp_files, 'first')
        csv_path2 = create_test_csv(self.temp_files, 'second')
        csv_path3 = create_test_csv(self.temp_files, 'third')
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            adapter1 = CSVAdapter(csv_path1)
            adapter2 = CSVAdapter(csv_path2)
            adapter3 = CSVAdapter(csv_path3)
            
            id1 = store.import_data(adapter1)
            id2 = store.import_data(adapter2)
            id3 = store.import_data(adapter3)
            
            # Delete the middle one
            store.delete_import(id2)
            
            imports = store.list_imports()
            self.assertEqual(len(imports), 2)
            
            # First and third still exist
            self.assertIsNotNone(store.get_import_info(id1))
            self.assertIsNotNone(store.get_import_info(id3))
            
            # Second is gone
            self.assertIsNone(store.get_import_info(id2))
    
    def test_delete_all_sequentially(self):
        """UC10-MI2: Can delete all imports one by one."""
        csv_path1 = create_test_csv(self.temp_files, 'first')
        csv_path2 = create_test_csv(self.temp_files, 'second')
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            adapter1 = CSVAdapter(csv_path1)
            adapter2 = CSVAdapter(csv_path2)
            
            id1 = store.import_data(adapter1)
            id2 = store.import_data(adapter2)
            
            self.assertEqual(len(store.list_imports()), 2)
            
            store.delete_import(id1)
            self.assertEqual(len(store.list_imports()), 1)
            
            store.delete_import(id2)
            self.assertEqual(len(store.list_imports()), 0)
    
    def test_other_imports_data_intact(self):
        """UC10-MI3: Other imports' data remains accessible."""
        csv_path1 = create_test_csv(self.temp_files, 'first')
        csv_path2 = create_test_csv(self.temp_files, 'second')
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            adapter1 = CSVAdapter(csv_path1)
            adapter2 = CSVAdapter(csv_path2)
            
            id1 = store.import_data(adapter1)
            id2 = store.import_data(adapter2)
            
            # Get data before delete
            data2_before = store.get_structured_data(id2)
            row_count_before = len(data2_before)
            
            # Delete first import
            store.delete_import(id1)
            
            # Second import's data still accessible
            data2_after = store.get_structured_data(id2)
            self.assertEqual(len(data2_after), row_count_before)


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestDeleteErrorHandling(unittest.TestCase):
    """System tests for delete error handling."""
    
    def setUp(self):
        """Set up temp database."""
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
    
    def test_delete_nonexistent_returns_false(self):
        """UC10-EH1: Deleting nonexistent import returns False."""
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            
            result = store.delete_import(99999)
            
            self.assertFalse(result)
    
    def test_delete_same_id_twice_returns_false(self):
        """UC10-EH2: Deleting same import twice returns False second time."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            import_id = store.import_data(adapter)
            
            # First delete succeeds
            result1 = store.delete_import(import_id)
            self.assertTrue(result1)
            
            # Second delete fails
            result2 = store.delete_import(import_id)
            self.assertFalse(result2)


# =============================================================================
# POST-DELETE STATE TESTS
# =============================================================================

class TestPostDeleteState(unittest.TestCase):
    """System tests for system state after deletion."""
    
    def setUp(self):
        """Set up temp database."""
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
    
    def test_can_reimport_after_delete(self):
        """UC10-PS1: Can import new data after deletion."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            
            id1 = store.import_data(adapter)
            store.delete_import(id1)
            
            # Re-import
            adapter2 = CSVAdapter(csv_path)
            id2 = store.import_data(adapter2)
            
            self.assertIsNotNone(id2)
            self.assertIsNotNone(store.get_import_info(id2))
    
    def test_new_import_gets_new_id(self):
        """UC10-PS2: New import after delete gets different ID."""
        csv_path = create_test_csv(self.temp_files)
        
        with patch('src.data.database.DB_PATH', self.test_db_path):
            store = DataStore()
            adapter = CSVAdapter(csv_path)
            
            id1 = store.import_data(adapter)
            store.delete_import(id1)
            
            adapter2 = CSVAdapter(csv_path)
            id2 = store.import_data(adapter2)
            
            # SQLite auto-increment continues from last used
            self.assertNotEqual(id1, id2)


if __name__ == '__main__':
    unittest.main()
