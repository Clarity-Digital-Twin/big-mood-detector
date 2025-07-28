"""
Test Temporal Ensemble Orchestrator Dependency Injection

TDD test to ensure TemporalEnsembleOrchestrator is properly wired in DI.
"""

from unittest.mock import Mock, patch

from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
    TemporalEnsembleOrchestrator,
)
from big_mood_detector.domain.value_objects.temporal_mood_assessment import (
    TemporalMoodAssessment,
)


class TestTemporalOrchestratorDI:
    """Test temporal orchestrator is properly injected."""

    def test_get_ensemble_orchestrator_returns_temporal_orchestrator(self):
        """Test that get_ensemble_orchestrator returns TemporalEnsembleOrchestrator."""
        from big_mood_detector.interfaces.api.dependencies import (
            get_ensemble_orchestrator,
        )

        # Mock the model loading to avoid file dependencies
        with patch('big_mood_detector.interfaces.api.dependencies.XGBoostMoodPredictor') as mock_xgboost_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Setup mocks
                mock_xgboost = Mock()
                mock_xgboost.load_models.return_value = True
                mock_xgboost.is_loaded = True
                mock_xgboost_class.return_value = mock_xgboost

                mock_container = Mock()
                mock_pat_predictor = Mock()
                mock_pat_predictor.is_loaded = True
                mock_container.resolve.return_value = mock_pat_predictor
                mock_get_container.return_value = mock_container

                # Get orchestrator
                orchestrator = get_ensemble_orchestrator()

                # Assert it's the temporal orchestrator
                assert orchestrator is not None
                assert isinstance(orchestrator, TemporalEnsembleOrchestrator)

    def test_temporal_orchestrator_has_required_dependencies(self):
        """Test that temporal orchestrator has all required dependencies."""
        from big_mood_detector.interfaces.api.dependencies import (
            get_ensemble_orchestrator,
        )

        with patch('big_mood_detector.interfaces.api.dependencies.XGBoostMoodPredictor') as mock_xgboost_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Setup mocks
                mock_xgboost = Mock()
                mock_xgboost.load_models.return_value = True
                mock_xgboost_class.return_value = mock_xgboost

                mock_container = Mock()
                mock_pat_predictor = Mock()
                mock_pat_encoder = Mock()

                # Mock container to return both predictor and encoder
                def resolve_side_effect(interface):
                    if 'PATPredictorInterface' in str(interface):
                        return mock_pat_predictor
                    elif 'PATModelInterface' in str(interface):
                        return mock_pat_encoder
                    return None

                mock_container.resolve.side_effect = resolve_side_effect
                mock_get_container.return_value = mock_container

                # Get orchestrator
                orchestrator = get_ensemble_orchestrator()

                # Verify it has all dependencies
                assert orchestrator is not None
                assert hasattr(orchestrator, 'pat_predictor')
                assert hasattr(orchestrator, 'xgboost_predictor')
                assert hasattr(orchestrator, 'pat_encoder')

    def test_temporal_orchestrator_returns_temporal_assessment(self):
        """Test that orchestrator returns TemporalMoodAssessment, not EnsemblePrediction."""
        import numpy as np

        from big_mood_detector.interfaces.api.dependencies import (
            get_ensemble_orchestrator,
        )

        with patch('big_mood_detector.interfaces.api.dependencies.XGBoostMoodPredictor') as mock_xgboost_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Setup comprehensive mocks
                mock_xgboost = Mock()
                mock_xgboost.load_models.return_value = True
                mock_xgboost_class.return_value = mock_xgboost

                mock_container = Mock()
                mock_pat_predictor = Mock()
                mock_pat_encoder = Mock()

                def resolve_side_effect(interface):
                    if 'PATPredictorInterface' in str(interface):
                        return mock_pat_predictor
                    elif 'PATModelInterface' in str(interface):
                        return mock_pat_encoder
                    return None

                mock_container.resolve.side_effect = resolve_side_effect
                mock_get_container.return_value = mock_container

                # Get orchestrator
                orchestrator = get_ensemble_orchestrator()

                # Test prediction returns TemporalMoodAssessment
                if orchestrator and hasattr(orchestrator, 'predict'):
                    # Mock inputs
                    statistical_features = np.random.rand(36)
                    pat_sequence = np.random.rand(7, 1440)

                    # Get prediction
                    result = orchestrator.predict(
                        statistical_features=statistical_features,
                        pat_sequence=pat_sequence,
                        user_id="test_user"
                    )

                    # Assert it's TemporalMoodAssessment, not EnsemblePrediction
                    assert isinstance(result, TemporalMoodAssessment)
                    assert hasattr(result, 'current_state')  # PAT assessment
                    assert hasattr(result, 'future_risk')     # XGBoost prediction
                    assert hasattr(result, 'temporal_concordance')
