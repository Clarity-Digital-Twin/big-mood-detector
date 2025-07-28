"""
Clean Temporal Endpoint Test

Following the principle of minimal mocking - using real orchestrator
with lightweight dummy models for fast, reliable tests.
"""


import numpy as np
import pytest
from fastapi.testclient import TestClient

from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
    TemporalEnsembleOrchestrator,
)
from big_mood_detector.domain.services.mood_predictor import MoodPrediction
from big_mood_detector.domain.services.pat_predictor import PATBinaryPredictions


class DummyPATPredictor:
    """Lightweight PAT predictor that returns fixed values."""

    def predict_from_embeddings(self, embeddings):
        return PATBinaryPredictions(
            depression_probability=0.72,
            benzodiazepine_probability=0.15,
            confidence=0.85
        )


class DummyXGBoostPredictor:
    """Lightweight XGBoost predictor that returns fixed values."""

    def predict(self, features):
        return MoodPrediction(
            depression_risk=0.35,
            hypomanic_risk=0.15,
            manic_risk=0.05,
            confidence=0.78
        )


class DummyPATEncoder:
    """Lightweight PAT encoder that returns fixed embeddings."""

    def encode(self, sequence):
        return np.ones(96, dtype=np.float32) * 0.5


@pytest.fixture
def real_temporal_orchestrator():
    """Create real orchestrator with dummy models."""
    return TemporalEnsembleOrchestrator(
        pat_predictor=DummyPATPredictor(),
        xgboost_predictor=DummyXGBoostPredictor(),
        pat_encoder=DummyPATEncoder()
    )


@pytest.fixture
def test_client_with_real_orchestrator(real_temporal_orchestrator):
    """Test client with real orchestrator dependency override."""
    from big_mood_detector.interfaces.api.dependencies import get_ensemble_orchestrator
    from big_mood_detector.interfaces.api.main import app

    # Override with real orchestrator
    app.dependency_overrides[get_ensemble_orchestrator] = lambda: real_temporal_orchestrator

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


class TestTemporalEndpointClean:
    """Clean tests for temporal endpoint with minimal mocking."""

    def test_temporal_endpoint_full_flow(self, test_client_with_real_orchestrator):
        """Test complete flow with real orchestrator."""
        response = test_client_with_real_orchestrator.post(
            "/api/v1/predictions/predict/temporal",
            json={
                "statistical_features": {
                    "sleep_duration": 7.5,
                    "sleep_efficiency": 0.85,
                    "sleep_timing_variance": 0.5,
                    "daily_steps": 8500,
                    "activity_variance": 1200,
                    "sedentary_hours": 8.5
                },
                "activity_sequence": [0.5] * 10080  # Fixed activity pattern
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "current_state" in data
        assert "future_risk" in data
        assert "temporal_concordance" in data
        assert "clinical_guidance" in data

        # Verify values match our dummy models
        assert data["current_state"]["depression_probability"] == 0.72
        assert data["future_risk"]["depression_risk"] == 0.35

        # Verify temporal analysis
        assert 0 <= data["temporal_concordance"] <= 1
        assert isinstance(data["requires_immediate_intervention"], bool)
        assert isinstance(data["requires_preventive_action"], bool)

    def test_temporal_endpoint_shows_clinical_guidance(self, test_client_with_real_orchestrator):
        """Test that clinical guidance is properly generated."""
        response = test_client_with_real_orchestrator.post(
            "/api/v1/predictions/predict/temporal",
            json={
                "statistical_features": {
                    "sleep_duration": 7.5,
                    "sleep_efficiency": 0.85,
                    "sleep_timing_variance": 0.5,
                    "daily_steps": 8500,
                    "activity_variance": 1200,
                    "sedentary_hours": 8.5
                },
                "activity_sequence": [0.5] * 10080
            }
        )

        data = response.json()

        # Should have clinical guidance based on temporal pattern
        assert data["clinical_guidance"] in [
            "Immediate clinical assessment recommended",
            "Implement preventive strategies today",
            "Monitor closely - state is changing",
            "Continue current management plan"
        ]

        # Monitoring frequency should be set
        assert data["monitoring_frequency"] in ["Daily", "Weekly"]

    def test_temporal_endpoint_validates_activity_length(self, test_client_with_real_orchestrator):
        """Test that activity sequence length is validated."""
        response = test_client_with_real_orchestrator.post(
            "/api/v1/predictions/predict/temporal",
            json={
                "statistical_features": {
                    "sleep_duration": 7.5,
                    "sleep_efficiency": 0.85,
                    "sleep_timing_variance": 0.5,
                    "daily_steps": 8500,
                    "activity_variance": 1200,
                    "sedentary_hours": 8.5
                },
                "activity_sequence": [0.5] * 100  # Wrong length
            }
        )

        assert response.status_code == 422
        assert "10080" in str(response.json())
