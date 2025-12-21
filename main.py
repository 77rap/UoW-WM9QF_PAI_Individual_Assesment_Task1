"""
Public Health Data Insights Dashboard - Main Entry Point
==========================================================

This is the main entry point for running the application.
Run this file to start the dashboard.

Usage:
    python main.py
    
Author: [Your Name]
Date: [Date]
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the application
from src.presentation import run_application


if __name__ == "__main__":
    print("=" * 60)
    print("  Public Health Data Insights Dashboard")
    print("=" * 60)
    print()
    print("Starting application...")
    print()
    
    try:
        run_application()
    except KeyboardInterrupt:
        print("\nApplication closed by user.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
