"""
Test Data Quality Validator

Ensures the validator correctly identifies sparse data and provides
appropriate warnings to users.
"""

import pytest
from datetime import datetime, date, timedelta

from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.application.services.data_quality_validator import (
    DataQualityValidator,
    DataQualityReport,
)


class TestDataQualityValidator:
    """Test data quality validation logic."""
    
    def test_perfect_data_quality(self):
        """Test validation with complete data."""
        # Create 14 days of perfect data
        sleep_records = []
        activity_records = []
        
        base_date = datetime(2025, 6, 1)
        for day in range(14):
            # Nightly sleep
            sleep_records.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=base_date + timedelta(days=day, hours=22),
                    end_date=base_date + timedelta(days=day + 1, hours=6),
                    state=SleepState.ASLEEP,
                )
            )
            
            # Daily activity
            for hour in range(24):
                activity_records.append(
                    ActivityRecord(
                        source_name="Apple Watch",
                        start_date=base_date + timedelta(days=day, hours=hour),
                        end_date=base_date + timedelta(days=day, hours=hour + 1),
                        value=100.0 if 7 <= hour <= 22 else 0.0,
                        activity_type=ActivityType.STEP_COUNT,
                        unit="count",
                    )
                )
        
        validator = DataQualityValidator()
        report = validator.validate_data_quality(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=[],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 14),
        )
        
        assert report.is_sufficient
        # Due to date assignment, last night's sleep is assigned to next day
        assert report.sleep_coverage >= 0.9  # Should be 13/14
        assert report.activity_coverage == 1.0
        assert len(report.warnings) == 0
        # With no heart data, score will be lower
        assert report.overall_quality_score >= 0.7
        
        message = validator.generate_user_message(report)
        assert "Good" in message or "Excellent" in message
    
    def test_sparse_sleep_data(self):
        """Test validation with sparse sleep data (the v0.5.4 scenario)."""
        # Only 4 nights out of 14
        sleep_records = [
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 2, 22, 0),
                end_date=datetime(2025, 6, 3, 6, 0),
                state=SleepState.ASLEEP,
            ),
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 5, 23, 0),
                end_date=datetime(2025, 6, 6, 7, 0),
                state=SleepState.ASLEEP,
            ),
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 9, 22, 30),
                end_date=datetime(2025, 6, 10, 6, 30),
                state=SleepState.ASLEEP,
            ),
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 13, 23, 0),
                end_date=datetime(2025, 6, 14, 7, 0),
                state=SleepState.ASLEEP,
            ),
        ]
        
        validator = DataQualityValidator()
        report = validator.validate_data_quality(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 14),
        )
        
        assert not report.is_sufficient  # Less than 7 days
        assert report.sleep_coverage < 0.5  # 4/14 = 0.29
        assert len(report.warnings) > 0
        assert "Critical" in report.warnings[0]
        assert len(report.recommendations) > 0
        
        message = validator.generate_user_message(report)
        assert "Insufficient" in message
    
    def test_data_gaps_detection(self):
        """Test detection of gaps in data."""
        # Create data with a 5-day gap
        sleep_records = []
        
        # First week
        for day in range(7):
            sleep_records.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=datetime(2025, 6, 1 + day, 22, 0),
                    end_date=datetime(2025, 6, 2 + day, 6, 0),
                    state=SleepState.ASLEEP,
                )
            )
        
        # Skip 5 days (June 8-12)
        
        # Last two days
        for day in [13, 14]:
            sleep_records.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=datetime(2025, 6, day, 22, 0),
                    end_date=datetime(2025, 6, day + 1, 6, 0),
                    state=SleepState.ASLEEP,
                )
            )
        
        validator = DataQualityValidator()
        report = validator.validate_data_quality(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 14),
        )
        
        assert report.is_sufficient  # Has 9 days total
        assert any("gaps" in w for w in report.warnings)
        assert any("5 days" in w for w in report.warnings)
    
    def test_edge_case_exactly_minimum_days(self):
        """Test with exactly the minimum required days."""
        # Exactly 7 days of sleep
        sleep_records = []
        for day in range(7):
            sleep_records.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=datetime(2025, 6, 1 + day, 22, 0),
                    end_date=datetime(2025, 6, 2 + day, 6, 0),
                    state=SleepState.ASLEEP,
                )
            )
        
        validator = DataQualityValidator(min_sleep_days=7)
        report = validator.validate_data_quality(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 14),
        )
        
        assert report.is_sufficient
        assert report.sleep_coverage == 0.5  # 7/14
    
    def test_date_assignment_consistency(self):
        """
        Test that validator uses the same date assignment as the pipeline.
        
        This ensures we don't have mismatches like in v0.5.3.
        """
        # Create midnight-crossing sleep
        sleep_records = [
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 26, 22, 0),  # Thursday night
                end_date=datetime(2025, 6, 27, 6, 0),     # Friday morning
                state=SleepState.ASLEEP,
            )
        ]
        
        validator = DataQualityValidator()
        report = validator.validate_data_quality(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=date(2025, 6, 26),
            end_date=date(2025, 6, 27),
        )
        
        # Should count as 1 day (June 27), not 2
        assert report.sleep_coverage == 0.5  # 1 day out of 2
    
    def test_user_messages_are_helpful(self):
        """Test that user messages are clear and actionable."""
        validator = DataQualityValidator()
        
        # Test different quality levels
        excellent_report = DataQualityReport(
            is_sufficient=True,
            sleep_coverage=0.95,
            activity_coverage=0.9,
            heart_coverage=0.8,
            warnings=[],
            recommendations=[],
        )
        assert "Excellent" in validator.generate_user_message(excellent_report)
        
        good_report = DataQualityReport(
            is_sufficient=True,
            sleep_coverage=0.7,
            activity_coverage=0.6,
            heart_coverage=0.5,
            warnings=["Some warning"],
            recommendations=[],
        )
        assert "Good" in validator.generate_user_message(good_report)
        
        poor_report = DataQualityReport(
            is_sufficient=False,
            sleep_coverage=0.3,
            activity_coverage=0.2,
            heart_coverage=0.0,
            warnings=["Critical warning"],
            recommendations=["Wear device more"],
        )
        message = validator.generate_user_message(poor_report)
        assert "Insufficient" in message
        assert "30%" in message  # Shows actual coverage