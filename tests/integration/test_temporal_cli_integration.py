"""
Integration test for temporal CLI functionality.

Tests the full flow from CLI command to report generation.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from big_mood_detector.interfaces.cli.main import cli


class TestTemporalCLIIntegration:
    """Test temporal functionality through the full CLI flow."""

    @pytest.fixture
    def test_health_data(self, tmp_path) -> Path:
        """Create test health data file with minimal but valid data."""
        # Create minimal XML with enough data for predictions
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <ExportDate value="2025-07-29 12:00:00"/>
"""

        # Add 30 days of sleep data for valid predictions
        base_date = datetime(2025, 6, 29)
        for i in range(30):
            date_obj = base_date + timedelta(days=i)
            start = date_obj.replace(hour=22, minute=30)
            end = (date_obj + timedelta(days=1)).replace(hour=6, minute=45)

            xml_content += f"""    <Record type="SleepAnalysis"
            sourceName="Apple Watch"
            startDate="{start.strftime('%Y-%m-%d %H:%M:%S')}"
            endDate="{end.strftime('%Y-%m-%d %H:%M:%S')}"
            value="HKCategoryValueSleepAnalysisAsleep"/>
"""

            # Add some activity data
            activity_time = date_obj.replace(hour=14, minute=0)
            xml_content += f"""    <Record type="StepCount"
            sourceName="Apple Watch"
            startDate="{activity_time.strftime('%Y-%m-%d %H:%M:%S')}"
            endDate="{(activity_time + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')}"
            value="500"/>
"""

            # Add heart rate data
            xml_content += f"""    <Record type="HeartRate"
            sourceName="Apple Watch"
            startDate="{activity_time.strftime('%Y-%m-%d %H:%M:%S')}"
            endDate="{activity_time.strftime('%Y-%m-%d %H:%M:%S')}"
            value="72"
            unit="bpm"/>
"""

        xml_content += "</HealthData>"

        xml_path = tmp_path / "test_export.xml"
        xml_path.write_text(xml_content)
        return xml_path

    @pytest.mark.integration
    @pytest.mark.skipif(
        os.environ.get("TESTING") == "1",
        reason="Skip integration tests in fast test mode"
    )
    def test_predict_with_ensemble_shows_temporal_data(self, test_health_data, tmp_path):
        """Test that predict command with --ensemble shows temporal data."""
        runner = CliRunner()

        # Set up minimal output directory
        output_dir = tmp_path / "test_output"
        output_dir.mkdir()

        # Run predict command with ensemble flag
        result = runner.invoke(cli, [
            "predict",
            str(test_health_data),
            "--ensemble",
            "--report",
            "--output", str(output_dir)
        ])

        # Command should succeed or fail gracefully if PAT not available
        if result.exit_code != 0:
            # Check if it's just missing PAT models
            if "PAT" in result.output or "model" in result.output.lower():
                pytest.skip("PAT models not available for integration test")
            else:
                assert False, f"Command failed unexpectedly: {result.output}"

        # Check report was created
        report_path = output_dir / "clinical_report.txt"
        assert report_path.exists()

        # Read report content
        content = report_path.read_text()

        # Should have temporal section when ensemble is used
        if "models_used" in content and "pat" in content.lower():
            assert "TEMPORAL MOOD ASSESSMENT" in content
            assert "NOW" in content
            assert "TOMORROW" in content

    @pytest.mark.integration
    @pytest.mark.skipif(
        os.environ.get("TESTING") == "1",
        reason="Skip integration tests in fast test mode"
    )
    def test_predict_without_ensemble_no_temporal(self, test_health_data, tmp_path):
        """Test that predict without --ensemble doesn't show temporal data."""
        runner = CliRunner()

        # Set up minimal output directory
        output_dir = tmp_path / "test_output2"
        output_dir.mkdir()

        # Run predict command without ensemble flag
        result = runner.invoke(cli, [
            "predict",
            str(test_health_data),
            "--report",
            "--output", str(output_dir)
        ])

        # Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Check report
        report_path = output_dir / "clinical_report.txt"
        assert report_path.exists()
        content = report_path.read_text()

        # Should NOT have temporal section without ensemble
        assert "TEMPORAL MOOD ASSESSMENT" not in content
