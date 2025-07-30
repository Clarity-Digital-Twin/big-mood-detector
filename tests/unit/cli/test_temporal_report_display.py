"""
Test temporal report display functionality.

Following TDD principles - these tests define the behavior we want.
"""

from datetime import date

import pytest

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineResult,
)
from big_mood_detector.interfaces.cli.commands import generate_clinical_report


class TestTemporalReportDisplay:
    """Test that temporal data is properly displayed in clinical reports."""

    @pytest.fixture
    def pipeline_result_with_temporal(self) -> PipelineResult:
        """Create a pipeline result with temporal assessment data."""
        return PipelineResult(
            daily_predictions={
                date(2025, 7, 29): {
                    "depression_risk": 0.42,  # XGBoost (TOMORROW)
                    "hypomanic_risk": 0.08,
                    "manic_risk": 0.05,
                    "confidence": 0.91,
                    "models_used": ["xgboost", "pat"],
                    # Temporal data that's currently ignored
                    "current_depression": 0.65,  # PAT (NOW)
                    "temporal_concordance": 0.77,
                    "confidence_scores": {
                        "xgboost": 0.91,
                        "pat": 0.82
                    }
                },
                date(2025, 7, 28): {
                    "depression_risk": 0.38,
                    "hypomanic_risk": 0.06,
                    "manic_risk": 0.04,
                    "confidence": 0.89,
                    "models_used": ["xgboost", "pat"],
                    "current_depression": 0.71,
                    "temporal_concordance": 0.67,
                }
            },
            overall_summary={
                "avg_depression_risk": 0.40,
                "avg_hypomanic_risk": 0.07,
                "avg_manic_risk": 0.045,
                "avg_confidence": 0.90,
                # These should be calculated and shown
                "avg_current_depression": 0.68,
                "avg_temporal_concordance": 0.72,
            },
            records_processed=1000,
            confidence_score=0.90,
            warnings=[],
            metadata={
                "ensemble_used": True,
                "pat_available": True,
            },
            processing_time_seconds=1.5
        )

    def test_temporal_section_appears_in_report(self, pipeline_result_with_temporal, tmp_path):
        """Report should have a dedicated temporal assessment section."""
        report_path = tmp_path / "report.txt"
        generate_clinical_report(pipeline_result_with_temporal, report_path)

        content = report_path.read_text()

        # Should have temporal section
        assert "TEMPORAL MOOD ASSESSMENT" in content
        assert "NOW vs TOMORROW" in content

    def test_temporal_section_shows_current_state(self, pipeline_result_with_temporal, tmp_path):
        """Temporal section should clearly show NOW (PAT) assessment."""
        report_path = tmp_path / "report.txt"
        generate_clinical_report(pipeline_result_with_temporal, report_path)

        content = report_path.read_text()

        # Should show current state
        assert "NOW (Current State - PAT):" in content
        assert "65.0%" in content or "65%" in content  # Current depression

    def test_temporal_section_shows_future_risk(self, pipeline_result_with_temporal, tmp_path):
        """Temporal section should clearly show TOMORROW (XGBoost) prediction."""
        report_path = tmp_path / "report.txt"
        generate_clinical_report(pipeline_result_with_temporal, report_path)

        content = report_path.read_text()

        # Should show future risk
        assert "TOMORROW (Future Risk - XGBoost):" in content
        assert "42.0%" in content or "42%" in content  # Future depression risk

    def test_temporal_concordance_displayed(self, pipeline_result_with_temporal, tmp_path):
        """Report should show temporal concordance metric."""
        report_path = tmp_path / "report.txt"
        generate_clinical_report(pipeline_result_with_temporal, report_path)

        content = report_path.read_text()

        # Should show concordance
        assert "Temporal Concordance:" in content
        assert "77.0%" in content or "77%" in content

    def test_temporal_pattern_interpretation(self, pipeline_result_with_temporal, tmp_path):
        """Report should interpret the temporal pattern."""
        report_path = tmp_path / "report.txt"
        generate_clinical_report(pipeline_result_with_temporal, report_path)

        content = report_path.read_text()

        # Should have pattern interpretation
        assert "Pattern:" in content
        # With 65% NOW and 42% TOMORROW, this is improving
        assert "Improving" in content or "improving" in content

    def test_daily_predictions_show_temporal_data(self, pipeline_result_with_temporal, tmp_path):
        """Daily predictions should show both NOW and TOMORROW."""
        report_path = tmp_path / "report.txt"
        generate_clinical_report(pipeline_result_with_temporal, report_path)

        content = report_path.read_text()

        # Find daily section
        daily_section_start = content.find("DETAILED DAILY ANALYSIS")
        assert daily_section_start > 0

        daily_content = content[daily_section_start:]

        # Should show temporal data for each day
        assert "NOW:" in daily_content or "Current State:" in daily_content
        assert "TOMORROW:" in daily_content or "Future Risk:" in daily_content

    def test_overall_summary_includes_temporal_averages(self, pipeline_result_with_temporal, tmp_path):
        """Overall summary should include average temporal metrics."""
        report_path = tmp_path / "report.txt"
        generate_clinical_report(pipeline_result_with_temporal, report_path)

        content = report_path.read_text()

        # Should show average current state
        assert "Average Current State:" in content or "Avg Current Depression:" in content
        assert "68" in content  # 68% average

        # Should show average concordance
        assert "Average Concordance:" in content or "Avg Temporal Concordance:" in content
        assert "72" in content  # 72% average

    def test_no_temporal_section_without_temporal_data(self, tmp_path):
        """Temporal section should not appear if no temporal data available."""
        # Create result without temporal data
        result = PipelineResult(
            daily_predictions={
                date(2025, 7, 29): {
                    "depression_risk": 0.42,
                    "hypomanic_risk": 0.08,
                    "manic_risk": 0.05,
                    "confidence": 0.91,
                    # No temporal fields
                }
            },
            overall_summary={
                "avg_depression_risk": 0.42,
                "avg_hypomanic_risk": 0.08,
                "avg_manic_risk": 0.05,
                "avg_confidence": 0.91,
            },
            records_processed=1000,
            confidence_score=0.91,
            warnings=[],
            metadata={},
            processing_time_seconds=1.2
        )

        report_path = tmp_path / "report.txt"
        generate_clinical_report(result, report_path)

        content = report_path.read_text()

        # Should NOT have temporal section
        assert "TEMPORAL MOOD ASSESSMENT" not in content
        assert "NOW vs TOMORROW" not in content

    def test_temporal_clinical_recommendations(self, tmp_path):
        """Temporal patterns should generate appropriate clinical recommendations."""
        # Test improving pattern
        improving_result = PipelineResult(
            daily_predictions={
                date(2025, 7, 29): {
                    "depression_risk": 0.25,  # Low tomorrow
                    "hypomanic_risk": 0.05,
                    "manic_risk": 0.02,
                    "confidence": 0.92,
                    "models_used": ["xgboost", "pat"],
                    "current_depression": 0.75,  # High now
                    "temporal_concordance": 0.50,
                }
            },
            overall_summary={
                "avg_depression_risk": 0.25,
                "avg_current_depression": 0.75,
            },
            records_processed=1000,
            confidence_score=0.92,
            warnings=[],
            metadata={"ensemble_used": True},
            processing_time_seconds=1.3
        )

        report_path = tmp_path / "improving.txt"
        generate_clinical_report(improving_result, report_path)

        content = report_path.read_text()

        # Should recognize improving pattern
        assert "Improving" in content or "improving" in content
        assert "Crisis resolving" in content or "improvement" in content

    def test_format_handles_missing_pat_gracefully(self, tmp_path):
        """Report should handle missing PAT data gracefully."""
        result = PipelineResult(
            daily_predictions={
                date(2025, 7, 29): {
                    "depression_risk": 0.42,
                    "hypomanic_risk": 0.08,
                    "manic_risk": 0.05,
                    "confidence": 0.91,
                    "models_used": ["xgboost"],  # No PAT
                    # Temporal fields might be None or missing
                    "current_depression": None,
                    "temporal_concordance": None,
                }
            },
            overall_summary={
                "avg_depression_risk": 0.42,
            },
            records_processed=1000,
            confidence_score=0.91,
            warnings=["PAT model unavailable"],
            metadata={"ensemble_used": True, "pat_available": False},
            processing_time_seconds=1.4
        )

        report_path = tmp_path / "report.txt"
        generate_clinical_report(result, report_path)

        content = report_path.read_text()

        # Should indicate PAT unavailable
        assert "PAT unavailable" in content or "PAT model unavailable" in content
        # Should still show XGBoost predictions
        assert "42" in content
