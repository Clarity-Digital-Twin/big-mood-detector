"""
Test that the date assignment fix actually works!

This test proves that midnight-crossing sleep can now be found correctly.
"""

from datetime import date, datetime

import pytest

from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.clinical_feature_extractor import (
    ClinicalFeatureExtractor,
)


class TestDateAssignmentFix:
    """Verify the critical date assignment bug is FIXED."""
    
    def test_midnight_crossing_sleep_is_now_found(self):
        """
        The fix works! Sleep crossing midnight can be found.
        
        This test PASSES after the fix, proving we solved the bug.
        """
        # Create realistic sleep: 22:30 to 06:45
        sleep = SleepRecord(
            source_name="Apple Watch",
            start_date=datetime(2025, 6, 26, 22, 30),  # Thursday night
            end_date=datetime(2025, 6, 27, 6, 45),     # Friday morning
            state=SleepState.ASLEEP
        )
        
        # Extract features using the FIXED extractor
        extractor = ClinicalFeatureExtractor()
        
        # This now WORKS!
        sleep_onset = extractor._extract_sleep_onset_hour([sleep], date(2025, 6, 27))
        
        # We get the REAL sleep onset time, not the default!
        assert sleep_onset == 22.5, f"Got real sleep onset {sleep_onset}, not default 23.0!"
        
        # Also test wake time
        wake_time = extractor._extract_wake_time_hour([sleep], date(2025, 6, 27))
        assert wake_time == 6.75, f"Got real wake time {wake_time}, not default 7.0!"
        
        # And fragmentation (should be 0 for single sleep period)
        fragmentation = extractor._calculate_sleep_fragmentation([sleep], date(2025, 6, 27))
        assert fragmentation == 0.0, "Single sleep period has no fragmentation"
    
    def test_multiple_sleep_patterns_all_work(self):
        """Test various sleep patterns all work correctly now."""
        test_cases = [
            # (name, start, end, expected_onset, expected_wake)
            ("Normal", datetime(2025, 6, 26, 22, 0), datetime(2025, 6, 27, 6, 0), 22.0, 6.0),
            ("Late", datetime(2025, 6, 27, 1, 0), datetime(2025, 6, 27, 9, 0), 1.0, 9.0),
            ("Very Late", datetime(2025, 6, 27, 3, 0), datetime(2025, 6, 27, 11, 0), 3.0, 11.0),
        ]
        
        extractor = ClinicalFeatureExtractor()
        
        for name, start, end, expected_onset, expected_wake in test_cases:
            sleep = SleepRecord(
                source_name="Test",
                start_date=start,
                end_date=end,
                state=SleepState.ASLEEP
            )
            
            # All assigned to June 27
            onset = extractor._extract_sleep_onset_hour([sleep], date(2025, 6, 27))
            wake = extractor._extract_wake_time_hour([sleep], date(2025, 6, 27))
            
            assert onset == expected_onset, f"{name}: onset {onset} != {expected_onset}"
            assert wake == expected_wake, f"{name}: wake {wake} != {expected_wake}"
    
    def test_fragmented_sleep_correctly_counted(self):
        """Test that multiple sleep episodes are correctly found."""
        # Night sleep + afternoon nap
        records = [
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 26, 23, 0),
                end_date=datetime(2025, 6, 27, 7, 0),
                state=SleepState.ASLEEP
            ),
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 27, 14, 0),
                end_date=datetime(2025, 6, 27, 14, 30),  # 30 min nap
                state=SleepState.ASLEEP
            ),
        ]
        
        extractor = ClinicalFeatureExtractor()
        fragmentation = extractor._calculate_sleep_fragmentation(records, date(2025, 6, 27))
        
        # 2 episodes = some fragmentation
        assert fragmentation > 0, "Multiple sleep episodes show fragmentation"
        assert fragmentation == (2 - 1) / 3.0, "Fragmentation formula is (episodes-1)/3"