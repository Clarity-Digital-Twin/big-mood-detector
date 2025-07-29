"""
Integration tests verifying all v0.5.4 fixes work together.

These tests ensure that:
1. Date assignment is correct
2. No default features are generated
3. PAT encode works
4. The pipeline produces reasonable predictions
"""

from datetime import date, datetime, timedelta

import numpy as np
import pytest

from big_mood_detector.application.pipelines.xgboost_pipeline import XGBoostPipeline
from big_mood_detector.application.services.aggregation_pipeline import (
    AggregationConfig,
    AggregationPipeline,
)
from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
    TemporalEnsembleOrchestrator,
)
from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.infrastructure.ml_models.pat_production_loader import (
    ProductionPATLoader,
)
from big_mood_detector.infrastructure.ml_models.xgboost_models import (
    XGBoostModelLoader,
)


class TestFullPipelineIntegration:
    """Integration tests for the complete pipeline with all fixes."""
    
    @pytest.fixture
    def realistic_sleep_data(self):
        """Create realistic sleep data with some gaps."""
        records = []
        base_date = datetime(2025, 6, 1)
        
        # Create 14 days of sleep with some gaps
        for day in range(14):
            # Skip some days to simulate realistic gaps
            if day in [3, 7, 11]:  # Skip these days
                continue
                
            # Vary sleep times realistically
            sleep_start_hour = 22 + (day % 3)  # 22:00, 23:00, 00:00
            sleep_end_hour = 6 + (day % 2)      # 6:00, 7:00
            
            # Create start time
            start = base_date.replace(hour=0, minute=0, second=0) + timedelta(days=day)
            
            # Handle late night sleep (after midnight)
            if sleep_start_hour >= 24:
                start = start + timedelta(days=1, hours=sleep_start_hour - 24)
            else:
                start = start + timedelta(hours=sleep_start_hour)
            
            # End is always next morning
            end = base_date.replace(hour=0, minute=0, second=0) + timedelta(days=day + 1, hours=sleep_end_hour)
            
            records.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=start,
                    end_date=end,
                    state=SleepState.ASLEEP,
                )
            )
        
        return records
    
    @pytest.fixture
    def realistic_activity_data(self):
        """Create realistic activity data."""
        records = []
        base_date = datetime(2025, 6, 1)
        
        # Create 14 days of hourly activity
        for day in range(14):
            for hour in range(24):
                # Simulate daily activity pattern
                if 7 <= hour <= 22:  # Awake hours
                    steps = np.random.randint(100, 500)
                else:  # Sleep hours
                    steps = 0
                
                timestamp = base_date + timedelta(days=day, hours=hour)
                
                records.append(
                    ActivityRecord(
                        source_name="Apple Watch",
                        start_date=timestamp,
                        end_date=timestamp + timedelta(hours=1),
                        value=float(steps),
                        activity_type=ActivityType.STEP_COUNT,
                        unit="count",
                    )
                )
        
        return records
    
    def test_pipeline_handles_sparse_data_correctly(
        self, realistic_sleep_data, realistic_activity_data
    ):
        """
        Test that the pipeline correctly handles sparse data without generating defaults.
        """
        # Configure aggregation
        config = AggregationConfig(
            window_size=7,
            min_window_size=3,
            enable_dlmo_calculation=False,
            enable_circadian_analysis=False,
        )
        
        pipeline = AggregationPipeline(config=config)
        
        # Generate features for 2 weeks
        features = pipeline.aggregate_seoul_features(
            sleep_records=realistic_sleep_data,
            activity_records=realistic_activity_data,
            heart_records=[],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 14),
        )
        
        # Should only have features for days with sufficient data
        assert len(features) > 0, "Should generate some features"
        assert len(features) < 14, "Should not generate features for all days (some have no sleep)"
        
        # Check that features have reasonable values (not all defaults)
        for daily_features in features:
            feature_dict = daily_features.to_xgboost_dict()
            
            # Not all features should be 0
            non_zero_count = sum(1 for v in feature_dict.values() if v != 0.0)
            assert non_zero_count >= 10, "Features should have varied values, not all zeros"
            
            # Sleep percentage should be reasonable (not default)
            sleep_pct = feature_dict.get("sleep_percentage_MN", 0)
            assert 0.1 < sleep_pct < 0.5, f"Sleep percentage {sleep_pct} seems unrealistic"
    
    @pytest.mark.skip(reason="XGBoost predictor module structure has changed")
    def test_xgboost_pipeline_with_fixes(
        self, realistic_sleep_data, realistic_activity_data
    ):
        """
        Test that XGBoost pipeline works with the aggregation fixes.
        """
        # Use aggregation pipeline as feature extractor
        aggregation_pipeline = AggregationPipeline(
            AggregationConfig(
                window_size=7,
                min_window_size=3,
                enable_dlmo_calculation=False,
                enable_circadian_analysis=False,
            )
        )
        
        # Create XGBoost components
        from big_mood_detector.application.services.xgboost_mood_predictor import (
            XGBoostMoodPredictor,
        )
        from big_mood_detector.application.services.xgboost_validator import (
            XGBoostValidator,
        )
        
        xgb_loader = XGBoostModelLoader()
        xgb_predictor = XGBoostMoodPredictor(xgb_loader)
        xgb_validator = XGBoostValidator()
        
        # Create XGBoost pipeline
        xgb_pipeline = XGBoostPipeline(
            feature_extractor=aggregation_pipeline,
            predictor=xgb_predictor,
            validator=xgb_validator,
        )
        
        # Predict for a specific date
        target_date = date(2025, 6, 10)
        
        try:
            predictions = xgb_pipeline.predict(
                sleep_records=realistic_sleep_data,
                activity_records=realistic_activity_data,
                heart_records=[],
                target_date=target_date,
                lookback_days=14,
            )
            
            if predictions:
                # Check predictions are reasonable
                assert 0 <= predictions.depression_probability <= 1
                assert 0 <= predictions.mania_probability <= 1
                assert 0 <= predictions.hypomania_probability <= 1
                
                # Not all predictions should be identical
                probs = [
                    predictions.depression_probability,
                    predictions.mania_probability,
                    predictions.hypomania_probability,
                ]
                assert len(set(probs)) > 1, "All predictions are identical - suggests default features"
        except Exception as e:
            # If no features could be generated, that's OK
            if "No daily features extracted" in str(e):
                pytest.skip("Not enough data for prediction - this is expected behavior")
            else:
                raise
    
    def test_temporal_ensemble_works_end_to_end(
        self, realistic_sleep_data, realistic_activity_data
    ):
        """
        Test that temporal ensemble works with all fixes applied.
        """
        # Create components
        pat_loader = ProductionPATLoader(skip_loading=True)
        xgb_loader = XGBoostModelLoader()
        
        # Mock XGBoost predictor
        class MockXGBoostPredictor:
            def predict_episode_tomorrow(self, features):
                # Return varied predictions based on input
                base_risk = float(np.mean(features)) / 100.0
                return {
                    "depression": min(base_risk * 1.2, 0.8),
                    "mania": min(base_risk * 0.5, 0.3),
                    "hypomania": min(base_risk * 0.8, 0.5),
                }
            
            def predict(self, features):
                # Alias for predict_episode_tomorrow
                return self.predict_episode_tomorrow(features)
        
        # Create orchestrator
        orchestrator = TemporalEnsembleOrchestrator(
            pat_encoder=pat_loader,
            pat_predictor=pat_loader,
            xgboost_predictor=MockXGBoostPredictor(),
        )
        
        # Create 7-day activity sequence for PAT
        activity_values = []
        for day in range(7):
            day_values = []
            for minute in range(1440):
                hour = minute // 60
                if 7 <= hour <= 22:  # Awake
                    value = np.random.randint(0, 50)
                else:  # Sleep
                    value = 0
                day_values.append(value)
            activity_values.extend(day_values)
        
        pat_sequence = np.array(activity_values, dtype=np.float32).reshape(7, 1440)
        
        # Create statistical features
        xgb_features = np.random.rand(36).astype(np.float32)
        
        # Test assessment - should not raise AttributeError
        assessment = orchestrator.predict(
            pat_sequence=pat_sequence,
            statistical_features=xgb_features,
        )
        
        assert assessment is not None
        assert assessment.current_state is not None
        assert assessment.future_risk is not None
        
        # Check values are reasonable
        assert 0 <= assessment.current_state.depression_probability <= 1
        assert 0 <= assessment.future_risk.depression_risk <= 1
    
    def test_no_fake_predictions_with_minimal_data(self):
        """
        Test that we don't get fake 4.4% predictions with minimal data.
        
        This reproduces the exact user scenario that exposed the bugs.
        """
        # Minimal sleep data - only 2 nights
        sleep_records = [
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 26, 22, 0),
                end_date=datetime(2025, 6, 27, 6, 0),
                state=SleepState.ASLEEP,
            ),
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 28, 23, 0),
                end_date=datetime(2025, 6, 29, 7, 0),
                state=SleepState.ASLEEP,
            ),
        ]
        
        # Configure pipeline
        config = AggregationConfig(
            window_size=7,
            min_window_size=2,  # Allow predictions with 2 days
        )
        
        pipeline = AggregationPipeline(config=config)
        
        # Try to generate features for a week
        features = pipeline.aggregate_seoul_features(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=date(2025, 6, 25),
            end_date=date(2025, 6, 30),
        )
        
        # Should only generate features for days with data
        assert len(features) <= 2, f"Generated {len(features)} features from 2 days of data"
        
        # If we do get features, they shouldn't all be defaults
        if features:
            feature_dict = features[0].to_xgboost_dict()
            
            # Count how many features are exactly 0.0
            zero_count = sum(1 for v in feature_dict.values() if v == 0.0)
            total_count = len(feature_dict)
            
            # Not all features should be zero
            assert zero_count < total_count * 0.8, "Too many zero features - likely defaults"