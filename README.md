# Public Health Data Insights Dashboard

A desktop application for exploring and analyzing public health datasets. Import data from CSV files or the WHO Global Health Observatory (GHO) API, then clean, filter, sort, and visualize your data. All imports are persisted in a local SQLite database.

Built with Python, Tkinter, pandas, and matplotlib.

## Getting Started

```bash
pip install pandas matplotlib requests pillow
python main.py
```

## Features

### Data Import
- **CSV Import**: Load local CSV files with automatic column type detection
- **WHO API Integration**: Fetch live data from the World Health Organization's GHO API by indicator code (e.g., life expectancy, neonatal mortality)

### Data Management
- **Persistent Storage**: All imported datasets are stored in SQLite and available across sessions
- **View Logs**: Access detailed operation logs to track all actions performed on your data

### Data Cleaning
- **Remove Missing Values**: Clean rows with missing data in selected columns
- **Customizable Missing Indicators**: Configure what counts as "missing" (N/A, Unknown, blanks, NULL, etc.)

### Filtering
- **Text Filters**: Select specific values from a list of unique entries
- **Numeric Filters**: Use dual-handle range sliders for precise numeric filtering
- **Date Filters**: Filter by date ranges with calendar-style selection

### Sorting
- **Column Header Sorting**: Click any column header to sort ascending/descending
- **Multi-Column Sorting**: Apply complex sort orders through the sort dialog

### Analysis
- **Summary Statistics**: 
  - Numeric columns: count, mean, median, std dev, min, max, quartiles
  - Text columns: mode, frequency counts, top 5 values
- **Aggregations**: Sum, mean, and count operations

### Visualization
- **Chart Types**: Line charts and bar charts
- **Multi-Series Support**: Plot multiple Y columns on the same chart
- **Export**: Save charts as PNG images

### Non-Destructive Operations
All filter, sort, and clean operations are applied as a pipeline. Original data remains untouched, and any operation can be removed at any time.

## Project Structure

```
├── main.py                  # Application entry point
├── src/
│   ├── __init__.py
│   ├── config.py            # Settings, constants, and logging configuration
│   ├── presentation.py      # GUI layer (Tkinter windows, dialogs, data table)
│   ├── data/                # Data layer
│   │   ├── __init__.py
│   │   ├── adapters.py      # CSV and WHO API data adapters
│   │   ├── database.py      # SQLite database initialization and connection
│   │   ├── store.py         # DataStore class for CRUD operations
│   │   └── utils.py         # Data utilities (type inference, column cleaning)
│   ├── analysis/            # Analysis layer
│   │   ├── __init__.py
│   │   ├── charts.py        # Chart generation (line, bar)
│   │   ├── operations.py    # Filter, sort, clean, and statistics operations
│   │   ├── session.py       # AnalysisSession for managing operation pipelines
│   │   └── utils.py         # Analysis utilities (date parsing, numeric detection)
│   ├── exports/             # Directory for exported CSV and chart files
│   └── logs/                # Application log files
└── test/
    ├── __init__.py
    ├── unit/                # Unit tests for individual components
    ├── integration/         # Integration tests for layer interactions
    └── system/              # End-to-end system tests
```

## Architecture

The application follows a three-layer architecture:

| Layer | Responsibility |
|-------|----------------|
| **Presentation** | Tkinter-based GUI: main window, dialogs, data table display, user interaction |
| **Analysis** | Data manipulation: filtering, sorting, cleaning, statistics, chart generation |
| **Data** | Persistence: SQLite storage, CSV/API adapters, CRUD operations |

## Dependencies

- **Python 3.10+**
- **pandas** - Data manipulation and analysis
- **matplotlib** - Chart generation
- **requests** - WHO API communication
- **Pillow** (optional) - Chart preview in the application

## Running Tests

Run all tests:
```bash
python -m pytest test/
```

Run with verbose output:
```bash
python -m pytest test/ -v
```

Run specific test category:
```bash
python -m pytest test/unit/          # Unit tests only
python -m pytest test/integration/   # Integration tests only
python -m pytest test/system/        # System tests only
```

---

Programming for Artificial Intelligence - Individual Assessment
