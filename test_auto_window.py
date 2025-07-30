#!/usr/bin/env python3
"""Test script for auto-window functionality."""

import subprocess
import sys
from pathlib import Path

def test_auto_window():
    """Test the auto-window CLI functionality."""
    
    # Find a test XML file
    test_file = Path("tests/fixtures/apple_health_export_sample.xml")
    if not test_file.exists():
        # Try another common location
        test_file = Path("data/input/apple_export/export.xml")
        if not test_file.exists():
            print("No test XML file found. Please provide a path to an Apple Health export.")
            return
    
    print(f"Testing auto-window with: {test_file}")
    print("=" * 60)
    
    # Run the predict command with auto-window (default on)
    cmd = [
        sys.executable,
        "src/big_mood_detector/main.py",
        "predict",
        str(test_file),
        "--verbose",
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
    # Test with --no-auto-window
    print("\n" + "=" * 60)
    print("Testing with --no-auto-window flag")
    print("=" * 60)
    
    cmd.append("--no-auto-window")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)

if __name__ == "__main__":
    test_auto_window()