"""
Test CLI PAT Integration

Tests that the CLI properly wires PAT predictor through DI container
to enable temporal separation (NOW vs TOMORROW).
"""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineConfig,
)
from big_mood_detector.interfaces.cli.main import cli


class TestCLIPATIntegration:
    """Test PAT integration in CLI command."""

    def test_cli_passes_di_container_to_pipeline(self, tmp_path):
        """CLI should pass DI container to MoodPredictionPipeline when ensemble is enabled."""
        runner = CliRunner()

        # Create a temporary test file
        test_file = tmp_path / "test.xml"
        test_file.write_text("<HealthData>Test</HealthData>")

        with patch('big_mood_detector.interfaces.cli.commands.MoodPredictionPipeline') as mock_pipeline_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Setup mocks
                mock_container = Mock()
                mock_get_container.return_value = mock_container

                mock_pipeline = Mock()
                mock_result = Mock()
                mock_result.has_errors = False
                mock_result.warnings = []
                mock_result.overall_summary = {
                    'avg_depression_risk': 0.1,
                    'avg_hypomanic_risk': 0.05,
                    'avg_manic_risk': 0.01,
                    'days_analyzed': 7
                }
                mock_result.confidence_score = 0.8
                mock_result.metadata = {}
                mock_pipeline.process_apple_health_file.return_value = mock_result
                mock_pipeline_class.return_value = mock_pipeline

                # Run CLI command with ensemble flag
                result = runner.invoke(cli, [
                    'predict', str(test_file),
                    '--ensemble',  # This should trigger PAT integration
                    '--format', 'summary'
                ])

                # Check command executed successfully
                assert result.exit_code == 0

                # Verify DI container was retrieved
                mock_get_container.assert_called_once()

                # Verify pipeline was created with DI container
                mock_pipeline_class.assert_called_once()
                call_args = mock_pipeline_class.call_args

                # Check config
                config = call_args.kwargs['config']
                assert isinstance(config, PipelineConfig)
                assert config.include_pat_sequences is True

                # Check DI container was passed
                assert 'di_container' in call_args.kwargs
                assert call_args.kwargs['di_container'] == mock_container

    def test_cli_verbose_shows_di_container_message(self, tmp_path):
        """CLI should show DI container message when verbose and ensemble are enabled."""
        runner = CliRunner()

        # Create a temporary test file
        test_file = tmp_path / "test.xml"
        test_file.write_text("<HealthData>Test</HealthData>")

        with patch('big_mood_detector.interfaces.cli.commands.MoodPredictionPipeline') as mock_pipeline_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Setup mocks
                mock_container = Mock()
                mock_get_container.return_value = mock_container

                mock_pipeline = Mock()
                mock_result = Mock()
                mock_result.has_errors = False
                mock_result.warnings = []
                mock_result.overall_summary = {
                    'avg_depression_risk': 0.1,
                    'avg_hypomanic_risk': 0.05,
                    'avg_manic_risk': 0.01,
                    'days_analyzed': 7
                }
                mock_result.confidence_score = 0.8
                mock_result.metadata = {}
                mock_pipeline.process_apple_health_file.return_value = mock_result
                mock_pipeline_class.return_value = mock_pipeline

                # Run CLI command with ensemble and verbose flags
                result = runner.invoke(cli, [
                    'predict', str(test_file),
                    '--ensemble',
                    '--verbose',  # Should show DI container message
                    '--format', 'summary'
                ])

                # Check command executed successfully
                assert result.exit_code == 0

                # Check verbose output contains DI container message
                assert "Using DI container for PAT integration" in result.output

    def test_cli_without_ensemble_does_not_use_di_container(self, tmp_path):
        """Without --ensemble flag, DI container should not be used."""
        runner = CliRunner()

        # Create a temporary test file
        test_file = tmp_path / "test.xml"
        test_file.write_text("<HealthData>Test</HealthData>")

        with patch('big_mood_detector.interfaces.cli.commands.MoodPredictionPipeline') as mock_pipeline_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Setup mock pipeline
                mock_pipeline = Mock()
                mock_result = Mock()
                mock_result.has_errors = False
                mock_result.warnings = []
                mock_result.overall_summary = {'days_analyzed': 0}
                mock_result.confidence_score = 0
                mock_result.metadata = {}
                mock_pipeline.process_apple_health_file.return_value = mock_result
                mock_pipeline_class.return_value = mock_pipeline

                # Run CLI command WITHOUT ensemble flag
                result = runner.invoke(cli, [
                    'predict', str(test_file),
                    '--format', 'summary'
                    # No --ensemble flag
                ])

                # Check command executed successfully
                assert result.exit_code == 0

                # DI container should NOT be retrieved
                mock_get_container.assert_not_called()

                # Verify pipeline was created without DI container
                mock_pipeline_class.assert_called_once()
                call_args = mock_pipeline_class.call_args

                # Check config
                config = call_args.kwargs['config']
                assert isinstance(config, PipelineConfig)
                assert config.include_pat_sequences is False

                # Check DI container was NOT passed
                assert call_args.kwargs['di_container'] is None
