"""DataStore class for data storage and retrieval operations."""

import json
import pandas as pd

from .database import get_connection, init_db
from .utils import clean_column_name, infer_sql_type


class DataStore:
    """Repository pattern class for data access: import, retrieve, CRUD operations."""
    
    def __init__(self):
        """Initialize DataStore and ensure database tables exist."""
        init_db()
    
    # --- IMPORT OPERATIONS ---
    
    def import_data(self, adapter):
        """Import data from adapter. Returns import_id."""
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
        """Create SQL table from records with inferred column types."""
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
    
    # --- READ OPERATIONS ---
    
    def list_imports(self):
        """Return DataFrame of all imports with metadata."""
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
        """Return DataFrame of all structured data tables."""
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
        """Return dict of import metadata, or None if not found."""
        connection = get_connection()
        cursor = connection.cursor()
        
        cursor.execute("SELECT * FROM imports WHERE id = ?", (import_id,))
        row = cursor.fetchone()
        
        connection.close()
        
        if row:
            return dict(row)
        return None
    
    def get_raw_data(self, import_id):
        """Return DataFrame of raw data with _record_id column for CRUD."""
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
        """Return DataFrame from structured table with optional WHERE filtering."""
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
        """Return list of (column_name, column_type) tuples."""
        connection = get_connection()
        cursor = connection.cursor()
        
        table_name = "data_" + str(import_id)
        cursor.execute("PRAGMA table_info(" + table_name + ")")
        columns = cursor.fetchall()
        
        connection.close()
        
        return [(col["name"], col["type"]) for col in columns]
    
    # --- CRUD OPERATIONS ---
    
    def add_record(self, import_id, data):
        """Add record to raw_records and structured table. Returns record_id."""
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
        """Update raw_records JSON. Returns True if updated."""
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
        """Delete from raw_records and update import count. Returns True if deleted."""
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
        """Delete import with all raw records and structured table. Returns True if deleted."""
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
