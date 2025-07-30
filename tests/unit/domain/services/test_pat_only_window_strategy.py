"""Unit tests for PAT-only window selection scenarios."""

from datetime import date, datetime, timedelta
import pytest

from big_mood_detector.domain.services.dual_model_window_strategy import (
    DualModelWindowStrategy,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState


class TestPATOnlyWindowStrategy:
    """Test cases for PAT-only window selection scenarios."""
    
    def test_pat_only_with_exactly_7_consecutive_days(self):
        """Test window selection with exactly 7 consecutive days of data."""
        # Create sleep records for exactly 7 consecutive days
        base_date = date(2025, 1, 15)
        sleep_records = []
        
        for i in range(7):
            current_date = base_date + timedelta(days=i)
            # Sleep from 10 PM to 6 AM
            start = datetime.combine(current_date - timedelta(days=1), datetime.min.time()).replace(hour=22)
            end = datetime.combine(current_date, datetime.min.time()).replace(hour=6)
            
            sleep_records.append(
                SleepRecord(
                    source_name="Test",
                    start_date=start,
                    end_date=end,
                    state=SleepState.ASLEEP
                )
            )
        
        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(sleep_records)
        
        # Should be able to run PAT (7 consecutive days)
        assert result.can_run_pat is True
        # Should NOT be able to run XGBoost (needs 30+ days)
        assert result.can_run_xgboost is False
        # Should NOT be able to run ensemble
        assert result.can_run_ensemble is False
        # Selection reason should indicate PAT-only mode
        assert "PAT only" in result.selection_reason
        assert result.optimal_window is not None
        assert result.optimal_window.days_count == 7
    
    def test_pat_with_more_than_7_but_less_than_30_days(self):
        """Test with 14 consecutive days - PAT yes, XGBoost no."""
        base_date = date(2025, 1, 15)
        sleep_records = []
        
        # Create 14 consecutive days
        for i in range(14):
            current_date = base_date + timedelta(days=i)
            start = datetime.combine(current_date - timedelta(days=1), datetime.min.time()).replace(hour=22)
            end = datetime.combine(current_date, datetime.min.time()).replace(hour=6)
            
            sleep_records.append(
                SleepRecord(
                    source_name="Test",
                    start_date=start,
                    end_date=end,
                    state=SleepState.ASLEEP
                )
            )
        
        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(sleep_records)
        
        assert result.can_run_pat is True
        assert result.can_run_xgboost is False  # Still less than 30 days
        assert len(result.pat_windows) > 0
        # PAT windows contain the full date range, not sliding windows
        assert result.optimal_window is not None
        assert result.optimal_window.days_count == 14
    
    def test_pat_fails_with_only_6_consecutive_days(self):
        """Test that PAT cannot run with only 6 consecutive days."""
        base_date = date(2025, 1, 15)
        sleep_records = []
        
        # Only 6 consecutive days
        for i in range(6):
            current_date = base_date + timedelta(days=i)
            start = datetime.combine(current_date - timedelta(days=1), datetime.min.time()).replace(hour=22)
            end = datetime.combine(current_date, datetime.min.time()).replace(hour=6)
            
            sleep_records.append(
                SleepRecord(
                    source_name="Test",
                    start_date=start,
                    end_date=end,
                    state=SleepState.ASLEEP
                )
            )
        
        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(sleep_records)
        
        assert result.can_run_pat is False
        assert result.can_run_xgboost is False
        assert "PAT requires 7 consecutive days" in result.selection_reason
        assert "Insufficient data" in result.selection_reason
    
    def test_pat_only_mode_with_gaps_in_data(self):
        """Test PAT selection with gaps - should find longest consecutive stretch."""
        base_date = date(2025, 1, 1)
        sleep_records = []
        
        # First 5 days
        for i in range(5):
            current_date = base_date + timedelta(days=i)
            start = datetime.combine(current_date - timedelta(days=1), datetime.min.time()).replace(hour=22)
            end = datetime.combine(current_date, datetime.min.time()).replace(hour=6)
            sleep_records.append(
                SleepRecord(source_name="Test", start_date=start, end_date=end, state=SleepState.ASLEEP)
            )
        
        # Gap of 3 days
        
        # Then 8 consecutive days
        for i in range(8):
            current_date = base_date + timedelta(days=8 + i)
            start = datetime.combine(current_date - timedelta(days=1), datetime.min.time()).replace(hour=22)
            end = datetime.combine(current_date, datetime.min.time()).replace(hour=6)
            sleep_records.append(
                SleepRecord(source_name="Test", start_date=start, end_date=end, state=SleepState.ASLEEP)
            )
        
        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(sleep_records)
        
        # Should find the 8-day consecutive stretch
        assert result.can_run_pat is True
        assert result.can_run_xgboost is False  # Only 13 total days
        # Should select from the 8-day window
        assert result.optimal_window is not None
        assert result.optimal_window.days_count >= 7