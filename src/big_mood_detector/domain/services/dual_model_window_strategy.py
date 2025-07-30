"""
Dual Model Window Strategy

Coordinates window selection between PAT and XGBoost models,
finding optimal periods where both can run or identifying
model-specific windows when needed.
"""

from dataclasses import dataclass
from typing import Any

from big_mood_detector.domain.services.sparse_window_strategy import (
    SparseDataWindow,
    SparseWindowStrategy,
)
from big_mood_detector.domain.services.window_selection_strategy import (
    DateWindow,
    MostRecentValidWindowStrategy,
)


@dataclass
class WindowAnalysisResult:
    """
    Complete analysis of available windows for both models.

    Attributes:
        pat_windows: Valid windows for PAT (7 consecutive days)
        xgboost_windows: Valid windows for XGBoost (30+ sparse days)
        optimal_window: Best window considering both models
        selection_reason: Human-readable explanation
        can_run_pat: Whether PAT has valid windows
        can_run_xgboost: Whether XGBoost has valid windows
        can_run_ensemble: Whether both can run on same data
    """

    pat_windows: list[DateWindow]
    xgboost_windows: list[SparseDataWindow]
    optimal_window: DateWindow | None
    selection_reason: str
    can_run_pat: bool
    can_run_xgboost: bool
    can_run_ensemble: bool


class DualModelWindowStrategy:
    """
    Coordinates window selection for PAT and XGBoost models.

    PAT requires: 7 consecutive days of minute-level activity
    XGBoost requires: 30-60 days of data (sparse acceptable)
    """

    PAT_REQUIRED_DAYS = 7
    XGBOOST_MIN_DAYS = 30
    XGBOOST_MIN_COVERAGE = 0.5

    def __init__(self) -> None:
        """Initialize with model-specific strategies."""
        self.pat_strategy = MostRecentValidWindowStrategy()
        self.xgboost_strategy = SparseWindowStrategy()

    def analyze_windows(self, records: list[Any]) -> WindowAnalysisResult:
        """
        Analyze data to find windows for both models.

        Args:
            records: Health records (sleep, activity, etc.)

        Returns:
            Complete analysis with windows and recommendations
        """
        # Find PAT windows (7 consecutive days)
        pat_windows = self.pat_strategy.find_windows(
            records,
            min_days=self.PAT_REQUIRED_DAYS
        )

        # Find XGBoost windows (30+ sparse days)
        xgboost_windows = self.xgboost_strategy.find_sparse_windows(
            records,
            min_days=self.XGBOOST_MIN_DAYS,
            min_coverage=self.XGBOOST_MIN_COVERAGE
        )

        # Determine capabilities
        can_run_pat = len(pat_windows) > 0
        can_run_xgboost = len(xgboost_windows) > 0

        # Find optimal window
        optimal_window, reason = self._find_optimal_window(
            pat_windows,
            xgboost_windows
        )

        # Build selection reason
        if not can_run_pat and not can_run_xgboost:
            reason = (
                f"Insufficient data for both models. "
                f"PAT requires {self.PAT_REQUIRED_DAYS} consecutive days. "
                f"XGBoost requires {self.XGBOOST_MIN_DAYS}+ days with "
                f"≥{int(self.XGBOOST_MIN_COVERAGE * 100)}% coverage."
            )
        elif not can_run_pat:
            reason = (
                f"PAT requires {self.PAT_REQUIRED_DAYS} consecutive days "
                f"(found {self._max_consecutive_days(records)} max). "
                f"Running XGBoost only."
            )
        elif not can_run_xgboost:
            reason = (
                f"XGBoost requires {self.XGBOOST_MIN_DAYS}+ days "
                f"(found {len({r.start_date.date() for r in records})} total). "
                f"Running PAT only."
            )

        return WindowAnalysisResult(
            pat_windows=pat_windows,
            xgboost_windows=xgboost_windows,
            optimal_window=optimal_window,
            selection_reason=reason,
            can_run_pat=can_run_pat,
            can_run_xgboost=can_run_xgboost,
            can_run_ensemble=can_run_pat and can_run_xgboost,
        )

    def _find_optimal_window(
        self,
        pat_windows: list[DateWindow],
        xgboost_windows: list[SparseDataWindow]
    ) -> tuple[DateWindow | None, str]:
        """
        Find the best window considering both models.

        Strategy:
        1. Prefer windows where both models can run
        2. Use most recent overlapping period
        3. Fall back to model-specific windows
        """
        if not pat_windows and not xgboost_windows:
            return None, "No valid windows found"

        if not pat_windows:
            # Convert XGBoost window to DateWindow format
            xgb = xgboost_windows[0]
            return DateWindow(
                start_date=xgb.start_date,
                end_date=xgb.end_date,
                days_count=xgb.total_days,
                data_quality=xgb.coverage_ratio
            ), "Using XGBoost window (PAT unavailable)"

        if not xgboost_windows:
            return pat_windows[0], "Using PAT window (XGBoost unavailable)"

        # Find overlapping windows
        for pat_window in pat_windows:
            for xgb_window in xgboost_windows:
                # Check if PAT window falls within XGBoost window
                if (xgb_window.start_date <= pat_window.start_date and
                    pat_window.end_date <= xgb_window.end_date):
                    return pat_window, "Both models have valid windows in same period"

        # No overlap - use most recent PAT window
        return pat_windows[0], "Using most recent PAT window (no overlap with XGBoost)"

    def _max_consecutive_days(self, records: list[Any]) -> int:
        """Find maximum consecutive days in records."""
        if not records:
            return 0

        sorted_dates = sorted({r.start_date.date() for r in records})
        if not sorted_dates:
            return 0

        max_consecutive = 1
        current_consecutive = 1

        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1

        return max_consecutive
