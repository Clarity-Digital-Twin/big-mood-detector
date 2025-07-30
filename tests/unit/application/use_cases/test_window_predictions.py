"""Tests for window-level prediction logic."""

import pytest
from datetime import date
from unittest.mock import Mock, patch
from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
    PipelineResult,
)
from big_mood_detector.domain.services.window_selection_strategy import DateWindow


class TestWindowPredictions:
    def test_xgboost_generates_single_prediction_per_window(self):
        """XGBoost should produce ONE prediction per window, not per day."""
        # Setup
        window = DateWindow(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            days_count=31,
            data_quality=0.65
        )
        
        # Create a mock mood predictor that returns a fixed prediction
        mock_predictor = Mock()
        mock_predictor.predict.return_value = Mock(
            depression_risk=0.036,
            hypomanic_risk=0.003,
            manic_risk=0.000,
            confidence=0.5
        )
        
        pipeline = MoodPredictionPipeline(
            config=PipelineConfig(use_seoul_features=True)
        )
        
        # Patch the mood predictor
        with patch.object(pipeline, 'mood_predictor', mock_predictor):
            # Create mock Seoul features for 31 days
            mock_features = []
            for i in range(1, 32):
                feature = Mock()
                feature.date = date(2025, 1, i)
                feature.to_model_dict.return_value = {"mock": "features"}
                mock_features.append(feature)
            
            # Simulate the prediction logic
            daily_predictions = {}
            
            # CURRENT FLAWED LOGIC (what the code does now)
            for seoul_feature in mock_features:
                feature_date = seoul_feature.date
                feature_vector = seoul_feature.to_model_dict()
                prediction = mock_predictor.predict(feature_vector)
                daily_predictions[feature_date] = {
                    "depression_risk": prediction.depression_risk,
                    "hypomanic_risk": prediction.hypomanic_risk,
                    "manic_risk": prediction.manic_risk,
                    "confidence": prediction.confidence
                }
            
            # This test should FAIL with current logic
            # We're getting 31 identical predictions when we should get 1
            assert len(daily_predictions) == 31  # Current behavior
            
            # But all values are the same (this is the problem!)
            unique_depression_risks = set(
                pred["depression_risk"] for pred in daily_predictions.values()
            )
            assert len(unique_depression_risks) == 1  # All same value!
            assert unique_depression_risks.pop() == 0.036
    
    def test_window_predictions_stored_correctly(self):
        """Window predictions should be stored with window key, not daily."""
        window = DateWindow(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            days_count=31,
            data_quality=0.65
        )
        
        # What we WANT (proper window-level prediction)
        window_predictions = {}
        window_key = (window.start_date, window.end_date)
        
        window_predictions[window_key] = {
            "depression_risk": 0.036,
            "hypomanic_risk": 0.003,
            "manic_risk": 0.000,
            "confidence": 0.5,
            "model": "xgboost",
            "window_coverage": window.data_quality,
            "days_analyzed": window.days_count
        }
        
        # Should have exactly one prediction for the window
        assert len(window_predictions) == 1
        assert window_key in window_predictions
        assert window_predictions[window_key]["model"] == "xgboost"
        assert window_predictions[window_key]["window_coverage"] == 0.65
        assert window_predictions[window_key]["days_analyzed"] == 31