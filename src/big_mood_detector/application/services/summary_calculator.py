"""Helper service for calculating overall summary from predictions."""

from datetime import date
from typing import Any

import numpy as np


class SummaryCalculator:
    """Calculates overall summary from daily or window predictions."""
    
    @staticmethod
    def calculate_from_daily_predictions(
        daily_predictions: dict[date, dict[str, Any]]
    ) -> tuple[dict[str, Any], float]:
        """Calculate overall summary from daily predictions.
        
        Args:
            daily_predictions: Dictionary of daily predictions
            
        Returns:
            Tuple of (overall_summary, confidence_score)
        """
        if not daily_predictions:
            return {}, 0.0
            
        all_predictions = list(daily_predictions.values())
        
        overall_summary = {
            "avg_depression_risk": float(
                np.mean([float(p["depression_risk"]) for p in all_predictions])
            ),
            "avg_hypomanic_risk": float(
                np.mean([float(p["hypomanic_risk"]) for p in all_predictions])
            ),
            "avg_manic_risk": float(
                np.mean([float(p["manic_risk"]) for p in all_predictions])
            ),
            "days_analyzed": len(daily_predictions),
        }
        
        confidence_score = float(
            np.mean([float(p["confidence"]) for p in all_predictions])
        )
        
        if np.isnan(confidence_score):
            confidence_score = 0.0
            
        return overall_summary, confidence_score
    
    @staticmethod
    def calculate_from_window_predictions(
        window_predictions: dict[tuple[date, date], dict[str, Any]]
    ) -> tuple[dict[str, Any], float]:
        """Calculate overall summary from window predictions.
        
        Args:
            window_predictions: Dictionary of window predictions
            
        Returns:
            Tuple of (overall_summary, confidence_score)
        """
        if not window_predictions:
            return {}, 0.0
            
        # Use the first (and likely only) window prediction for summary
        for window_key, pred in window_predictions.items():
            overall_summary = {
                "depression_risk": pred["depression_risk"],
                "hypomanic_risk": pred["hypomanic_risk"],
                "manic_risk": pred["manic_risk"],
                "window_analyzed": f"{window_key[0]} to {window_key[1]}",
                "analysis_type": "window",
                "model": pred.get("model", "unknown")
            }
            confidence_score = pred.get("confidence", 0.5)
            return overall_summary, confidence_score
            
        return {}, 0.0
    
    @staticmethod
    def adjust_confidence_for_warnings(
        confidence_score: float, 
        has_warnings: bool
    ) -> float:
        """Adjust confidence based on data quality warnings.
        
        Args:
            confidence_score: Original confidence score
            has_warnings: Whether there are data quality warnings
            
        Returns:
            Adjusted confidence score
        """
        if has_warnings:
            return float(confidence_score * 0.7)
        return confidence_score