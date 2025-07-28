"""
Test Temporal Prediction API Endpoint

TDD test for the new /predict/temporal endpoint that shows NOW vs TOMORROW.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import numpy as np


class TestTemporalEndpoint:
    """Test the temporal prediction endpoint."""

    @pytest.fixture
    def mock_temporal_orchestrator(self):
        """Create real temporal orchestrator with minimal mocking."""
        from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
            TemporalEnsembleOrchestrator,
        )
        from big_mood_detector.domain.services.mood_predictor import MoodPrediction
        from big_mood_detector.domain.services.pat_predictor import PATBinaryPredictions
        
        # Create minimal mocks for the actual models
        mock_pat_predictor = Mock()
        mock_pat_predictor.predict_from_embeddings.return_value = PATBinaryPredictions(
            depression_probability=0.72,
            benzodiazepine_probability=0.15,
            confidence=0.85
        )
        
        mock_xgboost = Mock()
        mock_xgboost.predict.return_value = MoodPrediction(
            depression_risk=0.35,
            hypomanic_risk=0.15,
            manic_risk=0.05,
            confidence=0.78
        )
        
        mock_encoder = Mock()
        mock_encoder.encode.return_value = np.random.rand(96)
        
        # Create real orchestrator with mocked models
        orchestrator = TemporalEnsembleOrchestrator(
            pat_predictor=mock_pat_predictor,
            xgboost_predictor=mock_xgboost,
            pat_encoder=mock_encoder
        )
        
        return orchestrator

    @pytest.fixture
    def test_client(self, mock_temporal_orchestrator):
        """Create test client with mocked dependencies."""
        from big_mood_detector.interfaces.api.main import app
        from big_mood_detector.interfaces.api.dependencies import get_ensemble_orchestrator
        
        # Override dependency
        app.dependency_overrides[get_ensemble_orchestrator] = lambda: mock_temporal_orchestrator
        
        yield TestClient(app)
        
        # Clean up
        app.dependency_overrides.clear()

    def test_temporal_endpoint_exists(self, test_client):
        """Test that /predict/temporal endpoint exists."""
        response = test_client.post(
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
                "activity_sequence": list(np.random.rand(10080).tolist())  # 7 days
            }
        )
        
        # Should not be 404
        assert response.status_code != 404
        
    def test_temporal_endpoint_returns_temporal_structure(self, test_client):
        """Test that endpoint returns proper temporal structure."""
        response = test_client.post(
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
                "activity_sequence": list(np.random.rand(10080).tolist())
            }
        )
        
        if response.status_code != 200:
            print(f"Response: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        
        # Check temporal structure
        assert "current_state" in data
        assert "future_risk" in data
        assert "temporal_concordance" in data
        assert "clinical_guidance" in data  # This should be derived from the assessment
        
        # Check current state (PAT)
        current = data["current_state"]
        assert "depression_probability" in current
        assert "confidence" in current
        
        # Check future risk (XGBoost)
        future = data["future_risk"]
        assert "depression_risk" in future
        assert "hypomanic_risk" in future
        assert "manic_risk" in future
        
    def test_temporal_endpoint_shows_now_vs_tomorrow(self, test_client):
        """Test that endpoint clearly separates NOW vs TOMORROW."""
        response = test_client.post(
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
                "activity_sequence": list(np.random.rand(10080).tolist())
            }
        )
        
        data = response.json()
        
        # Verify temporal separation
        assert data["current_state"]["depression_probability"] == 0.72  # NOW
        assert data["future_risk"]["depression_risk"] == 0.35  # TOMORROW
        assert data["temporal_concordance"] == 0.37  # Low agreement
        
    def test_temporal_endpoint_requires_activity_data(self, test_client):
        """Test that endpoint requires activity sequence for PAT."""
        response = test_client.post(
            "/api/v1/predictions/predict/temporal",
            json={
                "statistical_features": {
                    "sleep_duration": 7.5,
                    "sleep_efficiency": 0.85,
                    "sleep_timing_variance": 0.5,
                    "daily_steps": 8500,
                    "activity_variance": 1200,
                    "sedentary_hours": 8.5
                }
                # Missing activity_sequence
            }
        )
        
        assert response.status_code == 422  # Validation error
        
    def test_temporal_endpoint_validates_sequence_length(self, test_client):
        """Test that endpoint validates activity sequence is 7 days."""
        response = test_client.post(
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
                "activity_sequence": list(np.random.rand(100).tolist())  # Wrong length
            }
        )
        
        assert response.status_code == 422
        error = response.json()
        assert "10080" in str(error)  # Should mention expected length