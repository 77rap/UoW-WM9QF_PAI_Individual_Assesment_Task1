"""
Utility Functions Module
=========================

Helper functions for data processing and SQL operations.
"""

import re


def clean_column_name(name):
    """
    Convert a column name to a SQL-safe format.
    
    Transformations applied:
    - Convert to lowercase
    - Replace spaces and special characters with underscores
    - Remove consecutive underscores
    - Remove leading/trailing underscores
    
    Args:
        name (str): The original column name
        
    Returns:
        str: A cleaned, SQL-compatible column name
    """
    if name is None:
        return "unnamed_column"
    
    cleaned = name.lower()
    cleaned = re.sub(r'[^a-z0-9]', '_', cleaned)
    cleaned = re.sub(r'_+', '_', cleaned)
    cleaned = cleaned.strip('_')
    
    return cleaned if cleaned else "unnamed_column"


def infer_sql_type(values):
    """
    Infer the most appropriate SQL data type from a list of values.
    
    The function attempts to identify if values are integers, floats,
    or should remain as text. This is used when creating structured tables.
    
    Args:
        values (list): Sample values from a column
        
    Returns:
        str: SQL type ('INTEGER', 'REAL', or 'TEXT')
    """
    non_null_values = [v for v in values if v is not None]
    
    if len(non_null_values) == 0:
        return "TEXT"
    
    int_count = 0
    float_count = 0
    
    for value in non_null_values:
        str_value = str(value).strip()
        
        try:
            int(str_value)
            int_count = int_count + 1
            continue
        except ValueError:
            pass
        
        try:
            float(str_value)
            float_count = float_count + 1
            continue
        except ValueError:
            pass
    
    total = len(non_null_values)
    
    if int_count == total:
        return "INTEGER"
    elif int_count + float_count == total:
        return "REAL"
    else:
        return "TEXT"
