"""
Configuration and Utilities Module
===================================

This module centralizes all configuration constants and utility functions
for the Public Health Data Insights Dashboard.

Contents:
- Application constants (pagination, display limits)
- Default values (missing value indicators)
- File paths (database, logs, exports)
- Logging configuration and setup
- Common utility functions

Keeping configuration separate from main code:
- Makes it easy to adjust settings without modifying logic
- Removes "magic numbers" from the codebase
- Provides single source of truth for shared values

Author: [Your Name]
Date: [Date]
"""

import logging
import os
from datetime import datetime
from pathlib import Path


# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Base directory is where this config file is located
BASE_DIR = Path(__file__).parent

# Database file location
DATABASE_PATH = BASE_DIR / "health_data.db"

# Directory for exported files (CSV, images)
EXPORT_DIR = BASE_DIR / "exports"

# Directory for log files
LOG_DIR = BASE_DIR / "logs"

# Directory for sample data
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"


# =============================================================================
# APPLICATION CONSTANTS
# =============================================================================

# Application information
APP_NAME = "Public Health Data Insights Dashboard"
APP_VERSION = "1.0.0"

# Window dimensions (in pixels)
MAIN_WINDOW_WIDTH = 1200
MAIN_WINDOW_HEIGHT = 800
MAIN_WINDOW_MIN_WIDTH = 800
MAIN_WINDOW_MIN_HEIGHT = 600

POPUP_WIDTH = 600
POPUP_HEIGHT = 500


# =============================================================================
# DATA TABLE SETTINGS
# =============================================================================

# Number of rows to display per page in the data table
DEFAULT_PAGE_SIZE = 100

# Column width constraints (in pixels)
COLUMN_MIN_WIDTH = 80
COLUMN_MAX_WIDTH = 300
COLUMN_DEFAULT_WIDTH = 120

# Maximum characters to display in a cell before truncating
CELL_MAX_DISPLAY_CHARS = 50


# =============================================================================
# FILTER SETTINGS
# =============================================================================

# Maximum number of unique values to display in text filter selection
# Values beyond this limit require using the search function
MAX_FILTER_DISPLAY_VALUES = 20

# Default values to treat as "missing" during clean operations
DEFAULT_MISSING_VALUES = [
    "N/A",
    "n/a",
    "NA",
    "Unknown",
    "unknown",
    "UNKNOWN",
    "",
    "None",
    "none",
    "NULL",
    "null",
    "-",
    ".",
]


# =============================================================================
# CHART SETTINGS
# =============================================================================

# Default figure size for charts (width, height in inches)
CHART_FIGURE_SIZE = (10, 6)

# DPI for exported chart images
CHART_EXPORT_DPI = 150

# Available aggregation methods for charts
AGGREGATION_METHODS = ["sum", "mean", "count"]

# Default aggregation method
DEFAULT_AGGREGATION = "sum"


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log file name pattern (includes date)
LOG_FILE_PREFIX = "dashboard_"
LOG_FILE_EXTENSION = ".log"

# Log format: timestamp - level - message
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Date format for log entries
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default logging level
DEFAULT_LOG_LEVEL = logging.INFO


def get_log_file_path():
    """
    Generate the log file path for today's date.
    
    Creates the logs directory if it doesn't exist.
    Log files are named with the current date to allow
    easy tracking of activity over time.
    
    Returns:
        Path: Full path to today's log file
    """
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with today's date
    today = datetime.now().strftime("%Y-%m-%d")
    filename = LOG_FILE_PREFIX + today + LOG_FILE_EXTENSION
    
    return LOG_DIR / filename


def setup_logging(log_level=None):
    """
    Configure the application logging system.
    
    This function should be called once at application startup.
    It sets up logging to both a file and the console.
    
    Args:
        log_level (int, optional): Logging level (e.g., logging.DEBUG).
                                  Defaults to DEFAULT_LOG_LEVEL.
    
    Returns:
        logging.Logger: The configured logger instance
    """
    if log_level is None:
        log_level = DEFAULT_LOG_LEVEL
    
    # Get the log file path
    log_file = get_log_file_path()
    
    # Create logger
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(log_level)
    
    # Clear any existing handlers (prevents duplicate logs on re-init)
    logger.handlers = []
    
    # Create file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger():
    """
    Get the application logger instance.
    
    If logging has not been set up, this will set it up with defaults.
    
    Returns:
        logging.Logger: The application logger
    """
    logger = logging.getLogger(APP_NAME)
    
    # If no handlers, logging hasn't been set up yet
    if not logger.handlers:
        return setup_logging()
    
    return logger


# =============================================================================
# FILE EXPORT UTILITIES
# =============================================================================

def get_export_path(base_name, extension):
    """
    Generate a unique export file path.
    
    Creates the exports directory if needed. Adds a timestamp
    to ensure unique filenames.
    
    Args:
        base_name (str): Base name for the file (e.g., "vaccination_data")
        extension (str): File extension including dot (e.g., ".csv")
    
    Returns:
        Path: Full path for the export file
    """
    # Ensure export directory exists
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clean the base name (remove invalid characters)
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in base_name)
    safe_name = safe_name.strip()
    
    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = safe_name + "_" + timestamp + extension
    
    return EXPORT_DIR / filename


def get_default_csv_filename(source_name):
    """
    Generate a default filename for CSV export.
    
    Args:
        source_name (str): Name of the data source
    
    Returns:
        str: Suggested filename
    """
    # Remove .csv if already present
    if source_name.lower().endswith(".csv"):
        base_name = source_name[:-4]
    else:
        base_name = source_name
    
    timestamp = datetime.now().strftime("%Y%m%d")
    return base_name + "_export_" + timestamp + ".csv"


def get_default_chart_filename(chart_title):
    """
    Generate a default filename for chart image export.
    
    Args:
        chart_title (str): Title of the chart
    
    Returns:
        str: Suggested filename
    """
    # Clean the title for use as filename
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in chart_title)
    safe_title = safe_title.replace(" ", "_")
    
    timestamp = datetime.now().strftime("%Y%m%d")
    return safe_title + "_" + timestamp + ".png"


# =============================================================================
# DATA FORMATTING UTILITIES
# =============================================================================

def format_number(value, decimal_places=2):
    """
    Format a number for display with thousand separators.
    
    Args:
        value: The number to format (can be None)
        decimal_places (int): Number of decimal places
    
    Returns:
        str: Formatted number string
    """
    if value is None:
        return "N/A"
    
    try:
        if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
            return "{:,}".format(int(value))
        else:
            format_string = "{:,." + str(decimal_places) + "f}"
            return format_string.format(float(value))
    except (ValueError, TypeError):
        return str(value)


def truncate_text(text, max_length=CELL_MAX_DISPLAY_CHARS):
    """
    Truncate text and add ellipsis if it exceeds max length.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length before truncation
    
    Returns:
        str: Truncated text with ellipsis if needed
    """
    if text is None:
        return ""
    
    text_str = str(text)
    
    if len(text_str) <= max_length:
        return text_str
    
    return text_str[:max_length - 3] + "..."


def format_row_count(current, total):
    """
    Format a row count status message.
    
    Args:
        current (int): Number of rows currently shown
        total (int): Total number of rows
    
    Returns:
        str: Formatted status string
    """
    return "Showing {:,} of {:,} rows".format(current, total)


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def is_valid_filename(filename):
    """
    Check if a filename is valid for the current operating system.
    
    Args:
        filename (str): The filename to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not filename or filename.strip() == "":
        return False
    
    # Characters not allowed in filenames on most systems
    invalid_chars = '<>:"/\\|?*'
    
    for char in invalid_chars:
        if char in filename:
            return False
    
    return True


def ensure_directory_exists(path):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path (str or Path): Directory path
    
    Returns:
        bool: True if directory exists or was created
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

# Ensure required directories exist when module is imported
ensure_directory_exists(EXPORT_DIR)
ensure_directory_exists(LOG_DIR)
