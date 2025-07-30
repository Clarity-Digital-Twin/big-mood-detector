"""Regression test for PAT-only mode.

This test ensures that the system can correctly handle scenarios where:
1. We have exactly 7 consecutive days of data (PAT requirement)
2. But we don't have enough data for XGBoost (30+ days with 50% coverage)
"""

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.domain.entities.activity_record import ActivityRecord
from big_mood_detector.domain.entities.heart_rate_record import HeartRateRecord
from big_mood_detector.domain.entities.sleep_record import SleepRecord
from big_mood_detector.infrastructure.parsers.xml.activity_parser import ActivityParser
from big_mood_detector.infrastructure.parsers.xml.heart_rate_parser import (
    HeartRateParser,
)
from big_mood_detector.infrastructure.parsers.xml.sleep_parser import SleepParser


@pytest.mark.regression
class TestPATOnlyMode:
    """Test PAT-only mode scenarios."""
    
    def setup_method(self):
        """Set up test data with exactly 7 consecutive days."""
        # Create base date
        self.base_date = date(2025, 1, 15)
        
        # Create 7 consecutive days of data
        self.activity_records = []
        self.sleep_records = []
        self.heart_rate_records = []
        
        for day_offset in range(7):
            current_date = self.base_date + timedelta(days=day_offset)
            
            # Create 24 hours of activity data (minute-level)
            for hour in range(24):
                for minute in range(60):
                    timestamp = datetime.combine(
                        current_date, 
                        datetime.min.time()
                    ).replace(hour=hour, minute=minute)
                    
                    self.activity_records.append(
                        ActivityRecord(
                            timestamp=timestamp,
                            active_calories=0.5,
                            step_count=10 if 8 <= hour <= 20 else 0,
                            basal_calories=1.2
                        )
                    )
            
            # Add sleep record (8 hours)
            sleep_start = datetime.combine(
                current_date - timedelta(days=1), 
                datetime.min.time()
            ).replace(hour=22)
            sleep_end = datetime.combine(
                current_date, 
                datetime.min.time()
            ).replace(hour=6)
            
            self.sleep_records.append(
                SleepRecord(
                    start_date=sleep_start,
                    end_date=sleep_end,
                    is_in_bed=True,
                    sleep_phase="ASLEEP"
                )
            )
            
            # Add heart rate data
            for hour in range(24):
                timestamp = datetime.combine(
                    current_date, 
                    datetime.min.time()
                ).replace(hour=hour)
                
                self.heart_rate_records.append(
                    HeartRateRecord(
                        timestamp=timestamp,
                        heart_rate=60 if hour < 6 or hour > 22 else 75
                    )
                )
    
    @pytest.mark.slow
    def test_pat_only_mode_with_7_consecutive_days(self, tmp_path):
        """Test that PAT runs when we have exactly 7 consecutive days."""
        # Create mock XML file
        xml_file = tmp_path / "test_export.xml"
        xml_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData>
<HealthData locale="en_US">
  <ExportDate value="2025-01-31 09:08:45 -0800"/>
</HealthData>""")
        
        # Mock the parsers to return our test data
        with patch.object(ActivityParser, 'parse', return_value=self.activity_records):
            with patch.object(SleepParser, 'parse', return_value=self.sleep_records):
                with patch.object(HeartRateParser, 'parse', return_value=self.heart_rate_records):
                    # Create use case with PAT enabled
                    config = PipelineConfig(
                        use_seoul_features=True,
                        enable_pat_model=True,
                        enable_clinical_validation=True
                    )
                    
                    pipeline = MoodPredictionPipeline(config=config)
                    
                    # Process the data
                    result = pipeline.run(
                        file_path=xml_file,
                        start_date=self.base_date,
                        end_date=self.base_date + timedelta(days=6)
                    )
                    
                    # Verify PAT-only mode was used
                    assert result.metadata is not None
                    assert result.metadata.get("window_analysis") is not None
                    
                    window_analysis = result.metadata["window_analysis"]
                    assert window_analysis["can_run_pat"] is True
                    assert window_analysis["can_run_xgboost"] is False
                    assert window_analysis["max_consecutive_days"] == 7
                    assert window_analysis["coverage_percentage"] < 50  # Not enough for XGBoost
                    
                    # Verify we have daily predictions from PAT
                    assert len(result.daily_predictions) > 0
                    
                    # Check that predictions are from PAT
                    for date_key, prediction in result.daily_predictions.items():
                        assert "model" in prediction
                        assert prediction["model"] == "pat"
                        assert "current_depression_probability" in prediction
                        assert 0 <= prediction["current_depression_probability"] <= 1
    
    @pytest.mark.slow
    def test_pat_fails_with_broken_consecutive_days(self, tmp_path):
        """Test that PAT doesn't run when consecutive days are broken."""
        # Remove one day from the middle to break consecutive requirement
        filtered_activity = [
            r for r in self.activity_records 
            if r.timestamp.date() != self.base_date + timedelta(days=3)
        ]
        
        # Create mock XML file
        xml_file = tmp_path / "test_export.xml"
        xml_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData>
<HealthData locale="en_US">
  <ExportDate value="2025-01-31 09:08:45 -0800"/>
</HealthData>""")
        
        # Mock the parsers
        with patch.object(ActivityParser, 'parse', return_value=filtered_activity):
            with patch.object(SleepParser, 'parse', return_value=self.sleep_records):
                with patch.object(HeartRateParser, 'parse', return_value=self.heart_rate_records):
                    # Create use case
                    config = PipelineConfig(
                        use_seoul_features=True,
                        enable_pat_model=True,
                        enable_clinical_validation=True
                    )
                    
                    pipeline = MoodPredictionPipeline(config=config)
                    
                    # Process the data
                    result = pipeline.run(
                        file_path=xml_file,
                        start_date=self.base_date,
                        end_date=self.base_date + timedelta(days=6)
                    )
                    
                    # Verify PAT couldn't run
                    assert result.metadata is not None
                    window_analysis = result.metadata.get("window_analysis")
                    
                    if window_analysis:
                        assert window_analysis["can_run_pat"] is False
                        assert window_analysis["max_consecutive_days"] < 7
                    
                    # Should have no predictions since neither model can run
                    assert len(result.daily_predictions) == 0
                    assert len(result.window_predictions) == 0
    
    @pytest.mark.slow
    def test_pat_only_mode_messaging(self, tmp_path):
        """Test that appropriate messages are shown in PAT-only mode."""
        # Create mock XML file
        xml_file = tmp_path / "test_export.xml"
        xml_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData>
<HealthData locale="en_US">
  <ExportDate value="2025-01-31 09:08:45 -0800"/>
</HealthData>""")
        
        # Mock the parsers
        with patch.object(ActivityParser, 'parse', return_value=self.activity_records):
            with patch.object(SleepParser, 'parse', return_value=self.sleep_records):
                with patch.object(HeartRateParser, 'parse', return_value=self.heart_rate_records):
                    # Create use case
                    config = PipelineConfig(
                        use_seoul_features=True,
                        enable_pat_model=True,
                        enable_clinical_validation=True
                    )
                    
                    pipeline = MoodPredictionPipeline(config=config)
                    
                    # Process the data
                    result = pipeline.run(
                        file_path=xml_file,
                        start_date=self.base_date,
                        end_date=self.base_date + timedelta(days=6)
                    )
                    
                    # Check for appropriate warnings
                    assert any("PAT" in warning for warning in result.warnings)
                    
                    # Verify overall summary indicates PAT mode
                    assert result.overall_summary.get("primary_model") == "pat"
                    assert result.overall_summary.get("analysis_type") == "daily"