"""
Full pipeline integration tests.

Tests the complete flow from raw health data to clinical features and predictions.
"""

import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from big_mood_detector.application.services.aggregation_pipeline import (
    AggregationPipeline,
    AggregationConfig,
)
from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.domain.entities.heart_rate_record import HeartRateRecord, HeartMetricType
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.clinical_feature_extractor import (
    ClinicalFeatureExtractor,
    SeoulXGBoostFeatures,
)


@pytest.mark.integration
class TestFullPipelineIntegration:
    """Test the complete mood prediction pipeline end-to-end."""
    
    @pytest.fixture
    def realistic_health_data(self):
        """Create realistic health data for 30 days."""
        base_date = date.today() - timedelta(days=30)
        sleep_records = []
        activity_records = []
        heart_records = []
        
        for day in range(30):
            current_date = base_date + timedelta(days=day)
            
            # Realistic sleep pattern with some variation
            sleep_offset = (day % 7) * 0.5  # Vary sleep time across week
            sleep_duration = 7 + (day % 3) * 0.5  # Vary duration 7-8 hours
            
            sleep_records.append(
                SleepRecord(
                    source_name="Apple Health",
                    start_date=datetime.combine(current_date, datetime.min.time()) 
                              + timedelta(hours=23 + sleep_offset),
                    end_date=datetime.combine(current_date + timedelta(days=1), datetime.min.time()) 
                            + timedelta(hours=sleep_duration),
                    state=SleepState.ASLEEP,
                )
            )
            
            # Activity pattern - multiple records throughout the day
            for hour in [8, 12, 15, 18]:
                steps = 1000 + (hour * 100) + (day * 50) % 500
                activity_records.append(
                    ActivityRecord(
                        source_name="Apple Health",
                        start_date=datetime.combine(current_date, datetime.min.time()) 
                                  + timedelta(hours=hour),
                        end_date=datetime.combine(current_date, datetime.min.time()) 
                                + timedelta(hours=hour + 1),
                        activity_type=ActivityType.STEP_COUNT,
                        value=float(steps),
                        unit="count",
                    )
                )
            
            # Heart rate measurements throughout the day
            for hour in [6, 10, 14, 18, 22]:
                hr_value = 65 + (hour % 12) * 2  # Vary HR by time of day
                heart_records.append(
                    HeartRateRecord(
                        source_name="Apple Health",
                        timestamp=datetime.combine(current_date, datetime.min.time()) 
                                 + timedelta(hours=hour),
                        metric_type=HeartMetricType.HEART_RATE,
                        value=float(hr_value),
                        unit="bpm",
                    )
                )
                
                # Add some HRV data
                if hour in [10, 22]:
                    heart_records.append(
                        HeartRateRecord(
                            source_name="Apple Health",
                            timestamp=datetime.combine(current_date, datetime.min.time()) 
                                     + timedelta(hours=hour),
                            metric_type=HeartMetricType.HRV_SDNN,
                            value=45.0 + (day % 5) * 3,
                            unit="ms",
                        )
                    )
        
        return sleep_records, activity_records, heart_records
    
    def test_aggregation_pipeline_produces_valid_features(self, realistic_health_data):
        """Test that aggregation pipeline produces valid clinical features."""
        sleep, activity, heart = realistic_health_data
        
        # Create pipeline
        config = AggregationConfig(
            enable_dlmo_calculation=False,  # Disable for speed
            enable_circadian_analysis=True,
        )
        pipeline = AggregationPipeline(config=config)
        
        # Aggregate features for the last week
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        clinical_features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Verify we got features for most days (at least 5 out of 7)
        # Today might have incomplete data
        assert len(clinical_features) >= 5
        
        # Verify each feature set is valid
        for feature_set in clinical_features:
            assert feature_set is not None
            assert feature_set.seoul_features is not None
            
            # Check basic validity
            seoul = feature_set.seoul_features
            assert 0 <= seoul.sleep_duration_hours <= 24
            assert 0 <= seoul.sleep_efficiency <= 1
            assert seoul.total_steps >= 0
            assert 0 <= seoul.data_completeness <= 1
            
            # Check that we have non-zero values for days with complete data
            if seoul.data_completeness >= 0.8:  # Only check days with most data
                assert seoul.total_steps > 0  # We added activity data
                assert seoul.avg_resting_hr > 0  # We added HR data
                assert seoul.sleep_duration_hours > 0  # We added sleep data
    
    def test_feature_consistency_across_days(self, realistic_health_data):
        """Test that features are consistent and reasonable across multiple days."""
        sleep, activity, heart = realistic_health_data
        
        # Create pipeline
        config = AggregationConfig(enable_dlmo_calculation=False)
        pipeline = AggregationPipeline(config=config)
        
        # Aggregate features for 14 days
        end_date = date.today()
        start_date = end_date - timedelta(days=14)
        
        clinical_features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Collect metrics across days
        sleep_durations = []
        total_steps = []
        hr_values = []
        
        for feature_set in clinical_features:
            if feature_set and feature_set.seoul_features:
                seoul = feature_set.seoul_features
                sleep_durations.append(seoul.sleep_duration_hours)
                total_steps.append(seoul.total_steps)
                hr_values.append(seoul.avg_resting_hr)
        
        # Verify reasonable consistency
        assert len(sleep_durations) >= 10
        assert min(sleep_durations) >= 5  # At least 5 hours
        assert max(sleep_durations) <= 10  # At most 10 hours
        assert abs(max(sleep_durations) - min(sleep_durations)) <= 4  # Not too variable
        
        # Check non-zero values only
        non_zero_steps = [s for s in total_steps if s > 0]
        non_zero_hr = [hr for hr in hr_values if hr > 0]
        
        assert all(steps > 1000 for steps in non_zero_steps)  # Some activity each day with data
        assert all(60 <= hr <= 90 for hr in non_zero_hr)  # Reasonable HR range
    
    @pytest.mark.skipif(
        os.getenv("TESTING") == "1",
        reason="Skip ML model tests in fast mode"
    )
    def test_xgboost_feature_generation(self, realistic_health_data):
        """Test that features can be converted to XGBoost format."""
        sleep, activity, heart = realistic_health_data
        
        # Create pipeline
        config = AggregationConfig(enable_dlmo_calculation=False)
        pipeline = AggregationPipeline(config=config)
        
        # Get features for one day
        features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
        )
        
        # Verify we can convert to XGBoost format
        for feature_set in features:
            if feature_set and feature_set.seoul_features:
                xgb_features = feature_set.seoul_features.to_xgboost_features()
                
                # Should be 36 features
                assert len(xgb_features) == 36
                
                # All should be numeric
                assert all(isinstance(f, (int, float)) for f in xgb_features)
                
                # Should have reasonable values
                assert all(f >= 0 for f in xgb_features[:5])  # First few are durations/percentages
    
    def test_data_completeness_calculation(self, realistic_health_data):
        """Test that data completeness is calculated correctly."""
        sleep, activity, heart = realistic_health_data
        
        # Test with all data types
        config = AggregationConfig(enable_dlmo_calculation=False)
        pipeline = AggregationPipeline(config=config)
        
        features_all = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
        )
        
        # Should have high completeness with all data
        for feature_set in features_all:
            if feature_set and feature_set.seoul_features:
                assert feature_set.seoul_features.data_completeness >= 0.8
        
        # Test with missing heart data
        features_no_hr = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=[],
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
        )
        
        # Should have 0.8 completeness (missing 20% for HR)
        for feature_set in features_no_hr:
            if feature_set and feature_set.seoul_features:
                assert abs(feature_set.seoul_features.data_completeness - 0.8) < 0.01
    
    def test_circadian_metrics_calculation(self, realistic_health_data):
        """Test that circadian metrics are calculated when enabled."""
        sleep, activity, heart = realistic_health_data
        
        # Create pipeline with circadian analysis enabled
        config = AggregationConfig(
            enable_dlmo_calculation=False,
            enable_circadian_analysis=True,
        )
        pipeline = AggregationPipeline(config=config)
        
        # Need multiple days for circadian analysis
        features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        # Verify we got features
        assert len(features) > 0
        
        # Check that circadian metrics are present (even if some are defaults)
        for feature_set in features:
            if feature_set and feature_set.seoul_features:
                seoul = feature_set.seoul_features
                # These should be calculated or have reasonable defaults
                assert seoul.interdaily_stability >= 0
                assert seoul.intradaily_variability >= 0
                assert seoul.relative_amplitude >= 0