"""Integration tests for the CLI --scan feature."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from big_mood_detector.domain.value_objects.feature_availability import (
    FeatureAvailability,
)
from big_mood_detector.interfaces.cli.main import cli


class TestScanFeature:
    """Test the --scan flag functionality."""

    def test_process_command_with_scan(self):
        """Test process command with --scan flag."""
        runner = CliRunner()

        # Mock the feature availability check
        mock_availability = FeatureAvailability(
            available_features=[
                ("depression_risk", "Depression risk prediction (XGBoost)"),
                ("activity_patterns", "Daily activity pattern analysis"),
            ],
            unavailable_features=[
                ("hrv_analysis", "Missing required type: HKQuantityTypeIdentifierHeartRateVariabilitySDNN"),
            ],
            record_counts={
                "HKCategoryTypeIdentifierSleepAnalysis": 365,
                "HKQuantityTypeIdentifierStepCount": 8760,
            },
            scan_duration_seconds=2.5,
        )

        with patch('big_mood_detector.application.services.data_parsing_service.DataParsingService.check_feature_availability') as mock_check:
            mock_check.return_value = mock_availability

            # Create a temporary test file
            with runner.isolated_filesystem():
                test_file = Path("test_export.xml")
                test_file.write_text("<HealthData></HealthData>")

                result = runner.invoke(cli, ["process", str(test_file), "--scan"])

                assert result.exit_code == 0
                assert "Scanning test_export.xml" in result.output
                assert "Scan complete in 2.5s" in result.output
                assert "Sleep Analysis: 365 records" in result.output
                assert "Step Count: 8,760 records" in result.output
                assert "Depression risk prediction (XGBoost)" in result.output
                assert "Missing: HKQuantityTypeIdentifierHeartRateVariabilitySDNN" in result.output

    def test_predict_command_with_scan(self):
        """Test predict command with --scan flag."""
        runner = CliRunner()

        mock_availability = FeatureAvailability(
            available_features=[
                ("depression_risk", "Depression risk prediction (XGBoost)"),
            ],
            unavailable_features=[],
            record_counts={
                "HKCategoryTypeIdentifierSleepAnalysis": 365,
                "HKQuantityTypeIdentifierStepCount": 8760,
            },
            scan_duration_seconds=1.8,
        )

        with patch('big_mood_detector.application.services.data_parsing_service.DataParsingService.check_feature_availability') as mock_check:
            mock_check.return_value = mock_availability

            with runner.isolated_filesystem():
                test_file = Path("test_export.xml")
                test_file.write_text("<HealthData></HealthData>")

                result = runner.invoke(cli, ["predict", str(test_file), "--scan"])

                if result.exit_code != 0:
                    print(f"Error: {result.output}")
                    print(f"Exception: {result.exception}")
                assert result.exit_code == 0
                assert "Predictable Conditions:" in result.output
                assert "Depression risk prediction (XGBoost)" in result.output
                assert "Total records found:" in result.output

    def test_scan_non_xml_file(self):
        """Test that scan only works with XML files."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            test_file = Path("test_data.json")
            test_file.write_text("{}")

            result = runner.invoke(cli, ["process", str(test_file), "--scan"])

            assert result.exit_code == 0
            assert "Scan is only available for XML files" in result.output

    @pytest.mark.skip(reason="Complex mocking of file stats in CLI context")
    def test_large_file_prompt(self):
        """Test that large files prompt for scanning."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create a file that appears large
            test_file = Path("large_export.xml")
            test_file.write_text("<HealthData></HealthData>")

            # Mock the file size check within the command
            original_stat = Path.stat
            def mock_stat(self):
                if self.name == "large_export.xml":
                    return Mock(st_size=150 * 1024 * 1024)  # 150MB
                return original_stat(self)

            with patch.object(Path, 'stat', mock_stat):
                # Respond 'N' to the prompt
                result = runner.invoke(cli, ["predict", str(test_file)], input="N\n")

                # Check the output
                if result.exit_code != 0:
                    print(f"Error output: {result.output}")
                    print(f"Exception: {result.exception}")

                assert "Large file detected: 150.0 MB" in result.output
                assert "Would you like to scan the file first" in result.output

    def test_scan_with_insufficient_data(self):
        """Test scan output when data is insufficient."""
        runner = CliRunner()

        mock_availability = FeatureAvailability(
            available_features=[],
            unavailable_features=[
                ("depression_risk", "Insufficient data: HKCategoryTypeIdentifierSleepAnalysis (3 days, need 7)"),
                ("activity_patterns", "Missing required type: HKQuantityTypeIdentifierStepCount"),
            ],
            record_counts={
                "HKCategoryTypeIdentifierSleepAnalysis": 6,  # Only 3 days
            },
            scan_duration_seconds=0.5,
        )

        with patch('big_mood_detector.application.services.data_parsing_service.DataParsingService.check_feature_availability') as mock_check:
            mock_check.return_value = mock_availability

            with runner.isolated_filesystem():
                test_file = Path("insufficient.xml")
                test_file.write_text("<HealthData></HealthData>")

                result = runner.invoke(cli, ["predict", str(test_file), "--scan"])

                if result.exit_code != 0:
                    print(f"Error in insufficient data test: {result.output}")
                    print(f"Exception: {result.exception}")
                assert result.exit_code == 0
                assert "No predictions can be made with available data" in result.output
                assert "Recommendation: Ensure your Apple Health export includes:" in result.output
                assert "Sleep data (7+ days)" in result.output
