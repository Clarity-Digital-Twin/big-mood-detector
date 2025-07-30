"""Tests for the summary calculator service."""

from datetime import date

import numpy as np
import pytest

from big_mood_detector.application.services.summary_calculator import SummaryCalculator


class TestSummaryCalculator:
    """Test cases for SummaryCalculator."""
    
    def test_calculate_from_daily_predictions_empty(self):
        """Empty predictions should return empty summary."""
        summary, confidence = SummaryCalculator.calculate_from_daily_predictions({})
        assert summary == {}
        assert confidence == 0.0
    
    def test_calculate_from_daily_predictions_single_day(self):
        """Single day prediction should calculate correctly."""
        predictions = {
            date(2025, 1, 1): {
                "depression_risk": 0.8,
                "hypomanic_risk": 0.2,
                "manic_risk": 0.1,
                "confidence": 0.9
            }
        }
        
        summary, confidence = SummaryCalculator.calculate_from_daily_predictions(predictions)
        
        assert summary["avg_depression_risk"] == 0.8
        assert summary["avg_hypomanic_risk"] == 0.2
        assert summary["avg_manic_risk"] == 0.1
        assert summary["days_analyzed"] == 1
        assert confidence == 0.9
    
    def test_calculate_from_daily_predictions_multiple_days(self):
        """Multiple day predictions should average correctly."""
        predictions = {
            date(2025, 1, 1): {
                "depression_risk": 0.8,
                "hypomanic_risk": 0.2,
                "manic_risk": 0.1,
                "confidence": 0.9
            },
            date(2025, 1, 2): {
                "depression_risk": 0.6,
                "hypomanic_risk": 0.3,
                "manic_risk": 0.2,
                "confidence": 0.8
            }
        }
        
        summary, confidence = SummaryCalculator.calculate_from_daily_predictions(predictions)
        
        assert summary["avg_depression_risk"] == pytest.approx(0.7)
        assert summary["avg_hypomanic_risk"] == pytest.approx(0.25)
        assert summary["avg_manic_risk"] == pytest.approx(0.15)
        assert summary["days_analyzed"] == 2
        assert confidence == pytest.approx(0.85)
    
    def test_calculate_from_window_predictions_empty(self):
        """Empty window predictions should return empty summary."""
        summary, confidence = SummaryCalculator.calculate_from_window_predictions({})
        assert summary == {}
        assert confidence == 0.0
    
    def test_calculate_from_window_predictions_single_window(self):
        """Single window prediction should be used directly."""
        predictions = {
            (date(2025, 1, 1), date(2025, 1, 7)): {
                "depression_risk": 0.7,
                "hypomanic_risk": 0.3,
                "manic_risk": 0.15,
                "confidence": 0.85,
                "model": "xgboost"
            }
        }
        
        summary, confidence = SummaryCalculator.calculate_from_window_predictions(predictions)
        
        assert summary["depression_risk"] == 0.7
        assert summary["hypomanic_risk"] == 0.3
        assert summary["manic_risk"] == 0.15
        assert summary["window_analyzed"] == "2025-01-01 to 2025-01-07"
        assert summary["analysis_type"] == "window"
        assert summary["model"] == "xgboost"
        assert confidence == 0.85
    
    def test_calculate_from_window_predictions_missing_confidence(self):
        """Missing confidence should default to 0.5."""
        predictions = {
            (date(2025, 1, 1), date(2025, 1, 7)): {
                "depression_risk": 0.7,
                "hypomanic_risk": 0.3,
                "manic_risk": 0.15,
            }
        }
        
        summary, confidence = SummaryCalculator.calculate_from_window_predictions(predictions)
        assert confidence == 0.5
    
    def test_adjust_confidence_with_warnings(self):
        """Confidence should be reduced with warnings."""
        original_confidence = 0.9
        adjusted = SummaryCalculator.adjust_confidence_for_warnings(
            original_confidence, has_warnings=True
        )
        assert adjusted == pytest.approx(0.63)  # 0.9 * 0.7
    
    def test_adjust_confidence_without_warnings(self):
        """Confidence should remain unchanged without warnings."""
        original_confidence = 0.9
        adjusted = SummaryCalculator.adjust_confidence_for_warnings(
            original_confidence, has_warnings=False
        )
        assert adjusted == 0.9
    
    def test_nan_confidence_handling(self):
        """NaN confidence should be converted to 0.0."""
        predictions = {
            date(2025, 1, 1): {
                "depression_risk": 0.8,
                "hypomanic_risk": 0.2,
                "manic_risk": 0.1,
                "confidence": float('nan')
            }
        }
        
        summary, confidence = SummaryCalculator.calculate_from_daily_predictions(predictions)
        assert confidence == 0.0