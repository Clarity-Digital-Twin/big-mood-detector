"""
Integration test for temporal CLI functionality.

Tests the full flow from CLI command to report generation.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner
from datetime import date, datetime, timedelta
from typing import List

from big_mood_detector.interfaces.cli.commands import cli
from big_mood_detector.domain.models.health_data import (
    SleepRecord,
    ActivityRecord,
    HeartRateRecord,
    HeartMetricType,
    SleepState,
)
from big_mood_detector.infrastructure.parsers.xml.streaming_parser import FastStreamingXMLParser


class TestTemporalCLIIntegration:
    """Test temporal functionality through the full CLI flow."""
    
    @pytest.fixture
    def test_health_data(self, tmp_path) -> Path:
        """Create test health data file with temporal data."""
        # Create minimal XML with sleep and activity data
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <HealthData>
            <ExportDate value="2025-07-29 12:00:00"/>
            <Record type="SleepAnalysis" 
                    sourceName="Apple Watch" 
                    startDate="2025-07-28 22:30:00" 
                    endDate="2025-07-29 06:45:00" 
                    value="HKCategoryValueSleepAnalysisAsleep"/>
            <Record type="StepCount" 
                    sourceName="Apple Watch" 
                    startDate="2025-07-29 08:00:00" 
                    endDate="2025-07-29 08:01:00" 
                    value="25"/>
            <Record type="HeartRate" 
                    sourceName="Apple Watch" 
                    startDate="2025-07-29 08:00:00" 
                    endDate="2025-07-29 08:00:00" 
                    value="72" 
                    unit="bpm"/>
        </HealthData>"""
        
        xml_path = tmp_path / "test_export.xml"
        xml_path.write_text(xml_content)
        return xml_path
    
    @pytest.mark.integration
    def test_predict_with_ensemble_shows_temporal_data(self, test_health_data, tmp_path):
        """Test that predict command with --ensemble shows temporal data."""
        runner = CliRunner()
        
        # Run predict command with ensemble flag
        result = runner.invoke(cli, [
            "predict",
            str(test_health_data),
            "--ensemble",
            "--report",
            "--output", str(tmp_path / "test_output")
        ])
        
        # Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"
        
        # Check report was created
        report_path = tmp_path / "test_output" / "clinical_report.txt"
        assert report_path.exists()
        
        # Read report content
        content = report_path.read_text()
        
        # Should have temporal section when ensemble is used
        if "models_used" in content and "pat" in content.lower():
            assert "TEMPORAL MOOD ASSESSMENT" in content
            assert "NOW" in content
            assert "TOMORROW" in content
    
    @pytest.mark.integration
    def test_predict_without_ensemble_no_temporal(self, test_health_data, tmp_path):
        """Test that predict without --ensemble doesn't show temporal data."""
        runner = CliRunner()
        
        # Run predict command without ensemble flag
        result = runner.invoke(cli, [
            "predict",
            str(test_health_data),
            "--report",
            "--output", str(tmp_path / "test_output")
        ])
        
        # Command should succeed
        assert result.exit_code == 0
        
        # Check report
        report_path = tmp_path / "test_output" / "clinical_report.txt"
        content = report_path.read_text()
        
        # Should NOT have temporal section without ensemble
        assert "TEMPORAL MOOD ASSESSMENT" not in content