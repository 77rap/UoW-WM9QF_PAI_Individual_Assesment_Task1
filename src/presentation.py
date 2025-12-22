"""
Presentation Layer Module for Public Health Data Insights Dashboard
====================================================================

This module provides the graphical user interface using Tkinter.
It follows a design philosophy of limiting user actions wherever
possible to prevent errors.

Components:
- MainWindow: Primary application window with toolbar, operations panel,
              status bar, and data table
- SummaryPopup: Modal window for statistical summaries
- GraphPopup: Modal window for chart generation
- Various dialogs for adding operations

Design Principles:
- Dropdown menus instead of text fields where possible
- Range sliders with constrained bounds
- Button disabling to prevent invalid actions
- Immediate feedback via status bar

Author: [Your Name]
Date: [Date]
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from pathlib import Path

# Import our modules using proper package paths
from .config import (
    APP_NAME, APP_VERSION,
    MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT,
    MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT,
    POPUP_WIDTH, POPUP_HEIGHT,
    DEFAULT_PAGE_SIZE, COLUMN_MIN_WIDTH, COLUMN_MAX_WIDTH,
    CELL_MAX_DISPLAY_CHARS, MAX_FILTER_DISPLAY_VALUES,
    DEFAULT_MISSING_VALUES,
    get_logger, get_log_file_path, get_default_csv_filename, get_default_chart_filename,
    format_number, truncate_text, format_row_count
)
from .data import DataStore, CSVAdapter, WHOAPIAdapter
from .analysis import AnalysisSession


# =============================================================================
# CUSTOM WIDGETS
# =============================================================================

class DualRangeSlider(tk.Canvas):
    """
    A dual-handle range slider widget for selecting a range of values.
    
    This widget displays a single track with two draggable handles representing
    the lower and upper bounds of a range. The selected range is highlighted.
    """
    
    def __init__(self, parent, min_val, max_val, low_var, high_var, on_change=None,
                 width=350, height=50, **kwargs):
        """
        Initialize the dual range slider.
        
        Args:
            parent: Parent widget
            min_val: Minimum value of the range
            max_val: Maximum value of the range
            low_var: DoubleVar for the lower bound
            high_var: DoubleVar for the upper bound
            on_change: Callback function when values change
            width: Canvas width
            height: Canvas height
        """
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, **kwargs)
        
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.low_var = low_var
        self.high_var = high_var
        self.on_change = on_change
        
        # Dimensions
        self.slider_width = width
        self.slider_height = height
        self.track_height = 8
        self.handle_radius = 10
        self.padding = 20  # Left/right padding for handles
        
        # Colors
        self.track_color = "#ddd"
        self.range_color = "#4a90d9"
        self.handle_color = "#4a90d9"
        self.handle_border = "#2d5aa0"
        
        # State
        self.active_handle = None  # "low" or "high"
        
        # Draw initial state
        self._draw()
        
        # Bind events
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
    
    def _value_to_x(self, value):
        """Convert a value to x coordinate."""
        if self.max_val == self.min_val:
            return self.padding
        ratio = (value - self.min_val) / (self.max_val - self.min_val)
        return self.padding + ratio * (self.slider_width - 2 * self.padding)
    
    def _x_to_value(self, x):
        """Convert x coordinate to a value."""
        x = max(self.padding, min(x, self.slider_width - self.padding))
        if self.slider_width - 2 * self.padding == 0:
            return self.min_val
        ratio = (x - self.padding) / (self.slider_width - 2 * self.padding)
        return self.min_val + ratio * (self.max_val - self.min_val)
    
    def _draw(self):
        """Draw the slider."""
        self.delete("all")
        
        y_center = self.slider_height // 2
        track_y1 = y_center - self.track_height // 2
        track_y2 = y_center + self.track_height // 2
        
        # Draw background track
        self.create_rectangle(
            self.padding, track_y1,
            self.slider_width - self.padding, track_y2,
            fill=self.track_color, outline=""
        )
        
        # Get handle positions
        low_x = self._value_to_x(self.low_var.get())
        high_x = self._value_to_x(self.high_var.get())
        
        # Draw selected range
        self.create_rectangle(
            low_x, track_y1,
            high_x, track_y2,
            fill=self.range_color, outline=""
        )
        
        # Draw low handle
        self.create_oval(
            low_x - self.handle_radius, y_center - self.handle_radius,
            low_x + self.handle_radius, y_center + self.handle_radius,
            fill=self.handle_color, outline=self.handle_border, width=2,
            tags="low_handle"
        )
        
        # Draw high handle
        self.create_oval(
            high_x - self.handle_radius, y_center - self.handle_radius,
            high_x + self.handle_radius, y_center + self.handle_radius,
            fill=self.handle_color, outline=self.handle_border, width=2,
            tags="high_handle"
        )
        
        # Draw value labels
        self.create_text(
            self.padding, self.slider_height - 5,
            text=format_number(self.min_val), anchor="w",
            font=("TkDefaultFont", 8), fill="gray"
        )
        self.create_text(
            self.slider_width - self.padding, self.slider_height - 5,
            text=format_number(self.max_val), anchor="e",
            font=("TkDefaultFont", 8), fill="gray"
        )
    
    def _on_click(self, event):
        """Handle mouse click."""
        low_x = self._value_to_x(self.low_var.get())
        high_x = self._value_to_x(self.high_var.get())
        
        # Determine which handle is closer
        dist_low = abs(event.x - low_x)
        dist_high = abs(event.x - high_x)
        
        if dist_low <= dist_high and dist_low <= self.handle_radius * 2:
            self.active_handle = "low"
        elif dist_high <= self.handle_radius * 2:
            self.active_handle = "high"
        elif event.x < low_x:
            self.active_handle = "low"
        elif event.x > high_x:
            self.active_handle = "high"
        else:
            # Click in between - move the closer handle
            self.active_handle = "low" if dist_low < dist_high else "high"
        
        self._update_handle(event.x)
    
    def _on_drag(self, event):
        """Handle mouse drag."""
        if self.active_handle:
            self._update_handle(event.x)
    
    def _on_release(self, event):
        """Handle mouse release."""
        self.active_handle = None
    
    def _update_handle(self, x):
        """Update the active handle position."""
        value = self._x_to_value(x)
        
        if self.active_handle == "low":
            # Don't let low exceed high
            value = min(value, self.high_var.get())
            self.low_var.set(value)
        elif self.active_handle == "high":
            # Don't let high go below low
            value = max(value, self.low_var.get())
            self.high_var.set(value)
        
        self._draw()
        
        if self.on_change:
            self.on_change()
    
    def update_handles(self):
        """Redraw handles based on current variable values."""
        self._draw()


# =============================================================================
# MAIN APPLICATION WINDOW
# =============================================================================

class MainWindow:
    """
    Main application window containing all primary interface elements.
    
    Structure (top to bottom):
    - Toolbar: Dataset selection, import/export, summary/graph buttons
    - Operations Panel: Clean, Filter, Sort management sections
    - Status Bar: Current state summary
    - Data Table: Paginated data display
    """
    
    def __init__(self, root):
        """
        Initialize the main window.
        
        Args:
            root (tk.Tk): The root Tkinter window
        """
        self.root = root
        self.root.title(APP_NAME + " v" + APP_VERSION)
        self.root.geometry(str(MAIN_WINDOW_WIDTH) + "x" + str(MAIN_WINDOW_HEIGHT))
        self.root.minsize(MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT)
        
        # Initialize logger
        self.logger = get_logger()
        self.logger.info("Application started")
        
        # Initialize data store
        self.data_store = DataStore()
        
        # Current analysis session (None until dataset selected)
        self.session = None
        self.current_import_id = None
        
        # Pagination state
        self.current_page = 1
        self.page_size = DEFAULT_PAGE_SIZE
        
        # Build the interface
        self._create_toolbar()
        self._create_operations_panel()
        self._create_status_bar()
        self._create_data_table()
        
        # Load initial data
        self._refresh_dataset_list()
        
        # Log startup complete
        self.logger.info("Interface initialized successfully")
    
    # -------------------------------------------------------------------------
    # INTERFACE CREATION
    # -------------------------------------------------------------------------
    
    def _create_toolbar(self):
        """Create the toolbar with dataset selection and action buttons."""
        # Main toolbar container
        toolbar_container = ttk.Frame(self.root, padding="5")
        toolbar_container.pack(fill=tk.X, side=tk.TOP)
        
        # Row 1: Dataset selection and data management
        toolbar_row1 = ttk.Frame(toolbar_container)
        toolbar_row1.pack(fill=tk.X, pady=(0, 3))
        
        # Dataset selection
        ttk.Label(toolbar_row1, text="Dataset:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.dataset_var = tk.StringVar()
        self.dataset_dropdown = ttk.Combobox(
            toolbar_row1,
            textvariable=self.dataset_var,
            state="readonly",
            width=35
        )
        self.dataset_dropdown.pack(side=tk.LEFT, padx=(0, 10))
        self.dataset_dropdown.bind("<<ComboboxSelected>>", self._on_dataset_selected)
        
        # Import CSV button
        self.import_btn = ttk.Button(
            toolbar_row1,
            text="Import CSV",
            command=self._on_import_click
        )
        self.import_btn.pack(side=tk.LEFT, padx=2)
        
        # Import WHO API button
        self.import_api_btn = ttk.Button(
            toolbar_row1,
            text="Import WHO API",
            command=self._on_import_api_click
        )
        self.import_api_btn.pack(side=tk.LEFT, padx=2)
        
        # Export button
        self.export_btn = ttk.Button(
            toolbar_row1,
            text="Export CSV",
            command=self._on_export_click
        )
        self.export_btn.pack(side=tk.LEFT, padx=2)
        
        # Delete dataset button
        self.delete_btn = ttk.Button(
            toolbar_row1,
            text="Delete Dataset",
            command=self._on_delete_click
        )
        self.delete_btn.pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar_row1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Summary button
        self.summary_btn = ttk.Button(
            toolbar_row1,
            text="Summary",
            command=self._on_summary_click
        )
        self.summary_btn.pack(side=tk.LEFT, padx=2)
        
        # Graph button
        self.graph_btn = ttk.Button(
            toolbar_row1,
            text="Graph",
            command=self._on_graph_click
        )
        self.graph_btn.pack(side=tk.LEFT, padx=2)
        
        # Row 2: Record management and tools
        toolbar_row2 = ttk.Frame(toolbar_container)
        toolbar_row2.pack(fill=tk.X)
        
        # Record management label
        ttk.Label(toolbar_row2, text="Records:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Add Record button
        self.add_record_btn = ttk.Button(
            toolbar_row2,
            text="Add",
            command=self._on_add_record_click
        )
        self.add_record_btn.pack(side=tk.LEFT, padx=2)
        
        # Edit Record button
        self.edit_record_btn = ttk.Button(
            toolbar_row2,
            text="Edit",
            command=self._on_edit_record_click
        )
        self.edit_record_btn.pack(side=tk.LEFT, padx=2)
        
        # Delete Record button
        self.delete_record_btn = ttk.Button(
            toolbar_row2,
            text="Delete",
            command=self._on_delete_record_click
        )
        self.delete_record_btn.pack(side=tk.LEFT, padx=2)
        
        # Separator before log button
        ttk.Separator(toolbar_row2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # View Log button
        self.log_btn = ttk.Button(
            toolbar_row2,
            text="View Log",
            command=self._on_view_log_click
        )
        self.log_btn.pack(side=tk.LEFT, padx=2)
    
    def _create_operations_panel(self):
        """Create the operations panel with Clean, Filter, Sort sections."""
        # Main frame for operations
        self.ops_frame = ttk.LabelFrame(self.root, text="Operations", padding="5")
        self.ops_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create three columns
        ops_container = ttk.Frame(self.ops_frame)
        ops_container.pack(fill=tk.X)
        
        # Clean section
        self._create_clean_section(ops_container)
        
        # Filter section
        self._create_filter_section(ops_container)
        
        # Sort section
        self._create_sort_section(ops_container)
    
    def _create_clean_section(self, parent):
        """Create the Clean operations section."""
        clean_frame = ttk.LabelFrame(parent, text="Clean", padding="5")
        clean_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        # List of current clean operations
        self.clean_listbox = tk.Listbox(clean_frame, height=3, width=30)
        self.clean_listbox.pack(fill=tk.X, pady=(0, 5))
        
        # Buttons
        btn_frame = ttk.Frame(clean_frame)
        btn_frame.pack(fill=tk.X)
        
        self.add_clean_btn = ttk.Button(
            btn_frame,
            text="Add Clean",
            command=self._on_add_clean_click
        )
        self.add_clean_btn.pack(side=tk.LEFT, padx=2)
        
        self.remove_clean_btn = ttk.Button(
            btn_frame,
            text="Remove",
            command=self._on_remove_clean_click
        )
        self.remove_clean_btn.pack(side=tk.LEFT, padx=2)
    
    def _create_filter_section(self, parent):
        """Create the Filter operations section."""
        filter_frame = ttk.LabelFrame(parent, text="Filter", padding="5")
        filter_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        # List of current filters
        self.filter_listbox = tk.Listbox(filter_frame, height=3, width=30)
        self.filter_listbox.pack(fill=tk.X, pady=(0, 5))
        
        # Buttons
        btn_frame = ttk.Frame(filter_frame)
        btn_frame.pack(fill=tk.X)
        
        self.add_filter_btn = ttk.Button(
            btn_frame,
            text="Add Filter",
            command=self._on_add_filter_click
        )
        self.add_filter_btn.pack(side=tk.LEFT, padx=2)
        
        self.remove_filter_btn = ttk.Button(
            btn_frame,
            text="Remove",
            command=self._on_remove_filter_click
        )
        self.remove_filter_btn.pack(side=tk.LEFT, padx=2)
    
    def _create_sort_section(self, parent):
        """Create the Sort operations section."""
        sort_frame = ttk.LabelFrame(parent, text="Sort", padding="5")
        sort_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        # Current sort display
        self.sort_label = ttk.Label(sort_frame, text="No sort applied")
        self.sort_label.pack(fill=tk.X, pady=(0, 5))
        
        # Buttons
        btn_frame = ttk.Frame(sort_frame)
        btn_frame.pack(fill=tk.X)
        
        self.set_sort_btn = ttk.Button(
            btn_frame,
            text="Set Sort",
            command=self._on_set_sort_click
        )
        self.set_sort_btn.pack(side=tk.LEFT, padx=2)
        
        self.clear_sort_btn = ttk.Button(
            btn_frame,
            text="Clear",
            command=self._on_clear_sort_click
        )
        self.clear_sort_btn.pack(side=tk.LEFT, padx=2)
        
        # Clear All button (clears all operations at once)
        self.clear_all_btn = ttk.Button(
            btn_frame,
            text="Clear All Ops",
            command=self._on_clear_all_operations_click
        )
        self.clear_all_btn.pack(side=tk.LEFT, padx=(10, 2))
    
    def _create_status_bar(self):
        """Create the status bar showing current state."""
        self.status_frame = ttk.Frame(self.root, padding="5")
        self.status_frame.pack(fill=tk.X, padx=5)
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="No dataset loaded",
            font=("TkDefaultFont", 9)
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Warning label (hidden by default)
        self.warning_label = ttk.Label(
            self.status_frame,
            text="",
            foreground="red",
            font=("TkDefaultFont", 9, "bold")
        )
        self.warning_label.pack(side=tk.RIGHT)
    
    def _create_data_table(self):
        """Create the data table with scrollbars and pagination."""
        # Table frame
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create Treeview for table display
        self.tree = ttk.Treeview(table_frame, show="headings")
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Grid layout for table and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Bind header click for sorting
        self.tree.bind("<Button-1>", self._on_header_click)
        
        # Pagination controls
        self._create_pagination_controls()
    
    def _create_pagination_controls(self):
        """Create pagination controls below the data table."""
        page_frame = ttk.Frame(self.root, padding="5")
        page_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Previous button
        self.prev_btn = ttk.Button(
            page_frame,
            text="< Previous",
            command=self._on_prev_page
        )
        self.prev_btn.pack(side=tk.LEFT)
        
        # Page indicator
        self.page_label = ttk.Label(page_frame, text="Page 1 of 1")
        self.page_label.pack(side=tk.LEFT, padx=20)
        
        # Next button
        self.next_btn = ttk.Button(
            page_frame,
            text="Next >",
            command=self._on_next_page
        )
        self.next_btn.pack(side=tk.LEFT)
        
        # Page size selector
        ttk.Label(page_frame, text="Rows per page:").pack(side=tk.RIGHT, padx=(10, 5))
        
        self.page_size_var = tk.StringVar(value=str(DEFAULT_PAGE_SIZE))
        page_size_dropdown = ttk.Combobox(
            page_frame,
            textvariable=self.page_size_var,
            values=["25", "50", "100", "200", "500"],
            state="readonly",
            width=5
        )
        page_size_dropdown.pack(side=tk.RIGHT)
        page_size_dropdown.bind("<<ComboboxSelected>>", self._on_page_size_changed)
    
    # -------------------------------------------------------------------------
    # DATA REFRESH METHODS
    # -------------------------------------------------------------------------
    
    def _refresh_dataset_list(self):
        """Refresh the dataset dropdown with available imports."""
        imports_df = self.data_store.list_imports()
        
        if len(imports_df) == 0:
            self.dataset_dropdown["values"] = ["No datasets available"]
            self.dataset_var.set("No datasets available")
            return
        
        # Build list of options: "N. Source Name (X rows)"
        options = []
        self.import_id_map = {}  # Map display string to import_id
        
        for index in range(len(imports_df)):
            row = imports_df.iloc[index]
            # Use sequential number (index + 1) instead of database ID for display
            display = str(index + 1) + ". " + row["source_name"] + " (" + str(row["record_count"]) + " rows)"
            options.append(display)
            # Convert numpy.int64 to native Python int for SQLite compatibility
            self.import_id_map[display] = int(row["id"])
        
        self.dataset_dropdown["values"] = options
        
        # Select first option if nothing selected
        if not self.dataset_var.get() or self.dataset_var.get() == "No datasets available":
            self.dataset_var.set(options[0])
            self._load_dataset(self.import_id_map[options[0]])
    
    def _load_dataset(self, import_id):
        """
        Load a dataset and create an analysis session.
        
        Args:
            import_id (int): The ID of the import to load
        """
        self.current_import_id = import_id
        
        # Get data from data store
        df = self.data_store.get_raw_data(import_id)
        
        # Remove the internal _record_id column from display if present
        display_columns = [col for col in df.columns if not col.startswith("_")]
        df_display = df[display_columns]
        
        # Get source name for session
        import_info = self.data_store.get_import_info(import_id)
        source_name = import_info["source_name"] if import_info else "Unknown"
        
        # Create new analysis session
        self.session = AnalysisSession(df_display, source_name)
        
        # Reset pagination
        self.current_page = 1
        
        # Refresh display
        self._refresh_table()
        self._refresh_operations_display()
        self._update_status()
        
        self.logger.info("Loaded dataset: " + source_name + " (ID: " + str(import_id) + ")")
    
    def _refresh_table(self):
        """Refresh the data table with current view."""
        if self.session is None:
            return
        
        # Get current view from session
        df = self.session.get_current_view()
        
        # Clear existing data
        self.tree.delete(*self.tree.get_children())
        
        # Configure columns - add Row # as first column
        data_columns = list(df.columns)
        all_columns = ["#"] + data_columns
        self.tree["columns"] = all_columns
        
        # Configure row number column
        self.tree.heading("#", text="#")
        self.tree.column("#", width=50, minwidth=40, stretch=False)
        
        for col in data_columns:
            self.tree.heading(col, text=col)
            # Calculate column width based on header and data
            width = min(max(len(col) * 10, COLUMN_MIN_WIDTH), COLUMN_MAX_WIDTH)
            self.tree.column(col, width=width, minwidth=COLUMN_MIN_WIDTH)
        
        # Calculate pagination
        total_rows = len(df)
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        
        # Ensure current page is valid
        if self.current_page > total_pages:
            self.current_page = total_pages
        
        # Get rows for current page
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        page_df = df.iloc[start_idx:end_idx]
        
        # Insert rows with row numbers that continue across pages
        for index in range(len(page_df)):
            row = page_df.iloc[index]
            # Row number continues from previous pages
            row_number = start_idx + index + 1
            values = [row_number]  # Start with row number
            for col in data_columns:
                value = row[col]
                # Truncate long text
                display_value = truncate_text(value, CELL_MAX_DISPLAY_CHARS)
                values.append(display_value)
            self.tree.insert("", tk.END, values=values)
        
        # Update pagination display
        self.page_label.config(text="Page " + str(self.current_page) + " of " + str(total_pages))
        
        # Enable/disable pagination buttons
        self.prev_btn.config(state=tk.NORMAL if self.current_page > 1 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_page < total_pages else tk.DISABLED)
    
    def _refresh_operations_display(self):
        """Refresh the operations panel to show current operations."""
        if self.session is None:
            return
        
        # Refresh clean operations list
        self.clean_listbox.delete(0, tk.END)
        for op_id, description in self.session.list_clean_operations():
            self.clean_listbox.insert(tk.END, str(op_id) + ": " + description)
        
        # Refresh filter operations list
        self.filter_listbox.delete(0, tk.END)
        for op_id, description in self.session.list_filter_operations():
            self.filter_listbox.insert(tk.END, str(op_id) + ": " + description)
        
        # Refresh sort display
        sort_info = self.session.get_sort_operation()
        if sort_info:
            column, ascending = sort_info
            direction = "ascending" if ascending else "descending"
            self.sort_label.config(text=column + " (" + direction + ")")
        else:
            self.sort_label.config(text="No sort applied")
    
    def _update_status(self):
        """Update the status bar with current state."""
        if self.session is None:
            self.status_label.config(text="No dataset loaded")
            self.warning_label.config(text="")
            return
        
        # Build status message
        current_rows = self.session.get_row_count()
        total_rows = self.session.get_original_row_count()
        
        status_parts = [format_row_count(current_rows, total_rows)]
        
        clean_count = len(self.session.list_clean_operations())
        if clean_count > 0:
            status_parts.append(str(clean_count) + " clean operation" + ("s" if clean_count > 1 else ""))
        
        filter_count = len(self.session.list_filter_operations())
        if filter_count > 0:
            status_parts.append(str(filter_count) + " filter" + ("s" if filter_count > 1 else ""))
        
        sort_info = self.session.get_sort_operation()
        if sort_info:
            column, ascending = sort_info
            direction = "ascending" if ascending else "descending"
            status_parts.append("Sorted by " + column + " " + direction)
        
        self.status_label.config(text=" | ".join(status_parts))
        
        # Show warning if no data
        if current_rows == 0:
            self.warning_label.config(
                text="No data matches current criteria. Adjust filters or clean operations."
            )
        else:
            self.warning_label.config(text="")
    
    # -------------------------------------------------------------------------
    # EVENT HANDLERS - Toolbar
    # -------------------------------------------------------------------------
    
    def _on_dataset_selected(self, event):
        """Handle dataset selection from dropdown."""
        selected = self.dataset_var.get()
        if selected in self.import_id_map:
            import_id = self.import_id_map[selected]
            self._load_dataset(import_id)
    
    def _on_import_click(self):
        """Handle Import CSV button click."""
        # Open file dialog
        filepath = filedialog.askopenfilename(
            title="Select CSV file to import",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return  # User cancelled
        
        try:
            # Import the file
            adapter = CSVAdapter(filepath)
            import_id = self.data_store.import_data(adapter)
            
            self.logger.info("Imported CSV: " + filepath + " (ID: " + str(import_id) + ")")
            
            # Refresh dataset list and select new import
            self._refresh_dataset_list()
            
            # Find and select the new import
            for display, id_val in self.import_id_map.items():
                if id_val == import_id:
                    self.dataset_var.set(display)
                    self._load_dataset(import_id)
                    break
            
            messagebox.showinfo("Import Successful", "Data imported successfully!")
            
        except Exception as e:
            self.logger.error("Import failed: " + str(e))
            messagebox.showerror("Import Error", "Failed to import file:\n" + str(e))
    
    def _on_import_api_click(self):
        """Handle Import WHO API button click."""
        # Create dialog for indicator selection
        dialog = tk.Toplevel(self.root)
        dialog.title("Import from WHO API")
        dialog.geometry("450x320")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 320) // 2
        dialog.geometry("+{}+{}".format(x, y))
        
        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        ttk.Label(
            main_frame,
            text="Import from WHO Global Health Observatory",
            font=("TkDefaultFont", 11, "bold")
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Indicator selection
        ttk.Label(main_frame, text="Select Health Indicator:").pack(anchor=tk.W)
        
        indicator_var = tk.StringVar(value="life_expectancy")
        indicators = [
            ("Life Expectancy at Birth", "life_expectancy"),
            ("Infant Mortality Rate", "infant_mortality"),
            ("Neonatal Mortality Rate", "neonatal_mortality"),
            ("DTP3 Vaccination Coverage", "vaccination_dtp3"),
            ("Measles Vaccination Coverage", "vaccination_measles"),
        ]
        
        indicator_frame = ttk.Frame(main_frame)
        indicator_frame.pack(fill=tk.X, pady=5)
        
        for display_name, value in indicators:
            ttk.Radiobutton(
                indicator_frame,
                text=display_name,
                variable=indicator_var,
                value=value
            ).pack(anchor=tk.W)
        
        # Record limit
        limit_frame = ttk.Frame(main_frame)
        limit_frame.pack(fill=tk.X, pady=(15, 5))
        
        ttk.Label(limit_frame, text="Max Records:").pack(side=tk.LEFT)
        limit_var = tk.StringVar(value="1000")
        limit_entry = ttk.Entry(limit_frame, textvariable=limit_var, width=10)
        limit_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(limit_frame, text="(max 10000)").pack(side=tk.LEFT)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def do_import():
            try:
                limit = int(limit_var.get())
                if limit < 1 or limit > 10000:
                    raise ValueError("Limit must be between 1 and 10000")
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e))
                return
            
            indicator = indicator_var.get()
            dialog.destroy()
            
            # Show progress
            self.root.config(cursor="wait")
            self.root.update()
            
            try:
                adapter = WHOAPIAdapter(indicator=indicator, limit=limit)
                import_id = self.data_store.import_data(adapter)
                
                self.logger.info("Imported WHO API: " + indicator + " (ID: " + str(import_id) + ")")
                
                # Refresh dataset list and select new import
                self._refresh_dataset_list()
                
                # Find and select the new import
                for display, id_val in self.import_id_map.items():
                    if id_val == import_id:
                        self.dataset_var.set(display)
                        self._load_dataset(import_id)
                        break
                
                messagebox.showinfo("Import Successful", "WHO data imported successfully!")
                
            except Exception as e:
                self.logger.error("WHO API import failed: " + str(e))
                messagebox.showerror("Import Error", "Failed to import from WHO API:\n" + str(e))
            finally:
                self.root.config(cursor="")
        
        ttk.Button(button_frame, text="Import", command=do_import).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def _on_export_click(self):
        """Handle Export CSV button click."""
        if self.session is None:
            messagebox.showwarning("No Data", "Please select a dataset first.")
            return
        
        # Get default filename
        default_name = get_default_csv_filename(self.session.source_name)
        
        # Open save dialog
        filepath = filedialog.asksaveasfilename(
            title="Export CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return  # User cancelled
        
        try:
            # Get current view and export
            df = self.session.get_current_view()
            df.to_csv(filepath, index=False)
            
            self.logger.info("Exported CSV: " + filepath + " (" + str(len(df)) + " rows)")
            messagebox.showinfo("Export Successful", "Data exported to:\n" + filepath)
            
        except Exception as e:
            self.logger.error("Export failed: " + str(e))
            messagebox.showerror("Export Error", "Failed to export file:\n" + str(e))
    
    def _on_delete_click(self):
        """Handle Delete Dataset button click."""
        if self.current_import_id is None:
            messagebox.showwarning("No Dataset", "Please select a dataset first.")
            return
        
        # Get dataset name for confirmation
        selected = self.dataset_var.get()
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this dataset?\n\n" + selected + 
            "\n\nThis action cannot be undone.",
            icon="warning"
        )
        
        if not result:
            return  # User cancelled
        
        try:
            # Delete the import
            import_id = self.current_import_id
            success = self.data_store.delete_import(import_id)
            
            if success:
                self.logger.info("Deleted dataset: " + selected + " (ID: " + str(import_id) + ")")
                
                # Clear current session
                self.session = None
                self.current_import_id = None
                
                # Clear the table
                self.tree.delete(*self.tree.get_children())
                self.tree["columns"] = []
                
                # Refresh the dataset list
                self._refresh_dataset_list()
                
                # Update status
                self._update_status()
                
                messagebox.showinfo("Delete Successful", "Dataset deleted successfully.")
            else:
                messagebox.showerror("Delete Failed", "Dataset not found.")
                
        except Exception as e:
            self.logger.error("Delete failed: " + str(e))
            messagebox.showerror("Delete Error", "Failed to delete dataset:\n" + str(e))
    
    def _on_summary_click(self):
        """Handle Summary button click."""
        if self.session is None:
            messagebox.showwarning("No Data", "Please select a dataset first.")
            return
        
        if self.session.get_row_count() == 0:
            messagebox.showwarning("No Data", "No data available. Adjust your filters.")
            return
        
        # Open summary popup
        SummaryPopup(self.root, self.session, self.logger)
    
    def _on_graph_click(self):
        """Handle Graph button click."""
        if self.session is None:
            messagebox.showwarning("No Data", "Please select a dataset first.")
            return
        
        if self.session.get_row_count() == 0:
            messagebox.showwarning("No Data", "No data available. Adjust your filters.")
            return
        
        # Open graph popup
        GraphPopup(self.root, self.session, self.logger)
    
    def _on_view_log_click(self):
        """Handle View Log button click - opens the log file in the default text editor."""
        import os
        import subprocess
        import platform
        
        log_file = get_log_file_path()
        
        if not log_file.exists():
            messagebox.showinfo("No Log File", "No log file exists yet. Activities will be logged as you use the application.")
            return
        
        try:
            # Open log file with default system application
            if platform.system() == "Windows":
                os.startfile(str(log_file))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(log_file)])
            else:  # Linux
                subprocess.run(["xdg-open", str(log_file)])
            
            self.logger.info("Opened log file: " + str(log_file))
        except Exception as e:
            messagebox.showerror("Error", "Could not open log file: " + str(e))
            self.logger.error("Failed to open log file: " + str(e))
    
    # -------------------------------------------------------------------------
    # EVENT HANDLERS - Record CRUD Operations
    # -------------------------------------------------------------------------
    
    def _on_add_record_click(self):
        """Handle Add Record button click."""
        if self.current_import_id is None:
            messagebox.showwarning("No Dataset", "Please select a dataset first.")
            return
        
        # Open add record dialog
        AddRecordDialog(self.root, self.data_store, self.current_import_id, 
                        self.session.get_columns(), self._on_record_changed)
    
    def _on_edit_record_click(self):
        """Handle Edit Record button click."""
        if self.current_import_id is None:
            messagebox.showwarning("No Dataset", "Please select a dataset first.")
            return
        
        # Get selected row from treeview
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a row to edit.")
            return
        
        # Get the row number from the first column (index 0)
        row_values = self.tree.item(selection[0], "values")
        if not row_values:
            return
        
        row_number = int(row_values[0])  # First column is row #
        
        # Get the record_id from raw data
        raw_df = self.data_store.get_raw_data(self.current_import_id)
        if row_number > len(raw_df):
            messagebox.showerror("Error", "Row not found.")
            return
        
        record_id = int(raw_df.iloc[row_number - 1]["_record_id"])
        record_data = {col: raw_df.iloc[row_number - 1][col] 
                       for col in raw_df.columns if not col.startswith("_")}
        
        # Open edit record dialog
        EditRecordDialog(self.root, self.data_store, record_id, record_data, 
                         self._on_record_changed)
    
    def _on_delete_record_click(self):
        """Handle Delete Record button click."""
        if self.current_import_id is None:
            messagebox.showwarning("No Dataset", "Please select a dataset first.")
            return
        
        # Get selected row from treeview
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a row to delete.")
            return
        
        # Get the row number from the first column
        row_values = self.tree.item(selection[0], "values")
        if not row_values:
            return
        
        row_number = int(row_values[0])
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete row #" + str(row_number) + "?\n\n" +
            "This action cannot be undone.",
            icon="warning"
        )
        
        if not result:
            return
        
        # Get the record_id from raw data
        raw_df = self.data_store.get_raw_data(self.current_import_id)
        if row_number > len(raw_df):
            messagebox.showerror("Error", "Row not found.")
            return
        
        record_id = int(raw_df.iloc[row_number - 1]["_record_id"])
        
        try:
            success = self.data_store.delete_record(record_id)
            if success:
                self.logger.info("Deleted record ID: " + str(record_id))
                self._on_record_changed()
                messagebox.showinfo("Success", "Record deleted successfully.")
            else:
                messagebox.showerror("Error", "Record not found.")
        except Exception as e:
            self.logger.error("Delete record failed: " + str(e))
            messagebox.showerror("Error", "Failed to delete record: " + str(e))
    
    def _on_record_changed(self):
        """Callback when a record is added, edited, or deleted."""
        # Reload the dataset to reflect changes
        self._load_dataset(self.current_import_id)
        # Refresh the dataset list to update record counts
        self._refresh_dataset_list()
    
    # -------------------------------------------------------------------------
    # EVENT HANDLERS - Operations
    # -------------------------------------------------------------------------
    
    def _on_add_clean_click(self):
        """Handle Add Clean button click."""
        if self.session is None:
            messagebox.showwarning("No Data", "Please select a dataset first.")
            return
        
        # Open add clean dialog
        AddCleanDialog(self.root, self.session, self._on_operation_added)
    
    def _on_remove_clean_click(self):
        """Handle Remove Clean button click."""
        selection = self.clean_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a clean operation to remove.")
            return
        
        # Get the operation ID from the selected item
        selected_text = self.clean_listbox.get(selection[0])
        op_id = int(selected_text.split(":")[0])
        
        # Remove the operation
        self.session.remove_clean(op_id)
        self.logger.info("Removed clean operation ID: " + str(op_id))
        
        # Refresh display
        self._on_operation_added()
    
    def _on_add_filter_click(self):
        """Handle Add Filter button click."""
        if self.session is None:
            messagebox.showwarning("No Data", "Please select a dataset first.")
            return
        
        # Open add filter dialog
        AddFilterDialog(self.root, self.session, self._on_operation_added)
    
    def _on_remove_filter_click(self):
        """Handle Remove Filter button click."""
        selection = self.filter_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a filter to remove.")
            return
        
        # Get the operation ID from the selected item
        selected_text = self.filter_listbox.get(selection[0])
        op_id = int(selected_text.split(":")[0])
        
        # Remove the operation
        self.session.remove_filter(op_id)
        self.logger.info("Removed filter operation ID: " + str(op_id))
        
        # Refresh display
        self._on_operation_added()
    
    def _on_set_sort_click(self):
        """Handle Set Sort button click."""
        if self.session is None:
            messagebox.showwarning("No Data", "Please select a dataset first.")
            return
        
        # Open set sort dialog
        SetSortDialog(self.root, self.session, self._on_operation_added)
    
    def _on_clear_sort_click(self):
        """Handle Clear Sort button click."""
        if self.session is None:
            return
        
        self.session.clear_sort()
        self.logger.info("Cleared sort operation")
        self._on_operation_added()
    
    def _on_clear_all_operations_click(self):
        """Handle Clear All Operations button click."""
        if self.session is None:
            return
        
        # Check if there are any operations to clear
        ops = self.session.list_all_operations()
        if not ops["clean"] and not ops["filter"] and not ops["sort"]:
            messagebox.showinfo("No Operations", "There are no operations to clear.")
            return
        
        # Confirm clearing all
        result = messagebox.askyesno(
            "Clear All Operations",
            "This will remove all clean, filter, and sort operations.\n\n" +
            "Are you sure you want to continue?",
            icon="question"
        )
        
        if not result:
            return
        
        self.session.clear_all_operations()
        self.logger.info("Cleared all operations")
        self._on_operation_added()
    
    def _on_operation_added(self):
        """Called when any operation is added or removed."""
        self.current_page = 1  # Reset to first page
        self._refresh_table()
        self._refresh_operations_display()
        self._update_status()
    
    # -------------------------------------------------------------------------
    # EVENT HANDLERS - Table and Pagination
    # -------------------------------------------------------------------------
    
    def _on_header_click(self, event):
        """Handle click on table header for quick sorting."""
        if self.session is None:
            return
        
        # Get the column that was clicked
        region = self.tree.identify_region(event.x, event.y)
        if region != "heading":
            return
        
        column = self.tree.identify_column(event.x)
        col_index = int(column.replace("#", "")) - 1
        
        # Skip the row number column (index 0)
        if col_index == 0:
            return  # Row number column is not sortable
        
        # Adjust index to account for row number column
        data_col_index = col_index - 1
        
        columns = list(self.session.get_current_view().columns)
        if data_col_index < 0 or data_col_index >= len(columns):
            return
        
        col_name = columns[data_col_index]
        
        # Toggle sort direction if already sorting by this column
        current_sort = self.session.get_sort_operation()
        if current_sort and current_sort[0] == col_name:
            ascending = not current_sort[1]  # Toggle direction
        else:
            ascending = True
        
        self.session.set_sort(col_name, ascending)
        self.logger.info("Sort set via header click: " + col_name + " " + ("ascending" if ascending else "descending"))
        self._on_operation_added()
    
    def _on_prev_page(self):
        """Handle Previous page button click."""
        if self.current_page > 1:
            self.current_page = self.current_page - 1
            self._refresh_table()
    
    def _on_next_page(self):
        """Handle Next page button click."""
        if self.session is None:
            return
        
        total_rows = self.session.get_row_count()
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        
        if self.current_page < total_pages:
            self.current_page = self.current_page + 1
            self._refresh_table()
    
    def _on_page_size_changed(self, event):
        """Handle page size dropdown change."""
        try:
            self.page_size = int(self.page_size_var.get())
            self.current_page = 1  # Reset to first page
            self._refresh_table()
        except ValueError:
            pass


# =============================================================================
# DIALOG CLASSES
# =============================================================================

class AddCleanDialog:
    """Dialog for adding a clean operation."""
    
    def __init__(self, parent, session, callback):
        """
        Initialize the Add Clean dialog.
        
        Args:
            parent: Parent window
            session: Current AnalysisSession
            callback: Function to call when operation is added
        """
        self.session = session
        self.callback = callback
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Clean Operation")
        self.dialog.geometry("400x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Column selection
        ttk.Label(self.dialog, text="Select columns to check for missing values:").pack(
            anchor=tk.W, padx=10, pady=(10, 5)
        )
        
        # Listbox with checkboxes (using Listbox with selection)
        columns_frame = ttk.Frame(self.dialog)
        columns_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.columns_listbox = tk.Listbox(columns_frame, selectmode=tk.MULTIPLE, height=8)
        scrollbar = ttk.Scrollbar(columns_frame, orient=tk.VERTICAL, command=self.columns_listbox.yview)
        self.columns_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.columns_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate columns
        for col in session.get_columns():
            self.columns_listbox.insert(tk.END, col)
        
        # Missing values section
        ttk.Label(self.dialog, text="Values treated as missing:").pack(
            anchor=tk.W, padx=10, pady=(10, 5)
        )
        
        self.missing_text = tk.Text(self.dialog, height=3, width=40)
        self.missing_text.pack(padx=10, pady=5, fill=tk.X)
        self.missing_text.insert(tk.END, ", ".join(DEFAULT_MISSING_VALUES[:5]))
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Add", command=self._on_add, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)
    
    def _on_add(self):
        """Handle Add button click."""
        # Get selected columns
        selection = self.columns_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select at least one column.")
            return
        
        columns = [self.columns_listbox.get(i) for i in selection]
        
        # Get missing values
        missing_text = self.missing_text.get("1.0", tk.END).strip()
        missing_values = [v.strip() for v in missing_text.split(",") if v.strip()]
        
        # Add the clean operation
        self.session.add_clean(columns, missing_values if missing_values else None)
        
        self.dialog.destroy()
        self.callback()


class AddFilterDialog:
    """Dialog for adding a filter operation."""
    
    def __init__(self, parent, session, callback):
        """
        Initialize the Add Filter dialog.
        
        Args:
            parent: Parent window
            session: Current AnalysisSession
            callback: Function to call when filter is added
        """
        self.session = session
        self.callback = callback
        self.parent = parent
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Filter")
        self.dialog.geometry("450x450")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Column selection
        ttk.Label(self.dialog, text="Select column to filter:").pack(
            anchor=tk.W, padx=10, pady=(10, 5)
        )
        
        self.column_var = tk.StringVar()
        self.column_dropdown = ttk.Combobox(
            self.dialog,
            textvariable=self.column_var,
            state="readonly",
            width=30
        )
        self.column_dropdown["values"] = session.get_columns()
        self.column_dropdown.pack(anchor=tk.W, padx=10, pady=5)
        self.column_dropdown.bind("<<ComboboxSelected>>", self._on_column_selected)
        
        # Filter options frame (changes based on column type)
        self.options_frame = ttk.Frame(self.dialog)
        self.options_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Placeholder text
        self.placeholder_label = ttk.Label(
            self.options_frame,
            text="Select a column to see filter options"
        )
        self.placeholder_label.pack(pady=20)
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.add_btn = ttk.Button(btn_frame, text="Add Filter", command=self._on_add, state=tk.DISABLED, width=12)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)
        
        # Store current filter type and widgets
        self.filter_type = None
        self.filter_widgets = {}
    
    def _on_column_selected(self, event):
        """Handle column selection."""
        column = self.column_var.get()
        
        # Clear options frame
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        
        # Get filter options from session
        options = self.session.get_filter_options(column)
        self.filter_type = options.get("type")
        
        if self.filter_type == "text":
            self._create_text_filter_options(options)
        elif self.filter_type == "numeric":
            self._create_numeric_filter_options(options)
        elif self.filter_type == "date":
            self._create_date_filter_options(options)
        else:
            ttk.Label(self.options_frame, text="Cannot filter this column").pack(pady=20)
            return
        
        self.add_btn.config(state=tk.NORMAL)
    
    def _create_text_filter_options(self, options):
        """Create filter options for text columns."""
        values = options.get("values", [])
        truncated = options.get("truncated", False)
        
        if truncated:
            ttk.Label(
                self.options_frame,
                text="Showing " + str(len(values)) + " most common values. Use search for others.",
                foreground="orange"
            ).pack(anchor=tk.W, pady=(0, 5))
        
        ttk.Label(self.options_frame, text="Select values to include:").pack(anchor=tk.W)
        
        # Search entry
        search_frame = ttk.Frame(self.options_frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(search_frame, text="Search", command=self._on_search).pack(side=tk.LEFT)
        
        # Values listbox with scrollbar
        list_frame = ttk.Frame(self.options_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.values_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=10)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.values_listbox.yview)
        self.values_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.values_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        for val in values:
            self.values_listbox.insert(tk.END, str(val))
        
        self.filter_widgets["values_listbox"] = self.values_listbox
        self.filter_widgets["all_values"] = [str(v) for v in values]
    
    def _on_search(self):
        """Handle search button click for text filter."""
        search_term = self.search_var.get()
        if not search_term:
            return
        
        column = self.column_var.get()
        matches = self.session.search_filter_values(column, search_term)
        
        # Update listbox with search results
        self.values_listbox.delete(0, tk.END)
        for val in matches[:MAX_FILTER_DISPLAY_VALUES]:
            self.values_listbox.insert(tk.END, str(val))
    
    def _create_numeric_filter_options(self, options):
        """Create filter options for numeric columns with dual-handle range slider."""
        min_val = options.get("min", 0)
        max_val = options.get("max", 100)
        
        # Store data bounds for validation
        self.filter_widgets["data_min"] = min_val
        self.filter_widgets["data_max"] = max_val
        
        ttk.Label(self.options_frame, text="Select range:").pack(anchor=tk.W)
        
        # Show actual data range
        range_label = ttk.Label(
            self.options_frame,
            text="Data range: " + format_number(min_val) + " to " + format_number(max_val),
            foreground="gray"
        )
        range_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Create dual-handle range slider using Canvas
        self.min_var = tk.DoubleVar(value=min_val)
        self.max_var = tk.DoubleVar(value=max_val)
        
        slider_frame = ttk.Frame(self.options_frame)
        slider_frame.pack(fill=tk.X, pady=10)
        
        # Create the custom range slider
        self.range_slider = DualRangeSlider(
            slider_frame,
            min_val=min_val,
            max_val=max_val,
            low_var=self.min_var,
            high_var=self.max_var,
            on_change=self._on_range_changed
        )
        self.range_slider.pack(fill=tk.X, padx=10)
        
        # Entry fields for precise input
        entry_frame = ttk.Frame(self.options_frame)
        entry_frame.pack(fill=tk.X, pady=10)
        
        # Min entry
        ttk.Label(entry_frame, text="Min:").pack(side=tk.LEFT, padx=(0, 5))
        self.min_entry_var = tk.StringVar(value=format_number(min_val))
        min_entry = ttk.Entry(entry_frame, textvariable=self.min_entry_var, width=12)
        min_entry.pack(side=tk.LEFT, padx=(0, 20))
        min_entry.bind("<FocusOut>", lambda e: self._on_min_entry_changed())
        min_entry.bind("<Return>", lambda e: self._on_min_entry_changed())
        
        # Max entry
        ttk.Label(entry_frame, text="Max:").pack(side=tk.LEFT, padx=(0, 5))
        self.max_entry_var = tk.StringVar(value=format_number(max_val))
        max_entry = ttk.Entry(entry_frame, textvariable=self.max_entry_var, width=12)
        max_entry.pack(side=tk.LEFT)
        max_entry.bind("<FocusOut>", lambda e: self._on_max_entry_changed())
        max_entry.bind("<Return>", lambda e: self._on_max_entry_changed())
        
        # Selected range display
        self.range_display = ttk.Label(
            self.options_frame,
            text="Selected: " + format_number(min_val) + " to " + format_number(max_val),
            font=("TkDefaultFont", 9, "bold")
        )
        self.range_display.pack(anchor=tk.W, pady=5)
        
        # Validation message label (hidden initially)
        self.validation_label = ttk.Label(
            self.options_frame,
            text="",
            foreground="red"
        )
        self.validation_label.pack(anchor=tk.W)
        
        self.filter_widgets["min_var"] = self.min_var
        self.filter_widgets["max_var"] = self.max_var
        self.filter_widgets["min_entry_var"] = self.min_entry_var
        self.filter_widgets["max_entry_var"] = self.max_entry_var
    
    def _on_range_changed(self):
        """Handle range slider value change."""
        min_val = self.min_var.get()
        max_val = self.max_var.get()
        
        # Update entry fields
        self.min_entry_var.set(format_number(min_val))
        self.max_entry_var.set(format_number(max_val))
        self._update_range_display()
    
    def _on_min_entry_changed(self):
        """Handle minimum entry value change."""
        try:
            value = float(self.min_entry_var.get().replace(",", ""))
            data_min = self.filter_widgets["data_min"]
            data_max = self.filter_widgets["data_max"]
            
            # Clamp to data bounds
            if value < data_min:
                value = data_min
                self.validation_label.config(
                    text="Minimum clamped to data minimum: " + format_number(data_min)
                )
            elif value > data_max:
                value = data_max
                self.validation_label.config(
                    text="Minimum clamped to data maximum: " + format_number(data_max)
                )
            else:
                self.validation_label.config(text="")
            
            # Ensure min doesn't exceed max
            if value > self.max_var.get():
                value = self.max_var.get()
            
            self.min_var.set(value)
            self.min_entry_var.set(format_number(value))
            self.range_slider.update_handles()
            self._update_range_display()
        except ValueError:
            self.validation_label.config(text="Please enter a valid number")
    
    def _on_max_entry_changed(self):
        """Handle maximum entry value change."""
        try:
            value = float(self.max_entry_var.get().replace(",", ""))
            data_min = self.filter_widgets["data_min"]
            data_max = self.filter_widgets["data_max"]
            
            # Clamp to data bounds
            if value > data_max:
                value = data_max
                self.validation_label.config(
                    text="Maximum clamped to data maximum: " + format_number(data_max)
                )
            elif value < data_min:
                value = data_min
                self.validation_label.config(
                    text="Maximum clamped to data minimum: " + format_number(data_min)
                )
            else:
                self.validation_label.config(text="")
            
            # Ensure max doesn't go below min
            if value < self.min_var.get():
                value = self.min_var.get()
            
            self.max_var.set(value)
            self.max_entry_var.set(format_number(value))
            self.range_slider.update_handles()
            self._update_range_display()
        except ValueError:
            self.validation_label.config(text="Please enter a valid number")
    
    def _update_range_display(self):
        """Update the selected range display label."""
        min_val = self.min_var.get()
        max_val = self.max_var.get()
        self.range_display.config(
            text="Selected: " + format_number(min_val) + " to " + format_number(max_val)
        )
    
    def _create_date_filter_options(self, options):
        """Create filter options for date columns."""
        start_date = options.get("start")
        end_date = options.get("end")
        
        ttk.Label(self.options_frame, text="Select date range:").pack(anchor=tk.W)
        
        # Start date
        start_frame = ttk.Frame(self.options_frame)
        start_frame.pack(fill=tk.X, pady=5)
        ttk.Label(start_frame, text="Start date:").pack(side=tk.LEFT)
        
        start_str = str(start_date)[:10] if start_date else ""
        self.start_var = tk.StringVar(value=start_str)
        start_entry = ttk.Entry(start_frame, textvariable=self.start_var, width=15)
        start_entry.pack(side=tk.LEFT, padx=5)
        
        # End date
        end_frame = ttk.Frame(self.options_frame)
        end_frame.pack(fill=tk.X, pady=5)
        ttk.Label(end_frame, text="End date:").pack(side=tk.LEFT)
        
        end_str = str(end_date)[:10] if end_date else ""
        self.end_var = tk.StringVar(value=end_str)
        end_entry = ttk.Entry(end_frame, textvariable=self.end_var, width=15)
        end_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            self.options_frame,
            text="Format: YYYY-MM-DD",
            foreground="gray"
        ).pack(anchor=tk.W, pady=5)
        
        self.filter_widgets["start_var"] = self.start_var
        self.filter_widgets["end_var"] = self.end_var
    
    def _on_add(self):
        """Handle Add Filter button click."""
        column = self.column_var.get()
        
        try:
            if self.filter_type == "text":
                selection = self.filter_widgets["values_listbox"].curselection()
                if not selection:
                    messagebox.showwarning("No Selection", "Please select at least one value.")
                    return
                values = [self.filter_widgets["values_listbox"].get(i) for i in selection]
                self.session.add_filter_text(column, values)
                
            elif self.filter_type == "numeric":
                min_val = float(self.filter_widgets["min_var"].get())
                max_val = float(self.filter_widgets["max_var"].get())
                self.session.add_filter_numeric(column, min_val, max_val)
                
            elif self.filter_type == "date":
                start_date = self.filter_widgets["start_var"].get()
                end_date = self.filter_widgets["end_var"].get()
                self.session.add_filter_date(column, start_date, end_date)
            
            self.dialog.destroy()
            self.callback()
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))


class SetSortDialog:
    """Dialog for setting the sort operation."""
    
    def __init__(self, parent, session, callback):
        """
        Initialize the Set Sort dialog.
        
        Args:
            parent: Parent window
            session: Current AnalysisSession
            callback: Function to call when sort is set
        """
        self.session = session
        self.callback = callback
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Set Sort")
        self.dialog.geometry("350x220")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Column selection
        ttk.Label(self.dialog, text="Sort by column:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.column_var = tk.StringVar()
        column_dropdown = ttk.Combobox(
            self.dialog,
            textvariable=self.column_var,
            state="readonly",
            width=30
        )
        column_dropdown["values"] = session.get_columns()
        column_dropdown.pack(anchor=tk.W, padx=10, pady=5)
        
        # Set current sort if any
        current_sort = session.get_sort_operation()
        if current_sort:
            self.column_var.set(current_sort[0])
        
        # Direction selection
        ttk.Label(self.dialog, text="Direction:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.direction_var = tk.StringVar(value="ascending")
        if current_sort and not current_sort[1]:
            self.direction_var.set("descending")
        
        ttk.Radiobutton(
            self.dialog,
            text="Ascending (A-Z, 0-9, earliest first)",
            variable=self.direction_var,
            value="ascending"
        ).pack(anchor=tk.W, padx=20)
        
        ttk.Radiobutton(
            self.dialog,
            text="Descending (Z-A, 9-0, latest first)",
            variable=self.direction_var,
            value="descending"
        ).pack(anchor=tk.W, padx=20)
        
        # Buttons frame at bottom
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=15)
        
        ttk.Button(btn_frame, text="Apply Sort", command=self._on_apply, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)
    
    def _on_apply(self):
        """Handle Apply button click."""
        column = self.column_var.get()
        if not column:
            messagebox.showwarning("No Selection", "Please select a column.")
            return
        
        ascending = self.direction_var.get() == "ascending"
        self.session.set_sort(column, ascending)
        
        self.dialog.destroy()
        self.callback()


# =============================================================================
# POPUP WINDOWS
# =============================================================================

class SummaryPopup:
    """Popup window for generating statistical summaries."""
    
    def __init__(self, parent, session, logger):
        """
        Initialize the Summary popup.
        
        Args:
            parent: Parent window
            session: Current AnalysisSession
            logger: Logger instance
        """
        self.session = session
        self.logger = logger
        
        # Create popup window
        self.popup = tk.Toplevel(parent)
        self.popup.title("Summary Statistics")
        self.popup.geometry(str(POPUP_WIDTH) + "x" + str(POPUP_HEIGHT))
        self.popup.transient(parent)
        self.popup.grab_set()
        
        # Configuration section
        config_frame = ttk.LabelFrame(self.popup, text="Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Analyze column dropdown
        ttk.Label(config_frame, text="Analyze column:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.analyze_var = tk.StringVar()
        analyze_dropdown = ttk.Combobox(
            config_frame,
            textvariable=self.analyze_var,
            state="readonly",
            width=25
        )
        # All columns (both numeric and text)
        analyze_dropdown["values"] = session.get_columns()
        analyze_dropdown.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Group by dropdown
        ttk.Label(config_frame, text="Group by (optional):").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.group_var = tk.StringVar()
        group_dropdown = ttk.Combobox(
            config_frame,
            textvariable=self.group_var,
            state="readonly",
            width=25
        )
        group_dropdown["values"] = ["(No grouping)"] + session.get_columns()
        group_dropdown.set("(No grouping)")
        group_dropdown.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Generate button
        self.generate_btn = ttk.Button(
            config_frame,
            text="Generate Summary",
            command=self._on_generate,
            width=20
        )
        self.generate_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Results section
        results_frame = ttk.LabelFrame(self.popup, text="Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Results treeview
        self.results_tree = ttk.Treeview(results_frame, show="headings")
        results_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scroll.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Close button at bottom
        btn_frame = ttk.Frame(self.popup)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Close", command=self.popup.destroy, width=15).pack()
    
    def _on_generate(self):
        """Handle Generate Summary button click."""
        analyze_col = self.analyze_var.get()
        
        if not analyze_col:
            messagebox.showwarning("No Selection", "Please select a column to analyze.")
            return
        
        group_by = self.group_var.get()
        if group_by == "(No grouping)":
            group_by = None
        
        try:
            summary = self.session.get_summary(analyze_col, group_by)
            
            # Clear previous results
            self.results_tree.delete(*self.results_tree.get_children())
            
            if isinstance(summary, dict):
                # Single summary (no grouping)
                if "error" in summary:
                    messagebox.showerror("Error", summary["error"])
                    return
                
                # Display as single row
                columns = ["Statistic", "Value"]
                self.results_tree["columns"] = columns
                for col in columns:
                    self.results_tree.heading(col, text=col)
                    self.results_tree.column(col, width=200)
                
                # Text statistics that should not be formatted as numbers
                text_stats = ["column", "mode", "least_frequent", "top_5_values"]
                
                for key, value in summary.items():
                    if key != "column":
                        if key in text_stats:
                            display_val = str(value) if value is not None else "N/A"
                        else:
                            display_val = format_number(value)
                        self.results_tree.insert("", tk.END, values=[key, display_val])
            else:
                # Grouped summary (DataFrame)
                columns = list(summary.columns)
                self.results_tree["columns"] = columns
                for col in columns:
                    self.results_tree.heading(col, text=col)
                    self.results_tree.column(col, width=100)
                
                # Text statistics that should not be formatted as numbers
                text_stats = ["column", "group", "mode", "least_frequent", "top_5_values"]
                
                for idx in range(len(summary)):
                    row = summary.iloc[idx]
                    values = []
                    for col in columns:
                        if col in text_stats:
                            values.append(str(row[col]) if row[col] is not None else "N/A")
                        else:
                            values.append(format_number(row[col]))
                    self.results_tree.insert("", tk.END, values=values)
            
            self.logger.info("Generated summary for " + analyze_col + 
                           (" grouped by " + group_by if group_by else ""))
            
        except Exception as e:
            messagebox.showerror("Error", str(e))


class GraphPopup:
    """Popup window for generating charts with multiple Y-axis lines."""
    
    def __init__(self, parent, session, logger):
        """
        Initialize the Graph popup.
        
        Args:
            parent: Parent window
            session: Current AnalysisSession
            logger: Logger instance
        """
        self.session = session
        self.logger = logger
        self.y_columns = []  # List of selected Y columns
        
        # Create popup window
        self.popup = tk.Toplevel(parent)
        self.popup.title("Generate Graph")
        self.popup.geometry("750x650")
        self.popup.transient(parent)
        self.popup.grab_set()
        
        # Configuration section
        config_frame = ttk.LabelFrame(self.popup, text="Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # X axis dropdown
        x_frame = ttk.Frame(config_frame)
        x_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(x_frame, text="X Axis:", width=12).pack(side=tk.LEFT)
        
        self.x_var = tk.StringVar()
        self.x_dropdown = ttk.Combobox(
            x_frame,
            textvariable=self.x_var,
            state="readonly",
            width=25
        )
        self.x_dropdown["values"] = session.get_columns()
        self.x_dropdown.pack(side=tk.LEFT, padx=5)
        self.x_dropdown.bind("<<ComboboxSelected>>", self._on_x_changed)
        
        # Store all numeric columns for Y axis filtering
        self.all_numeric_columns = session.get_numeric_columns()
        
        # Y axis section with add/remove functionality
        y_section_frame = ttk.LabelFrame(config_frame, text="Y Axis Lines", padding="5")
        y_section_frame.pack(fill=tk.X, pady=10)
        
        # Add Y line controls
        add_y_frame = ttk.Frame(y_section_frame)
        add_y_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(add_y_frame, text="Add Y Column:").pack(side=tk.LEFT)
        
        self.y_add_var = tk.StringVar()
        self.y_dropdown = ttk.Combobox(
            add_y_frame,
            textvariable=self.y_add_var,
            state="readonly",
            width=20
        )
        # Initially show all numeric columns (will be filtered when X is selected)
        self.y_dropdown["values"] = self.all_numeric_columns
        self.y_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            add_y_frame,
            text="+ Add Line",
            command=self._add_y_column,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # List of current Y columns
        list_frame = ttk.Frame(y_section_frame)
        list_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(list_frame, text="Selected Y Lines:").pack(side=tk.LEFT)
        
        self.y_listbox = tk.Listbox(list_frame, height=4, width=40)
        self.y_listbox.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        y_btn_frame = ttk.Frame(list_frame)
        y_btn_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            y_btn_frame,
            text="Remove",
            command=self._remove_y_column,
            width=8
        ).pack(pady=2)
        
        ttk.Button(
            y_btn_frame,
            text="Clear All",
            command=self._clear_y_columns,
            width=8
        ).pack(pady=2)
        
        # Aggregation dropdown
        agg_frame = ttk.Frame(config_frame)
        agg_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(agg_frame, text="Aggregation:", width=12).pack(side=tk.LEFT)
        
        self.agg_var = tk.StringVar(value="sum")
        agg_dropdown = ttk.Combobox(
            agg_frame,
            textvariable=self.agg_var,
            state="readonly",
            width=15
        )
        agg_dropdown["values"] = ["sum", "mean", "count"]
        agg_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Group by dropdown (only shown for single Y column)
        group_frame = ttk.Frame(config_frame)
        group_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(group_frame, text="Group By:", width=12).pack(side=tk.LEFT)
        
        self.group_var = tk.StringVar(value="(No grouping)")
        self.group_dropdown = ttk.Combobox(
            group_frame,
            textvariable=self.group_var,
            state="readonly",
            width=25
        )
        # Populate with all columns plus no grouping option
        group_options = ["(No grouping)"] + session.get_columns()
        self.group_dropdown["values"] = group_options
        self.group_dropdown.pack(side=tk.LEFT, padx=5)
        
        self.group_note = ttk.Label(
            group_frame, 
            text="(only for single Y line)", 
            foreground="gray"
        )
        self.group_note.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.generate_btn = ttk.Button(
            btn_frame,
            text="Generate Graph",
            command=self._on_generate,
            width=20
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = ttk.Button(
            btn_frame,
            text="Export Image",
            command=self._on_export,
            state=tk.DISABLED,
            width=20
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        # Chart display area
        self.chart_frame = ttk.LabelFrame(self.popup, text="Chart", padding="10")
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.chart_label = ttk.Label(
            self.chart_frame,
            text="1. Select X Axis\n2. Add one or more Y Lines\n3. Click 'Generate Graph'"
        )
        self.chart_label.pack(expand=True)
        
        # Close button at bottom
        btn_frame = ttk.Frame(self.popup)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Close", command=self.popup.destroy, width=15).pack()
        
        # Store current figure path
        self.current_chart_path = None
    
    def _on_x_changed(self, event):
        """Handle X axis selection change - update Y dropdown to exclude X column."""
        x_col = self.x_var.get()
        
        # Filter out the X column from Y options
        available_y = [col for col in self.all_numeric_columns if col != x_col]
        self.y_dropdown["values"] = available_y
        
        # Clear Y dropdown selection if it was the same as X
        if self.y_add_var.get() == x_col:
            self.y_add_var.set("")
        
        # Also remove X from already selected Y columns if present
        if x_col in self.y_columns:
            self.y_columns.remove(x_col)
            self._update_y_listbox()
    
    def _add_y_column(self):
        """Add a Y column to the list."""
        col = self.y_add_var.get()
        if not col:
            messagebox.showwarning("No Selection", "Please select a column to add.")
            return
        
        if col in self.y_columns:
            messagebox.showinfo("Already Added", "This column is already in the list.")
            return
        
        self.y_columns.append(col)
        self._update_y_listbox()
        self._update_group_by_state()
        
        # Clear the dropdown selection
        self.y_add_var.set("")
    
    def _remove_y_column(self):
        """Remove the selected Y column from the list."""
        selection = self.y_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a line to remove.")
            return
        
        index = selection[0]
        self.y_columns.pop(index)
        self._update_y_listbox()
        self._update_group_by_state()
    
    def _clear_y_columns(self):
        """Clear all Y columns."""
        self.y_columns = []
        self._update_y_listbox()
        self._update_group_by_state()
    
    def _update_group_by_state(self):
        """Enable/disable group by based on number of Y columns."""
        if len(self.y_columns) <= 1:
            self.group_dropdown.config(state="readonly")
            self.group_note.config(text="(for single Y line)")
        else:
            self.group_dropdown.config(state="disabled")
            self.group_var.set("(No grouping)")
            self.group_note.config(text="(disabled for multi-line)")
    
    def _update_y_listbox(self):
        """Update the Y columns listbox display."""
        self.y_listbox.delete(0, tk.END)
        for i, col in enumerate(self.y_columns):
            self.y_listbox.insert(tk.END, str(i + 1) + ". " + col)
    
    def _on_generate(self):
        """Handle Generate Graph button click."""
        x_col = self.x_var.get()
        
        if not x_col:
            messagebox.showwarning("Missing Selection", "Please select an X axis column.")
            return
        
        if len(self.y_columns) == 0:
            messagebox.showwarning("Missing Selection", "Please add at least one Y axis line.")
            return
        
        aggregation = self.agg_var.get()
        
        # Get group_by (only for single Y column)
        group_by = None
        if len(self.y_columns) == 1:
            group_by = self.group_var.get()
            if group_by == "(No grouping)":
                group_by = None
        
        try:
            # Generate chart (don't show, just create)
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            
            # Use appropriate chart function based on Y columns and grouping
            if len(self.y_columns) == 1 and group_by is not None:
                # Single Y with grouping - use standard chart with group_by
                fig = self.session.generate_chart(
                    x_col, self.y_columns[0], group_by=group_by, 
                    aggregation=aggregation, show=False
                )
            else:
                # Multi-line chart (or single without grouping)
                fig = self.session.generate_multi_line_chart(
                    x_col, self.y_columns, aggregation, show=False
                )
            
            # Save to temporary file
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            self.current_chart_path = temp_file.name
            temp_file.close()
            
            self.session.export_chart(self.current_chart_path)
            
            # Display in popup
            from PIL import Image, ImageTk
            
            # Clear previous chart
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            
            # Load and display image
            img = Image.open(self.current_chart_path)
            img = img.resize((680, 380), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            img_label = ttk.Label(self.chart_frame, image=photo)
            img_label.image = photo  # Keep reference
            img_label.pack(expand=True)
            
            # Enable export button
            self.export_btn.config(state=tk.NORMAL)
            
            y_names = ", ".join(self.y_columns)
            group_info = " grouped by " + group_by if group_by else ""
            self.logger.info("Generated chart: " + y_names + " by " + x_col + 
                           group_info + " (aggregation: " + aggregation + ")")
            
            # Close the matplotlib figure to free memory
            import matplotlib.pyplot as plt
            plt.close(fig)
            
        except ImportError:
            # PIL not available, show message instead
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            
            ttk.Label(
                self.chart_frame,
                text="Chart generated! Use 'Export Image' to save.\n(Install Pillow to preview here)"
            ).pack(expand=True)
            
            self.export_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _on_export(self):
        """Handle Export Image button click."""
        if self.current_chart_path is None:
            messagebox.showwarning("No Chart", "Please generate a chart first.")
            return
        
        # Generate default filename
        x_col = self.x_var.get()
        agg = self.agg_var.get()
        if len(self.y_columns) == 1:
            y_name = self.y_columns[0]
        else:
            y_name = "multi_" + str(len(self.y_columns)) + "_lines"
        default_name = y_name + "_" + agg + "_by_" + x_col + ".png"
        
        # Open save dialog
        filepath = filedialog.asksaveasfilename(
            title="Export Chart",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            # Copy temp file to chosen location
            import shutil
            shutil.copy(self.current_chart_path, filepath)
            
            self.logger.info("Exported chart to: " + filepath)
            messagebox.showinfo("Export Successful", "Chart exported to:\n" + filepath)
            
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


# =============================================================================
# CRUD DIALOGS - Add and Edit Records
# =============================================================================

class AddRecordDialog:
    """Dialog for adding a new record to a dataset."""
    
    def __init__(self, parent, data_store, import_id, columns, callback):
        """
        Initialize the add record dialog.
        
        Args:
            parent: Parent window
            data_store: DataStore instance
            import_id: ID of the import to add record to
            columns: List of column names
            callback: Function to call after successful add
        """
        self.data_store = data_store
        self.import_id = import_id
        self.columns = columns
        self.callback = callback
        self.entries = {}
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Record")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry("+{}+{}".format(x, y))
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        # Scrollable frame for fields
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create entry field for each column
        for i, col in enumerate(self.columns):
            ttk.Label(scrollable_frame, text=col + ":").grid(
                row=i, column=0, sticky="e", padx=5, pady=3
            )
            entry = ttk.Entry(scrollable_frame, width=40)
            entry.grid(row=i, column=1, sticky="ew", padx=5, pady=3)
            self.entries[col] = entry
        
        scrollable_frame.columnconfigure(1, weight=1)
        
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(btn_frame, text="Add Record", command=self._on_add).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT)
    
    def _on_add(self):
        """Handle Add button click."""
        # Collect data from entries
        data = {}
        for col, entry in self.entries.items():
            value = entry.get().strip()
            data[col] = value if value else None
        
        try:
            record_id = self.data_store.add_record(self.import_id, data)
            self.dialog.destroy()
            self.callback()
            messagebox.showinfo("Success", "Record added successfully (ID: " + str(record_id) + ")")
        except Exception as e:
            messagebox.showerror("Error", "Failed to add record: " + str(e))


class EditRecordDialog:
    """Dialog for editing an existing record."""
    
    def __init__(self, parent, data_store, record_id, record_data, callback):
        """
        Initialize the edit record dialog.
        
        Args:
            parent: Parent window
            data_store: DataStore instance
            record_id: ID of the record to edit
            record_data: Current record data as dictionary
            callback: Function to call after successful edit
        """
        self.data_store = data_store
        self.record_id = record_id
        self.record_data = record_data
        self.callback = callback
        self.entries = {}
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Record (ID: " + str(record_id) + ")")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry("+{}+{}".format(x, y))
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        # Scrollable frame for fields
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create entry field for each column with current values
        for i, (col, value) in enumerate(self.record_data.items()):
            ttk.Label(scrollable_frame, text=col + ":").grid(
                row=i, column=0, sticky="e", padx=5, pady=3
            )
            entry = ttk.Entry(scrollable_frame, width=40)
            entry.grid(row=i, column=1, sticky="ew", padx=5, pady=3)
            # Pre-fill with current value
            if value is not None:
                entry.insert(0, str(value))
            self.entries[col] = entry
        
        scrollable_frame.columnconfigure(1, weight=1)
        
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(btn_frame, text="Save Changes", command=self._on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT)
    
    def _on_save(self):
        """Handle Save button click."""
        # Collect updated data from entries
        updated_data = {}
        for col, entry in self.entries.items():
            value = entry.get().strip()
            updated_data[col] = value if value else None
        
        try:
            success = self.data_store.update_record(self.record_id, updated_data)
            if success:
                self.dialog.destroy()
                self.callback()
                messagebox.showinfo("Success", "Record updated successfully.")
            else:
                messagebox.showerror("Error", "Record not found.")
        except Exception as e:
            messagebox.showerror("Error", "Failed to update record: " + str(e))


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

def run_application():
    """Initialize and run the application."""
    # Set up logging
    logger = get_logger()
    logger.info("=" * 50)
    logger.info("Application starting")
    
    # Create root window
    root = tk.Tk()
    
    # Create main application
    app = MainWindow(root)
    
    # Handle window close
    def on_closing():
        logger.info("Application shutting down")
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start main loop
    root.mainloop()


if __name__ == "__main__":
    run_application()