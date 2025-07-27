"""
Test XGBoostPipeline uses DailyFeatures from AggregationPipeline.

This is the CORRECT implementation that has existed since July 23, 2025.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock, MagicMock, patch
import numpy as np

from big_mood_detector.application.pipelines.xgboost_pipeline import (
    XGBoostPipeline,
    XGBoostResult,
)
from big_mood_detector.application.services.aggregation_pipeline import (
    AggregationPipeline,
    DailyFeatures,
)
from big_mood_detector.application.validators.pipeline_validators import XGBoostValidator
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.entities.activity_record import ActivityRecord, ActivityType
from big_mood_detector.domain.entities.heart_rate_record import HeartRateRecord, HeartMetricType


class TestXGBoostPipelineWithDailyFeatures:
    """Test XGBoostPipeline using the CORRECT DailyFeatures implementation."""

    @pytest.fixture
    def sleep_records(self):
        """Create 60 days of sleep data."""
        records = []
        for day in range(60):
            records.append(
                SleepRecord(
                    source_name="iPhone",
                    start_date=datetime(2024, 1, 1, 23, 0) + timedelta(days=day),
                    end_date=datetime(2024, 1, 2, 7, 0) + timedelta(days=day),  # 8 hours
                    state=SleepState.ASLEEP,
                )
            )
        return records

    @pytest.fixture
    def activity_records(self):
        """Create 60 days of activity data."""
        records = []
        for day in range(60):
            records.append(
                ActivityRecord(
                    source_name="iPhone",
                    start_date=datetime(2024, 1, 1, 0, 0) + timedelta(days=day),
                    end_date=datetime(2024, 1, 1, 23, 59) + timedelta(days=day),
                    activity_type=ActivityType.STEP_COUNT,
                    value=10000,
                    unit="count",
                )
            )
        return records

    @pytest.fixture
    def heart_records(self):
        """Create 60 days of heart rate data."""
        records = []
        for day in range(60):
            records.append(
                HeartRateRecord(
                    source_name="Apple Watch",
                    timestamp=datetime(2024, 1, 1, 8, 0) + timedelta(days=day),
                    value=70,
                    metric_type=HeartMetricType.RESTING_HEART_RATE,
                    unit="bpm",
                )
            )
        return records

    def test_xgboost_pipeline_uses_aggregation_pipeline(self, sleep_records, activity_records, heart_records):
        """Verify XGBoostPipeline uses AggregationPipeline.aggregate_seoul_features()."""
        
        # Create aggregation pipeline
        aggregation_pipeline = AggregationPipeline()
        
        # Create mock predictor
        mock_predictor = Mock()
        captured_features = None
        
        def capture_features(features, user_id):
            nonlocal captured_features
            captured_features = features
            return {
                "depression": {"probability": 0.2},
                "mania": {"probability": 0.1},
                "hypomania": {"probability": 0.15},
            }
        
        mock_predictor.predict_mood_episodes.side_effect = capture_features
        
        # Create validator
        validator = XGBoostValidator()
        
        # Create pipeline with aggregation pipeline
        pipeline = XGBoostPipeline(
            feature_extractor=aggregation_pipeline,  # Pass AggregationPipeline
            predictor=mock_predictor,
            validator=validator,
        )
        
        # Run pipeline
        result = pipeline.process(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            target_date=date(2024, 3, 1),
        )
        
        # Verify result
        assert result is not None
        assert isinstance(result, XGBoostResult)
        
        # Verify features were extracted
        assert captured_features is not None
        assert len(captured_features) == 36
        
        # Verify it's a list (XGBoost expects a list/array)
        assert isinstance(captured_features, (list, np.ndarray))

    def test_daily_features_format_matches_xgboost_expectations(self):
        """Verify DailyFeatures produces the correct feature dictionary."""
        # Create a sample DailyFeatures
        from big_mood_detector.infrastructure.ml_models.xgboost_models import XGBoostModelLoader
        
        # This is what should happen inside the pipeline
        aggregation_pipeline = AggregationPipeline()
        
        # Mock some daily features
        daily_features = DailyFeatures(
            date=date(2024, 1, 1),
            # All the required fields with mock values
            sleep_percentage_mean=33.33,
            sleep_percentage_std=5.0,
            sleep_percentage_zscore=0.0,
            sleep_amplitude_mean=0.5,
            sleep_amplitude_std=0.1,
            sleep_amplitude_zscore=0.0,
            long_sleep_num_mean=1.0,
            long_sleep_num_std=0.0,
            long_sleep_num_zscore=0.0,
            long_sleep_len_mean=8.0,
            long_sleep_len_std=1.0,
            long_sleep_len_zscore=0.0,
            long_sleep_st_mean=7.5,
            long_sleep_st_std=0.5,
            long_sleep_st_zscore=0.0,
            long_sleep_wt_mean=0.5,
            long_sleep_wt_std=0.1,
            long_sleep_wt_zscore=0.0,
            short_sleep_num_mean=0.0,
            short_sleep_num_std=0.0,
            short_sleep_num_zscore=0.0,
            short_sleep_len_mean=0.0,
            short_sleep_len_std=0.0,
            short_sleep_len_zscore=0.0,
            short_sleep_st_mean=0.0,
            short_sleep_st_std=0.0,
            short_sleep_st_zscore=0.0,
            short_sleep_wt_mean=0.0,
            short_sleep_wt_std=0.0,
            short_sleep_wt_zscore=0.0,
            circadian_amplitude_mean=1.5,
            circadian_amplitude_std=0.0,
            circadian_amplitude_zscore=0.0,
            circadian_phase_mean=21.0,
            circadian_phase_std=1.0,
            circadian_phase_zscore=0.0,
        )
        
        # Get XGBoost dict
        xgboost_dict = daily_features.to_xgboost_dict()
        
        # Verify all expected features are present
        loader = XGBoostModelLoader()
        for feature_name in loader.FEATURE_NAMES:
            assert feature_name in xgboost_dict, f"Missing feature: {feature_name}"
        
        # Verify we can convert to list in correct order
        feature_vector = [xgboost_dict[name] for name in loader.FEATURE_NAMES]
        assert len(feature_vector) == 36
        assert all(isinstance(x, (int, float)) for x in feature_vector)