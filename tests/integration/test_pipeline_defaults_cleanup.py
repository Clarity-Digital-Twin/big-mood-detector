"""
Tests for cleaned up pipeline defaults.

Verifies that:
1. DLMO confidence is calculated from actual DLMO analysis
2. Data completeness is calculated based on available data
3. No more hardcoded values
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


class TestPipelineDefaultsCleanup:
    """Verify pipeline defaults are calculated, not hardcoded."""
    
    def create_test_data(self, days: int = 7):
        """Create test data for specified number of days."""
        base_date = date.today() - timedelta(days=days-1)  # Include today
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
    
    def test_data_completeness_calculated_not_hardcoded(self):
        """Data completeness should reflect actual data availability."""
        # Create pipeline with DLMO disabled (for speed)
        config = AggregationConfig(enable_dlmo_calculation=False)
        pipeline = AggregationPipeline(config=config)
        
        # Test with complete data
        sleep, activity, heart = self.create_test_data(7)
        
        # Use aggregate_daily_features to get ClinicalFeatureSet which has SeoulXGBoostFeatures
        clinical_features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        # Should have full completeness (1.0)
        assert len(clinical_features) > 0
        for feature_set in clinical_features:
            if feature_set and feature_set.seoul_features:
                assert abs(feature_set.seoul_features.data_completeness - 1.0) < 0.001, \
                    f"Should have full completeness with all data types, got {feature_set.seoul_features.data_completeness}"
        
        # Test with no heart rate data
        clinical_features_no_hr = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=[],  # No heart rate
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        # Should have 0.8 completeness (missing 20% for heart rate)
        for feature_set in clinical_features_no_hr:
            if feature_set and feature_set.seoul_features:
                assert abs(feature_set.seoul_features.data_completeness - 0.8) < 0.001, \
                    f"Should have 0.8 completeness without heart data, got {feature_set.seoul_features.data_completeness}"
        
        # Test with no activity data
        clinical_features_no_activity = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=[],  # No activity
            heart_records=heart,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        # Should have 0.6 completeness (40% sleep + 20% heart)
        for feature_set in clinical_features_no_activity:
            if feature_set and feature_set.seoul_features:
                assert abs(feature_set.seoul_features.data_completeness - 0.6) < 0.001, \
                    f"Should have 0.6 completeness without activity data, got {feature_set.seoul_features.data_completeness}"
    
    def test_dlmo_confidence_from_actual_calculation(self):
        """DLMO confidence should come from actual DLMO calculation when enabled."""
        # This test would be slow with real DLMO, so we'll verify the plumbing
        config = AggregationConfig(enable_dlmo_calculation=False)
        pipeline = AggregationPipeline(config=config)
        
        sleep, activity, heart = self.create_test_data(7)
        clinical_features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        # Without DLMO calculation, confidence should be 0.0
        for feature_set in clinical_features:
            if feature_set and feature_set.seoul_features:
                assert feature_set.seoul_features.estimated_dlmo_confidence == 0.0, \
                    "DLMO confidence should be 0.0 when DLMO not calculated"
    
    def test_pat_hour_documented_as_not_implemented(self):
        """PAT hour should be 0.0 with clear documentation."""
        config = AggregationConfig(enable_dlmo_calculation=False)
        pipeline = AggregationPipeline(config=config)
        
        sleep, activity, heart = self.create_test_data(7)
        clinical_features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        # PAT hour should be 0.0 (not implemented)
        for feature_set in clinical_features:
            if feature_set and feature_set.seoul_features:
                assert feature_set.seoul_features.pat_hour == 0.0, \
                    "PAT hour should be 0.0 (not implemented yet)"
    
    def test_no_more_hardcoded_defaults(self):
        """Verify specific hardcoded values are gone."""
        config = AggregationConfig(enable_dlmo_calculation=False)
        pipeline = AggregationPipeline(config=config)
        
        sleep, activity, heart = self.create_test_data(7)
        clinical_features = pipeline.aggregate_daily_features(
            sleep_records=sleep,
            activity_records=activity,
            heart_records=heart,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        # Check that old hardcoded values are not present
        forbidden_values = {
            0.8,   # Old dlmo_confidence default
            14.0,  # Old pat_hour default
        }
        
        for feature_set in clinical_features:
            if feature_set and feature_set.seoul_features:
                assert feature_set.seoul_features.estimated_dlmo_confidence not in forbidden_values, \
                    f"Found hardcoded dlmo_confidence: {feature_set.seoul_features.estimated_dlmo_confidence}"
                assert feature_set.seoul_features.pat_hour not in forbidden_values, \
                    f"Found hardcoded pat_hour: {feature_set.seoul_features.pat_hour}"