"""Tests for dynamic timeout calculation based on file size."""

import pytest
from big_mood_detector.interfaces.cli.commands import calculate_timeout


class TestTimeoutCalculation:
    def test_small_files_get_standard_timeout(self):
        """Files under 50MB should have 2 minute timeout."""
        assert calculate_timeout(10) == 120
        assert calculate_timeout(49) == 120
        assert calculate_timeout(0.5) == 120
    
    def test_medium_files_get_extended_timeout(self):
        """Files 50-200MB should have 5 minute timeout."""
        assert calculate_timeout(50) == 300
        assert calculate_timeout(100) == 300
        assert calculate_timeout(199) == 300
    
    def test_large_files_get_no_timeout(self):
        """Files over 200MB should have no timeout (0 = infinite)."""
        assert calculate_timeout(200) == 0
        assert calculate_timeout(500) == 0
        assert calculate_timeout(1000) == 0
    
    def test_edge_cases(self):
        """Test edge cases at boundaries."""
        assert calculate_timeout(49.9) == 120
        assert calculate_timeout(50.0) == 300
        assert calculate_timeout(199.9) == 300
        assert calculate_timeout(200.0) == 0