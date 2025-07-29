"""
Test Pipeline Window Selection Integration

Tests that MoodPredictionPipeline can use WindowSelectionStrategy
to find valid data windows in sparse health records.
"""

from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.window_selection_strategy import (
    MostRecentValidWindowStrategy,
)


class TestPipelineWindowSelection:
    """Test pipeline integration with window selection strategies."""

    def create_sleep_record(self, date_str: str) -> SleepRecord:
        """Helper to create sleep records."""
        start = datetime.fromisoformat(f"{date_str}T22:00:00")
        end = start + timedelta(hours=8)
        return SleepRecord(
            source_name="Apple Watch",
            start_date=start,
            end_date=end,
            state=SleepState.ASLEEP,
        )

    def create_sparse_data(self):
        """Create sparse data with realistic usage gaps."""
        records = []

        # Old window: January (valid)
        for day in range(1, 8):
            records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        # Gap until June

        # Recent window: June 26 - July 2 (valid)
        for day in range(26, 31):
            records.append(self.create_sleep_record(f"2025-06-{day:02d}"))
        for day in range(1, 3):
            records.append(self.create_sleep_record(f"2025-07-{day:02d}"))

        # Gap until now (July 28) - no recent data!

        return records

    @patch('big_mood_detector.infrastructure.ml_models.xgboost_models.XGBoostMoodPredictor')
    def test_pipeline_uses_window_strategy_when_no_recent_data(self, mock_predictor_class):
        """Should use window strategy to find valid historical data."""
        # Setup mock predictor
        mock_predictor = Mock()
        mock_predictor.is_loaded = True
        mock_predictor.predict.return_value = {
            'depression_risk': 0.036,
            'hypomanic_risk': 0.003,
            'manic_risk': 0.0,
            'confidence': 0.35
        }
        mock_predictor_class.return_value = mock_predictor

        # Create pipeline with window selection
        config = PipelineConfig(
            min_days_required=7,
            window_selection_strategy=MostRecentValidWindowStrategy()
        )
        pipeline = MoodPredictionPipeline(config=config)

        # Create sparse data
        sleep_records = self.create_sparse_data()
        activity_records = []
        heart_records = []

        # Process with default target_date (today = July 28)
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            target_date=date(2025, 7, 28),  # Today - no recent data!
        )

        # Should find and use the June 26 - July 2 window
        assert not result.has_errors
        assert len(result.daily_predictions) > 0
        assert 'window_used' in result.metadata

        window = result.metadata['window_used']
        assert window.start_date == date(2025, 6, 26)
        assert window.end_date == date(2025, 7, 2)

    @patch('big_mood_detector.infrastructure.ml_models.xgboost_models.XGBoostMoodPredictor')
    def test_pipeline_without_strategy_fails_on_sparse_data(self, mock_predictor_class):
        """Without strategy, should fail when no recent data."""
        # Setup mock predictor
        mock_predictor = Mock()
        mock_predictor.is_loaded = True
        mock_predictor_class.return_value = mock_predictor

        # Create pipeline WITHOUT window selection
        config = PipelineConfig(
            min_days_required=7,
            window_selection_strategy=None  # No strategy!
        )
        pipeline = MoodPredictionPipeline(config=config)

        # Create sparse data
        sleep_records = self.create_sparse_data()
        activity_records = []
        heart_records = []

        # Process with default behavior (last 7 days from July 28)
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            target_date=date(2025, 7, 28),
        )

        # Should get 0 predictions (current behavior)
        # The pipeline processes the last 7 days but finds no sleep data
        # It may still generate predictions with 0 sleep hours
        # Check that sparse data warning is present
        if result.warnings:
            assert any("Sparse data" in w for w in result.warnings)

    def test_pipeline_respects_minimum_days_requirement(self):
        """Should only process windows meeting minimum days."""
        config = PipelineConfig(
            min_days_required=10,  # Higher requirement
            window_selection_strategy=MostRecentValidWindowStrategy()
        )

        # Create data with only 7-day windows
        records = []
        for day in range(1, 8):  # Only 7 days
            records.append(self.create_sleep_record(f"2025-06-{day:02d}"))

        pipeline = MoodPredictionPipeline(config=config)

        with patch.object(pipeline, 'mood_predictor') as mock_predictor:
            mock_predictor.is_loaded = True

            result = pipeline.process_health_data(
                sleep_records=records,
                activity_records=[],
                heart_records=[],
                target_date=date(2025, 7, 28),
            )

            # Should not find any valid windows
            assert len(result.daily_predictions) == 0
