"""
Test that the PAT loader encode() method fix works.

This verifies that ProductionPATLoader now implements the encode()
method required by the temporal ensemble orchestrator.
"""

import numpy as np
import pytest

from big_mood_detector.domain.services.pat_encoder import PATEncoderInterface
from big_mood_detector.infrastructure.ml_models.pat_production_loader import (
    ProductionPATLoader,
)


class TestPATEncodeFix:
    """Verify that the PAT encode bug is fixed."""
    
    def test_production_pat_loader_has_encode_method(self):
        """
        ProductionPATLoader now has the encode() method.
        
        This was missing in v0.5.4, causing ensemble predictions to fail.
        """
        loader = ProductionPATLoader(skip_loading=True)
        
        # Should have encode method
        assert hasattr(loader, 'encode'), "PAT loader should have encode() method"
        
        # Should implement PATEncoderInterface
        assert isinstance(loader, PATEncoderInterface), "Should implement PATEncoderInterface"
    
    def test_encode_accepts_7x1440_shape(self):
        """
        encode() should accept (7, 1440) shaped input.
        
        This is what the temporal ensemble provides.
        """
        loader = ProductionPATLoader(skip_loading=True)
        
        # Create dummy 7-day sequence
        sequence = np.zeros((7, 1440), dtype=np.float32)
        
        # Should not raise error
        try:
            embeddings = loader.encode(sequence)
            # In test mode, should return 96-dim vector
            assert embeddings.shape == (96,), f"Expected (96,) embeddings, got {embeddings.shape}"
        except Exception as e:
            pytest.fail(f"encode() failed with (7, 1440) input: {e}")
    
    def test_encode_accepts_flattened_shape(self):
        """
        encode() should also accept flattened (10080,) input.
        """
        loader = ProductionPATLoader(skip_loading=True)
        
        # Create flattened sequence
        sequence = np.zeros(10080, dtype=np.float32)
        
        # Should not raise error
        try:
            embeddings = loader.encode(sequence)
            assert embeddings.shape == (96,), f"Expected (96,) embeddings, got {embeddings.shape}"
        except Exception as e:
            pytest.fail(f"encode() failed with (10080,) input: {e}")
    
    def test_validate_sequence_works(self):
        """
        validate_sequence() should correctly validate input shapes.
        """
        loader = ProductionPATLoader(skip_loading=True)
        
        # Valid shapes
        assert loader.validate_sequence(np.zeros((7, 1440), dtype=np.float32))
        assert loader.validate_sequence(np.zeros(10080, dtype=np.float32))
        
        # Invalid shapes
        assert not loader.validate_sequence(np.zeros((6, 1440), dtype=np.float32))
        assert not loader.validate_sequence(np.zeros(9000, dtype=np.float32))
        assert not loader.validate_sequence(np.zeros((7, 1440, 1), dtype=np.float32))
    
    def test_temporal_ensemble_can_use_loader(self):
        """
        Integration test: Temporal ensemble can now use the loader.
        """
        from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
            TemporalEnsembleOrchestrator,
        )
        
        # Create loader
        pat_loader = ProductionPATLoader(skip_loading=True)
        
        # Mock XGBoost predictor
        class MockXGBoost:
            def predict_episode_tomorrow(self, features):
                return {"depression": 0.1, "mania": 0.1, "hypomania": 0.1}
        
        # Create orchestrator - should not fail
        orchestrator = TemporalEnsembleOrchestrator(
            pat_encoder=pat_loader,  # Can use as encoder now!
            pat_predictor=pat_loader,  # Also predictor
            xgboost_predictor=MockXGBoost(),
        )
        
        # Test prediction
        pat_sequence = np.zeros((7, 1440), dtype=np.float32)
        xgb_features = np.zeros(36, dtype=np.float32)
        
        # Should not raise AttributeError anymore
        try:
            assessment = orchestrator.assess_temporal_mood_state(
                pat_sequence=pat_sequence,
                statistical_features=xgb_features,
            )
            assert assessment is not None, "Should return assessment"
        except AttributeError as e:
            if "encode" in str(e):
                pytest.fail(f"encode() method still missing: {e}")