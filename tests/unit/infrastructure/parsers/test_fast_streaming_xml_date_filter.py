"""Test date filtering in fast streaming XML parser."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from big_mood_detector.infrastructure.parsers.xml.fast_streaming_parser import (
    FastStreamingXMLParser,
)


@pytest.fixture
def sample_xml_with_dates() -> str:
    """Create sample XML with various dates."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Record type="HKCategoryTypeIdentifierSleepAnalysis"
            startDate="2025-01-01 23:00:00 -0700"
            endDate="2025-01-02 07:00:00 -0700"
            value="HKCategoryValueSleepAnalysisInBed"/>
    <Record type="HKCategoryTypeIdentifierSleepAnalysis"
            startDate="2025-05-15 22:30:00 -0700"
            endDate="2025-05-16 06:30:00 -0700"
            value="HKCategoryValueSleepAnalysisAsleep"/>
    <Record type="HKCategoryTypeIdentifierSleepAnalysis"
            startDate="2025-06-01 23:15:00 -0700"
            endDate="2025-06-02 07:45:00 -0700"
            value="HKCategoryValueSleepAnalysisInBed"/>
    <Record type="HKQuantityTypeIdentifierStepCount"
            startDate="2025-05-20 10:00:00 -0700"
            endDate="2025-05-20 10:05:00 -0700"
            value="250"/>
</HealthData>"""


class TestFastStreamingXMLDateFilter:
    """Test date filtering functionality in fast parser."""

    def test_date_filter_raw_iter_records(self, sample_xml_with_dates: str):
        """Test that raw iter_records date filtering works correctly."""
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(sample_xml_with_dates)
            temp_path = Path(f.name)

        try:
            parser = FastStreamingXMLParser()

            # Test with datetime objects (what parse_file passes internally)
            records = list(
                parser.iter_records(
                    temp_path,
                    record_types=None,
                    start_date=datetime(2025, 5, 1),
                    end_date=datetime(2025, 5, 31),
                )
            )

            # Should include May records only
            assert len(records) == 2
            
            # Check dates
            dates = [r["startDate"] for r in records]
            assert any("2025-05-15" in d for d in dates)
            assert any("2025-05-20" in d for d in dates)

        finally:
            temp_path.unlink()

    def test_date_filter_no_type_error(self, sample_xml_with_dates: str):
        """Test that date/datetime comparison doesn't raise TypeError."""
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(sample_xml_with_dates)
            temp_path = Path(f.name)

        try:
            parser = FastStreamingXMLParser()

            # This should not raise TypeError when comparing date vs datetime
            # The fix converts datetime.date() for comparison
            try:
                records = list(
                    parser.iter_records(
                        temp_path,
                        start_date=datetime(2025, 5, 1),
                        end_date=datetime(2025, 5, 31),
                    )
                )
                # If we get here, the date comparison worked
                assert True
            except TypeError as e:
                if "can't compare" in str(e):
                    pytest.fail(f"Date comparison failed: {e}")
                else:
                    raise

        finally:
            temp_path.unlink()

    def test_date_filter_with_datetime_comparison_bug(self, sample_xml_with_dates: str):
        """Test that date/datetime comparison works correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(sample_xml_with_dates)
            temp_path = Path(f.name)

        try:
            parser = FastStreamingXMLParser()

            # This should not raise TypeError for date/datetime comparison
            records = list(
                parser.parse_file(
                    temp_path,
                    entity_type="sleep",
                    start_date="2025-05-01",
                    end_date="2025-05-31"
                )
            )

            # Should have 1 sleep record in May
            assert len(records) == 1
            assert records[0].start_date.month == 5

        finally:
            temp_path.unlink()

    def test_date_filter_edge_case_inclusive(self, sample_xml_with_dates: str):
        """Test that date filtering is inclusive of the boundary dates."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(sample_xml_with_dates)
            temp_path = Path(f.name)

        try:
            parser = FastStreamingXMLParser()

            # Test exact date match
            records = list(
                parser.parse_file(
                    temp_path,
                    entity_type="all", 
                    start_date="2025-05-15",
                    end_date="2025-05-15"
                )
            )

            # Should include the sleep record that starts on May 15
            assert len(records) == 1

        finally:
            temp_path.unlink()