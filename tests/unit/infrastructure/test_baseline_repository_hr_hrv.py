"""
Test baseline repositories handle HR/HRV fields correctly.
"""
import pytest
from pathlib import Path
from datetime import date, datetime
import shutil

from big_mood_detector.infrastructure.repositories.file_baseline_repository import (
    FileBaselineRepository,
)
from big_mood_detector.domain.repositories.baseline_repository_interface import UserBaseline


class TestBaselineRepositoryHRHRV:
    """Test that baseline repositories handle HR/HRV fields correctly."""
    
    @pytest.fixture(autouse=True)
    def cleanup_test_files(self):
        """Clean up test files before and after each test."""
        test_path = Path("./test_hr_hrv_baselines")
        
        # Clean before test
        if test_path.exists():
            shutil.rmtree(test_path)
        
        yield
        
        # Clean after test
        if test_path.exists():
            shutil.rmtree(test_path)
    
    def test_file_repository_saves_and_retrieves_hr_hrv_fields(self):
        """Test FileBaselineRepository handles HR/HRV fields."""
        repo = FileBaselineRepository(Path("./test_hr_hrv_baselines"))
        
        # Create baseline with specific HR/HRV values
        baseline = UserBaseline(
            user_id="hr_test_user",
            baseline_date=date(2024, 1, 15),
            sleep_mean=7.5,
            sleep_std=1.2,
            activity_mean=8000.0,
            activity_std=2000.0,
            circadian_phase=22.0,
            heart_rate_mean=75.0,  # Custom value
            heart_rate_std=8.0,    # Custom value
            hrv_mean=42.0,         # Custom value
            hrv_std=12.0,          # Custom value
            last_updated=datetime(2024, 1, 15, 10, 0),
            data_points=30
        )
        
        # Save baseline
        repo.save_baseline(baseline)
        
        # Retrieve baseline
        retrieved = repo.get_baseline("hr_test_user")
        
        # Verify all fields including HR/HRV
        assert retrieved is not None
        assert retrieved.heart_rate_mean == 75.0
        assert retrieved.heart_rate_std == 8.0
        assert retrieved.hrv_mean == 42.0
        assert retrieved.hrv_std == 12.0
    
    def test_file_repository_backward_compatibility(self):
        """Test FileBaselineRepository handles old baselines without HR/HRV."""
        repo = FileBaselineRepository(Path("./test_hr_hrv_baselines"))
        
        # Create and save a baseline with HR/HRV
        baseline = UserBaseline(
            user_id="backward_compat_user",
            baseline_date=date(2024, 1, 15),
            sleep_mean=7.5,
            sleep_std=1.2,
            activity_mean=8000.0,
            activity_std=2000.0,
            circadian_phase=22.0,
            last_updated=datetime(2024, 1, 15, 10, 0),
            data_points=30
        )
        repo.save_baseline(baseline)
        
        # Manually modify the saved file to simulate old format (no HR/HRV fields)
        import json
        history_file = Path("./test_hr_hrv_baselines/backward_compat_user/baseline_history.json")
        with open(history_file, 'r') as f:
            data = json.load(f)
        
        # Remove HR/HRV fields to simulate old format
        for entry in data:
            entry.pop('heart_rate_mean', None)
            entry.pop('heart_rate_std', None)
            entry.pop('hrv_mean', None)
            entry.pop('hrv_std', None)
        
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Try to load the old format baseline
        retrieved = repo.get_baseline("backward_compat_user")
        
        # Should use default values for missing HR/HRV fields
        assert retrieved is not None
        assert retrieved.heart_rate_mean == 70.0  # Default
        assert retrieved.heart_rate_std == 10.0   # Default
        assert retrieved.hrv_mean == 50.0        # Default
        assert retrieved.hrv_std == 15.0         # Default