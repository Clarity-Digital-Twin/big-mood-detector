"""Integration test for window-based report generation."""

import pytest
from datetime import date, datetime, timedelta
from pathlib import Path
import tempfile
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.domain.services.dual_model_window_strategy import DualModelWindowStrategy
from big_mood_detector.interfaces.cli.commands import generate_clinical_report


class TestWindowReportGeneration:
    def test_window_prediction_appears_in_report(self, tmp_path):
        """Test that window predictions are properly formatted in the report."""
        # Create sparse sleep data
        sleep_records = []
        base_date = datetime(2024, 12, 15)
        for i in range(35):
            if i % 3 != 2:  # Skip every 3rd day for sparsity
                sleep_date = base_date + timedelta(days=i)
                sleep_records.append(
                    SleepRecord(
                        source_name="Test",
                        start_date=sleep_date.replace(hour=22, minute=0),
                        end_date=(sleep_date + timedelta(days=1)).replace(hour=6, minute=0),
                        state=SleepState.ASLEEP
                    )
                )
        
        # Process with window strategy
        pipeline = MoodPredictionPipeline(
            config=PipelineConfig(
                use_seoul_features=True,
                window_selection_strategy=DualModelWindowStrategy()
            )
        )
        
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 1, 18)
        )
        
        # Generate report
        report_path = tmp_path / "test_report.txt"
        generate_clinical_report(result, report_path)
        
        # Read and verify report content
        report_content = report_path.read_text()
        
        # Check for window selection section
        assert "DATA WINDOW SELECTION" in report_content
        assert "Window Period:" in report_content
        assert "Data Coverage:" in report_content
        assert "Models Available: XGBoost only" in report_content
        
        # Check for window-level analysis section
        if result.window_predictions:
            assert "WINDOW-LEVEL ANALYSIS" in report_content
            assert "Period:" in report_content
            assert "Model: XGBOOST" in report_content
            assert "Depression Risk:" in report_content
            
        # Should NOT have daily analysis when in window mode
        if not result.daily_predictions:
            assert "DETAILED DAILY ANALYSIS" not in report_content
        
        print("\n=== GENERATED REPORT ===")
        print(report_content)
        print("========================")