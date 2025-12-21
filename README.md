# Public Health Data Insights Dashboard

Desktop app for working with public health datasets. Import CSV files or pull data from the WHO API, then clean, filter, sort, and visualize the data. Everything is stored in SQLite so your imports persist between sessions.

Built with Python, Tkinter, pandas, and matplotlib.

## Getting Started

```bash
pip install pandas matplotlib requests pillow
python main.py
```

## What it does

**Import data** from CSV files or the WHO GHO API. The app stores everything in a local SQLite database so you can come back to your datasets later.

**Clean your data** by removing rows with missing values. You can specify which columns to check and what counts as "missing" (N/A, Unknown, blanks, etc.).

**Filter** by text values (pick from a list), numeric ranges (there's a nice dual-handle slider), or date ranges.

**Sort** by clicking column headers or using the sort dialog.

**Analyze** with summary statistics - for numeric columns you get mean, median, std dev, etc. For text columns you get mode (most common value), frequency counts, and top 5 values.

**Graph** your data with line or bar charts. You can plot multiple Y columns on the same chart and aggregate by sum, mean, or count.

All operations are non-destructive - the original data stays untouched and you can remove operations at any time.

## Project layout

```
├── main.py              # run this
├── src/
│   ├── config.py        # settings and constants
│   ├── presentation.py  # all the GUI code
│   ├── data/            # database stuff, CSV/API adapters
│   └── analysis/        # filtering, sorting, charts, stats
└── test/
    ├── unit/
    └── integration/
```

The code is organized in layers:
- **Presentation** handles the UI (Tkinter windows, dialogs, the data table)
- **Analysis** does the actual data manipulation without touching the original
- **Data** manages storage and retrieval from SQLite

## Dependencies

- Python 3.10+
- pandas
- matplotlib  
- requests (for WHO API)
- Pillow (optional, lets you preview charts in the app)

## Running tests

```bash
python -m pytest test/
```

---

University of Westminster  
Programming for Artificial Intelligence - Individual Assessment
