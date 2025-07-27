"""
Unit tests for XGBoost feature validation and error handling.

These tests ensure the XGBoost pipeline produces valid feature vectors
and handles errors gracefully.
"""

import math
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest

from big_mood_detector.application.pipelines.xgboost_pipeline import (
    XGBoostPipeline,
    XGBoostResult,
)
from big_mood_detector.application.validators.pipeline_validators import (
    XGBoostValidator,
)
from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState


class TestXGBoostFeatureValidation:
    """Test XGBoost feature vector validation."""

    @pytest.fixture
    def mock_feature_extractor(self) -> Mock:
        """Mock feature extractor that returns valid features."""
        from big_mood_detector.infrastructure.ml_models.xgboost_models import (
            XGBoostModelLoader,
        )

        mock = Mock()
        loader = XGBoostModelLoader()

        # Mock DailyFeatures
        mock_daily = Mock()
        # Return dict with all expected feature names
        mock_daily.to_model_dict.return_value = dict.fromkeys(loader.FEATURE_NAMES, 0.5)

        # Mock aggregate_seoul_features to return list of DailyFeatures
        mock.aggregate_seoul_features.return_value = [mock_daily]

        # Keep old interface for backward compatibility if needed
        mock_seoul = Mock()
        mock_seoul.to_xgboost_features.return_value = [0.5] * 36
        mock_features = Mock()
        mock_features.seoul_features = mock_seoul
        mock.extract_clinical_features.return_value = mock_features

        return mock

    @pytest.fixture
    def mock_predictor(self) -> Mock:
        """Mock XGBoost predictor."""
        from big_mood_detector.domain.services.mood_predictor import MoodPrediction
        
        mock = Mock()
        mock.predict.return_value = MoodPrediction(
            depression_risk=0.15,
            manic_risk=0.98,  # High mania risk!
            hypomanic_risk=0.45,
            confidence=0.9
        )
        return mock

    @pytest.fixture
    def pipeline(self, mock_feature_extractor: Mock, mock_predictor: Mock) -> XGBoostPipeline:
        """Create pipeline with mocks."""
        return XGBoostPipeline(
            feature_extractor=mock_feature_extractor,
            predictor=mock_predictor,
            validator=XGBoostValidator(),
        )

    def test_validates_feature_vector_length(
        self,
        pipeline: XGBoostPipeline,
        mock_feature_extractor: Mock,
    ) -> None:
        """Test that pipeline validates feature vector has exactly 36 features."""
        from big_mood_detector.infrastructure.ml_models.xgboost_models import (
            XGBoostModelLoader,
        )
        loader = XGBoostModelLoader()

        # Create invalid feature vector with wrong length
        # For new interface
        mock_daily = Mock()
        # Return dict with only 35 features (missing one)
        mock_daily.to_model_dict.return_value = {
            name: 0.5 for name in loader.FEATURE_NAMES[:-1]  # Skip last feature
        }
        mock_feature_extractor.aggregate_seoul_features.return_value = [mock_daily]

        # For old interface (if still used)
        mock_seoul = Mock()
        mock_seoul.to_xgboost_features.return_value = [0.5] * 35  # Only 35 features!
        mock_features = Mock()
        mock_features.seoul_features = mock_seoul
        mock_feature_extractor.extract_clinical_features.return_value = mock_features

        # Create minimal valid data
        sleep_records = [
            SleepRecord(
                source_name="Test",
                start_date=datetime(2025, 5, i+1, 22, 0, tzinfo=UTC),
                end_date=datetime(2025, 5, i+2, 6, 0, tzinfo=UTC),
                state=SleepState.ASLEEP,
            )
            for i in range(30)  # 30 days
        ]

        result = pipeline.process(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 5, 30),
        )

        # Should return None due to invalid feature vector
        assert result is None

    def test_detects_nan_in_features(
        self,
        pipeline: XGBoostPipeline,
        mock_feature_extractor: Mock,
    ) -> None:
        """Test that pipeline detects NaN values in feature vector."""
        from big_mood_detector.infrastructure.ml_models.xgboost_models import (
            XGBoostModelLoader,
        )
        loader = XGBoostModelLoader()

        # Mock DailyFeatures with NaN
        mock_daily = Mock()
        # Create dict with one NaN value
        feature_dict = dict.fromkeys(loader.FEATURE_NAMES, 0.5)
        feature_dict[loader.FEATURE_NAMES[-1]] = float('nan')  # Last feature is NaN
        mock_daily.to_model_dict.return_value = feature_dict
        mock_feature_extractor.aggregate_seoul_features.return_value = [mock_daily]

        # Also update old interface
        features = [0.5] * 35 + [float('nan')]
        mock_seoul = Mock()
        mock_seoul.to_xgboost_features.return_value = features
        mock_features = Mock()
        mock_features.seoul_features = mock_seoul
        mock_feature_extractor.extract_clinical_features.return_value = mock_features

        # Create minimal valid data
        sleep_records = [
            SleepRecord(
                source_name="Test",
                start_date=datetime(2025, 5, i+1, 22, 0, tzinfo=UTC),
                end_date=datetime(2025, 5, i+2, 6, 0, tzinfo=UTC),
                state=SleepState.ASLEEP,
            )
            for i in range(30)
        ]

        result = pipeline.process(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 5, 30),
        )

        assert result is None

    def test_detects_inf_in_features(
        self,
        pipeline: XGBoostPipeline,
        mock_feature_extractor: Mock,
    ) -> None:
        """Test that pipeline detects infinite values in feature vector."""
        from big_mood_detector.infrastructure.ml_models.xgboost_models import (
            XGBoostModelLoader,
        )
        loader = XGBoostModelLoader()

        # Mock DailyFeatures with Inf
        mock_daily = Mock()
        # Create dict with one Inf value
        feature_dict = dict.fromkeys(loader.FEATURE_NAMES, 0.5)
        feature_dict[loader.FEATURE_NAMES[-1]] = float('inf')  # Last feature is Inf
        mock_daily.to_model_dict.return_value = feature_dict
        mock_feature_extractor.aggregate_seoul_features.return_value = [mock_daily]

        # Also update old interface
        features = [0.5] * 35 + [float('inf')]
        mock_seoul = Mock()
        mock_seoul.to_xgboost_features.return_value = features
        mock_features = Mock()
        mock_features.seoul_features = mock_seoul
        mock_feature_extractor.extract_clinical_features.return_value = mock_features

        # Create minimal valid data
        sleep_records = [
            SleepRecord(
                source_name="Test",
                start_date=datetime(2025, 5, i+1, 22, 0, tzinfo=UTC),
                end_date=datetime(2025, 5, i+2, 6, 0, tzinfo=UTC),
                state=SleepState.ASLEEP,
            )
            for i in range(30)
        ]

        result = pipeline.process(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 5, 30),
        )

        assert result is None

    def test_successful_mania_detection(
        self,
        pipeline: XGBoostPipeline,
        mock_predictor: Mock,
    ) -> None:
        """Test successful prediction with high mania risk."""
        # Create 30 days of data
        sleep_records = []
        activity_records = []

        for i in range(30):
            # Reduced sleep (mania indicator)
            sleep_records.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=datetime(2025, 5, i+1, 2, 0, tzinfo=UTC),  # Late sleep
                    end_date=datetime(2025, 5, i+1, 5, 0, tzinfo=UTC),   # Only 3 hours!
                    state=SleepState.ASLEEP,
                )
            )

            # High activity (mania indicator)
            activity_records.append(
                ActivityRecord(
                    source_name="Apple Watch",
                    start_date=datetime(2025, 5, i+1, 6, 0, tzinfo=UTC),
                    end_date=datetime(2025, 5, i+1, 23, 0, tzinfo=UTC),
                    activity_type=ActivityType.STEP_COUNT,
                    value=20000.0,  # Very high step count
                    unit="count",
                )
            )

        result = pipeline.process(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=[],
            target_date=date(2025, 5, 30),
        )

        assert result is not None
        assert isinstance(result, XGBoostResult)
        assert result.mania_probability == 0.98  # High mania risk!
        assert result.highest_risk_episode == "mania"
        assert "High risk for mania" in result.clinical_interpretation
        assert result.confidence_level in ["high", "medium", "low"]

        # Verify predictor was called with valid features
        mock_predictor.predict.assert_called_once()
        call_args = mock_predictor.predict.call_args
        # Check if it's called with keyword argument
        if 'features' in call_args.kwargs:
            features = call_args.kwargs['features']
        else:
            # First positional argument
            features = call_args.args[0]
        assert len(features) == 36
        assert all(not math.isnan(f) and not math.isinf(f) for f in features)

    def test_filters_records_to_date_range(
        self,
        pipeline: XGBoostPipeline,
        mock_feature_extractor: Mock,
    ) -> None:
        """Test that pipeline filters records to only the needed date range."""
        # Create 100 days of data
        all_sleep_records = []
        for i in range(100):
            all_sleep_records.append(
                SleepRecord(
                    source_name="Test",
                    start_date=datetime(2025, 4, 1, 22, 0, tzinfo=UTC) + timedelta(days=i),
                    end_date=datetime(2025, 4, 2, 6, 0, tzinfo=UTC) + timedelta(days=i),
                    state=SleepState.ASLEEP,
                )
            )

        # Process with target date that should only use last 60 days
        result = pipeline.process(
            sleep_records=all_sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 7, 9),
        )

        # With real aggregation pipeline, just verify result is valid
        assert result is not None
        # Pipeline should have used at most 60 days
        assert result.data_days_used <= 60

    def test_probabilities_are_valid(
        self,
        pipeline: XGBoostPipeline,
        mock_predictor: Mock,
    ) -> None:
        """Test that all probabilities are between 0 and 1."""
        # Set up predictor with edge case probabilities
        mock_predictor.predict_mood_episodes.return_value = {
            "depression": {"probability": 0.0, "risk_level": "low"},
            "mania": {"probability": 1.0, "risk_level": "high"},
            "hypomania": {"probability": 0.5, "risk_level": "medium"},
        }

        # Create minimal data
        sleep_records = [
            SleepRecord(
                source_name="Test",
                start_date=datetime(2025, 5, i+1, 22, 0, tzinfo=UTC),
                end_date=datetime(2025, 5, i+2, 6, 0, tzinfo=UTC),
                state=SleepState.ASLEEP,
            )
            for i in range(30)
        ]

        result = pipeline.process(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 5, 30),
        )

        assert result is not None
        # Check all probabilities are valid
        assert 0.0 <= result.depression_probability <= 1.0
        assert 0.0 <= result.mania_probability <= 1.0
        assert 0.0 <= result.hypomania_probability <= 1.0
