"""
Test CLI PAT Integration

Tests that the CLI properly wires PAT predictor through DI container
to enable temporal separation (NOW vs TOMORROW).
"""

from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.interfaces.cli.commands import predict_command


class TestCLIPATIntegration:
    """Test PAT integration in CLI command."""

    @patch('big_mood_detector.interfaces.cli.commands.Path')
    @patch('big_mood_detector.interfaces.cli.commands.MoodPredictionPipeline')
    @patch('big_mood_detector.infrastructure.di.get_container')
    def test_cli_passes_di_container_to_pipeline(
        self, mock_get_container, mock_pipeline_class, mock_path
    ):
        """CLI should pass DI container to MoodPredictionPipeline."""
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
        
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.is_file.return_value = True
        
        # Run predict command with ensemble flag (which should enable PAT)
        with patch('click.echo'):
            predict_command(
                input_path="test.xml",
                output=None,
                format="summary",
                start_date=None,
                end_date=None,
                days_back=None,
                date_range=None,
                ensemble=True,  # This should trigger PAT integration
                user_id=None,
                model_dir=None,
                report=False,
                window_strategy=None,
                auto_find_window=False,
                verbose=False,
            )
        
        # Verify pipeline was created with DI container
        mock_pipeline_class.assert_called_once()
        call_args = mock_pipeline_class.call_args
        
        # Check that config was passed
        assert call_args[0][0].ensemble_config is not None
        
        # Should have created pipeline with DI container
        assert 'di_container' in call_args[1]
        assert call_args[1]['di_container'] == mock_container

    @patch('big_mood_detector.infrastructure.ml_models.xgboost_models.XGBoostMoodPredictor')
    @patch('big_mood_detector.infrastructure.ml_models.pat_production_loader.ProductionPATLoader')
    def test_pipeline_creates_temporal_orchestrator_with_di(
        self, mock_pat_loader_class, mock_xgboost_class
    ):
        """Pipeline should create TemporalEnsembleOrchestrator when PAT is available."""
        # Setup mocks
        mock_xgboost = Mock()
        mock_xgboost.is_loaded = True
        mock_xgboost.load_models.return_value = True
        mock_xgboost_class.return_value = mock_xgboost
        
        mock_pat_loader = Mock()
        mock_pat_loader.is_loaded = True
        mock_pat_loader_class.return_value = mock_pat_loader
        
        # Create mock DI container that provides PAT predictor
        mock_container = Mock()
        mock_pat_predictor = Mock()
        mock_container.resolve.return_value = mock_pat_predictor
        
        # Create pipeline with DI container
        config = PipelineConfig(
            ensemble_config=Mock()  # Enable ensemble
        )
        pipeline = MoodPredictionPipeline(config=config, di_container=mock_container)
        
        # Should have created temporal orchestrator
        assert pipeline.ensemble_orchestrator is not None
        
        # Should have resolved PAT predictor from DI
        mock_container.resolve.assert_called()

    def test_cli_without_ensemble_does_not_create_pat(self):
        """Without --ensemble flag, PAT should not be loaded."""
        with patch('big_mood_detector.interfaces.cli.commands.MoodPredictionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_result = Mock()
            mock_result.has_errors = False
            mock_result.warnings = []
            mock_result.overall_summary = {'days_analyzed': 0}
            mock_result.confidence_score = 0
            mock_result.metadata = {}
            mock_pipeline.process_apple_health_file.return_value = mock_result
            mock_pipeline_class.return_value = mock_pipeline
            
            with patch('click.echo'):
                with patch('big_mood_detector.interfaces.cli.commands.Path') as mock_path:
                    mock_path.return_value.exists.return_value = True
                    mock_path.return_value.is_file.return_value = True
                    
                    predict_command(
                        input_path="test.xml",
                        output=None,
                        format="summary",
                        start_date=None,
                        end_date=None,
                        days_back=None,
                        date_range=None,
                        ensemble=False,  # No ensemble
                        user_id=None,
                        model_dir=None,
                        report=False,
                        window_strategy=None,
                        auto_find_window=False,
                        verbose=False,
                    )
            
            # Should not have ensemble config
            call_args = mock_pipeline_class.call_args
            assert call_args[0][0].ensemble_config is None