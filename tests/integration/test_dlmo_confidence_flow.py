"""
Test that DLMO confidence flows correctly from CircadianPhaseResult to SeoulXGBoostFeatures.
"""

from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from big_mood_detector.application.services.aggregation_pipeline import (
    AggregationConfig,
    AggregationPipeline,
)
from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.domain.entities.heart_rate_record import (
    HeartMetricType,
    HeartRateRecord,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.dlmo_calculator import CircadianPhaseResult


class TestDLMOConfidenceFlow:
    """Verify DLMO confidence propagates through the pipeline."""

    def create_test_data(self, days: int = 7):
        """Create test data for specified number of days."""
        base_date = date.today() - timedelta(days=days-1)
        sleep_records = []
        activity_records = []
        heart_records = []

        for day in range(days):
            current_date = base_date + timedelta(days=day)

            # Sleep record
            sleep_records.append(
                SleepRecord(
                    source_name="Test",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=22),
                    end_date=datetime.combine(current_date + timedelta(days=1), datetime.min.time()) + timedelta(hours=6),
                    state=SleepState.ASLEEP,
                )
            )

            # Activity record
            activity_records.append(
                ActivityRecord(
                    source_name="Test",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=9),
                    end_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=10),
                    activity_type=ActivityType.STEP_COUNT,
                    value=5000.0,
                    unit="count",
                )
            )

            # Heart rate record
            heart_records.append(
                HeartRateRecord(
                    source_name="Test",
                    timestamp=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=12),
                    metric_type=HeartMetricType.HEART_RATE,
                    value=70.0,
                    unit="bpm",
                )
            )

        return sleep_records, activity_records, heart_records

    @patch('big_mood_detector.application.services.aggregation_pipeline.DLMOCalculator')
    def test_dlmo_confidence_from_calculator_to_features(self, mock_dlmo_class):
        """Test that DLMO confidence from calculator flows to SeoulXGBoostFeatures."""
        # Create a mock DLMO calculator instance
        mock_dlmo_instance = Mock()
        mock_dlmo_class.return_value = mock_dlmo_instance

        # Create a mock CircadianPhaseResult with specific confidence
        mock_result = CircadianPhaseResult(
            date=date.today(),
            estimated_dlmo_hour=20.5,
            cbt_min_hour=4.5,
            cbt_amplitude=1.2,
            phase_angle=2.5,
            confidence=0.85  # This is the confidence we want to verify flows through
        )
        mock_dlmo_instance.calculate_dlmo.return_value = mock_result

        # Create pipeline with DLMO enabled
        config = AggregationConfig(enable_dlmo_calculation=True)
        pipeline = AggregationPipeline(config=config)

        # Create test data
        sleep, activity, heart = self.create_test_data(7)

        # Aggregate features
        clinical_features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )

        # Verify the confidence flowed through
        assert len(clinical_features) > 0
        for feature_set in clinical_features:
            if feature_set and feature_set.seoul_features:
                # When DLMO is calculated, confidence should match the mock result
                if feature_set.seoul_features.estimated_dlmo_hour != 21.0:  # Not default
                    assert feature_set.seoul_features.estimated_dlmo_confidence == 0.85, \
                        f"Expected confidence 0.85 from mock, got {feature_set.seoul_features.estimated_dlmo_confidence}"

    def test_dlmo_confidence_zero_when_disabled(self):
        """Test that DLMO confidence is 0.0 when DLMO calculation is disabled."""
        # Create pipeline with DLMO disabled
        config = AggregationConfig(enable_dlmo_calculation=False)
        pipeline = AggregationPipeline(config=config)

        # Create test data
        sleep, activity, heart = self.create_test_data(7)

        # Aggregate features
        clinical_features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )

        # Verify confidence is 0.0 when DLMO not calculated
        assert len(clinical_features) > 0
        for feature_set in clinical_features:
            if feature_set and feature_set.seoul_features:
                assert feature_set.seoul_features.estimated_dlmo_confidence == 0.0, \
                    "DLMO confidence should be 0.0 when DLMO calculation is disabled"
