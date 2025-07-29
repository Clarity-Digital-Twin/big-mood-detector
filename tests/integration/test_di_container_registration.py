"""
Tests for dependency injection container registration.

These tests verify that all required services are properly registered
and can be resolved.
"""

import pytest
from unittest.mock import Mock, patch

from big_mood_detector.domain.services.pat_encoder import PATEncoderInterface
from big_mood_detector.domain.services.pat_predictor import PATPredictorInterface
from big_mood_detector.infrastructure.di import get_container
from big_mood_detector.infrastructure.di.container import (
    Container,
    DependencyNotFoundError,
)
from big_mood_detector.infrastructure.ml_models.pat_production_loader import (
    ProductionPATLoader,
)


class TestDIContainerRegistration:
    """Verify all services are properly registered in DI container."""
    
    def test_container_exists_and_initializes(self):
        """Basic test that container can be created."""
        container = get_container()
        assert container is not None
        assert isinstance(container, Container)
    
    def test_pat_encoder_interface_registered(self):
        """PAT encoder interface must be resolvable."""
        container = get_container()
        
        # This will FAIL - interface not registered
        # Currently raises DependencyNotFoundError
        encoder = container.resolve(PATEncoderInterface)
        
        assert encoder is not None
        assert isinstance(encoder, PATEncoderInterface)
    
    def test_pat_predictor_interface_registered(self):
        """PAT predictor interface must be resolvable."""
        container = get_container()
        
        # This will FAIL - interface not registered
        predictor = container.resolve(PATPredictorInterface)
        
        assert predictor is not None
        assert isinstance(predictor, PATPredictorInterface)
    
    def test_pat_interfaces_resolve_to_same_instance(self):
        """Both PAT interfaces should resolve to the same singleton instance."""
        container = get_container()
        
        # This will FAIL - not registered
        encoder = container.resolve(PATEncoderInterface)
        predictor = container.resolve(PATPredictorInterface)
        
        # Should be the same instance (ProductionPATLoader implements both)
        assert encoder is predictor, \
            "PAT encoder and predictor should be the same instance"
        assert isinstance(encoder, ProductionPATLoader)
    
    def test_xgboost_predictor_registered(self):
        """XGBoost predictor should be registered."""
        from big_mood_detector.infrastructure.ml_models.xgboost_models import (
            XGBoostMoodPredictor,
        )
        
        container = get_container()
        
        # This might work if XGBoost is registered
        predictor = container.resolve(XGBoostMoodPredictor)
        
        assert predictor is not None
        assert isinstance(predictor, XGBoostMoodPredictor)
    
    def test_container_resolution_failures_are_clear(self):
        """When resolution fails, error should be informative."""
        container = get_container()
        
        # Try to resolve non-existent service
        with pytest.raises(DependencyNotFoundError) as exc_info:
            container.resolve(type("NonExistentService", (), {}))
        
        # Error should mention the service name
        assert "NonExistentService" in str(exc_info.value)
    
    def test_api_dependencies_can_resolve_services(self):
        """API dependencies module should successfully get services."""
        from big_mood_detector.interfaces.api.dependencies import (
            get_ensemble_orchestrator,
        )
        
        # Mock successful model loading
        with patch('big_mood_detector.infrastructure.ml_models.xgboost_models.XGBoostMoodPredictor') as mock_xgb:
            mock_xgb.return_value.load_models.return_value = True
            mock_xgb.return_value.is_loaded = True
            
            # This will FAIL - PAT services not registered
            orchestrator = get_ensemble_orchestrator()
            
            # Should get a valid orchestrator, not None
            assert orchestrator is not None, \
                "Should create ensemble orchestrator when services available"
    
    def test_service_registration_module_exists(self):
        """There should be a module for registering services."""
        # This will FAIL - module doesn't exist yet
        from big_mood_detector.infrastructure.di.service_registration import (
            register_ml_services,
        )
        
        container = Container()
        register_ml_services(container)
        
        # After registration, should be able to resolve
        encoder = container.resolve(PATEncoderInterface)
        assert encoder is not None
    
    def test_container_singleton_behavior(self):
        """Services registered as singletons should return same instance."""
        container = get_container()
        
        # Get PAT encoder twice
        encoder1 = container.resolve(PATEncoderInterface)
        encoder2 = container.resolve(PATEncoderInterface)
        
        # Should be exact same instance
        assert encoder1 is encoder2, "Singleton should return same instance"
    
    def test_container_with_mock_registration(self):
        """Test that we can register mocks for testing."""
        container = Container()
        
        # Register mocks
        mock_encoder = Mock(spec=PATEncoderInterface)
        mock_predictor = Mock(spec=PATPredictorInterface)
        
        container.register(PATEncoderInterface, lambda: mock_encoder)
        container.register(PATPredictorInterface, lambda: mock_predictor)
        
        # Resolve should return our mocks
        resolved_encoder = container.resolve(PATEncoderInterface)
        resolved_predictor = container.resolve(PATPredictorInterface)
        
        assert resolved_encoder is mock_encoder
        assert resolved_predictor is mock_predictor