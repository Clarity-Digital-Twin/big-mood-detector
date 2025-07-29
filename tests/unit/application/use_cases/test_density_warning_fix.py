"""Test fix for misleading density warnings (Issue #69)."""

from datetime import date, datetime, timedelta
from unittest.mock import Mock

import pytest

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState


class TestDensityWarningFix:
    """Test that density warnings are meaningful, not misleading."""

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

    def test_misleading_density_warning_scenario(self):
        """Test the exact scenario from the trial run."""
        # Create sparse data over 2+ years (like 738K records case)
        sleep_records = []
        
        # Old data from 2023
        for day in range(1, 8):
            sleep_records.append(self.create_sleep_record(f"2023-01-{day:02d}"))
        
        # Gap of ~2 years
        
        # Recent valid window (June 26 - July 2, 2025)
        for day in range(26, 31):
            sleep_records.append(self.create_sleep_record(f"2025-06-{day:02d}"))
        for day in range(1, 3):
            sleep_records.append(self.create_sleep_record(f"2025-07-{day:02d}"))
        
        # Total: 14 days of data over ~2.5 years
        
        # Create pipeline
        pipeline = MoodPredictionPipeline()
        
        # Process with current date (July 28, 2025)
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 7, 28),  # Today - system looks at last 7 days
        )
        
        # The old behavior would show "Sparse data: 1.5% density" (14 days / 912 days)
        # which is misleading because the user has valid dense windows
        
        # Check for misleading warning
        if result.warnings:
            for warning in result.warnings:
                if "density" in warning.lower():
                    # Extract the percentage
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?%)', warning)
                    if match:
                        percentage = float(match.group(1).rstrip('%'))
                        # If density is calculated over entire span, it would be ~1.5%
                        # This is misleading!
                        assert percentage > 5, f"Misleading density warning: {warning}"

    def test_density_should_consider_windows_not_total_span(self):
        """Density should be calculated within meaningful windows, not total span."""
        # Create data with clear dense windows
        sleep_records = []
        
        # Window 1: January 2025 (dense - 30 days)
        for day in range(1, 31):
            sleep_records.append(self.create_sleep_record(f"2025-01-{day:02d}"))
        
        # Gap of 5 months
        
        # Window 2: June 2025 (dense - 30 days)  
        for day in range(1, 31):
            if day <= 30:  # June has 30 days
                sleep_records.append(self.create_sleep_record(f"2025-06-{day:02d}"))
        
        # If calculated over total span: 60 days / 180 days = 33% (misleading)
        # If calculated within windows: 100% density in each window (accurate)
        
        # Create a mock window selection strategy that selects June window
        from unittest.mock import Mock
        mock_strategy = Mock()
        mock_window = Mock()
        mock_window.start_date = date(2025, 6, 1)
        mock_window.end_date = date(2025, 6, 30)
        mock_window.days_count = 30
        mock_window.data_quality = 1.0
        mock_strategy.find_windows.return_value = [mock_window]
        
        config = PipelineConfig(window_selection_strategy=mock_strategy)
        pipeline = MoodPredictionPipeline(config=config)
        
        # Process June window
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 6, 30),
        )
        
        # Should not warn about sparse data when looking at a dense window
        density_warnings = [w for w in result.warnings if "sparse" in w.lower() and "density" in w.lower()]
        assert len(density_warnings) == 0, f"Should not warn about density in dense window: {density_warnings}"

    def test_meaningful_density_warning_for_actually_sparse_data(self):
        """Should still warn when data is actually sparse within the analysis window."""
        # Create truly sparse data
        sleep_records = []
        
        # Only 3 days in a 30-day window
        sleep_records.append(self.create_sleep_record("2025-06-01"))
        sleep_records.append(self.create_sleep_record("2025-06-15"))
        sleep_records.append(self.create_sleep_record("2025-06-30"))
        
        # Create pipeline that will analyze June
        from unittest.mock import Mock
        mock_strategy = Mock()
        mock_window = Mock()
        mock_window.start_date = date(2025, 6, 1)
        mock_window.end_date = date(2025, 6, 30)
        mock_window.days_count = 30
        mock_window.data_quality = 0.1  # Low quality due to sparse data
        mock_strategy.find_windows.return_value = [mock_window]
        
        config = PipelineConfig(window_selection_strategy=mock_strategy)
        pipeline = MoodPredictionPipeline(config=config)
        
        # Process the sparse month
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 6, 30),
        )
        
        # Debug output
        print(f"All warnings: {result.warnings}")
        
        # Should warn about sparse data (3/30 = 10%)
        density_warnings = [w for w in result.warnings if "sparse" in w.lower()]
        assert len(density_warnings) > 0, f"Should warn about truly sparse data. Got warnings: {result.warnings}"
        
        # Check the percentage is reasonable
        for warning in density_warnings:
            if "density" in warning or "coverage" in warning:
                import re
                match = re.search(r'(\d+(?:\.\d+)?%)', warning)
                if match:
                    percentage = float(match.group(1).rstrip('%'))
                    # 10% is accurate for 3 days in 30
                    assert 5 <= percentage <= 15, f"Density calculation seems wrong: {warning}"