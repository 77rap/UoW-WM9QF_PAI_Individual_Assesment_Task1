"""Utility functions for data processing and SQL operations."""

import re


def clean_column_name(name):
    """Convert column name to SQL-safe format (lowercase, underscores, no special chars)."""
    if name is None:
        return "unnamed_column"
    
    cleaned = name.lower()
    cleaned = re.sub(r'[^a-z0-9]', '_', cleaned)
    cleaned = re.sub(r'_+', '_', cleaned)
    cleaned = cleaned.strip('_')
    
    return cleaned if cleaned else "unnamed_column"


def infer_sql_type(values):
    """Infer SQL type from values: returns 'INTEGER', 'REAL', or 'TEXT'."""
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
