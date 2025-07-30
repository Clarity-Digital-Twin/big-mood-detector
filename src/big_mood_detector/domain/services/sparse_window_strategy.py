"""
Sparse Window Selection Strategy

Finds data windows that allow gaps, suitable for XGBoost models
that can work with sparse data over longer periods.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from big_mood_detector.domain.services.window_selection_strategy import (
    DateWindow,
    WindowSelectionStrategy,
)


@dataclass(frozen=True)
class SparseDataWindow:
    """
    Window allowing non-consecutive days of data.

    Attributes:
        start_date: First date of the window
        end_date: Last date of the window (inclusive)
        total_days: Total calendar days in the window
        days_with_data: Number of days that have records
        coverage_ratio: Proportion of days with data (0-1)
    """

    start_date: date
    end_date: date
    total_days: int
    days_with_data: int
    coverage_ratio: float

    def __post_init__(self) -> None:
        """Validate window invariants."""
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")

        if not 0 <= self.coverage_ratio <= 1:
            raise ValueError("Coverage ratio must be between 0 and 1")

        if self.days_with_data > self.total_days:
            raise ValueError("Days with data cannot exceed total days")

        # Verify total_days matches date range
        actual_days = (self.end_date - self.start_date).days + 1
        if self.total_days != actual_days:
            object.__setattr__(self, 'total_days', actual_days)

    @property
    def spans_days(self) -> int:
        """Calendar days spanned by the window."""
        return (self.end_date - self.start_date).days + 1


class SparseWindowStrategy(WindowSelectionStrategy):
    """
    Finds windows with sparse data coverage suitable for XGBoost.

    Unlike consecutive strategies, this allows gaps in data as long
    as minimum coverage requirements are met.
    """

    def find_windows(
        self,
        records: list[Any],
        min_days: int = 30,
        min_coverage: float | None = None
    ) -> list[DateWindow]:
        """
        Find windows with sufficient sparse coverage.

        Args:
            records: List of health records with start_date attribute
            min_days: Minimum total days required (calendar days)
            min_coverage: Minimum proportion of days with data (0-1)

        Returns:
            List of valid sparse windows as DateWindow objects, sorted by recency
        """
        if not records:
            return []

        # Default coverage if not specified
        if min_coverage is None:
            min_coverage = 0.5

        # Get unique dates with data
        dates_with_data = self._extract_unique_dates(records)

        if not dates_with_data:
            return []

        # Find all possible windows
        sparse_windows = self._find_sparse_windows(
            dates_with_data,
            min_days,
            min_coverage
        )

        # Convert SparseDataWindow to DateWindow and sort by recency
        date_windows = [
            DateWindow(
                start_date=w.start_date,
                end_date=w.end_date,
                days_count=w.total_days,
                data_quality=w.coverage_ratio
            )
            for w in sparse_windows
        ]

        return sorted(date_windows, key=lambda w: w.end_date, reverse=True)

    def find_sparse_windows(
        self,
        records: list[Any],
        min_days: int = 30,
        min_coverage: float = 0.5
    ) -> list[SparseDataWindow]:
        """
        Find windows with sparse coverage, returning full SparseDataWindow objects.

        This method is used by DualModelWindowStrategy to get detailed window info.
        """
        if not records:
            return []

        # Get unique dates with data
        dates_with_data = self._extract_unique_dates(records)

        if not dates_with_data:
            return []

        # Find all possible windows
        windows = self._find_sparse_windows(
            dates_with_data,
            min_days,
            min_coverage
        )

        # Sort by recency (most recent first)
        return sorted(windows, key=lambda w: w.end_date, reverse=True)

    def _extract_unique_dates(self, records: list[Any]) -> list[date]:
        """Extract sorted unique dates from records."""
        dates = set()
        for record in records:
            if hasattr(record, 'start_date'):
                record_date = record.start_date
                if hasattr(record_date, 'date'):
                    dates.add(record_date.date())
                else:
                    dates.add(record_date)

        return sorted(dates)

    def _find_sparse_windows(
        self,
        dates_with_data: list[date],
        min_days: int,
        min_coverage: float
    ) -> list[SparseDataWindow]:
        """Find all windows meeting sparse criteria."""
        if not dates_with_data:
            return []

        windows = []

        # Try different window starting points
        for i in range(len(dates_with_data)):
            start_date = dates_with_data[i]

            # Try different window end points
            for j in range(i, len(dates_with_data)):
                end_date = dates_with_data[j]

                # Calculate window metrics
                total_days = (end_date - start_date).days + 1

                # Skip if window too small
                if total_days < min_days:
                    continue

                # Count days with data in this window
                days_with_data = self._count_days_in_range(
                    dates_with_data,
                    start_date,
                    end_date
                )

                coverage_ratio = days_with_data / total_days

                # Check if meets coverage requirement
                if coverage_ratio >= min_coverage:
                    window = SparseDataWindow(
                        start_date=start_date,
                        end_date=end_date,
                        total_days=total_days,
                        days_with_data=days_with_data,
                        coverage_ratio=coverage_ratio
                    )
                    windows.append(window)

        # Remove redundant windows (keep best coverage for each date range)
        return self._filter_redundant_windows(windows)

    def _count_days_in_range(
        self,
        all_dates: list[date],
        start_date: date,
        end_date: date
    ) -> int:
        """Count how many dates fall within the range."""
        count = 0
        for d in all_dates:
            if start_date <= d <= end_date:
                count += 1
        return count

    def _filter_redundant_windows(
        self,
        windows: list[SparseDataWindow]
    ) -> list[SparseDataWindow]:
        """Remove redundant windows, keeping best coverage for each period."""
        if not windows:
            return []

        # Group by date range
        unique_windows = {}

        for window in windows:
            key = (window.start_date, window.end_date)

            if key not in unique_windows:
                unique_windows[key] = window
            else:
                # Keep window with better coverage
                if window.coverage_ratio > unique_windows[key].coverage_ratio:
                    unique_windows[key] = window

        return list(unique_windows.values())
