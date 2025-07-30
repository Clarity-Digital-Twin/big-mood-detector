"""
Test Temporal Ensemble Orchestrator Dependency Injection

TDD test to ensure TemporalEnsembleOrchestrator is properly wired in DI.
"""

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
    TemporalEnsembleOrchestrator,
)
from big_mood_detector.domain.value_objects.temporal_mood_assessment import (
    TemporalMoodAssessment,
)


class TestTemporalOrchestratorDI:
    """Test temporal orchestrator is properly injected."""

    @pytest.fixture(autouse=True)
    def reset_di_container(self) -> Generator[None, None, None]:
        """Reset DI container between tests to avoid state pollution."""
        # Import here to avoid circular imports
        from big_mood_detector.infrastructure.di.container import reset_container
        from big_mood_detector.interfaces.api.dependencies import (
            get_ensemble_orchestrator,
        )

        # Reset before test
        reset_container()
        # Also clear the orchestrator cache
        get_ensemble_orchestrator.cache_clear()
        yield
        # Reset after test
        reset_container()
        get_ensemble_orchestrator.cache_clear()

    def test_get_ensemble_orchestrator_returns_temporal_orchestrator(self) -> None:
        """Test that get_ensemble_orchestrator returns TemporalEnsembleOrchestrator."""
        from big_mood_detector.interfaces.api.dependencies import (
            get_ensemble_orchestrator,
        )

        # Mock the model loading to avoid file dependencies
        with patch('big_mood_detector.interfaces.api.dependencies.XGBoostMoodPredictor') as mock_xgboost_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Setup mocks with SimpleNamespace to avoid Mock comparison issues
                mock_xgboost = SimpleNamespace(
                    load_models=lambda x: True,
                    is_loaded=True
                )
                mock_xgboost_class.return_value = mock_xgboost

                mock_pat_predictor = SimpleNamespace(
                    is_loaded=True
                )

                mock_container = SimpleNamespace(
                    resolve=lambda interface: mock_pat_predictor
                )
                mock_get_container.return_value = mock_container

                # Get orchestrator
                orchestrator = get_ensemble_orchestrator()

                # Assert it's the temporal orchestrator
                assert orchestrator is not None
                assert isinstance(orchestrator, TemporalEnsembleOrchestrator)

    def test_temporal_orchestrator_has_required_dependencies(self) -> None:
        """Test that temporal orchestrator has all required dependencies."""
        from big_mood_detector.interfaces.api.dependencies import (
            get_ensemble_orchestrator,
        )

        with patch('big_mood_detector.interfaces.api.dependencies.XGBoostMoodPredictor') as mock_xgboost_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Setup mocks with SimpleNamespace
                mock_xgboost = SimpleNamespace(
                    load_models=lambda x: True,
                    predict=lambda features: SimpleNamespace(
                        depression_risk=0.4,
                        hypomanic_risk=0.2,
                        manic_risk=0.1,
                        confidence=0.85
                    )
                )
                mock_xgboost_class.return_value = mock_xgboost

                # Create simple objects for PAT predictor and encoder
                mock_pat_predictor = SimpleNamespace(
                    predict_from_embeddings=lambda emb: SimpleNamespace(
                        depression_probability=0.7,
                        benzodiazepine_probability=0.3,
                        confidence=0.9
                    )
                )
                mock_pat_encoder = SimpleNamespace(
                    encode=lambda seq: np.random.rand(96).astype(np.float32)
                )

                # Simple container mock
                mock_container = SimpleNamespace(
                    resolve=lambda interface: (
                        mock_pat_predictor if 'PATPredictorInterface' in str(interface)
                        else mock_pat_encoder if 'PATEncoderInterface' in str(interface)
                        else None
                    )
                )
                mock_get_container.return_value = mock_container

                # Get orchestrator
                orchestrator = get_ensemble_orchestrator()

                # Verify it has all dependencies
                assert orchestrator is not None
                assert hasattr(orchestrator, 'pat_predictor')
                assert hasattr(orchestrator, 'xgboost_predictor')
                assert hasattr(orchestrator, 'pat_encoder')

    def test_temporal_orchestrator_returns_temporal_assessment(self) -> None:
        """Test that orchestrator returns TemporalMoodAssessment, not EnsemblePrediction."""
        from big_mood_detector.interfaces.api.dependencies import (
            get_ensemble_orchestrator,
        )

        with patch('big_mood_detector.interfaces.api.dependencies.XGBoostMoodPredictor') as mock_xgboost_class:
            with patch('big_mood_detector.infrastructure.di.get_container') as mock_get_container:
                # Create simple mock objects that return real values
                mock_xgboost = SimpleNamespace(
                    load_models=lambda x: True,
                    predict=lambda features: SimpleNamespace(
                        depression_risk=0.4,
                        hypomanic_risk=0.2,
                        manic_risk=0.1,
                        confidence=0.85
                    )
                )
                mock_xgboost_class.return_value = mock_xgboost

                # Create PAT mocks with real values
                mock_pat_predictor = SimpleNamespace(
                    predict_from_embeddings=lambda emb: SimpleNamespace(
                        depression_probability=0.7,
                        benzodiazepine_probability=0.3,
                        confidence=0.9
                    )
                )

                mock_pat_encoder = SimpleNamespace(
                    encode=lambda seq: np.random.rand(96).astype(np.float32)
                )

                # Simple container mock
                mock_container = SimpleNamespace(
                    resolve=lambda interface: (
                        mock_pat_predictor if 'PATPredictorInterface' in str(interface)
                        else mock_pat_encoder if 'PATEncoderInterface' in str(interface)
                        else None
                    )
                )
                mock_get_container.return_value = mock_container

                # Get orchestrator
                orchestrator = get_ensemble_orchestrator()

                # Test prediction returns TemporalMoodAssessment
                if orchestrator and isinstance(orchestrator, TemporalEnsembleOrchestrator):
                    # Real inputs
                    statistical_features = np.random.rand(36).astype(np.float32)
                    pat_sequence = np.random.rand(7, 1440).astype(np.float32)

                    # Get prediction - TemporalEnsembleOrchestrator has different signature
                    result = orchestrator.predict(
                        statistical_features=statistical_features,
                        pat_sequence=pat_sequence,
                        user_id="test_user"
                    )

                    # Assert it's TemporalMoodAssessment
                    assert isinstance(result, TemporalMoodAssessment)
                    assert hasattr(result, 'current_state')
                    assert hasattr(result, 'future_risk')
                    assert hasattr(result, 'temporal_concordance')
