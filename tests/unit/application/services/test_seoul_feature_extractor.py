"""
Unit tests for Seoul Feature Extractor.

Tests the optimized feature extraction for XGBoost models,
including edge cases like missing HRV data.
"""

from datetime import UTC, date, datetime

import pytest

from big_mood_detector.application.services.seoul_feature_extractor import (
    SeoulFeatureExtractor,
)
from big_mood_detector.domain.entities.activity_record import ActivityRecord, ActivityType
from big_mood_detector.domain.entities.heart_rate_record import (
    HeartMetricType,
    HeartRateRecord,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState


class TestSeoulFeatureExtractor:
    """Test Seoul feature extraction."""

    @pytest.fixture
    def extractor(self) -> SeoulFeatureExtractor:
        """Create feature extractor."""
        return SeoulFeatureExtractor()

    @pytest.fixture
    def target_date(self) -> date:
        """Target date for feature extraction."""
        return date(2025, 7, 26)

    def test_extract_with_no_hrv_data(
        self, extractor: SeoulFeatureExtractor, target_date: date
    ) -> None:
        """Test extraction when heart rate records have no HRV data (division by zero bug)."""
        # Create sleep records
        sleep_records = [
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 7, 25, 22, 0, tzinfo=UTC),
                end_date=datetime(2025, 7, 26, 6, 0, tzinfo=UTC),
                state=SleepState.ASLEEP,
            )
        ]

        # Create activity records
        activity_records = [
            ActivityRecord(
                source_name="iPhone",
                start_date=datetime(2025, 7, 26, 0, 0, tzinfo=UTC),
                end_date=datetime(2025, 7, 26, 23, 59, tzinfo=UTC),
                activity_type=ActivityType.STEP_COUNT,
                value=5000.0,
                unit="count",
            )
        ]

        # Create heart records WITHOUT HRV data
        heart_records = [
            HeartRateRecord(
                source_name="Apple Watch",
                timestamp=datetime(2025, 7, 26, 12, 0, tzinfo=UTC),
                metric_type=HeartMetricType.HEART_RATE,
                value=72.0,
                unit="count/min",
            ),
            HeartRateRecord(
                source_name="Apple Watch",
                timestamp=datetime(2025, 7, 26, 13, 0, tzinfo=UTC),
                metric_type=HeartMetricType.RESTING_HEART_RATE,
                value=65.0,
                unit="count/min",
            ),
            # Note: No HRV records!
        ]

        # This should not raise ZeroDivisionError
        features = extractor.extract_seoul_features(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            target_date=target_date,
        )

        # Should return valid features with defaults for missing HRV
        assert features is not None
        assert features.date == target_date
        # Since there's no aggregation for the single day, it should use default
        assert features.avg_resting_hr == 72.0  # From HEART_RATE, not RESTING (no aggregation)
        assert features.hrv_sdnn == 50.0  # Default when no HRV data

    def test_extract_with_empty_data(
        self, extractor: SeoulFeatureExtractor, target_date: date
    ) -> None:
        """Test extraction with no data returns valid defaults."""
        features = extractor.extract_seoul_features(
            sleep_records=[],
            activity_records=[],
            heart_records=[],
            target_date=target_date,
        )

        assert features is not None
        assert features.date == target_date
        # Check some defaults
        assert features.sleep_duration_hours == 0.0
        assert features.total_steps == 0
        assert features.avg_resting_hr == 70.0  # Default
        assert features.hrv_sdnn == 50.0  # Default

    def test_extract_with_mixed_heart_data(
        self, extractor: SeoulFeatureExtractor, target_date: date
    ) -> None:
        """Test extraction with some days having HRV and some not."""
        sleep_records = []
        activity_records = []
        heart_records = []

        # Day 1: Has both HR and HRV
        heart_records.extend([
            HeartRateRecord(
                source_name="Apple Watch",
                timestamp=datetime(2025, 7, 24, 12, 0, tzinfo=UTC),
                metric_type=HeartMetricType.RESTING_HEART_RATE,
                value=60.0,
                unit="count/min",
            ),
            HeartRateRecord(
                source_name="Apple Watch",
                timestamp=datetime(2025, 7, 24, 12, 0, tzinfo=UTC),
                metric_type=HeartMetricType.HRV_SDNN,
                value=45.0,
                unit="ms",
            ),
        ])

        # Day 2: Has HR but no HRV
        heart_records.append(
            HeartRateRecord(
                source_name="Apple Watch",
                timestamp=datetime(2025, 7, 25, 12, 0, tzinfo=UTC),
                metric_type=HeartMetricType.RESTING_HEART_RATE,
                value=65.0,
                unit="count/min",
            )
        )

        # Day 3: Has both again
        heart_records.extend([
            HeartRateRecord(
                source_name="Apple Watch",
                timestamp=datetime(2025, 7, 26, 12, 0, tzinfo=UTC),
                metric_type=HeartMetricType.RESTING_HEART_RATE,
                value=70.0,
                unit="count/min",
            ),
            HeartRateRecord(
                source_name="Apple Watch",
                timestamp=datetime(2025, 7, 26, 12, 0, tzinfo=UTC),
                metric_type=HeartMetricType.HRV_SDNN,
                value=55.0,
                unit="ms",
            ),
        ])

        features = extractor.extract_seoul_features(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            target_date=target_date,
        )

        assert features is not None
        # Should average only the days with data
        assert features.avg_resting_hr == pytest.approx(65.0, rel=0.01)  # (60+65+70)/3
        assert features.hrv_sdnn == pytest.approx(50.0, rel=0.01)  # (45+55)/2

    def test_feature_vector_generation(
        self, extractor: SeoulFeatureExtractor, target_date: date
    ) -> None:
        """Test that feature vector has exactly 36 features."""
        # Create minimal data
        sleep_records = [
            SleepRecord(
                source_name="Test",
                start_date=datetime(2025, 7, 25, 22, 0, tzinfo=UTC),
                end_date=datetime(2025, 7, 26, 6, 0, tzinfo=UTC),
                state=SleepState.ASLEEP,
            )
        ]

        features = extractor.extract_seoul_features(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=target_date,
        )

        # Get feature vector
        feature_vector = features.to_xgboost_features()

        # Must have exactly 36 features
        assert len(feature_vector) == 36
        # All features must be numeric
        assert all(isinstance(f, (int, float)) for f in feature_vector)
        # No NaN or inf values
        import math
        assert not any(math.isnan(f) or math.isinf(f) for f in feature_vector)