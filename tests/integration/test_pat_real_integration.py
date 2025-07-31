"""
Real PAT integration tests - NO MOCKS ALLOWED.

These tests verify PAT actually works with real models and data.
They will FAIL until we fix the identified bugs.
"""

import os
from datetime import date, datetime, timedelta

import numpy as np
import pytest

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.activity_sequence_extractor import (
    ActivitySequenceExtractor,
)
from big_mood_detector.infrastructure.ml_models.pat_production_loader import (
    ProductionPATLoader,
)


@pytest.mark.real_integration
@pytest.mark.skipif(
    os.environ.get("STUB_MODELS", "0") == "1",
    reason="Real integration tests require actual models"
)
class TestPATRealIntegration:
    """Test PAT integration with real models - no mocks allowed."""

    @pytest.fixture
    def real_activity_data(self):
        """Create 7 days of realistic activity data."""
        base_date = date.today() - timedelta(days=7)
        records = []

        for day in range(7):
            current_date = base_date + timedelta(days=day)

            # Morning activity (7 AM - 9 AM)
            records.append(
                ActivityRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=7),
                    end_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=9),
                    activity_type=ActivityType.STEP_COUNT,
                    value=2000.0,
                    unit="count",
                )
            )

            # Afternoon activity (12 PM - 1 PM)
            records.append(
                ActivityRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=12),
                    end_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=13),
                    activity_type=ActivityType.STEP_COUNT,
                    value=1500.0,
                    unit="count",
                )
            )

            # Evening activity (5 PM - 7 PM) - varying pattern
            evening_steps = 3000.0 + (1000.0 * np.sin(day * np.pi / 3.5))
            records.append(
                ActivityRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=17),
                    end_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=19),
                    activity_type=ActivityType.STEP_COUNT,
                    value=max(0, evening_steps),
                    unit="count",
                )
            )

        return records

    def test_pat_sequence_extraction_returns_correct_shape(self, real_activity_data):
        """PAT needs (7, 1440) shape array - will FAIL until method name fixed."""
        # Arrange
        extractor = ActivitySequenceExtractor()

        # Act - This will FAIL with AttributeError until we fix the method name
        sequence = extractor.extract_minute_sequence(real_activity_data, days=7)

        # Assert
        assert sequence.shape == (7 * 1440,), f"Expected shape (10080,), got {sequence.shape}"
        assert not np.all(sequence == 0), "Sequence should contain actual activity data"
        assert np.sum(sequence) > 0, "Total activity should be greater than 0"

    @pytest.mark.skipif(
        os.environ.get("TESTING") == "1",
        reason="Real models not loaded when TESTING=1"
    )
    def test_pat_loads_real_weights_not_stubs(self):
        """Verify real model weights are loaded, not test stubs."""
        # This will FAIL if TESTING=1 because stubs are loaded
        loader = ProductionPATLoader()

        # Check that real model is loaded
        assert loader.is_loaded, "PAT model should be loaded"
        assert hasattr(loader.model, 'encoder'), "Model should have encoder"
        assert hasattr(loader.model, 'head'), "Model should have depression head"

        # Verify it's not returning stub values
        # Flatten to match expected shape (10080,)
        dummy_sequence = np.zeros((7, 1440), dtype=np.float32).flatten()
        depression_prob = loader.predict_depression_from_activity(dummy_sequence)

        # Stub always returns 0.5, real model should return different value
        assert depression_prob != 0.5, "Model returning stub value 0.5"

    @pytest.mark.skipif(
        os.environ.get("TESTING") == "1",
        reason="Real models not loaded when TESTING=1"
    )
    def test_pat_predictions_vary_by_input(self, real_activity_data):
        """PAT should give different predictions for different activity patterns."""
        # Arrange
        loader = ProductionPATLoader()
        extractor = ActivitySequenceExtractor()

        # Create two different activity patterns
        active_data = real_activity_data
        sedentary_data = [
            ActivityRecord(
                source_name=r.source_name,
                start_date=r.start_date,
                end_date=r.end_date,
                activity_type=r.activity_type,
                value=r.value * 0.2,  # 20% of normal activity
                unit=r.unit,
            )
            for r in real_activity_data
        ]

        # Extract sequences - will FAIL until method name fixed
        active_seq = extractor.extract_minute_sequence(active_data, days=7)
        sedentary_seq = extractor.extract_minute_sequence(sedentary_data, days=7)

        # Reshape for PAT
        active_seq = active_seq.reshape(7, 1440)
        sedentary_seq = sedentary_seq.reshape(7, 1440)

        # Get predictions - flatten to (10080,) shape
        active_pred = loader.predict_depression_from_activity(active_seq.flatten())
        sedentary_pred = loader.predict_depression_from_activity(sedentary_seq.flatten())

        # Assert predictions are different
        assert active_pred != sedentary_pred, \
            "PAT should give different predictions for different activity levels"

    def test_pat_integration_in_pipeline(self):
        """Test PAT works in full pipeline with ensemble mode."""
        # Arrange
        config = PipelineConfig(
            include_pat_sequences=True,  # Enable ensemble
            min_days_required=7,
        )
        pipeline = MoodPredictionPipeline(config=config)

        # Create test data
        base_date = date.today() - timedelta(days=14)
        sleep_records = []
        activity_records = []

        for day in range(14):
            current_date = base_date + timedelta(days=day)

            # Sleep
            sleep_records.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=23),
                    end_date=datetime.combine(current_date + timedelta(days=1), datetime.min.time()) + timedelta(hours=7),
                    state=SleepState.ASLEEP,
                )
            )

            # Activity
            activity_records.append(
                ActivityRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=10),
                    end_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=11),
                    activity_type=ActivityType.STEP_COUNT,
                    value=3000.0,
                    unit="count",
                )
            )

        # Act - Process with ensemble
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=[],
            target_date=base_date + timedelta(days=13),
        )

        # Assert
        assert result.daily_predictions, "Should have daily predictions"

        # Check that PAT was actually used (not just XGBoost)
        for _date_key, prediction in result.daily_predictions.items():
            if "models_used" in prediction:
                assert "pat" in prediction["models_used"], "PAT should be in models used"
                assert "xgboost" in prediction["models_used"], "XGBoost should be in models used"

            # Verify temporal predictions exist
            if "current_depression" in prediction:
                current = prediction["current_depression"]
                future = prediction["depression_risk"]

                # They should be different (not both 0.5 or both 0.44)
                assert current != future, "NOW and TOMORROW should have different values"

                # Should not be hardcoded values
                assert current not in [0.5, 0.56, 0.563], "Current should not be hardcoded"
                assert future not in [0.044, 0.033, 0.034], "Future should not be hardcoded"
