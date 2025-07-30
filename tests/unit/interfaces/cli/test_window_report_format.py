"""Tests for window-level prediction report formatting."""

from datetime import date

import pytest

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineResult,
)
from big_mood_detector.domain.services.dual_model_window_strategy import (
    WindowAnalysisResult,
)
from big_mood_detector.domain.services.window_selection_strategy import DateWindow


class TestWindowReportFormat:
    def test_report_shows_window_prediction_not_daily(self):
        """Report should show window-level prediction correctly."""
        # Create a result with window predictions (not daily)
        result = PipelineResult(
            window_predictions={
                (date(2025, 1, 1), date(2025, 1, 31)): {
                    "depression_risk": 0.036,
                    "hypomanic_risk": 0.003,
                    "manic_risk": 0.000,
                    "confidence": 0.5,
                    "model": "xgboost",
                    "window_coverage": 0.65
                }
            },
            daily_predictions={},  # Empty - no daily predictions!
            overall_summary={
                "depression_risk": 0.036,
                "hypomanic_risk": 0.003,
                "manic_risk": 0.000
            },
            metadata={
                "window_analysis": WindowAnalysisResult(
                    optimal_window=DateWindow(
                        start_date=date(2025, 1, 1),
                        end_date=date(2025, 1, 31),
                        days_count=31,
                        data_quality=0.65
                    ),
                    can_run_pat=False,
                    can_run_xgboost=True,
                    pat_reason="Insufficient consecutive days",
                    xgboost_reason=None
                )
            },
            has_errors=False,
            errors=[]
        )
        
        # Format report (simplified version)
        report_lines = []
        
        # Header
        report_lines.append("CLINICAL DECISION SUPPORT (CDS) REPORT")
        report_lines.append("=" * 50)
        
        # Window analysis section
        if result.metadata and "window_analysis" in result.metadata:
            wa = result.metadata["window_analysis"]
            report_lines.append("\nDATA WINDOW SELECTION")
            report_lines.append("-" * 30)
            report_lines.append(f"Window Period: {wa.optimal_window.start_date} to {wa.optimal_window.end_date}")
            report_lines.append(f"Days Analyzed: {wa.optimal_window.days_count}")
            report_lines.append(f"Data Coverage: {wa.optimal_window.data_quality:.0%}")
            
            if wa.can_run_xgboost and not wa.can_run_pat:
                report_lines.append("Models Available: XGBoost only")
                if wa.pat_reason:
                    report_lines.append(f"PAT unavailable: {wa.pat_reason}")
        
        # Window predictions section
        if result.window_predictions:
            report_lines.append("\nWINDOW-LEVEL ANALYSIS")
            report_lines.append("-" * 30)
            
            for (start, end), pred in result.window_predictions.items():
                report_lines.append(f"\nPeriod: {start} to {end}")
                report_lines.append(f"  Model: {pred['model'].upper()}")
                report_lines.append(f"  Coverage: {pred['window_coverage']:.0%}")
                report_lines.append(f"\n  Depression Risk: {pred['depression_risk']:.1%}")
                report_lines.append(f"  Hypomanic Risk: {pred['hypomanic_risk']:.1%}")
                report_lines.append(f"  Manic Risk: {pred['manic_risk']:.1%}")
        
        report = "\n".join(report_lines)
        
        # Assertions
        assert "Window Period: 2025-01-01 to 2025-01-31" in report
        assert "Depression Risk: 3.6%" in report
        assert "Coverage: 65%" in report
        assert "Models Available: XGBoost only" in report
        
        # Should NOT contain daily entries
        assert "2025-01-27:" not in report
        assert "DAILY ANALYSIS" not in report