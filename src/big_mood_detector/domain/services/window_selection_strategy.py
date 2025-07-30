"""
Window Selection Strategy

Domain service for finding valid consecutive data windows in sparse health records.
Implements Strategy pattern for different window selection approaches.

Clean architecture principles:
- Pure domain logic, no infrastructure dependencies
- Immutable value objects
- Clear abstractions with single responsibility
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class DateWindow:
    """
    Immutable value object representing a valid data window.

    Attributes:
        start_date: First date of the window
        end_date: Last date of the window (inclusive)
        days_count: Number of days in the window
        data_quality: Quality score 0-1 (1 = perfect consistency)
    """

    start_date: date
    end_date: date
    days_count: int
    data_quality: float

    def __post_init__(self) -> None:
        """Validate window invariants."""
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")

        if not 0 <= self.data_quality <= 1:
            raise ValueError("Data quality must be between 0 and 1")

        # Verify days count matches date range
        actual_days = (self.end_date - self.start_date).days + 1
        if self.days_count != actual_days:
            object.__setattr__(self, 'days_count', actual_days)


class WindowSelectionStrategy(ABC):
    """
    Abstract strategy for finding valid data windows.

    Different strategies can prioritize:
    - Recency (most recent valid window)
    - Quality (best data consistency)
    - Comprehensiveness (all valid windows)
    """

    @abstractmethod
    def find_windows(
        self,
        records: list[Any],  # List of health records (sleep, activity, etc)
        min_days: int = 7,
        min_coverage: float | None = None  # Optional coverage requirement for sparse strategies
    ) -> list[DateWindow]:
        """
        Find valid consecutive data windows.

        Args:
            records: List of health records with start_date attribute
            min_days: Minimum consecutive days required for a valid window

        Returns:
            List of valid windows, ordered by strategy-specific criteria
        """
        pass


class MostRecentValidWindowStrategy(WindowSelectionStrategy):
    """
    Finds the most recent window with sufficient consecutive data.

    Optimized for clinical relevance - recent data is usually
    more representative of current health state.
    """

    def find_windows(
        self,
        records: list[Any],
        min_days: int = 7,
        min_coverage: float | None = None  # Ignored in consecutive strategies
    ) -> list[DateWindow]:
        """Find the most recent valid window."""
        if not records:
            return []

        # Sort records by date
        sorted_records = sorted(records, key=lambda r: r.start_date)

        # Find all consecutive windows
        windows = self._find_consecutive_windows(sorted_records, min_days)

        if not windows:
            return []

        # Return only the most recent window
        return [windows[-1]]  # Already sorted by start date

    def _find_consecutive_windows(
        self,
        sorted_records: list[Any],
        min_days: int
    ) -> list[DateWindow]:
        """Find all windows with consecutive days of data."""
        if not sorted_records:
            return []

        windows = []
        current_window_start = sorted_records[0].start_date.date()
        current_window_dates = [current_window_start]

        for i in range(1, len(sorted_records)):
            record_date = sorted_records[i].start_date.date()
            expected_date = current_window_dates[-1] + timedelta(days=1)

            if record_date == expected_date:
                # Consecutive day
                current_window_dates.append(record_date)
            else:
                # Gap found - check if current window is valid
                if len(current_window_dates) >= min_days:
                    window = DateWindow(
                        start_date=current_window_dates[0],
                        end_date=current_window_dates[-1],
                        days_count=len(current_window_dates),
                        data_quality=1.0  # Perfect consecutive days
                    )
                    windows.append(window)

                # Start new window
                current_window_start = record_date
                current_window_dates = [record_date]

        # Check final window
        if len(current_window_dates) >= min_days:
            window = DateWindow(
                start_date=current_window_dates[0],
                end_date=current_window_dates[-1],
                days_count=len(current_window_dates),
                data_quality=1.0
            )
            windows.append(window)

        return windows


class BestQualityWindowStrategy(WindowSelectionStrategy):
    """
    Finds the window with highest data quality and consistency.

    Quality factors:
    - Sleep duration consistency
    - Data completeness
    - Absence of outliers
    """

    def find_windows(
        self,
        records: list[Any],
        min_days: int = 7,
        min_coverage: float | None = None  # Ignored in consecutive strategies
    ) -> list[DateWindow]:
        """Find the highest quality window."""
        if not records:
            return []

        # Find all valid windows
        all_windows = self._find_all_windows(records, min_days)

        if not all_windows:
            return []

        # Score each window and return the best
        best_window = max(all_windows, key=lambda w: w.data_quality)
        return [best_window]

    def _find_all_windows(
        self,
        records: list[Any],
        min_days: int
    ) -> list[DateWindow]:
        """Find all windows and calculate quality scores."""
        sorted_records = sorted(records, key=lambda r: r.start_date)
        windows = []

        # Group records by date
        from collections import defaultdict
        records_by_date = defaultdict(list)
        for record in sorted_records:
            record_date = record.start_date.date()
            records_by_date[record_date].append(record)

        # Find consecutive windows
        dates = sorted(records_by_date.keys())
        i = 0

        while i < len(dates):
            # Try to build a window starting at dates[i]
            window_dates = [dates[i]]
            j = i + 1

            while j < len(dates) and dates[j] == window_dates[-1] + timedelta(days=1):
                window_dates.append(dates[j])
                j += 1

            if len(window_dates) >= min_days:
                # Calculate quality based on sleep consistency
                quality = self._calculate_window_quality(
                    window_dates, records_by_date
                )

                window = DateWindow(
                    start_date=window_dates[0],
                    end_date=window_dates[-1],
                    days_count=len(window_dates),
                    data_quality=quality
                )
                windows.append(window)

            i = j if j > i + 1 else i + 1

        return windows

    def _calculate_window_quality(
        self,
        window_dates: list[date],
        records_by_date: dict[date, list[Any]]
    ) -> float:
        """
        Calculate quality score based on data consistency.

        Factors:
        - Sleep duration variance (lower is better)
        - Completeness (no missing data)
        """
        sleep_durations = []

        for window_date in window_dates:
            day_records = records_by_date.get(window_date, [])
            if day_records:
                # Calculate total sleep duration for the day
                day_duration = 0
                for record in day_records:
                    if hasattr(record, 'start_date') and hasattr(record, 'end_date'):
                        duration_minutes = (record.end_date - record.start_date).total_seconds() / 60
                        day_duration += duration_minutes
                if day_duration > 0:
                    sleep_durations.append(day_duration)

        if not sleep_durations:
            return 0.5  # No duration data, neutral quality

        # Calculate consistency score
        import statistics
        if len(sleep_durations) > 1:
            std_dev = statistics.stdev(sleep_durations)
            # Normalize variance (assuming 480±120 minutes is reasonable)
            consistency_score = max(0, 1 - (std_dev / 120))
        else:
            consistency_score = 1.0

        # Completeness score (all days have data)
        completeness_score = len(sleep_durations) / len(window_dates)

        # Weighted average
        return 0.7 * consistency_score + 0.3 * completeness_score


class AllValidWindowsStrategy(WindowSelectionStrategy):
    """
    Finds all valid windows in the dataset.

    Useful for:
    - Comprehensive analysis
    - Finding best prediction opportunities
    - Understanding data availability patterns
    """

    def find_windows(
        self,
        records: list[Any],
        min_days: int = 7,
        min_coverage: float | None = None  # Ignored in consecutive strategies
    ) -> list[DateWindow]:
        """Find all valid windows, ordered by recency."""
        if not records:
            return []

        # Use helper from MostRecentValidWindowStrategy
        strategy = MostRecentValidWindowStrategy()
        all_windows = strategy._find_consecutive_windows(
            sorted(records, key=lambda r: r.start_date),
            min_days
        )

        # Return in reverse order (most recent first)
        return list(reversed(all_windows))
