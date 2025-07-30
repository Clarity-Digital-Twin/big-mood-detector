"""Integration tests for timezone handling throughout the pipeline."""

import pytest
from datetime import datetime, timezone, date
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)


class TestTimezoneRobustness:
    def test_pipeline_handles_mixed_timezone_data(self):
        """Pipeline should handle both aware and naive inputs gracefully."""
        # Create records with mixed timezones
        records = [
            SleepRecord(
                source_name="Test",
                start_date=datetime(2025, 1, 27, 22, 0, tzinfo=timezone.utc),
                end_date=datetime(2025, 1, 28, 6, 0, tzinfo=timezone.utc),
                state=SleepState.ASLEEP
            ),
            SleepRecord(
                source_name="Test",
                start_date=datetime(2025, 1, 28, 22, 0),  # Naive
                end_date=datetime(2025, 1, 29, 6, 0),      # Naive
                state=SleepState.ASLEEP
            )
        ]
        
        pipeline = MoodPredictionPipeline(
            config=PipelineConfig(use_seoul_features=True)
        )
        
        # This should not raise TypeError about mixing timezone-aware and naive
        result = pipeline.process_health_data(
            sleep_records=records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 1, 29)
        )
        
        assert result.has_errors is False
        assert result.overall_summary is not None
    
    def test_feature_extraction_with_aware_datetimes(self):
        """Feature extraction should handle timezone-aware inputs correctly."""
        # Create timezone-aware sleep records
        records = []
        for day in range(30):
            start_dt = datetime(2025, 1, 1 + day, 22, 0, tzinfo=timezone.utc)
            end_dt = datetime(2025, 1, 2 + day, 6, 0, tzinfo=timezone.utc)
            
            records.append(SleepRecord(
                source_name="Test",
                start_date=start_dt,
                end_date=end_dt,
                state=SleepState.ASLEEP
            ))
        
        pipeline = MoodPredictionPipeline(
            config=PipelineConfig(use_seoul_features=True)
        )
        
        # Should complete without timezone errors
        result = pipeline.process_health_data(
            sleep_records=records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 1, 31)
        )
        
        assert result.has_errors is False
        assert len(result.daily_predictions) > 0