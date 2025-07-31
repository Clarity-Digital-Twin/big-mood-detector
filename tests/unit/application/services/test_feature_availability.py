"""Test feature availability checking in DataParsingService."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from big_mood_detector.application.services.data_parsing_service import (
    DataParsingService,
)
from big_mood_detector.domain.value_objects.feature_availability import (
    FeatureAvailability,
)
from big_mood_detector.domain.value_objects.feature_requirements import (
    FEATURE_REQUIREMENTS,
)


class TestFeatureAvailability:
    """Test feature availability functionality."""

    def test_check_feature_availability_all_features_available(self):
        """Test when all features have sufficient data."""
        service = DataParsingService()
        
        # Mock the parser's count_records_by_type method
        mock_parser = Mock()
        mock_parser.count_records_by_type.return_value = {
            "HKCategoryTypeIdentifierSleepAnalysis": 365,
            "HKQuantityTypeIdentifierStepCount": 8760,  # Hourly for a year
            "HKQuantityTypeIdentifierHeartRate": 50000,
            "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": 365,
            "HKQuantityTypeIdentifierRespiratoryRate": 365,
            "HKQuantityTypeIdentifierActiveEnergyBurned": 365,
            "HKQuantityTypeIdentifierDistanceWalkingRunning": 365,
        }
        
        with patch.object(service, '_xml_parser', mock_parser):
            start_time = time.time()
            availability = service.check_feature_availability(Path("test.xml"))
            duration = time.time() - start_time
            
            # Should have all features available
            assert len(availability.available_features) >= 6
            assert len(availability.unavailable_features) == 0
            assert availability.has_minimum_features()
            
            # Check specific features
            feature_names = {name for name, _ in availability.available_features}
            assert "depression_risk" in feature_names
            assert "mania_risk" in feature_names
            assert "hrv_analysis" in feature_names
            
            # Should be fast
            assert duration < 0.1

    def test_check_feature_availability_missing_hrv(self):
        """Test when HRV data is missing."""
        service = DataParsingService()
        
        mock_parser = Mock()
        mock_parser.count_records_by_type.return_value = {
            "HKCategoryTypeIdentifierSleepAnalysis": 365,
            "HKQuantityTypeIdentifierStepCount": 8760,
            "HKQuantityTypeIdentifierHeartRate": 50000,
            # No HRV data
        }
        
        with patch.object(service, '_xml_parser', mock_parser):
            availability = service.check_feature_availability(Path("test.xml"))
            
            # Should still have basic features
            assert availability.has_minimum_features()
            
            # HRV analysis should be unavailable
            unavailable_names = {name for name, _ in availability.unavailable_features}
            assert "hrv_analysis" in unavailable_names
            
            # Should have reason for unavailability
            hrv_reason = next(
                reason for name, reason in availability.unavailable_features 
                if name == "hrv_analysis"
            )
            assert "HKQuantityTypeIdentifierHeartRateVariabilitySDNN" in hrv_reason

    def test_check_feature_availability_insufficient_data(self):
        """Test when data exists but is insufficient."""
        service = DataParsingService()
        
        mock_parser = Mock()
        mock_parser.count_records_by_type.return_value = {
            "HKCategoryTypeIdentifierSleepAnalysis": 3,  # Only 3 days (insufficient)
            "HKQuantityTypeIdentifierStepCount": 100,    # ~4 days (insufficient) 
            "HKQuantityTypeIdentifierHeartRate": 200,    # 2 days (present but insufficient)
            "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": 5,  # Only 5 days
        }
        
        with patch.object(service, '_xml_parser', mock_parser):
            availability = service.check_feature_availability(Path("test.xml"))
            
            # Should not have minimum features due to insufficient data
            assert not availability.has_minimum_features()
            
            # Check reasons mention insufficient data or missing
            for feature, reason in availability.unavailable_features:
                assert "insufficient" in reason.lower() or "missing required type:" in reason.lower()

    def test_check_feature_availability_empty_file(self):
        """Test with empty XML file."""
        service = DataParsingService()
        
        mock_parser = Mock()
        mock_parser.count_records_by_type.return_value = {}
        
        with patch.object(service, '_xml_parser', mock_parser):
            availability = service.check_feature_availability(Path("empty.xml"))
            
            assert len(availability.available_features) == 0
            assert len(availability.unavailable_features) == len(FEATURE_REQUIREMENTS)
            assert not availability.has_minimum_features()
            assert availability.total_records == 0

    def test_feature_availability_major_types(self):
        """Test get_major_types method."""
        availability = FeatureAvailability(
            available_features=[],
            unavailable_features=[],
            record_counts={
                "HKCategoryTypeIdentifierSleepAnalysis": 365,
                "HKQuantityTypeIdentifierStepCount": 8760,
                "HKQuantityTypeIdentifierHeartRate": 50000,
                "HKQuantityTypeIdentifierSomeUnknownType": 100,
            }
        )
        
        major_types = availability.get_major_types()
        
        # Should be sorted by count
        assert major_types[0] == ("Heart Rate", 50000)
        assert major_types[1] == ("Step Count", 8760)
        assert major_types[2] == ("Sleep Analysis", 365)
        
        # Unknown types should not appear
        assert len(major_types) == 3

    def test_format_missing_data_summary(self):
        """Test formatting of missing data summary."""
        availability = FeatureAvailability(
            available_features=[("depression_risk", "Depression risk prediction")],
            unavailable_features=[
                ("hrv_analysis", "Missing required type: HKQuantityTypeIdentifierHeartRateVariabilitySDNN"),
                ("respiratory_analysis", "Missing required type: HKQuantityTypeIdentifierRespiratoryRate"),
            ],
            record_counts={}
        )
        
        summary = availability.format_missing_data_summary()
        # Should contain the missing types
        assert summary.startswith("Missing:")
        assert "HKQuantityTypeIdentifierHeartRateVariabilitySDNN" in summary
        assert "HKQuantityTypeIdentifierRespiratoryRate" in summary