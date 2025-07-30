"""
Integration tests for CLI window selection flags.

Tests the --auto-find-window and --window-strategy flags
with realistic data patterns.
"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from big_mood_detector.interfaces.cli.main import cli


class TestCLIWindowSelection:
    """Test CLI window selection functionality."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_health_file(self, tmp_path):
        """Create a mock health export file."""
        export_file = tmp_path / "export.xml"
        export_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData [
<!ELEMENT HealthData (Record)*>
<!ELEMENT Record EMPTY>
<!ATTLIST Record type CDATA #REQUIRED>
<!ATTLIST Record sourceName CDATA #REQUIRED>
<!ATTLIST Record startDate CDATA #REQUIRED>
<!ATTLIST Record endDate CDATA #REQUIRED>
<!ATTLIST Record value CDATA #IMPLIED>
]>
<HealthData locale="en_US">
  <!-- Sleep records from June 26 - July 2 (7 days) -->
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-06-26 22:00:00 +0000" endDate="2025-06-27 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-06-27 22:00:00 +0000" endDate="2025-06-28 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-06-28 22:00:00 +0000" endDate="2025-06-29 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-06-29 22:00:00 +0000" endDate="2025-06-30 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-06-30 22:00:00 +0000" endDate="2025-07-01 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-07-01 22:00:00 +0000" endDate="2025-07-02 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-07-02 22:00:00 +0000" endDate="2025-07-03 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
</HealthData>
""")
        return export_file

    @patch('big_mood_detector.infrastructure.ml_models.xgboost_models.XGBoostMoodPredictor')
    def test_auto_find_window_flag(self, mock_predictor_class, runner, mock_health_file):
        """Test --auto-find-window flag finds valid window."""
        # Setup mock predictor
        mock_predictor = Mock()
        mock_predictor.is_loaded = True
        mock_predictor.predict.return_value = Mock(
            depression_risk=0.036,
            hypomanic_risk=0.003,
            manic_risk=0.0,
            confidence=0.35
        )
        mock_predictor_class.return_value = mock_predictor

        # Run command with auto-find-window
        result = runner.invoke(cli, [
            'predict',
            str(mock_health_file),
            '--auto-find-window',
            '--verbose'
        ])

        # Should succeed and use MostRecentValidWindowStrategy
        assert result.exit_code == 0
        assert "Using window selection strategy: MostRecentValidWindowStrategy" in result.output
        assert "Depression Risk:" in result.output

    @patch('big_mood_detector.infrastructure.ml_models.xgboost_models.XGBoostMoodPredictor')
    def test_window_strategy_best(self, mock_predictor_class, runner, mock_health_file):
        """Test --window-strategy best finds highest quality window."""
        # Setup mock predictor
        mock_predictor = Mock()
        mock_predictor.is_loaded = True
        mock_predictor.predict.return_value = Mock(
            depression_risk=0.05,
            hypomanic_risk=0.01,
            manic_risk=0.0,
            confidence=0.9
        )
        mock_predictor_class.return_value = mock_predictor

        # Run command with window-strategy best
        result = runner.invoke(cli, [
            'predict',
            str(mock_health_file),
            '--window-strategy', 'best',
            '--verbose'
        ])

        # Should succeed and use BestQualityWindowStrategy
        assert result.exit_code == 0
        assert "Using window selection strategy: BestQualityWindowStrategy" in result.output
        assert "Depression Risk:" in result.output

    def test_window_strategy_all(self, runner, mock_health_file):
        """Test --window-strategy all shows all valid windows."""
        # Run command with window-strategy all
        result = runner.invoke(cli, [
            'predict',
            str(mock_health_file),
            '--window-strategy', 'all'
        ])

        # Should show all windows and exit early
        assert result.exit_code == 0
        assert "Found" in result.output
        assert "valid prediction windows" in result.output
        assert "Use --date-range to analyze a specific window" in result.output

    @patch('big_mood_detector.infrastructure.ml_models.xgboost_models.XGBoostMoodPredictor')
    def test_no_window_strategy_uses_legacy(self, mock_predictor_class, runner, mock_health_file):
        """Test without window strategy uses legacy behavior."""
        # Setup mock predictor
        mock_predictor = Mock()
        mock_predictor.is_loaded = True
        mock_predictor.predict.return_value = Mock(
            depression_risk=0.1,
            hypomanic_risk=0.02,
            manic_risk=0.0,
            confidence=0.5
        )
        mock_predictor_class.return_value = mock_predictor

        # Run command without window selection
        result = runner.invoke(cli, [
            'predict',
            str(mock_health_file),
            '--verbose'
        ])

        # Should use legacy behavior (no window strategy message)
        assert result.exit_code == 0
        assert "Using window selection strategy" not in result.output

    def test_auto_find_window_with_no_valid_data(self, runner, tmp_path):
        """Test --auto-find-window with no valid windows."""
        # Create export with no consecutive sleep data
        export_file = tmp_path / "sparse_export.xml"
        export_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData [
<!ELEMENT HealthData (Record)*>
<!ELEMENT Record EMPTY>
<!ATTLIST Record type CDATA #REQUIRED>
<!ATTLIST Record sourceName CDATA #REQUIRED>
<!ATTLIST Record startDate CDATA #REQUIRED>
<!ATTLIST Record endDate CDATA #REQUIRED>
<!ATTLIST Record value CDATA #IMPLIED>
]>
<HealthData locale="en_US">
  <!-- Only 3 days of sleep (not enough for 7-day window) -->
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-06-01 22:00:00 +0000" endDate="2025-06-02 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-06-02 22:00:00 +0000" endDate="2025-06-03 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
          startDate="2025-06-03 22:00:00 +0000" endDate="2025-06-04 06:00:00 +0000"
          value="HKCategoryValueSleepAnalysisAsleep"/>
</HealthData>
""")

        # Run with auto-find-window
        result = runner.invoke(cli, [
            'predict',
            str(export_file),
            '--auto-find-window'
        ])

        # Should report no valid windows
        assert result.exit_code == 0
        assert "No valid 7-day windows found" in result.output
