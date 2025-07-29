"""Simple test for fast streaming XML parser date filtering."""

import tempfile
from datetime import datetime
from pathlib import Path

from big_mood_detector.infrastructure.parsers.xml.fast_streaming_parser import (
    FastStreamingXMLParser,
)


def test_fast_parser_date_comparison_fix():
    """Test that date/datetime comparison doesn't raise TypeError."""
    # Create minimal XML
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Record type="HKCategoryTypeIdentifierSleepAnalysis"
            startDate="2025-05-15 22:30:00 -0700"
            endDate="2025-05-16 06:30:00 -0700"
            value="HKCategoryValueSleepAnalysisAsleep"/>
</HealthData>"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(xml_content)
        temp_path = Path(f.name)
    
    try:
        parser = FastStreamingXMLParser()
        
        # First, test raw iter_records to see the date filtering logic
        records = list(parser.iter_records(
            temp_path,
            record_types=None,
            start_date=datetime(2025, 5, 1),  # Pass datetime objects
            end_date=datetime(2025, 5, 31)
        ))
        
        print(f"Raw records found: {len(records)}")
        for r in records:
            print(f"Record: {r}")
        
        # This should not raise TypeError
        assert len(records) >= 0  # Just check it doesn't crash
        
    finally:
        temp_path.unlink()


if __name__ == "__main__":
    test_fast_parser_date_comparison_fix()