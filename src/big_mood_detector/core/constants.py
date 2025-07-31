"""
Core constants for the Big Mood Detector application.

This module contains important constants used throughout the application.
"""

# Timeout thresholds (in MB and seconds)
SMALL_FILE_THRESHOLD_MB = 50  # Files under 50MB use standard timeout
LARGE_FILE_THRESHOLD_MB = 200  # Files over 200MB have no timeout

SMALL_FILE_TIMEOUT_SECONDS = 120  # 2 minutes for small files
MEDIUM_FILE_TIMEOUT_SECONDS = 300  # 5 minutes for medium files
NO_TIMEOUT = 0  # No timeout for large files