"""
Test Sparse Window Strategy for XGBoost

Tests for finding windows with gaps in data, suitable for XGBoost
which can work with sparse data over 30-60 days.
"""

from datetime import date, datetime, timedelta

import pytest

from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState


class TestSparseWindowStrategy:
    """Test finding windows that allow gaps in data."""

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

    def test_finds_30_day_window_with_50_percent_coverage(self):
        """Should find window with exactly 50% data coverage over 30 days."""
        records = []
        # Create 15 days of data spread over 30 days (50% coverage)
        for day in range(1, 32, 2):  # Every other day, 1 to 31
            if day <= 31:
                records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseWindowStrategy,
        )

        strategy = SparseWindowStrategy()
        windows = strategy.find_windows(records, min_days=30, min_coverage=0.5)

        # Debug output
        if not windows:
            # Check what dates we have
            dates = sorted({r.start_date.date() for r in records})
            print(f"Dates with data: {len(dates)} days")
            print(f"First: {dates[0]}, Last: {dates[-1]}")
            print(f"Span: {(dates[-1] - dates[0]).days + 1} days")

        assert len(windows) >= 1
        # Check the first window
        window = windows[0]
        assert window.start_date == date(2025, 1, 1)
        assert window.end_date == date(2025, 1, 31)
        assert window.days_with_data == 16  # Days 1,3,5...31
        assert window.total_days == 31
        assert abs(window.coverage_ratio - 16/31) < 0.01  # ~0.516

    def test_rejects_window_below_minimum_coverage(self):
        """Should reject window with 40% coverage when 50% required."""
        records = []
        # Create 12 days of data over 30 days (40% coverage)
        for day in [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 30, 31]:
            if day <= 30:
                records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseWindowStrategy,
        )

        strategy = SparseWindowStrategy()
        windows = strategy.find_windows(records, min_days=30, min_coverage=0.5)

        assert len(windows) == 0

    def test_finds_multiple_valid_sparse_windows(self):
        """Should find all windows meeting sparse criteria."""
        records = []

        # Window 1: January - 20 days over 40 days (50% coverage)
        for day in range(1, 41, 2):
            if day <= 31:
                records.append(self.create_sleep_record(f"2025-01-{day:02d}"))
            else:
                records.append(self.create_sleep_record(f"2025-02-{day-31:02d}"))

        # Gap in February

        # Window 2: March-April - 35 days over 60 days (58% coverage)
        march_april_days = []
        for day in range(1, 61):
            if day % 5 != 0:  # Skip every 5th day
                if day <= 31:
                    records.append(self.create_sleep_record(f"2025-03-{day:02d}"))
                else:
                    records.append(self.create_sleep_record(f"2025-04-{day-31:02d}"))

        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseWindowStrategy,
        )

        strategy = SparseWindowStrategy()
        windows = strategy.find_windows(records, min_days=30, min_coverage=0.5)

        assert len(windows) >= 2
        # Windows should be sorted by end date (recency)
        # The most recent window should end in April
        assert windows[0].end_date.month == 4  # April

    def test_handles_dense_data_as_valid_sparse_window(self):
        """Should accept consecutive data as 100% coverage sparse window."""
        records = []
        # 45 consecutive days (100% coverage)
        for day in range(1, 46):
            if day <= 31:
                records.append(self.create_sleep_record(f"2025-01-{day:02d}"))
            else:
                records.append(self.create_sleep_record(f"2025-02-{day-31:02d}"))

        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseWindowStrategy,
        )

        strategy = SparseWindowStrategy()
        windows = strategy.find_windows(records, min_days=30, min_coverage=0.5)

        assert len(windows) >= 1
        assert windows[0].coverage_ratio == 1.0
        assert windows[0].days_with_data == 45

    def test_respects_minimum_days_parameter(self):
        """Should only find windows with enough total days."""
        records = []
        # Create data: days 1,2,3,4,6,7,8,9,11,12,13,14,16,17,18,19,21,22,23,24,26 = 21 days
        for day in range(1, 27):
            if day % 5 != 0:  # Skip every 5th day (5,10,15,20,25)
                records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseWindowStrategy,
        )

        strategy = SparseWindowStrategy()
        
        # Should not find window when min_days=30
        windows = strategy.find_windows(records, min_days=30, min_coverage=0.5)
        assert len(windows) == 0

        # Should find window when min_days=25
        windows = strategy.find_windows(records, min_days=25, min_coverage=0.5)
        
        # Debug output if no windows found
        if not windows:
            dates = sorted({r.start_date.date() for r in records})
            print(f"\nDebug info:")
            print(f"Total unique dates: {len(dates)}")
            print(f"Date range: {dates[0]} to {dates[-1]}")
            print(f"Span: {(dates[-1] - dates[0]).days + 1} days")
            print(f"Coverage: {len(dates)}/{(dates[-1] - dates[0]).days + 1} = {len(dates)/((dates[-1] - dates[0]).days + 1):.2%}")
        
        assert len(windows) >= 1  # Should find at least one window

    def test_sliding_window_finds_best_coverage(self):
        """Should use sliding window to find optimal coverage periods."""
        records = []
        
        # Poor coverage at start
        for day in [1, 7, 14, 21, 28]:
            records.append(self.create_sleep_record(f"2025-01-{day:02d}"))
        
        # Good coverage in middle (Feb-Mar)
        for day in range(1, 61):
            if day <= 28 and day % 3 != 0:  # 2 out of 3 days in Feb
                records.append(self.create_sleep_record(f"2025-02-{day:02d}"))
            elif day > 28 and day <= 59 and (day - 28) % 3 != 0:  # 2 out of 3 days in Mar (up to 31)
                records.append(self.create_sleep_record(f"2025-03-{day-28:02d}"))

        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseWindowStrategy,
        )

        strategy = SparseWindowStrategy()
        windows = strategy.find_windows(records, min_days=30, min_coverage=0.6)

        # Should find the Feb-Mar window with good coverage
        assert len(windows) >= 1
        best_window = max(windows, key=lambda w: w.coverage_ratio)
        assert best_window.coverage_ratio >= 0.6

    def test_real_world_xgboost_scenario(self):
        """Test typical XGBoost use case: 60 days with 65% coverage."""
        records = []
        
        # Simulate realistic Apple Watch usage over 3 months
        # Week 1-2: Good compliance
        for day in range(1, 15):
            records.append(self.create_sleep_record(f"2025-01-{day:02d}"))
        
        # Week 3-4: Sporadic (vacation?)
        for day in [17, 20, 24, 28]:
            records.append(self.create_sleep_record(f"2025-01-{day:02d}"))
        
        # February: Better compliance with some gaps
        for day in range(1, 29):
            if day not in [5, 6, 12, 13, 19, 20, 26, 27]:  # Weekend gaps
                records.append(self.create_sleep_record(f"2025-02-{day:02d}"))
        
        # March: Good compliance
        for day in range(1, 20):
            if day not in [7, 14]:  # Occasional misses
                records.append(self.create_sleep_record(f"2025-03-{day:02d}"))

        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseWindowStrategy,
        )

        strategy = SparseWindowStrategy()
        windows = strategy.find_windows(records, min_days=60, min_coverage=0.5)

        # Should find at least one 60-day window
        assert len(windows) >= 1
        
        # Check the best window
        best_window = max(windows, key=lambda w: w.coverage_ratio)
        assert best_window.total_days >= 60
        assert best_window.coverage_ratio >= 0.5
        assert best_window.coverage_ratio <= 1.0


class TestSparseDataWindow:
    """Test the SparseDataWindow value object."""

    def test_creates_valid_sparse_window(self):
        """Should create window with coverage information."""
        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseDataWindow,
        )

        window = SparseDataWindow(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 30),
            total_days=30,
            days_with_data=20,
            coverage_ratio=0.67,
        )

        assert window.start_date == date(2025, 1, 1)
        assert window.end_date == date(2025, 1, 30)
        assert window.total_days == 30
        assert window.days_with_data == 20
        assert window.coverage_ratio == 0.67

    def test_calculates_spans_days(self):
        """Should calculate calendar days in range."""
        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseDataWindow,
        )

        window = SparseDataWindow(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            total_days=31,
            days_with_data=20,
            coverage_ratio=0.65,
        )

        assert window.spans_days == 31

    def test_validates_coverage_ratio(self):
        """Should ensure coverage ratio is valid."""
        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseDataWindow,
        )

        # Coverage > 1.0 should fail
        with pytest.raises(ValueError, match="Coverage ratio must be between 0 and 1"):
            SparseDataWindow(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 30),
                total_days=30,
                days_with_data=40,  # More than total!
                coverage_ratio=1.33,
            )

    def test_validates_days_consistency(self):
        """Should ensure days_with_data <= total_days."""
        from big_mood_detector.domain.services.sparse_window_strategy import (
            SparseDataWindow,
        )

        with pytest.raises(ValueError, match="Days with data cannot exceed total days"):
            SparseDataWindow(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 30),
                total_days=30,
                days_with_data=40,
                coverage_ratio=0.5,
            )