"""
Data Quality Validator

Validates health data quality and provides warnings about potential issues
that could affect prediction accuracy.

Following Clean Code principles:
- Single Responsibility: Only validates data quality
- Clear warnings and actionable feedback
- Testable validation logic
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from big_mood_detector.domain.entities.activity_record import ActivityRecord
from big_mood_detector.domain.entities.heart_rate_record import HeartRateRecord
from big_mood_detector.domain.entities.sleep_record import SleepRecord
from big_mood_detector.domain.services.date_assignment import UniversalDateAssignment


@dataclass
class DataQualityReport:
    """Report on data quality for mood prediction."""
    
    is_sufficient: bool
    sleep_coverage: float  # 0-1, fraction of days with sleep data
    activity_coverage: float  # 0-1, fraction of days with activity data
    heart_coverage: float  # 0-1, fraction of days with heart data
    warnings: list[str]
    recommendations: list[str]
    
    @property
    def overall_quality_score(self) -> float:
        """Calculate overall quality score (0-1)."""
        # Weighted average: sleep is most important
        return (
            self.sleep_coverage * 0.5 +
            self.activity_coverage * 0.3 +
            self.heart_coverage * 0.2
        )


class DataQualityValidator:
    """
    Validates health data quality for mood predictions.
    
    Ensures users understand when predictions might be unreliable
    due to sparse or missing data.
    """
    
    def __init__(
        self,
        min_sleep_days: int = 7,
        min_coverage_ratio: float = 0.5,
        warn_coverage_ratio: float = 0.7,
    ):
        """
        Initialize validator with thresholds.
        
        Args:
            min_sleep_days: Minimum days of sleep data required
            min_coverage_ratio: Minimum data coverage to proceed
            warn_coverage_ratio: Coverage below this triggers warnings
        """
        self.min_sleep_days = min_sleep_days
        self.min_coverage_ratio = min_coverage_ratio
        self.warn_coverage_ratio = warn_coverage_ratio
    
    def validate_data_quality(
        self,
        sleep_records: list[SleepRecord],
        activity_records: list[ActivityRecord],
        heart_records: list[HeartRateRecord],
        start_date: date,
        end_date: date,
    ) -> DataQualityReport:
        """
        Validate data quality for the specified date range.
        
        Args:
            sleep_records: Sleep data
            activity_records: Activity data
            heart_records: Heart rate data
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            DataQualityReport with coverage metrics and warnings
        """
        warnings = []
        recommendations = []
        
        # Calculate date range
        total_days = (end_date - start_date).days + 1
        
        # Analyze sleep coverage
        sleep_days = self._count_days_with_sleep(
            sleep_records, start_date, end_date
        )
        sleep_coverage = sleep_days / total_days if total_days > 0 else 0
        
        # Analyze activity coverage
        activity_days = self._count_days_with_activity(
            activity_records, start_date, end_date
        )
        activity_coverage = activity_days / total_days if total_days > 0 else 0
        
        # Analyze heart rate coverage
        heart_days = self._count_days_with_heart_rate(
            heart_records, start_date, end_date
        )
        heart_coverage = heart_days / total_days if total_days > 0 else 0
        
        # Check minimum requirements
        is_sufficient = sleep_days >= self.min_sleep_days
        
        # Generate warnings
        if sleep_coverage < self.min_coverage_ratio:
            warnings.append(
                f"Critical: Only {sleep_coverage:.0%} of days have sleep data. "
                f"Predictions will be unreliable."
            )
            recommendations.append(
                "Wear your device to sleep for at least 7 consecutive nights "
                "to get accurate mood predictions."
            )
        elif sleep_coverage < self.warn_coverage_ratio:
            warnings.append(
                f"Warning: Sleep data coverage is {sleep_coverage:.0%}. "
                f"Some predictions may be less accurate."
            )
            recommendations.append(
                "For best results, wear your device to sleep every night."
            )
        
        # Check for gaps
        gaps = self._find_data_gaps(sleep_records, start_date, end_date)
        if gaps:
            longest_gap = max(gap[1] for gap in gaps)
            if longest_gap >= 3:
                warnings.append(
                    f"Found {len(gaps)} gaps in sleep data, "
                    f"longest gap is {longest_gap} days."
                )
                recommendations.append(
                    "Try to avoid long gaps in data collection for better predictions."
                )
        
        # Activity warnings
        if activity_coverage < 0.3:
            warnings.append(
                f"Very low activity data coverage ({activity_coverage:.0%}). "
                f"Activity patterns help improve predictions."
            )
            recommendations.append(
                "Enable activity tracking on your device for better insights."
            )
        
        # Create report
        return DataQualityReport(
            is_sufficient=is_sufficient,
            sleep_coverage=sleep_coverage,
            activity_coverage=activity_coverage,
            heart_coverage=heart_coverage,
            warnings=warnings,
            recommendations=recommendations,
        )
    
    def _count_days_with_sleep(
        self,
        sleep_records: list[SleepRecord],
        start_date: date,
        end_date: date,
    ) -> int:
        """Count days with sleep data in the date range."""
        # Group sleep by assigned date
        sleep_by_date = UniversalDateAssignment.group_records_by_date(sleep_records)
        
        # Count days in range
        count = 0
        current = start_date
        while current <= end_date:
            if current in sleep_by_date:
                count += 1
            current += timedelta(days=1)
        
        return count
    
    def _count_days_with_activity(
        self,
        activity_records: list[ActivityRecord],
        start_date: date,
        end_date: date,
    ) -> int:
        """Count days with activity data."""
        days_with_activity = set()
        
        for record in activity_records:
            record_date = record.start_date.date()
            if start_date <= record_date <= end_date:
                days_with_activity.add(record_date)
        
        return len(days_with_activity)
    
    def _count_days_with_heart_rate(
        self,
        heart_records: list[HeartRateRecord],
        start_date: date,
        end_date: date,
    ) -> int:
        """Count days with heart rate data."""
        days_with_hr = set()
        
        for record in heart_records:
            record_date = record.timestamp.date()
            if start_date <= record_date <= end_date:
                days_with_hr.add(record_date)
        
        return len(days_with_hr)
    
    def _find_data_gaps(
        self,
        sleep_records: list[SleepRecord],
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, int]]:
        """Find gaps in sleep data.
        
        Returns:
            List of (gap_start_date, gap_length_days) tuples
        """
        # Get all dates with sleep
        sleep_by_date = UniversalDateAssignment.group_records_by_date(sleep_records)
        sleep_dates = set(sleep_by_date.keys())
        
        # Find gaps
        gaps = []
        current = start_date
        gap_start = None
        
        while current <= end_date:
            if current not in sleep_dates:
                if gap_start is None:
                    gap_start = current
            else:
                if gap_start is not None:
                    gap_length = (current - gap_start).days
                    gaps.append((gap_start, gap_length))
                    gap_start = None
            
            current += timedelta(days=1)
        
        # Handle gap at end
        if gap_start is not None:
            gap_length = (end_date - gap_start).days + 1
            gaps.append((gap_start, gap_length))
        
        return gaps
    
    def generate_user_message(self, report: DataQualityReport) -> str:
        """
        Generate a user-friendly message about data quality.
        
        Args:
            report: Data quality report
            
        Returns:
            Human-readable message
        """
        if not report.is_sufficient:
            return (
                "⚠️ Insufficient data for reliable predictions. "
                f"You have {report.sleep_coverage:.0%} sleep data coverage. "
                "Please wear your device for at least 7 nights and try again."
            )
        
        quality = report.overall_quality_score
        if quality >= 0.8:
            return "✅ Excellent data quality! Your predictions will be highly reliable."
        elif quality >= 0.6:
            return "👍 Good data quality. Your predictions should be reasonably accurate."
        else:
            return (
                "⚡ Fair data quality. Predictions are available but may be less accurate. "
                "For best results, wear your device more consistently."
            )