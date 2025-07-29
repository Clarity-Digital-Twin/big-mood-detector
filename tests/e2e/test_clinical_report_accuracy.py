"""
End-to-end tests for clinical report accuracy.

These tests verify the complete pipeline from data input to report generation
produces accurate, real predictions with correct dates.
"""

import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner

from big_mood_detector.application.services.clinical_report_formatter import (
    ClinicalReportFormatter,
)
from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.domain.entities.heart_rate_record import HeartRateRecord
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.interfaces.cli.main import cli


@pytest.mark.e2e
@pytest.mark.real_integration
class TestClinicalReportAccuracy:
    """Full pipeline tests with real data producing accurate reports."""
    
    @pytest.fixture
    def comprehensive_test_data(self):
        """Create comprehensive test data for 14 days."""
        base_date = date.today() - timedelta(days=21)
        sleep_records = []
        activity_records = []
        heart_records = []
        
        for day in range(14):
            current_date = base_date + timedelta(days=day)
            
            # Sleep: 10 PM to 6 AM with some variation
            sleep_duration = 8 + np.sin(day * 0.5) * 1  # 7-9 hours
            sleep_records.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) 
                              + timedelta(hours=22),
                    end_date=datetime.combine(current_date + timedelta(days=1), datetime.min.time()) 
                            + timedelta(hours=22 + sleep_duration - 24),
                    state=SleepState.ASLEEP,
                )
            )
            
            # Activity: Variable throughout day
            # Morning
            activity_records.append(
                ActivityRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=7),
                    end_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=8),
                    activity_type=ActivityType.STEP_COUNT,
                    value=1000 + day * 50,  # Increasing morning activity
                    unit="count",
                )
            )
            
            # Afternoon
            activity_records.append(
                ActivityRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=14),
                    end_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=15),
                    activity_type=ActivityType.STEP_COUNT,
                    value=2000 + np.sin(day * 0.3) * 500,
                    unit="count",
                )
            )
            
            # Evening
            activity_records.append(
                ActivityRecord(
                    source_name="Apple Watch",
                    start_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=18),
                    end_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=19),
                    activity_type=ActivityType.STEP_COUNT,
                    value=1500 - day * 30,  # Decreasing evening activity
                    unit="count",
                )
            )
            
            # Heart rate: Several measurements throughout day
            for hour in [7, 12, 15, 20]:
                hr_value = 70 + np.sin(day * 0.2 + hour * 0.1) * 10
                heart_records.append(
                    HeartRateRecord(
                        source_name="Apple Watch",
                        timestamp=datetime.combine(current_date, datetime.min.time()) 
                                 + timedelta(hours=hour),
                        value=hr_value,
                        unit="bpm",
                    )
                )
        
        return {
            "sleep": sleep_records,
            "activity": activity_records,
            "heart_rate": heart_records,
            "start_date": base_date,
            "end_date": base_date + timedelta(days=13),
        }
    
    def test_ensemble_report_shows_both_models(self, comprehensive_test_data):
        """When --ensemble used, report should show both PAT and XGBoost."""
        # Arrange
        config = PipelineConfig(
            include_pat_sequences=True,
            min_days_required=7,
        )
        pipeline = MoodPredictionPipeline(config=config)
        formatter = ClinicalReportFormatter()
        
        # Act
        result = pipeline.process_health_data(
            sleep_records=comprehensive_test_data["sleep"],
            activity_records=comprehensive_test_data["activity"],
            heart_records=comprehensive_test_data["heart_rate"],
            target_date=comprehensive_test_data["end_date"],
        )
        
        report = formatter.format(result)
        
        # Assert - This will FAIL until PAT is properly integrated
        assert "models: xgboost, pat" in report.lower() or \
               "models_used" in str(result.daily_predictions), \
               "Report should indicate both models were used"
        
        # Check that temporal assessment is present
        assert "TEMPORAL MOOD ASSESSMENT" in report, \
            "Should have temporal mood assessment section"
        assert "NOW" in report and "TOMORROW" in report, \
            "Should show current state and future risk"
    
    def test_temporal_predictions_different(self, comprehensive_test_data):
        """NOW and TOMORROW predictions should have different values."""
        # Arrange
        config = PipelineConfig(
            include_pat_sequences=True,
        )
        pipeline = MoodPredictionPipeline(config=config)
        
        # Act
        result = pipeline.process_health_data(
            sleep_records=comprehensive_test_data["sleep"],
            activity_records=comprehensive_test_data["activity"],
            heart_records=comprehensive_test_data["heart_rate"],
            target_date=comprehensive_test_data["end_date"],
        )
        
        # Assert - This will FAIL with hardcoded values
        temporal_values_found = False
        for date_key, prediction in result.daily_predictions.items():
            if "current_depression" in prediction and "depression_risk" in prediction:
                temporal_values_found = True
                current = prediction["current_depression"]
                future = prediction["depression_risk"]
                
                # Should be different values
                assert current != future, \
                    f"NOW ({current}) and TOMORROW ({future}) should be different"
                
                # Should not be hardcoded
                assert current not in [0.5, 0.56, 0.563], \
                    f"Current depression {current} appears to be hardcoded"
                assert future not in [0.044, 0.033, 0.034], \
                    f"Future risk {future} appears to be hardcoded"
        
        assert temporal_values_found, "Should have temporal predictions in results"
    
    def test_predictions_vary_across_days(self, comprehensive_test_data):
        """Predictions should vary day-to-day based on changing patterns."""
        config = PipelineConfig(
            include_pat_sequences=True,
        )
        pipeline = MoodPredictionPipeline(config=config)
        
        result = pipeline.process_health_data(
            sleep_records=comprehensive_test_data["sleep"],
            activity_records=comprehensive_test_data["activity"],
            heart_records=comprehensive_test_data["heart_rate"],
            target_date=comprehensive_test_data["end_date"],
        )
        
        # Collect all depression risk values
        depression_risks = []
        for prediction in result.daily_predictions.values():
            if "depression_risk" in prediction:
                depression_risks.append(prediction["depression_risk"])
        
        # Should have multiple days of predictions
        assert len(depression_risks) >= 7, "Should have at least 7 days of predictions"
        
        # Should not all be the same (indicates fake data)
        unique_risks = set(depression_risks)
        assert len(unique_risks) > 1, \
            f"All predictions are the same: {depression_risks[0]}, indicates fake data"
        
        # Check variance is reasonable
        if len(depression_risks) > 1:
            variance = np.var(depression_risks)
            assert variance > 0.0001, \
                f"Predictions have too little variance: {variance}, may be fake"
    
    def test_cli_ensemble_command_produces_report(self, comprehensive_test_data, tmp_path):
        """Test full CLI command with --ensemble flag."""
        # Create test XML file
        xml_content = self._create_test_xml(comprehensive_test_data)
        xml_file = tmp_path / "test_export.xml"
        xml_file.write_text(xml_content)
        
        runner = CliRunner()
        
        # Run CLI command
        result = runner.invoke(cli, [
            "predict",
            str(xml_file),
            "--ensemble",
            "--report",
            "--output", str(tmp_path),
        ])
        
        # This will FAIL if PAT not properly integrated
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        
        # Check report file created
        report_file = tmp_path / "clinical_report.txt"
        assert report_file.exists(), "Report file should be created"
        
        report_content = report_file.read_text()
        
        # Verify report content
        assert "CLINICAL DECISION SUPPORT (CDS) REPORT" in report_content
        assert "TEMPORAL MOOD ASSESSMENT" in report_content
        assert "NOW" in report_content and "TOMORROW" in report_content
        
        # Should not have repetitive warnings
        warning_count = report_content.count("PAT sequence unavailable")
        assert warning_count < 3, \
            f"Too many PAT warnings ({warning_count}), indicates PAT failing repeatedly"
    
    def test_report_dates_match_data_dates(self, comprehensive_test_data):
        """Report should show dates from actual data, not current date."""
        config = PipelineConfig()
        pipeline = MoodPredictionPipeline(config=config)
        formatter = ClinicalReportFormatter()
        
        # Process without specifying target_date
        result = pipeline.process_health_data(
            sleep_records=comprehensive_test_data["sleep"],
            activity_records=comprehensive_test_data["activity"],
            heart_records=comprehensive_test_data["heart_rate"],
            target_date=None,  # Should use data's max date
        )
        
        report = formatter.format(result)
        
        # Check that dates in report match data dates
        data_end = comprehensive_test_data["end_date"]
        
        # This will FAIL - currently uses today's date
        assert str(data_end) in report, \
            f"Report should contain actual data end date {data_end}"
        
        # Should not contain today's date (unless data is from today)
        if data_end != date.today():
            assert str(date.today()) not in report, \
                f"Report should not contain today's date {date.today()} when data is older"
    
    def _create_test_xml(self, test_data):
        """Create a minimal test XML file."""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<HealthData>\n'
        xml += f'  <ExportDate value="{datetime.now()}"/>\n'
        
        # Add sleep records
        for sleep in test_data["sleep"][:5]:  # Just a few for testing
            xml += f'  <Record type="SleepAnalysis" sourceName="{sleep.source_name}" '
            xml += f'startDate="{sleep.start_date}" endDate="{sleep.end_date}" '
            xml += f'value="HKCategoryValueSleepAnalysis{sleep.state.value}"/>\n'
        
        # Add activity records
        for activity in test_data["activity"][:5]:
            xml += f'  <Record type="StepCount" sourceName="{activity.source_name}" '
            xml += f'startDate="{activity.start_date}" endDate="{activity.end_date}" '
            xml += f'value="{activity.value}" unit="{activity.unit}"/>\n'
        
        xml += '</HealthData>'
        return xml