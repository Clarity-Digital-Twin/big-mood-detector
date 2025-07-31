"""Test enhanced XML counting functionality."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from big_mood_detector.infrastructure.parsers.xml.fast_streaming_parser import (
    FastStreamingXMLParser,
)


class TestEnhancedXMLCounting:
    """Test enhanced record counting functionality."""

    def test_count_records_by_type_basic_mode(self):
        """Test that basic mode returns same as count_records_by_date."""
        parser = FastStreamingXMLParser()
        
        # Mock the existing count_records_by_date method
        with patch.object(parser, 'count_records_by_date') as mock_count:
            mock_count.return_value = {
                "sleep": 100,
                "activity": 200,
                "heart": 50,
                "total": 350
            }
            
            # Call with detailed=False (default)
            result = parser.count_records_by_type(Path("test.xml"), detailed=False)
            
            assert result == {
                "sleep": 100,
                "activity": 200,
                "heart": 50,
                "total": 350
            }
            mock_count.assert_called_once_with(Path("test.xml"))

    def test_count_records_by_type_detailed_mode(self):
        """Test that detailed mode returns all record types."""
        parser = FastStreamingXMLParser()
        
        # Mock iter_records to return test data
        test_records = [
            {"type": "HKQuantityTypeIdentifierStepCount"},
            {"type": "HKQuantityTypeIdentifierStepCount"},
            {"type": "HKCategoryTypeIdentifierSleepAnalysis"},
            {"type": "HKQuantityTypeIdentifierHeartRate"},
            {"type": "HKQuantityTypeIdentifierHeartRate"},
            {"type": "HKQuantityTypeIdentifierHeartRate"},
            {"type": "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"},
            {"type": "Unknown"},  # Test handling of missing type
        ]
        
        with patch.object(parser, 'iter_records') as mock_iter:
            mock_iter.return_value = iter(test_records)
            
            result = parser.count_records_by_type(Path("test.xml"), detailed=True)
            
            assert result == {
                "HKQuantityTypeIdentifierStepCount": 2,
                "HKCategoryTypeIdentifierSleepAnalysis": 1,
                "HKQuantityTypeIdentifierHeartRate": 3,
                "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": 1,
                "Unknown": 1,
            }
            mock_iter.assert_called_once_with(Path("test.xml"))

    def test_count_records_by_type_empty_file(self):
        """Test handling of empty file."""
        parser = FastStreamingXMLParser()
        
        with patch.object(parser, 'iter_records') as mock_iter:
            mock_iter.return_value = iter([])  # Empty iterator
            
            result = parser.count_records_by_type(Path("empty.xml"), detailed=True)
            
            assert result == {}

    def test_count_records_by_type_performance(self):
        """Test that counting is efficient for large files."""
        parser = FastStreamingXMLParser()
        
        # Simulate a large file with many records
        def generate_records():
            for i in range(100000):  # 100k records
                yield {
                    "type": f"HKQuantityTypeIdentifier{i % 10}",
                    "startDate": "2024-01-01T00:00:00Z"
                }
        
        with patch.object(parser, 'iter_records') as mock_iter:
            mock_iter.return_value = generate_records()
            
            import time
            start = time.time()
            result = parser.count_records_by_type(Path("large.xml"), detailed=True)
            duration = time.time() - start
            
            # Should complete quickly even for 100k records
            assert duration < 1.0  # Less than 1 second
            
            # Should have 10 different record types
            assert len(result) == 10
            
            # Each type should have 10k records
            for count in result.values():
                assert count == 10000

    def test_scan_time_for_large_file(self):
        """Test that scanning completes within time limit."""
        parser = FastStreamingXMLParser()
        
        # Mock a 500MB file scan
        def generate_large_file_records():
            # Simulate 5 million records (typical for 500MB)
            for i in range(5_000_000):
                yield {
                    "type": "HKQuantityTypeIdentifierStepCount" if i % 2 
                           else "HKCategoryTypeIdentifierSleepAnalysis"
                }
        
        with patch.object(parser, 'iter_records') as mock_iter:
            mock_iter.return_value = generate_large_file_records()
            
            import time
            start = time.time()
            result = parser.count_records_by_type(Path("500mb.xml"), detailed=True)
            duration = time.time() - start
            
            # Should complete within 5 seconds for 500MB file
            assert duration < 5.0
            
            assert result["HKQuantityTypeIdentifierStepCount"] == 2_500_000
            assert result["HKCategoryTypeIdentifierSleepAnalysis"] == 2_500_000