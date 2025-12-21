"""
Public Health Data Insights Dashboard - Source Package
=======================================================

This package contains all source code for the dashboard application.

Subpackages:
- data: Data ingestion, storage, and retrieval
- analysis: Data analysis, filtering, and visualization
- config: Centralized configuration

Modules:
- presentation: GUI/CLI interface
"""

from . import config
from . import data
from . import analysis
