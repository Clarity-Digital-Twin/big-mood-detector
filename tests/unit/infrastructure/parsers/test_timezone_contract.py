"""Tests for timezone consistency throughout the application."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from big_mood_detector.infrastructure.parsers.xml.streaming_adapter import StreamingXMLParser
from big_mood_detector.domain.contracts.timezone_contract import TimezoneContract


class TestTimezoneContract:
    def test_parser_always_outputs_naive_datetimes(self):
        """XML parser must convert all datetimes to naive (UTC)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData [
<!-- HealthKit Export Version: 12.0 -->
<!ELEMENT Record EMPTY>
<!ATTLIST Record
  type         CDATA #REQUIRED
  sourceName   CDATA #REQUIRED
  sourceVersion CDATA #IMPLIED
  device       CDATA #IMPLIED
  unit         CDATA #IMPLIED
  creationDate CDATA #IMPLIED
  startDate    CDATA #REQUIRED
  endDate      CDATA #IMPLIED
  value        CDATA #IMPLIED>
]>
<HealthData locale="en_US">
  <ExportDate value="2025-01-31 09:08:45 -0800"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" 
          sourceName="JJ's Apple Watch" 
          sourceVersion="11.2" 
          startDate="2025-01-27 22:30:00 +0000"
          endDate="2025-01-28 06:30:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleepCore"/>
</HealthData>"""
        
        # Write to temporary file since parser expects file path
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = f.name
        
        try:
            parser = StreamingXMLParser()
            # parse_file returns a generator of records
            records = list(parser.parse_file(temp_path, entity_type="sleep"))
            
            assert len(records) > 0
            sleep_record = records[0]
            assert sleep_record.start_date.tzinfo is None
            assert sleep_record.end_date.tzinfo is None
            # Should be converted to UTC time but as naive
            assert sleep_record.start_date == datetime(2025, 1, 27, 22, 30)
            assert sleep_record.end_date == datetime(2025, 1, 28, 6, 30)
        finally:
            Path(temp_path).unlink()
    
    def test_contract_converts_aware_to_naive(self):
        """Contract should convert aware datetimes to naive."""
        aware_dt = datetime(2025, 1, 27, 22, 30, tzinfo=timezone.utc)
        naive_dt = TimezoneContract.ensure_naive(aware_dt)
        
        assert naive_dt.tzinfo is None
        assert naive_dt == datetime(2025, 1, 27, 22, 30)
    
    def test_contract_preserves_naive(self):
        """Contract should leave naive datetimes unchanged."""
        naive_dt = datetime(2025, 1, 27, 22, 30)
        result = TimezoneContract.ensure_naive(naive_dt)
        
        assert result == naive_dt
        assert result.tzinfo is None
    
    def test_contract_validates_domain_datetime(self):
        """Contract should validate that datetimes meet domain requirements."""
        # Naive datetime should pass
        naive_dt = datetime(2025, 1, 27, 22, 30)
        TimezoneContract.validate_domain_datetime(naive_dt)  # Should not raise
        
        # Aware datetime should fail
        aware_dt = datetime(2025, 1, 27, 22, 30, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Domain layer requires timezone-naive datetimes"):
            TimezoneContract.validate_domain_datetime(aware_dt)