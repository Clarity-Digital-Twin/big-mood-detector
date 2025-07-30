"""
Test Dual Model Window Strategy

Tests for coordinating window selection between PAT (7 consecutive days)
and XGBoost (30+ sparse days) models.
"""

from datetime import date, datetime, timedelta

from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState


class TestDualModelWindowStrategy:
    """Test coordinating window selection for both models."""

    def create_sleep_record(self, date_str: str) -> SleepRecord:
        """Helper to create sleep records."""
        start = datetime.fromisoformat(f"{date_str}T22:00:00")
        end = start + timedelta(hours=8)
        return SleepRecord(
            source_name="Apple Watch",
            start_date=start,
            end_date=end,
            state=SleepState.ASLEEP,
        )

    def test_finds_overlapping_windows_when_available(self):
        """Should identify when both models can use same period."""
        records = []

        # Create 45 consecutive days (good for both models)
        for day in range(1, 46):
            if day <= 31:
                records.append(self.create_sleep_record(f"2025-01-{day:02d}"))
            else:
                records.append(self.create_sleep_record(f"2025-02-{day-31:02d}"))

        from big_mood_detector.domain.services.dual_model_window_strategy import (
            DualModelWindowStrategy,
        )

        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(records)

        assert result.can_run_pat is True
        assert result.can_run_xgboost is True
        assert result.can_run_ensemble is True
        assert len(result.pat_windows) >= 1
        assert len(result.xgboost_windows) >= 1
        assert result.optimal_window is not None

    def test_handles_pat_only_scenario(self):
        """Should handle when only PAT has valid windows (7 consecutive days)."""
        records = []

        # Create only 8 consecutive days (not enough for XGBoost)
        for day in range(1, 9):
            records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        from big_mood_detector.domain.services.dual_model_window_strategy import (
            DualModelWindowStrategy,
        )

        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(records)

        assert result.can_run_pat is True
        assert result.can_run_xgboost is False
        assert result.can_run_ensemble is False
        assert len(result.pat_windows) >= 1
        assert len(result.xgboost_windows) == 0

    def test_handles_xgboost_only_scenario(self):
        """Should handle when only XGBoost has valid windows (sparse 30+ days)."""
        records = []

        # Create sparse data: 4 days per week for 10 weeks = 40 days over 70 days (57% coverage)
        base_date = date(2025, 1, 1)
        for week in range(10):
            # Monday, Tuesday, Thursday, Friday pattern
            for day_offset in [0, 1, 3, 4]:
                current_date = base_date + timedelta(weeks=week, days=day_offset)
                records.append(self.create_sleep_record(str(current_date)))

        from big_mood_detector.domain.services.dual_model_window_strategy import (
            DualModelWindowStrategy,
        )

        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(records)

        assert result.can_run_pat is False  # No 7 consecutive days
        assert result.can_run_xgboost is True  # Has 30+ days sparse
        assert result.can_run_ensemble is False
        assert len(result.pat_windows) == 0
        assert len(result.xgboost_windows) >= 1

    def test_selects_optimal_overlapping_window(self):
        """Should prefer windows where both models can run."""
        records = []

        # Window 1: January 1-7 (PAT only, 7 days)
        for day in range(1, 8):
            records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        # Gap

        # Window 2: March-April (45 days, good for both)
        for day in range(1, 46):
            if day <= 31:
                records.append(self.create_sleep_record(f"2025-03-{day:02d}"))
            else:
                records.append(self.create_sleep_record(f"2025-04-{day-31:02d}"))

        from big_mood_detector.domain.services.dual_model_window_strategy import (
            DualModelWindowStrategy,
        )

        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(records)

        assert result.can_run_ensemble is True
        assert result.optimal_window is not None
        # Should select March-April window where both can run
        assert result.optimal_window.start_date.month == 3

    def test_provides_clear_reason_when_no_windows_available(self):
        """Should explain why models cannot run."""
        records = []

        # Only 5 sporadic days (not enough for either model)
        for day in [1, 5, 10, 15, 20]:
            records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        from big_mood_detector.domain.services.dual_model_window_strategy import (
            DualModelWindowStrategy,
        )

        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(records)

        assert result.can_run_pat is False
        assert result.can_run_xgboost is False
        assert result.can_run_ensemble is False
        assert "PAT requires 7 consecutive days" in result.selection_reason
        assert "XGBoost requires 30+ days" in result.selection_reason

    def test_real_world_mixed_data_scenario(self):
        """Test with realistic Apple Watch usage patterns."""
        records = []

        # January: Good compliance (25 days)
        for day in range(1, 32):
            if day not in [6, 7, 13, 14, 20, 21]:  # Skip weekends
                records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        # February: Poor compliance (10 days)
        for day in [1, 5, 8, 12, 15, 18, 22, 25, 27, 28]:
            records.append(self.create_sleep_record(f"2025-02-{day:02d}"))

        # March: Excellent compliance (all days)
        for day in range(1, 32):
            records.append(self.create_sleep_record(f"2025-03-{day:02d}"))

        # April: Moderate compliance (20 days)
        for day in range(1, 31):
            if day % 3 != 0:  # Skip every 3rd day
                records.append(self.create_sleep_record(f"2025-04-{day:02d}"))

        from big_mood_detector.domain.services.dual_model_window_strategy import (
            DualModelWindowStrategy,
        )

        strategy = DualModelWindowStrategy()
        result = strategy.analyze_windows(records)

        # Should find windows for both models
        assert result.can_run_pat is True  # March has 31 consecutive days
        assert result.can_run_xgboost is True  # Multiple 30+ day windows
        assert result.can_run_ensemble is True

        # Should find a window where both models can run
        assert result.optimal_window is not None
        # The optimal window should be within a period that has good coverage
        assert result.optimal_window.days_count >= 7  # At least PAT minimum


class TestWindowAnalysisResult:
    """Test the result object returned by dual analysis."""

    def test_creates_valid_result(self):
        """Should create result with all required fields."""
        from big_mood_detector.domain.services.dual_model_window_strategy import (
            WindowAnalysisResult,
        )
        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseDataWindow,
        )
        from big_mood_detector.domain.services.window_selection_strategy import (
            DateWindow,
        )

        pat_window = DateWindow(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            days_count=7,
            data_quality=1.0,
        )

        xgb_window = SparseDataWindow(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            total_days=31,
            days_with_data=25,
            coverage_ratio=0.81,
        )

        result = WindowAnalysisResult(
            pat_windows=[pat_window],
            xgboost_windows=[xgb_window],
            optimal_window=pat_window,
            selection_reason="Both models have valid windows in same period",
            can_run_pat=True,
            can_run_xgboost=True,
            can_run_ensemble=True,
        )

        assert len(result.pat_windows) == 1
        assert len(result.xgboost_windows) == 1
        assert result.optimal_window == pat_window
        assert result.can_run_ensemble is True
