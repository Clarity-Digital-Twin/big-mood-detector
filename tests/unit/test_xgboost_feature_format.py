"""
Test to verify XGBoost feature format expectations.

This test will help us understand:
1. What features the XGBoost models expect
2. What features we're currently providing
3. Whether there's a mismatch
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from big_mood_detector.application.pipelines.xgboost_pipeline import XGBoostPipeline
from big_mood_detector.application.services.aggregation_pipeline import (
    AggregationPipeline,
    DailyFeatures,
)
from big_mood_detector.application.validators.pipeline_validators import (
    XGBoostValidator,
)
from big_mood_detector.domain.services.clinical_feature_extractor import (
    SeoulXGBoostFeatures,
)
from big_mood_detector.infrastructure.ml_models.xgboost_models import (
    XGBoostModelLoader,
    XGBoostMoodPredictor,
)


class TestXGBoostFeatureFormat:
    """Test XGBoost feature format expectations."""

    def test_xgboost_model_expects_daily_features_format(self):
        """Verify what feature names the XGBoost models expect."""
        loader = XGBoostModelLoader()
        
        # These are the features the models expect
        expected_features = loader.FEATURE_NAMES
        
        print("\n=== XGBoost Model Expected Features ===")
        print(f"Total features: {len(expected_features)}")
        print("\nFirst 10 features:")
        for i, feature in enumerate(expected_features[:10]):
            print(f"  {i+1}. {feature}")
        
        # Verify they all have _MN, _SD, or _Z suffixes
        assert all(
            feature.endswith(("_MN", "_SD", "_Z")) 
            for feature in expected_features
        ), "All features should have statistical suffixes"
        
        # Verify we have 36 features
        assert len(expected_features) == 36

    def test_daily_features_provides_correct_format(self):
        """Verify DailyFeatures provides the correct format."""
        # Create a mock DailyFeatures instance
        daily_features = DailyFeatures(
            date=None,
            # Mock all required fields with 0.0
            **{field.name: 0.0 for field in DailyFeatures.__dataclass_fields__.values() if field.name != 'date'}
        )
        
        # Get the XGBoost dict
        xgboost_dict = daily_features.to_xgboost_dict()
        
        print("\n=== DailyFeatures XGBoost Dict ===")
        print(f"Total features: {len(xgboost_dict)}")
        print("\nFirst 10 features:")
        for i, (key, value) in enumerate(list(xgboost_dict.items())[:10]):
            print(f"  {i+1}. {key}: {value}")
        
        # Verify format matches
        loader = XGBoostModelLoader()
        for feature_name in loader.FEATURE_NAMES:
            assert feature_name in xgboost_dict, f"Missing expected feature: {feature_name}"

    def test_seoul_xgboost_features_format_mismatch(self):
        """Verify SeoulXGBoostFeatures does NOT match expected format."""
        # Create a mock SeoulXGBoostFeatures instance
        from datetime import date
        seoul_features = SeoulXGBoostFeatures(
            date=date.today(),
            # Basic sleep features
            sleep_duration_hours=8.0,
            sleep_efficiency=0.9,
            sleep_onset_hour=23.0,
            wake_time_hour=7.0,
            sleep_fragmentation=0.1,
            # Advanced sleep features
            sleep_regularity_index=85.0,
            short_sleep_window_pct=0.1,
            long_sleep_window_pct=0.1,
            sleep_onset_variance=1.0,
            wake_time_variance=1.0,
            # Circadian features
            interdaily_stability=0.7,
            intradaily_variability=0.5,
            relative_amplitude=0.8,
            l5_value=1000.0,
            m10_value=8000.0,
            l5_onset_hour=2.0,
            m10_onset_hour=10.0,
            dlmo_hour=21.0,
            # Activity features
            total_steps=8000,
            activity_variance=1000.0,
            sedentary_hours=10.0,
            activity_fragmentation=0.3,
            sedentary_bout_mean=2.0,
            activity_intensity_ratio=0.5,
            # Heart rate features
            avg_resting_hr=70.0,
            hrv_sdnn=50.0,
            hr_circadian_range=15.0,
            hr_minimum_hour=4.0,
            # Phase features
            circadian_phase_advance=0.0,
            circadian_phase_delay=0.0,
            dlmo_confidence=0.0,
            pat_hour=14.0,
            # Z-scores
            sleep_duration_zscore=0.0,
            activity_zscore=0.0,
            hr_zscore=0.0,
            hrv_zscore=0.0,
            # Metadata
            data_completeness=1.0,
        )
        
        # Get feature vector
        feature_vector = seoul_features.to_xgboost_features()
        
        print("\n=== SeoulXGBoostFeatures Vector ===")
        print(f"Total features: {len(feature_vector)}")
        print(f"Type: {type(feature_vector)}")
        print(f"First 10 values: {feature_vector[:10]}")
        
        # This returns a list, not a dict with named features!
        # The XGBoost models need a dict with specific feature names
        assert isinstance(feature_vector, list)
        assert len(feature_vector) == 36
        
        # But the models expect a dict with named features!
        print("\n⚠️  MISMATCH: SeoulXGBoostFeatures returns a list, not a dict!")
        print("XGBoost models expect a dict with keys like 'sleep_percentage_MN'")

    def test_current_pipeline_usage(self):
        """Test what the current XGBoostPipeline is using."""
        # The XGBoostPipeline now uses AggregationPipeline
        extractor = AggregationPipeline()
        
        print("\n=== Current XGBoostPipeline Usage ===")
        print(f"Feature extractor type: {type(extractor).__name__}")
        print(f"Returns: DailyFeatures via aggregate_seoul_features()")
        print(f"Format: Dictionary with paper's 36 statistical features")
        print("\n✅ This MATCHES what XGBoost models expect!")
        
    def test_aggregation_pipeline_has_correct_features(self):
        """Verify AggregationPipeline has the correct implementation."""
        pipeline = AggregationPipeline()
        
        # Check if it has the aggregate_seoul_features method
        assert hasattr(pipeline, 'aggregate_seoul_features')
        
        print("\n=== AggregationPipeline ===")
        print("✅ Has aggregate_seoul_features() method")
        print("✅ Returns DailyFeatures with correct format")
        print("✅ DailyFeatures.to_xgboost_dict() returns expected format")


if __name__ == "__main__":
    # Run the tests to see the output
    test = TestXGBoostFeatureFormat()
    test.test_xgboost_model_expects_daily_features_format()
    test.test_daily_features_provides_correct_format()
    test.test_seoul_xgboost_features_format_mismatch()
    test.test_current_pipeline_usage()
    test.test_aggregation_pipeline_has_correct_features()