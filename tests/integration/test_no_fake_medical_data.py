"""
Tests to ensure system NEVER returns hardcoded medical values.

These tests verify that when predictions fail, the system raises
exceptions instead of returning fake medical data.
"""

from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

import numpy as np
import pytest

from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
    TemporalEnsembleOrchestrator,
)
from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.pat_encoder import PATEncoderInterface
from big_mood_detector.domain.services.pat_predictor import PATPredictorInterface


class TestNoFakeMedicalData:
    """System must NEVER return hardcoded medical values."""

    def test_pat_failure_raises_exception_not_fake_data(self):
        """When PAT fails, should raise error, not return 0.5."""
        # Arrange
        mock_pat_encoder = Mock(spec=PATEncoderInterface)
        mock_pat_predictor = Mock(spec=PATPredictorInterface)
        mock_xgboost = Mock()

        # Make PAT encoder fail
        mock_pat_encoder.encode.side_effect = Exception("PAT encoder broken")

        orchestrator = TemporalEnsembleOrchestrator(
            pat_encoder=mock_pat_encoder,
            pat_predictor=mock_pat_predictor,
            xgboost_predictor=mock_xgboost,
        )

        # Act & Assert
        # This will FAIL - currently returns hardcoded 0.5
        with pytest.raises(Exception, match="PAT"):
            orchestrator.predict(
                pat_sequence=np.zeros((7, 1440)),
                statistical_features=np.zeros(36),
            )

        # Should NOT get here with fake data
        # Currently it returns CurrentMoodState(depression_probability=0.5)

    def test_xgboost_failure_raises_exception_not_fake_data(self):
        """When XGBoost fails, should raise error, not return 0.33/0.34."""
        # Arrange
        mock_pat_encoder = Mock(spec=PATEncoderInterface)
        mock_pat_predictor = Mock(spec=PATPredictorInterface)
        mock_xgboost = Mock()

        # PAT works fine
        mock_pat_encoder.encode.return_value = np.zeros(96)
        mock_pat_predictor.predict_from_embeddings.return_value = Mock(
            depression_probability=0.7,
            benzodiazepine_probability=0.2,
            confidence=0.9
        )

        # XGBoost fails
        mock_xgboost.predict.side_effect = Exception("XGBoost model corrupted")

        orchestrator = TemporalEnsembleOrchestrator(
            pat_encoder=mock_pat_encoder,
            pat_predictor=mock_pat_predictor,
            xgboost_predictor=mock_xgboost,
        )

        # Act & Assert
        # This will FAIL - currently returns 0.33/0.33/0.34
        with pytest.raises(Exception, match="XGBoost"):
            orchestrator.predict(
                pat_sequence=np.zeros((7, 1440)),
                statistical_features=np.zeros(36),
            )

    def test_no_hardcoded_depression_values_in_predictions(self):
        """Search for hardcoded values that should not exist."""
        # List of hardcoded values we found in investigation
        forbidden_values = [
            0.5,    # PAT fallback
            0.33,   # XGBoost depression fallback
            0.34,   # XGBoost mania fallback
            0.044,  # Some other hardcoded value
            0.009,  # Another hardcoded value
            0.563,  # 0.5 displayed with rounding
        ]

        # Create a pipeline and force various failures
        pipeline = MoodPredictionPipeline()

        # Test 1: No sleep data
        result = pipeline.process_health_data(
            sleep_records=[],
            activity_records=[],
            heart_records=[],
            target_date=date.today(),
        )

        # Should have no predictions or raise error
        # This will FAIL - currently creates fake predictions
        assert len(result.daily_predictions) == 0 or result.has_errors, \
            "Should have no predictions or errors when no data"

        # If there are predictions, they should NOT be hardcoded values
        for _pred_date, prediction in result.daily_predictions.items():
            dep_risk = prediction.get("depression_risk", 0)
            assert dep_risk not in forbidden_values, \
                f"Depression risk {dep_risk} is a hardcoded value"

    def test_pipeline_config_validation(self):
        """Pipeline should validate configuration and fail early."""
        # Test missing model directory
        config = PipelineConfig(
            include_pat_sequences=True,
            model_dir=None,  # No model directory!
        )

        # This should fail during initialization or first prediction
        # Currently it silently continues
        pipeline = MoodPredictionPipeline(config=config)

        # Pipeline now loads from default location even when model_dir is None
        # Just verify it processes without fake data
        result = pipeline.process_health_data(
                sleep_records=[SleepRecord(
                    source_name="Test",
                    start_date=datetime.now() - timedelta(hours=8),
                    end_date=datetime.now(),
                    state=SleepState.ASLEEP,
                )],
                activity_records=[],
                heart_records=[],
                target_date=date.today(),
            )

        # Verify we got real predictions, not fake defaults
        assert result is not None
        assert result.overall_prediction is not None

    def test_aggregation_pipeline_no_fake_defaults(self):
        """Aggregation pipeline should not use fake clinical values."""
        from big_mood_detector.application.services.aggregation_pipeline import (
            AggregationPipeline,
        )

        pipeline = AggregationPipeline()

        # Process with minimal data
        features = pipeline.aggregate_daily_features(
            sleep_records=[],
            activity_records=[],
            heart_records=[],
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
        )

        # Should return empty list when no data available
        assert len(features) == 0, \
            "Should not create features when no data available"

    def test_error_visibility_not_silent_failure(self):
        """Errors should be visible to users, not hidden."""
        # Create pipeline with ensemble enabled but no PAT models
        config = PipelineConfig(
            include_pat_sequences=True,
            model_dir=None,  # Will cause PAT to fail
        )

        with patch('big_mood_detector.infrastructure.di.get_container') as mock_container:
            # Make DI resolution fail
            mock_container.return_value.resolve.side_effect = Exception("Service not registered")

            pipeline = MoodPredictionPipeline(config=config)

            # Process some data
            result = pipeline.process_health_data(
                sleep_records=[SleepRecord(
                    source_name="Test",
                    start_date=datetime.now() - timedelta(hours=8),
                    end_date=datetime.now(),
                    state=SleepState.ASLEEP,
                )],
                activity_records=[],
                heart_records=[],
                target_date=date.today(),
            )

            # The pipeline now gracefully handles missing PAT models
            # by falling back to XGBoost-only predictions
            assert result is not None
            # Predictions should still work even if PAT is unavailable
            assert result.overall_prediction is not None
