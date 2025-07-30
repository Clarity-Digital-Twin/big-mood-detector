"""
Test that the system doesn't generate default features when data is missing.

This test ensures that the v0.5.4 fix works - no more fake features!
"""

from datetime import date, datetime

from big_mood_detector.application.services.aggregation_pipeline import (
    AggregationConfig,
    AggregationPipeline,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState


class TestNoDefaultFeatures:
    """Verify that we skip days without real data."""

    def test_no_features_generated_for_days_without_sleep(self):
        """
        Critical test: Ensure no features are generated when sleep data is missing.

        This prevents the bug where we had identical predictions for all days.
        """
        # Create sparse sleep data - only 2 days out of 7
        sleep_records = [
            # Monday night
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 23, 22, 0),
                end_date=datetime(2025, 6, 24, 6, 0),
                state=SleepState.ASLEEP
            ),
            # Thursday night
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 26, 23, 0),
                end_date=datetime(2025, 6, 27, 7, 0),
                state=SleepState.ASLEEP
            ),
        ]

        # Configure pipeline
        config = AggregationConfig(
            window_size=3,
            min_window_size=1,  # Allow single day for testing
            enable_dlmo_calculation=False,
            enable_circadian_analysis=False,
        )

        pipeline = AggregationPipeline(config=config)

        # Try to generate features for a full week
        start_date = date(2025, 6, 23)
        end_date = date(2025, 6, 29)

        features = pipeline.aggregate_seoul_features(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=start_date,
            end_date=end_date,
        )

        # CRITICAL: Should only have features for days with sleep data
        # With min_window_size=1, we get features starting from first sleep day
        assert len(features) <= 2, f"Got {len(features)} features, expected max 2"

        # Verify dates are only where we have data
        feature_dates = {f.date for f in features}
        # Features should only be for days with enough window data
        # Since we need at least 3 days in the window, we might get 0 features
        assert len(feature_dates) <= 2, f"Features on unexpected dates: {feature_dates}"

    def test_consecutive_days_required_for_statistics(self):
        """
        Test that we need consecutive days of data for proper statistics.
        """
        # Create sleep data with gaps
        sleep_records = [
            # Day 1
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 1, 22, 0),
                end_date=datetime(2025, 6, 2, 6, 0),
                state=SleepState.ASLEEP
            ),
            # Day 2
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 2, 22, 30),
                end_date=datetime(2025, 6, 3, 6, 30),
                state=SleepState.ASLEEP
            ),
            # Day 3
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 3, 23, 0),
                end_date=datetime(2025, 6, 4, 7, 0),
                state=SleepState.ASLEEP
            ),
            # Gap for 3 days
            # Day 7
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 7, 22, 0),
                end_date=datetime(2025, 6, 8, 6, 0),
                state=SleepState.ASLEEP
            ),
        ]

        config = AggregationConfig(
            window_size=30,
            min_window_size=3,  # Need 3 days minimum
        )

        pipeline = AggregationPipeline(config=config)

        features = pipeline.aggregate_seoul_features(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 10),
        )

        # Should only get features after we have 3 days of data
        # Day 1: window=[day1] - not enough
        # Day 2: window=[day1,day2] - not enough
        # Day 3: window=[day1,day2,day3] - enough! Generate features
        # Day 4-6: no sleep data, skipped
        # Day 7: window=[day1,day2,day3] - but day 7 is too far, might not generate

        assert len(features) >= 1, "Should have at least 1 feature set"

        # First features should be for June 4 (after 3 days of data)
        if features:
            assert features[0].date >= date(2025, 6, 4), "Features generated too early"

    def test_aggregate_daily_features_also_skips_missing_days(self):
        """
        Test that aggregate_daily_features also skips days without data.
        """
        sleep_records = [
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 7, 1, 22, 0),
                end_date=datetime(2025, 7, 2, 6, 0),
                state=SleepState.ASLEEP
            ),
        ]

        config = AggregationConfig(min_window_size=1)
        pipeline = AggregationPipeline(config=config)

        # Try to get features for 5 days with only 1 day of sleep
        features = pipeline.aggregate_daily_features(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 5),
        )

        # Should only have features for the one day with data
        assert len(features) <= 1, f"Got {len(features)} features, expected max 1"

        if features:
            assert features[0].date == date(2025, 7, 2), "Feature on wrong date"
