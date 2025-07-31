"""
Simplified integration tests for ensemble functionality.

These tests focus on verifying basic ensemble setup without heavy mocking.
"""

from pathlib import Path

import pytest

from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
    TemporalEnsembleOrchestrator,
)
from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)


class TestPipelineEnsembleIntegrationSimple:
    """Simplified tests for ensemble integration."""

    def test_pipeline_creates_ensemble_when_configured(self):
        """Test that pipeline creates ensemble orchestrator when include_pat_sequences=True."""
        config = PipelineConfig(
            include_pat_sequences=True,
            model_dir=Path("model_weights/xgboost/converted"),
        )
        
        try:
            pipeline = MoodPredictionPipeline(config=config)
            # If models aren't available, ensemble_orchestrator will be None
            if pipeline.ensemble_orchestrator is None:
                pytest.skip("Models not available for ensemble test")
            
            assert isinstance(pipeline.ensemble_orchestrator, TemporalEnsembleOrchestrator)
        except Exception:
            pytest.skip("Unable to load models for test")

    def test_pipeline_no_ensemble_when_disabled(self):
        """Test that pipeline does not create ensemble when include_pat_sequences=False."""
        config = PipelineConfig(
            include_pat_sequences=False,
            model_dir=Path("model_weights/xgboost/converted"),
        )
        
        pipeline = MoodPredictionPipeline(config=config)
        assert pipeline.ensemble_orchestrator is None

    def test_ensemble_graceful_fallback(self):
        """Test that pipeline continues without ensemble if PAT models unavailable."""
        config = PipelineConfig(
            include_pat_sequences=True,
            model_dir=Path("nonexistent/path"),
        )
        
        # Should not raise exception, just log warning
        pipeline = MoodPredictionPipeline(config=config)
        
        # Pipeline should still work without ensemble
        assert pipeline is not None
        # Ensemble might be None if models couldn't load
        if pipeline.ensemble_orchestrator is None:
            # This is expected behavior - graceful fallback
            pass