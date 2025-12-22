"""Chart generation using matplotlib. Supports line, bar, and grouped visualizations."""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# Import from parent package config
try:
    from ..config import CHART_FIGURE_SIZE, CHART_EXPORT_DPI, AGGREGATION_METHODS
except ImportError:
    # Fallback for direct module execution
    CHART_FIGURE_SIZE = (10, 6)
    CHART_EXPORT_DPI = 150
    AGGREGATION_METHODS = ["sum", "mean", "count"]

from .utils import detect_column_type


def generate_chart(data, x_column, y_column, group_by=None, aggregation="sum", show=True):
    """Generate chart. Args: data, x_column, y_column (numeric), group_by, aggregation, show."""
    if len(data) == 0:
        raise ValueError("No data available to graph. Adjust filters or clean operations.")
    
    if x_column not in data.columns:
        raise ValueError("X column not found: " + x_column)
    
    if y_column not in data.columns:
        raise ValueError("Y column not found: " + y_column)
    
    y_type = detect_column_type(data[y_column])
    if y_type != "numeric":
        raise ValueError("Y column must be numeric. '" + y_column + "' is " + y_type)
    
    if group_by is not None and group_by not in data.columns:
        raise ValueError("Group by column not found: " + group_by)
    
    if aggregation not in AGGREGATION_METHODS:
        raise ValueError("Aggregation must be one of: " + ", ".join(AGGREGATION_METHODS))
    
    chart_data = data.copy()
    chart_data = chart_data.dropna(subset=[x_column, y_column])
    
    if len(chart_data) == 0:
        raise ValueError("No valid data points after removing missing values")
    
    chart_data[y_column] = pd.to_numeric(chart_data[y_column], errors='coerce')
    
    x_type = detect_column_type(chart_data[x_column])
    use_line_chart = x_type in ["date", "numeric"]
    
    if x_type == "date":
        chart_data[x_column] = pd.to_datetime(chart_data[x_column], errors='coerce')
    elif x_type == "numeric":
        chart_data[x_column] = pd.to_numeric(chart_data[x_column], errors='coerce')
    
    agg_data = _aggregate_data(chart_data, x_column, y_column, group_by, aggregation)
    agg_data = agg_data.sort_values(by=x_column)
    
    fig, ax = plt.subplots(figsize=CHART_FIGURE_SIZE)
    
    if group_by is not None:
        _plot_grouped(ax, agg_data, x_column, y_column, group_by, use_line_chart)
    else:
        _plot_single(ax, agg_data, x_column, y_column, use_line_chart)
    
    _set_labels(ax, x_column, y_column, group_by, aggregation, use_line_chart)
    
    plt.tight_layout()
    
    if show:
        plt.show()
    
    return fig


def generate_multi_line_chart(data, x_column, y_columns, aggregation="sum", show=True):
    """Generate multi-line chart with multiple Y columns on same X axis."""
    if len(data) == 0:
        raise ValueError("No data available to graph. Adjust filters or clean operations.")
    
    if x_column not in data.columns:
        raise ValueError("X column not found: " + x_column)
    
    if not y_columns or len(y_columns) == 0:
        raise ValueError("At least one Y column is required")
    
    # Validate Y columns are numeric
    for y_col in y_columns:
        if y_col not in data.columns:
            raise ValueError("Y column not found: " + y_col)
        y_type = detect_column_type(data[y_col])
        if y_type != "numeric":
            raise ValueError("Y column must be numeric. '" + y_col + "' is " + y_type)
    
    if aggregation not in AGGREGATION_METHODS:
        raise ValueError("Aggregation must be one of: " + ", ".join(AGGREGATION_METHODS))
    
    chart_data = data.copy()
    x_type = detect_column_type(chart_data[x_column])
    use_line_chart = x_type in ["date", "numeric"]
    
    if x_type == "date":
        chart_data[x_column] = pd.to_datetime(chart_data[x_column], errors='coerce')
    elif x_type == "numeric":
        chart_data[x_column] = pd.to_numeric(chart_data[x_column], errors='coerce')
    
    # Convert Y columns to numeric
    for y_col in y_columns:
        chart_data[y_col] = pd.to_numeric(chart_data[y_col], errors='coerce')
    
    fig, ax = plt.subplots(figsize=CHART_FIGURE_SIZE)
    
    # Color palette for multiple lines
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Plot each Y column as separate line
    for i, y_col in enumerate(y_columns):
        y_data = chart_data[[x_column, y_col]].dropna()
        
        if len(y_data) == 0:
            continue
        # Aggregate data
        if aggregation == "sum":
            agg_data = y_data.groupby(x_column)[y_col].sum().reset_index()
        elif aggregation == "mean":
            agg_data = y_data.groupby(x_column)[y_col].mean().reset_index()
        else:  # count
            agg_data = y_data.groupby(x_column)[y_col].count().reset_index()
        
        agg_data = agg_data.sort_values(by=x_column)
        
        color = colors[i % len(colors)]
        
        if use_line_chart:
            ax.plot(agg_data[x_column], agg_data[y_col], 
                   marker='o', color=color, label=y_col, linewidth=2, markersize=4)
        else:
            # For bar charts with multiple series, we need to offset bars
            x_positions = range(len(agg_data))
            bar_width = 0.8 / len(y_columns)
            offset = (i - len(y_columns)/2 + 0.5) * bar_width
            ax.bar([p + offset for p in x_positions], agg_data[y_col], 
                  width=bar_width, color=color, label=y_col)
            if i == 0:
                ax.set_xticks(x_positions)
                ax.set_xticklabels(agg_data[x_column].astype(str), rotation=45, ha='right')
    # Set labels
    ax.set_xlabel(x_column)
    if len(y_columns) == 1:
        ax.set_ylabel(y_columns[0] + " (" + aggregation + ")")
    else:
        ax.set_ylabel("Value (" + aggregation + ")")
    # Set title
    if len(y_columns) <= 3:
        y_names = ", ".join(y_columns)
    else:
        y_names = ", ".join(y_columns[:2]) + " + " + str(len(y_columns) - 2) + " more"
    ax.set_title(y_names + " by " + x_column)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if show:
        plt.show()
    
    return fig


def _aggregate_data(chart_data, x_column, y_column, group_by, aggregation):
    """Aggregate data by x_column (and group_by if provided)."""
    if group_by is not None:
        if aggregation == "sum":
            agg_data = chart_data.groupby([x_column, group_by])[y_column].sum().reset_index()
        elif aggregation == "mean":
            agg_data = chart_data.groupby([x_column, group_by])[y_column].mean().reset_index()
        else:
            agg_data = chart_data.groupby([x_column, group_by])[y_column].count().reset_index()
    else:
        if aggregation == "sum":
            agg_data = chart_data.groupby(x_column)[y_column].sum().reset_index()
        elif aggregation == "mean":
            agg_data = chart_data.groupby(x_column)[y_column].mean().reset_index()
        else:
            agg_data = chart_data.groupby(x_column)[y_column].count().reset_index()
    
    return agg_data


def _plot_grouped(ax, agg_data, x_column, y_column, group_by, use_line_chart):
    """Plot data with multiple series grouped by column."""
    groups = agg_data[group_by].unique()
    
    for group_value in groups:
        group_data = agg_data[agg_data[group_by] == group_value]
        
        if use_line_chart:
            ax.plot(group_data[x_column], group_data[y_column], 
                   marker='o', label=str(group_value))
    
    if not use_line_chart:
        pivot_data = agg_data.pivot(index=x_column, columns=group_by, values=y_column)
        pivot_data.plot(kind='bar', ax=ax)


def _plot_single(ax, agg_data, x_column, y_column, use_line_chart):
    """Plot single series data as line or bar chart."""
    if use_line_chart:
        ax.plot(agg_data[x_column], agg_data[y_column], marker='o', color='steelblue', label=y_column)
    else:
        ax.bar(agg_data[x_column].astype(str), agg_data[y_column], color='steelblue', label=y_column)


def _set_labels(ax, x_column, y_column, group_by, aggregation, use_line_chart):
    """Set axis labels, title, and legend."""
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column + " (" + aggregation + ")")
    
    if group_by is not None:
        title = y_column + " by " + x_column + " (grouped by " + group_by + ")"
    else:
        title = y_column + " by " + x_column
    ax.set_title(title)
    
    if group_by is not None:
        ax.legend(title=group_by)
    else:
        ax.legend()
    
    if not use_line_chart:
        plt.xticks(rotation=45, ha='right')


def export_chart(figure, filepath):
    """Export chart figure to file. Raises ValueError if figure is None."""
    if figure is None:
        raise ValueError("No chart has been generated. Call generate_chart() first.")
    
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    figure.savefig(filepath, dpi=CHART_EXPORT_DPI, bbox_inches='tight')
    
    return True
