"""
Test Window Selection Strategies

Clean TDD tests for window selection logic that finds valid
consecutive data windows in sparse health records.
"""

from datetime import date, datetime, timedelta

import pytest

from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.window_selection_strategy import (
    AllValidWindowsStrategy,
    BestQualityWindowStrategy,
    DateWindow,
    MostRecentValidWindowStrategy,
    WindowSelectionStrategy,
)


class TestWindowSelectionStrategy:
    """Test the abstract interface."""

    def test_interface_requires_implementation(self):
        """Should not be instantiable directly."""
        with pytest.raises(TypeError):
            WindowSelectionStrategy()


class TestDateWindow:
    """Test the DateWindow value object."""

    def test_creates_valid_window(self):
        """Should create window with start and end dates."""
        window = DateWindow(
            start_date=date(2025, 6, 26),
            end_date=date(2025, 7, 2),
            days_count=7,
            data_quality=0.95,
        )

        assert window.start_date == date(2025, 6, 26)
        assert window.end_date == date(2025, 7, 2)
        assert window.days_count == 7
        assert window.data_quality == 0.95

    def test_validates_date_order(self):
        """Should ensure start <= end."""
        with pytest.raises(ValueError, match="Start date must be before end date"):
            DateWindow(
                start_date=date(2025, 7, 2),
                end_date=date(2025, 6, 26),
                days_count=7,
                data_quality=1.0,
            )

    def test_validates_quality_range(self):
        """Should ensure quality is 0-1."""
        with pytest.raises(ValueError, match="Data quality must be between 0 and 1"):
            DateWindow(
                start_date=date(2025, 6, 26),
                end_date=date(2025, 7, 2),
                days_count=7,
                data_quality=1.5,
            )


class TestMostRecentValidWindowStrategy:
    """Test finding the most recent valid window."""

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

    def test_finds_most_recent_7_day_window(self):
        """Should find the most recent window with 7+ consecutive days."""
        records = [
            # Old window (January)
            *[self.create_sleep_record(f"2025-01-{day:02d}") for day in range(1, 8)],
            # Gap
            # Recent window (June-July)
            *[self.create_sleep_record(f"2025-06-{day:02d}") for day in range(26, 31)],
            *[self.create_sleep_record(f"2025-07-{day:02d}") for day in range(1, 3)],
        ]

        strategy = MostRecentValidWindowStrategy()
        windows = strategy.find_windows(records, min_days=7)

        assert len(windows) == 1
        assert windows[0].start_date == date(2025, 6, 26)
        assert windows[0].end_date == date(2025, 7, 2)
        assert windows[0].days_count == 7

    def test_returns_empty_when_no_valid_windows(self):
        """Should return empty list when no consecutive windows exist."""
        records = [
            # Sporadic data - no 7 consecutive days
            self.create_sleep_record("2025-06-01"),
            self.create_sleep_record("2025-06-05"),
            self.create_sleep_record("2025-06-10"),
            self.create_sleep_record("2025-06-15"),
            self.create_sleep_record("2025-06-20"),
            self.create_sleep_record("2025-06-25"),
        ]

        strategy = MostRecentValidWindowStrategy()
        windows = strategy.find_windows(records, min_days=7)

        assert len(windows) == 0

    def test_handles_multiple_valid_windows(self):
        """Should return only the most recent when multiple windows exist."""
        records = [
            # Window 1: January
            *[self.create_sleep_record(f"2025-01-{day:02d}") for day in range(1, 15)],
            # Window 2: March
            *[self.create_sleep_record(f"2025-03-{day:02d}") for day in range(10, 20)],
            # Window 3: June (most recent)
            *[self.create_sleep_record(f"2025-06-{day:02d}") for day in range(20, 27)],
        ]

        strategy = MostRecentValidWindowStrategy()
        windows = strategy.find_windows(records, min_days=7)

        assert len(windows) == 1
        assert windows[0].start_date == date(2025, 6, 20)

    def test_respects_minimum_days_parameter(self):
        """Should only find windows meeting minimum days requirement."""
        records = [
            # 5-day window (too short for min_days=7)
            *[self.create_sleep_record(f"2025-06-{day:02d}") for day in range(1, 6)],
            # 10-day window (valid)
            *[self.create_sleep_record(f"2025-07-{day:02d}") for day in range(1, 11)],
        ]

        strategy = MostRecentValidWindowStrategy()

        # With min_days=7, should only find July window
        windows = strategy.find_windows(records, min_days=7)
        assert len(windows) == 1
        assert windows[0].start_date == date(2025, 7, 1)

        # With min_days=5, should find both
        windows = strategy.find_windows(records, min_days=5)
        assert len(windows) == 1  # Still only most recent
        assert windows[0].start_date == date(2025, 7, 1)


class TestBestQualityWindowStrategy:
    """Test finding the highest quality window."""

    def create_sleep_record(
        self, date_str: str, duration_hours: float = 8
    ) -> SleepRecord:
        """Helper to create sleep records with variable duration."""
        start = datetime.fromisoformat(f"{date_str}T22:00:00")
        end = start + timedelta(hours=duration_hours)
        return SleepRecord(
            source_name="Apple Watch",
            start_date=start,
            end_date=end,
            state=SleepState.ASLEEP,
        )

    def test_finds_window_with_best_data_quality(self):
        """Should find window with most consistent sleep duration."""
        records = [
            # Window 1: Inconsistent sleep (4-12 hours)
            self.create_sleep_record("2025-01-01", 4),
            self.create_sleep_record("2025-01-02", 12),
            self.create_sleep_record("2025-01-03", 6),
            self.create_sleep_record("2025-01-04", 10),
            self.create_sleep_record("2025-01-05", 5),
            self.create_sleep_record("2025-01-06", 11),
            self.create_sleep_record("2025-01-07", 7),
            # Window 2: Consistent sleep (7-8 hours) - BEST QUALITY
            *[self.create_sleep_record(f"2025-03-{day:02d}", 7.5) for day in range(10, 17)],
            # Window 3: Moderate consistency
            *[self.create_sleep_record(f"2025-06-{day:02d}", 6 + (day % 3)) for day in range(20, 27)],
        ]

        strategy = BestQualityWindowStrategy()
        windows = strategy.find_windows(records, min_days=7)

        assert len(windows) == 1
        assert windows[0].start_date == date(2025, 3, 10)
        assert windows[0].data_quality > 0.8  # High quality due to consistency

    def test_quality_considers_data_completeness(self):
        """Should factor in missing data within windows."""
        records = [
            # Window with gap (missing day 4)
            self.create_sleep_record("2025-01-01"),
            self.create_sleep_record("2025-01-02"),
            self.create_sleep_record("2025-01-03"),
            # Missing 2025-01-04
            self.create_sleep_record("2025-01-05"),
            self.create_sleep_record("2025-01-06"),
            self.create_sleep_record("2025-01-07"),
            self.create_sleep_record("2025-01-08"),
            # Complete window (better quality)
            *[self.create_sleep_record(f"2025-02-{day:02d}") for day in range(1, 8)],
        ]

        strategy = BestQualityWindowStrategy()
        windows = strategy.find_windows(records, min_days=7)

        assert len(windows) == 1
        assert windows[0].start_date == date(2025, 2, 1)  # Complete window wins


class TestAllValidWindowsStrategy:
    """Test finding all valid windows."""

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

    def test_finds_all_valid_windows(self):
        """Should return all windows meeting criteria."""
        records = [
            # Window 1: 7 days
            *[self.create_sleep_record(f"2025-01-{day:02d}") for day in range(1, 8)],
            # Gap
            # Window 2: 10 days
            *[self.create_sleep_record(f"2025-03-{day:02d}") for day in range(10, 20)],
            # Gap
            # Window 3: 14 days
            *[self.create_sleep_record(f"2025-06-{day:02d}") for day in range(15, 29)],
        ]

        strategy = AllValidWindowsStrategy()
        windows = strategy.find_windows(records, min_days=7)

        assert len(windows) == 3
        assert windows[0].start_date == date(2025, 6, 15)  # Most recent first
        assert windows[1].start_date == date(2025, 3, 10)
        assert windows[2].start_date == date(2025, 1, 1)

    def test_excludes_windows_below_threshold(self):
        """Should not include windows shorter than min_days."""
        records = [
            # 5 days (too short)
            *[self.create_sleep_record(f"2025-01-{day:02d}") for day in range(1, 6)],
            # 7 days (valid)
            *[self.create_sleep_record(f"2025-02-{day:02d}") for day in range(1, 8)],
            # 3 days (too short)
            *[self.create_sleep_record(f"2025-03-{day:02d}") for day in range(1, 4)],
        ]

        strategy = AllValidWindowsStrategy()
        windows = strategy.find_windows(records, min_days=7)

        assert len(windows) == 1
        assert windows[0].start_date == date(2025, 2, 1)

    def test_handles_continuous_data(self):
        """Should find single window for continuous data."""
        records = [
            # Long continuous stretch
            *[self.create_sleep_record(f"2025-01-{day:02d}") for day in range(1, 21)],
        ]

        strategy = AllValidWindowsStrategy()
        windows = strategy.find_windows(records, min_days=7)

        # Should find the entire 20-day window as one
        assert len(windows) == 1
        assert windows[0].days_count == 20
        assert windows[0].start_date == date(2025, 1, 1)
        assert windows[0].end_date == date(2025, 1, 20)


class TestRealWorldScenarios:
    """Test with patterns from actual user data."""

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

    def test_handles_sporadic_apple_watch_usage(self):
        """User wears watch 2-3 nights per week."""
        records = []
        start_date = date(2025, 1, 1)

        # Simulate 3 months of sporadic usage
        for day_offset in range(90):
            current_date = start_date + timedelta(days=day_offset)
            # Wear watch ~40% of nights (sporadic)
            if day_offset % 7 in [1, 3, 5]:  # Mon, Wed, Fri pattern
                records.append(self.create_sleep_record(str(current_date)))

        strategy = MostRecentValidWindowStrategy()
        windows = strategy.find_windows(records, min_days=7)

        # Should not find any 7-consecutive-day windows
        assert len(windows) == 0

    def test_handles_vacation_gaps(self):
        """User has consistent usage with vacation gaps."""
        records = []

        # January: consistent usage
        for day in range(1, 32):
            records.append(self.create_sleep_record(f"2025-01-{day:02d}"))

        # February 1-14: vacation (no watch)
        # February 15-28: back to consistent usage
        for day in range(15, 29):
            records.append(self.create_sleep_record(f"2025-02-{day:02d}"))

        # March: consistent usage
        for day in range(1, 32):
            if day <= 31:  # March has 31 days
                records.append(self.create_sleep_record(f"2025-03-{day:02d}"))

        strategy = AllValidWindowsStrategy()
        windows = strategy.find_windows(records, min_days=7)

        # Should find 2 windows: January (31 days) and Feb15-Mar31 (45 days continuous)
        assert len(windows) == 2
        # Most recent window should span Feb-Mar
        assert windows[0].start_date == date(2025, 2, 15)
        assert windows[0].end_date == date(2025, 3, 31)
        # Second window should be January
        assert windows[1].start_date == date(2025, 1, 1)
        assert windows[1].end_date == date(2025, 1, 31)

    def test_sparse_data_pattern_with_clusters(self):
        """Test pattern from real-world data: sparse clusters over long periods."""
        records = []

        # Simulate real user pattern: clusters of usage with long gaps
        # Cluster 1: January 2025 (44 days)
        for day in range(2, 46):
            if day <= 31:
                records.append(self.create_sleep_record(f"2025-01-{day:02d}"))
            else:
                records.append(self.create_sleep_record(f"2025-02-{day-31:02d}"))

        # Gap until March

        # Cluster 2: March 2025 (14 days)
        for day in range(9, 23):
            records.append(self.create_sleep_record(f"2025-03-{day:02d}"))

        # Small cluster end of March (7 days)
        for day in range(24, 31):
            records.append(self.create_sleep_record(f"2025-03-{day:02d}"))

        # Gap until June

        # Cluster 3: June-July 2025 (7 days) - Most recent
        for day in range(26, 31):
            records.append(self.create_sleep_record(f"2025-06-{day:02d}"))
        for day in range(1, 3):
            records.append(self.create_sleep_record(f"2025-07-{day:02d}"))

        # Test most recent strategy
        recent_strategy = MostRecentValidWindowStrategy()
        recent_windows = recent_strategy.find_windows(records, min_days=7)

        assert len(recent_windows) == 1
        assert recent_windows[0].start_date == date(2025, 6, 26)
        assert recent_windows[0].end_date == date(2025, 7, 2)

        # Test all windows strategy
        all_strategy = AllValidWindowsStrategy()
        all_windows = all_strategy.find_windows(records, min_days=7)

        # Should find windows in June-July, March, and January-February
        assert len(all_windows) >= 3

        # Test best quality strategy
        quality_strategy = BestQualityWindowStrategy()
        quality_windows = quality_strategy.find_windows(records, min_days=7)

        # Should find the window with best consistency
        assert len(quality_windows) == 1
        # Likely from the 44-day January stretch
        assert quality_windows[0].days_count >= 7
