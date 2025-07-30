"""Integration test for window-level predictions."""

from datetime import date, datetime, timedelta

import pytest

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.dual_model_window_strategy import (
    DualModelWindowStrategy,
)
from big_mood_detector.domain.services.sparse_window_strategy import (
    SparseWindowStrategy,
)


class TestWindowLevelPredictions:
    def test_xgboost_window_prediction_behavior(self):
        """Test that XGBoost makes window-level predictions, not daily."""
        # Create 35 days of sparse sleep data (to ensure we have 30+ days)
        sleep_records = []
        base_date = datetime(2024, 12, 15)  # Start in December to have enough data
        for i in range(35):
            if i % 3 != 2:  # Skip every 3rd day for sparsity (~67% coverage)
                sleep_date = base_date + timedelta(days=i)
                sleep_records.append(
                    SleepRecord(
                        source_name="Test",
                        start_date=sleep_date.replace(hour=22, minute=0),
                        end_date=(sleep_date + timedelta(days=1)).replace(hour=6, minute=0),
                        state=SleepState.ASLEEP
                    )
                )
        
        # Configure pipeline with dual model strategy (which will detect XGBoost-only scenario)
        pipeline = MoodPredictionPipeline(
            config=PipelineConfig(
                use_seoul_features=True,
                window_selection_strategy=DualModelWindowStrategy()
            )
        )
        
        # Debug: check what we created
        print(f"Created {len(sleep_records)} sleep records")
        print(f"Date range: {min(r.start_date.date() for r in sleep_records)} to {max(r.start_date.date() for r in sleep_records)}")
        
        # Process data
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 1, 18)  # Mid January
        )
        
        # Debug: check what was returned
        print(f"Result metadata: {result.metadata}")
        print(f"Warnings: {result.warnings}")
        
        # NEW behavior: window predictions instead of daily
        assert hasattr(result, 'window_predictions'), "Should have window_predictions attribute"
        
        # Should have window predictions
        assert len(result.window_predictions) > 0, "Should have at least one window prediction"
        
        # Should NOT have daily predictions in XGBoost-only mode
        assert len(result.daily_predictions) == 0, "Should not have daily predictions in window mode"
        
        # Check window prediction structure
        for window_key, prediction in result.window_predictions.items():
            start_date, end_date = window_key
            assert isinstance(start_date, date)
            assert isinstance(end_date, date)
            assert start_date < end_date
            
            # Check prediction contents
            assert "depression_risk" in prediction
            assert "model" in prediction
            assert prediction["model"] == "xgboost"
            assert "window_coverage" in prediction
            assert "days_analyzed" in prediction
    
    def test_desired_window_prediction_structure(self):
        """Test the desired structure for window-level predictions."""
        # This is what we WANT the result to look like
        
        from big_mood_detector.domain.services.window_selection_strategy import (
            DateWindow,
        )
        
        window = DateWindow(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 30),
            days_count=30,
            data_quality=0.67  # 20 out of 30 days
        )
        
        # Desired result structure
        desired_result = {
            "window_predictions": {
                (window.start_date, window.end_date): {
                    "depression_risk": 0.036,
                    "hypomanic_risk": 0.003,
                    "manic_risk": 0.000,
                    "confidence": 0.5,
                    "model": "xgboost",
                    "window_coverage": window.data_quality,
                    "days_analyzed": window.days_count,
                    "feature_aggregation": "window_mean"  # How features were aggregated
                }
            },
            "daily_predictions": {},  # Empty for XGBoost-only mode
            "metadata": {
                "window_analysis": {
                    "optimal_window": window,
                    "can_run_pat": False,
                    "can_run_xgboost": True,
                    "pat_reason": "No 7 consecutive days found",
                    "xgboost_reason": None
                }
            }
        }
        
        # Verify structure
        assert "window_predictions" in desired_result
        assert len(desired_result["window_predictions"]) == 1
        
        # Get the single window prediction
        window_key = list(desired_result["window_predictions"].keys())[0]
        window_pred = desired_result["window_predictions"][window_key]
        
        # Verify it's a single prediction for the entire window
        assert window_pred["model"] == "xgboost"
        assert window_pred["days_analyzed"] == 30
        assert window_pred["window_coverage"] == 0.67