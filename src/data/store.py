"""
DataStore Class Module
======================

Main class for managing data storage and retrieval operations.
"""

import json
import pandas as pd

from .database import get_connection, init_db
from .utils import clean_column_name, infer_sql_type


class DataStore:
    """
    Main class for managing data storage and retrieval operations.
    
    This class provides methods for:
    - Importing data from adapters (CSV, API)
    - Retrieving raw and structured data
    - CRUD operations on individual records
    - Managing imports and their associated data
    
    The DataStore follows the Repository pattern, providing a centralized
    interface for all data access operations.
    """
    
    def __init__(self):
        """
        Initialize the DataStore and ensure database tables exist.
        """
        init_db()
    
    # -------------------------------------------------------------------------
    # IMPORT OPERATIONS
    # -------------------------------------------------------------------------
    
    def import_data(self, adapter):
        """
        Import data from an adapter into the database.
        
        This method performs the complete import process:
        1. Fetch data using the adapter
        2. Create an import record for tracking
        3. Store raw data as JSON in raw_records table
        4. Create a structured table with proper SQL columns
        
        Args:
            adapter (DataAdapter): An adapter instance (CSVAdapter or WHOAPIAdapter)
            
        Returns:
            int: The import_id of the newly created import
            
        Raises:
            Exception: If the import process fails
        """
        records = adapter.fetch()
        
        if len(records) == 0:
            raise ValueError("No records returned from the data source")
        
        connection = get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO imports (source_name, source_type, record_count) 
                VALUES (?, ?, ?)
                """,
                (adapter.source_name, adapter.source_type, len(records))
            )
            import_id = cursor.lastrowid
            
            for record in records:
                json_data = json.dumps(record)
                cursor.execute(
                    "INSERT INTO raw_records (import_id, row_data) VALUES (?, ?)",
                    (import_id, json_data)
                )
            
            self._create_structured_table(cursor, import_id, records)
            connection.commit()
            
            return import_id
            
        except Exception as error:
            connection.rollback()
            raise error
            
        finally:
            connection.close()
    
    def _create_structured_table(self, cursor, import_id, records):
        """
        Create a structured SQL table from imported records.
        
        This is a private helper method that:
        1. Determines column names and types from the data
        2. Creates a new table with appropriate schema
        3. Inserts all records into the new table
        4. Registers the table in data_tables registry
        
        Args:
            cursor: Database cursor for executing SQL
            import_id (int): The ID of the import
            records (list): List of dictionaries containing the data
        """
        table_name = "data_" + str(import_id)
        original_columns = list(records[0].keys())
        
        column_mapping = {}
        for col in original_columns:
            cleaned = clean_column_name(col)
            column_mapping[col] = cleaned
        
        column_types = {}
        for original_col in original_columns:
            values = [record.get(original_col) for record in records]
            sql_type = infer_sql_type(values)
            column_types[column_mapping[original_col]] = sql_type
        
        # Start with row_id for record identification
        column_definitions = ["row_id INTEGER PRIMARY KEY AUTOINCREMENT"]
        
        for original_col in original_columns:
            cleaned_col = column_mapping[original_col]
            sql_type = column_types[cleaned_col]
            column_definitions.append(cleaned_col + " " + sql_type)
        
        columns_str = ", ".join(column_definitions)
        create_sql = "CREATE TABLE " + table_name + " (" + columns_str + ")"
        cursor.execute(create_sql)
        
        cleaned_columns = [column_mapping[col] for col in original_columns]
        placeholders = ", ".join(["?" for _ in cleaned_columns])
        columns_list = ", ".join(cleaned_columns)
        insert_sql = "INSERT INTO " + table_name + " (" + columns_list + ") VALUES (" + placeholders + ")"
        
        for record in records:
            values = [record.get(original_col) for original_col in original_columns]
            cursor.execute(insert_sql, values)
        
        cursor.execute(
            "INSERT INTO data_tables (import_id, table_name) VALUES (?, ?)",
            (import_id, table_name)
        )
    
    # -------------------------------------------------------------------------
    # READ OPERATIONS - Listing and Retrieval
    # -------------------------------------------------------------------------
    
    def list_imports(self):
        """
        List all imports in the database.
        
        Returns:
            pandas.DataFrame: A DataFrame containing import metadata
                with columns: id, source_name, source_type, record_count, imported_at
        """
        connection = get_connection()
        
        query = """
            SELECT id, source_name, source_type, record_count, imported_at 
            FROM imports 
            ORDER BY imported_at DESC
        """
        
        dataframe = pd.read_sql_query(query, connection)
        connection.close()
        
        return dataframe
    
    def list_data_tables(self):
        """
        List all structured data tables that have been created.
        
        Returns:
            pandas.DataFrame: A DataFrame containing table registry information
                with columns: id, import_id, table_name, created_at, source_name
        """
        connection = get_connection()
        
        query = """
            SELECT dt.id, dt.import_id, dt.table_name, dt.created_at, 
                   i.source_name
            FROM data_tables dt
            JOIN imports i ON dt.import_id = i.id
            ORDER BY dt.created_at DESC
        """
        
        dataframe = pd.read_sql_query(query, connection)
        connection.close()
        
        return dataframe
    
    def get_import_info(self, import_id):
        """
        Get metadata about a specific import.
        
        Args:
            import_id (int): The ID of the import to look up
            
        Returns:
            dict or None: Import metadata as a dictionary, or None if not found
        """
        connection = get_connection()
        cursor = connection.cursor()
        
        cursor.execute("SELECT * FROM imports WHERE id = ?", (import_id,))
        row = cursor.fetchone()
        
        connection.close()
        
        if row:
            return dict(row)
        return None
    
    def get_raw_data(self, import_id):
        """
        Retrieve raw data for an import as a pandas DataFrame.
        
        This reconstructs the original data structure from JSON storage,
        allowing users to see all original columns exactly as imported.
        
        Args:
            import_id (int): The ID of the import to retrieve
            
        Returns:
            pandas.DataFrame: DataFrame containing all original data
                with an additional '_record_id' column for reference
        """
        connection = get_connection()
        cursor = connection.cursor()
        
        cursor.execute(
            "SELECT id, row_data FROM raw_records WHERE import_id = ?",
            (import_id,)
        )
        rows = cursor.fetchall()
        
        connection.close()
        
        if len(rows) == 0:
            return pd.DataFrame()
        
        records = []
        for row in rows:
            data = json.loads(row["row_data"])
            data["_record_id"] = row["id"]  # For CRUD operations
            records.append(data)
        
        return pd.DataFrame(records)
    
    def get_structured_data(self, import_id, where_clause=None, params=None):
        """
        Retrieve data from a structured table with optional filtering.
        
        This method queries the dynamically created SQL table (data_1, etc.)
        which has proper columns and allows efficient SQL filtering.
        
        Args:
            import_id (int): The ID of the import
            where_clause (str, optional): SQL WHERE clause without 'WHERE' keyword
                                         Example: "year > ? AND country_code = ?"
            params (tuple, optional): Parameters for the WHERE clause placeholders
            
        Returns:
            pandas.DataFrame: Filtered data from the structured table
        """
        connection = get_connection()
        table_name = "data_" + str(import_id)
        query = "SELECT * FROM " + table_name
        
        if where_clause is not None:
            query = query + " WHERE " + where_clause
        
        if params is not None:
            dataframe = pd.read_sql_query(query, connection, params=params)
        else:
            dataframe = pd.read_sql_query(query, connection)
        
        connection.close()
        
        return dataframe
    
    def get_table_columns(self, import_id):
        """
        Get the column names and types for a structured table.
        
        Useful for displaying available columns to users for filtering.
        
        Args:
            import_id (int): The ID of the import
            
        Returns:
            list: List of tuples (column_name, column_type)
        """
        connection = get_connection()
        cursor = connection.cursor()
        
        table_name = "data_" + str(import_id)
        cursor.execute("PRAGMA table_info(" + table_name + ")")
        columns = cursor.fetchall()
        
        connection.close()
        
        return [(col["name"], col["type"]) for col in columns]
    
    # -------------------------------------------------------------------------
    # CRUD OPERATIONS - Create, Update, Delete
    # -------------------------------------------------------------------------
    
    def add_record(self, import_id, data):
        """
        Add a new record to an existing import.
        
        The record is added to both the raw_records table (as JSON)
        and the structured table (as a row with columns).
        
        Args:
            import_id (int): The ID of the import to add the record to
            data (dict): The record data as a dictionary
            
        Returns:
            int: The ID of the newly created raw record
        """
        connection = get_connection()
        cursor = connection.cursor()
        
        try:
            json_data = json.dumps(data)
            cursor.execute(
                "INSERT INTO raw_records (import_id, row_data) VALUES (?, ?)",
                (import_id, json_data)
            )
            record_id = cursor.lastrowid
            
            table_name = "data_" + str(import_id)
            
            cursor.execute("PRAGMA table_info(" + table_name + ")")
            pragma_results = cursor.fetchall()
            existing_columns = [col["name"] for col in pragma_results]
            
            columns_to_insert = []
            values_to_insert = []
            
            for key, value in data.items():
                cleaned_key = clean_column_name(key)
                if cleaned_key in existing_columns:
                    columns_to_insert.append(cleaned_key)
                    values_to_insert.append(value)
            
            if len(columns_to_insert) > 0:
                placeholders = ", ".join(["?" for _ in columns_to_insert])
                columns_str = ", ".join(columns_to_insert)
                insert_sql = "INSERT INTO " + table_name + " (" + columns_str + ") VALUES (" + placeholders + ")"
                cursor.execute(insert_sql, values_to_insert)
            
            cursor.execute(
                "UPDATE imports SET record_count = record_count + 1 WHERE id = ?",
                (import_id,)
            )
            
            connection.commit()
            return record_id
            
        except Exception as error:
            connection.rollback()
            raise error
            
        finally:
            connection.close()
    
    def update_record(self, record_id, updated_data):
        """
        Update an existing record in the raw_records table.
        
        Note: This updates the JSON in raw_records. The structured table
        is not automatically updated (would require additional logic to
        match raw records to structured table rows).
        
        Args:
            record_id (int): The ID of the record in raw_records table
            updated_data (dict): The new data to store
            
        Returns:
            bool: True if the record was updated, False if not found
        """
        connection = get_connection()
        cursor = connection.cursor()
        
        try:
            json_data = json.dumps(updated_data)
            cursor.execute(
                "UPDATE raw_records SET row_data = ? WHERE id = ?",
                (json_data, record_id)
            )
            
            updated = cursor.rowcount > 0
            connection.commit()
            return updated
            
        except Exception as error:
            connection.rollback()
            raise error
            
        finally:
            connection.close()
    
    def delete_record(self, record_id):
        """
        Delete a single record from the raw_records table.
        
        Also updates the record count in the imports table.
        
        Args:
            record_id (int): The ID of the record to delete
            
        Returns:
            bool: True if the record was deleted, False if not found
        """
        connection = get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(
                "SELECT import_id FROM raw_records WHERE id = ?",
                (record_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                connection.close()
                return False
            
            import_id = row["import_id"]
            cursor.execute("DELETE FROM raw_records WHERE id = ?", (record_id,))
            cursor.execute(
                "UPDATE imports SET record_count = record_count - 1 WHERE id = ?",
                (import_id,)
            )
            
            connection.commit()
            return True
            
        except Exception as error:
            connection.rollback()
            raise error
            
        finally:
            connection.close()
    
    def delete_import(self, import_id):
        """
        Delete an entire import and all associated data.
        
        This removes:
        - The import record from imports table
        - All raw records from raw_records table
        - The structured table (data_X)
        - The data_tables registry entry
        
        Args:
            import_id (int): The ID of the import to delete
            
        Returns:
            bool: True if the import was deleted, False if not found
        """
        connection = get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("SELECT id FROM imports WHERE id = ?", (import_id,))
            if cursor.fetchone() is None:
                connection.close()
                return False
            
            table_name = "data_" + str(import_id)
            cursor.execute("DROP TABLE IF EXISTS " + table_name)
            cursor.execute("DELETE FROM data_tables WHERE import_id = ?", (import_id,))
            cursor.execute("DELETE FROM raw_records WHERE import_id = ?", (import_id,))
            cursor.execute("DELETE FROM imports WHERE id = ?", (import_id,))
            
            connection.commit()
            return True
            
        except Exception as error:
            connection.rollback()
            raise error
            
        finally:
            connection.close()
