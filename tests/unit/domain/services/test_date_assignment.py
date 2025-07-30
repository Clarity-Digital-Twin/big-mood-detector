"""
Test Universal Date Assignment Service

Ensures our single source of truth for date assignment works correctly.
These tests prevent the v0.5.3 date mismatch bug from ever returning.
"""

from datetime import date, datetime

from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.domain.services.date_assignment import UniversalDateAssignment


class TestUniversalDateAssignment:
    """Test the centralized date assignment logic."""

    def test_normal_night_sleep_assigned_to_wake_date(self):
        """
        Most common case: sleep from ~22:00 to ~06:00.
        Should be assigned to the wake date (next morning).
        """
        sleep = SleepRecord(
            source_name="Apple Watch",
            start_date=datetime(2025, 6, 26, 22, 30),  # Thursday night
            end_date=datetime(2025, 6, 27, 6, 45),     # Friday morning
            state=SleepState.ASLEEP
        )

        assigned = UniversalDateAssignment.assign_sleep_to_date(sleep)
        assert assigned == date(2025, 6, 27), "Night sleep assigned to wake date"

    def test_late_night_sleep_still_assigned_to_wake_date(self):
        """
        Late sleeper: 02:00 to 10:00.
        Still assigned to wake date since wake < 3pm.
        """
        sleep = SleepRecord(
            source_name="Apple Watch",
            start_date=datetime(2025, 6, 27, 2, 0),   # Early Friday morning
            end_date=datetime(2025, 6, 27, 10, 0),    # Friday mid-morning
            state=SleepState.ASLEEP
        )

        assigned = UniversalDateAssignment.assign_sleep_to_date(sleep)
        assert assigned == date(2025, 6, 27), "Late sleep still on same day"

    def test_shift_worker_sleep_assigned_to_next_date(self):
        """
        Shift worker: sleeps 08:00 to 16:00.
        Wake at 4pm > 3pm cutoff, so assigned to NEXT date.
        """
        sleep = SleepRecord(
            source_name="Apple Watch",
            start_date=datetime(2025, 6, 27, 8, 0),    # Friday morning
            end_date=datetime(2025, 6, 27, 16, 0),     # Friday 4pm
            state=SleepState.ASLEEP
        )

        assigned = UniversalDateAssignment.assign_sleep_to_date(sleep)
        assert assigned == date(2025, 6, 28), "Day sleep assigned to next date"

    def test_exact_3pm_cutoff_assigned_to_same_date(self):
        """
        Edge case: wake at exactly 15:00 (3pm).
        Should be assigned to SAME date per Apple Health (inclusive).
        """
        sleep = SleepRecord(
            source_name="Apple Watch",
            start_date=datetime(2025, 6, 27, 7, 0),
            end_date=datetime(2025, 6, 27, 15, 0),  # Exactly 3pm
            state=SleepState.ASLEEP
        )

        assigned = UniversalDateAssignment.assign_sleep_to_date(sleep)
        assert assigned == date(2025, 6, 27), "3pm exactly stays on same date"

    def test_find_sleep_for_date_finds_midnight_crossing(self):
        """
        Critical test: Ensure we can find sleep that crosses midnight.
        This is what was broken in v0.5.3!
        """
        # Sleep from Thursday night to Friday morning
        sleep = SleepRecord(
            source_name="Apple Watch",
            start_date=datetime(2025, 6, 26, 22, 0),
            end_date=datetime(2025, 6, 27, 6, 0),
            state=SleepState.ASLEEP
        )

        # Find sleep for Friday
        found = UniversalDateAssignment.find_sleep_for_date(
            [sleep],
            date(2025, 6, 27)
        )

        assert len(found) == 1, "Should find midnight-crossing sleep"
        assert found[0] == sleep, "Found the correct sleep record"

    def test_find_sleep_handles_multiple_records(self):
        """
        Test finding sleep when multiple records exist.
        Common with naps or fragmented sleep.
        """
        records = [
            # Thursday night to Friday morning (belongs to Friday)
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 26, 22, 0),
                end_date=datetime(2025, 6, 27, 6, 0),
                state=SleepState.ASLEEP
            ),
            # Friday afternoon nap (belongs to Saturday due to 3pm rule)
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 27, 14, 0),
                end_date=datetime(2025, 6, 27, 15, 30),
                state=SleepState.ASLEEP
            ),
            # Friday night to Saturday morning (belongs to Saturday)
            SleepRecord(
                source_name="Apple Watch",
                start_date=datetime(2025, 6, 27, 23, 0),
                end_date=datetime(2025, 6, 28, 7, 0),
                state=SleepState.ASLEEP
            ),
        ]

        # Find Friday's sleep
        friday_sleep = UniversalDateAssignment.find_sleep_for_date(
            records,
            date(2025, 6, 27)
        )
        assert len(friday_sleep) == 1, "Only night sleep belongs to Friday"
        assert friday_sleep[0].start_date.date() == date(2025, 6, 26)

        # Find Saturday's sleep
        saturday_sleep = UniversalDateAssignment.find_sleep_for_date(
            records,
            date(2025, 6, 28)
        )
        assert len(saturday_sleep) == 2, "Nap and night sleep belong to Saturday"

    def test_group_records_by_date(self):
        """Test grouping multiple records by assigned date."""
        records = [
            # Monday night -> Tuesday
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 23, 22, 0),
                end_date=datetime(2025, 6, 24, 6, 0),
                state=SleepState.ASLEEP
            ),
            # Tuesday night -> Wednesday
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 24, 23, 0),
                end_date=datetime(2025, 6, 25, 7, 0),
                state=SleepState.ASLEEP
            ),
            # Wednesday shift work -> Thursday
            SleepRecord(
                source_name="Watch",
                start_date=datetime(2025, 6, 25, 8, 0),
                end_date=datetime(2025, 6, 25, 16, 0),
                state=SleepState.ASLEEP
            ),
        ]

        grouped = UniversalDateAssignment.group_records_by_date(records)

        assert len(grouped) == 3, "Three different dates"
        assert date(2025, 6, 24) in grouped, "Tuesday has sleep"
        assert date(2025, 6, 25) in grouped, "Wednesday has sleep"
        assert date(2025, 6, 26) in grouped, "Thursday has shift sleep"

    def test_validate_date_assignment_explains_logic(self):
        """Test the debugging/validation helper."""
        # Normal sleep
        normal = SleepRecord(
            source_name="Watch",
            start_date=datetime(2025, 6, 26, 22, 30),
            end_date=datetime(2025, 6, 27, 6, 45),
            state=SleepState.ASLEEP
        )

        explanation = UniversalDateAssignment.validate_date_assignment(normal)
        assert "wake at 06:45, before 3pm" in explanation
        assert "assigned to 2025-06-27" in explanation

        # Shift worker
        shift = SleepRecord(
            source_name="Watch",
            start_date=datetime(2025, 6, 27, 8, 0),
            end_date=datetime(2025, 6, 27, 16, 30),
            state=SleepState.ASLEEP
        )

        explanation = UniversalDateAssignment.validate_date_assignment(shift)
        assert "wake at 16:30, after 3pm" in explanation
        assert "assigned to next day 2025-06-28" in explanation

    def test_matches_sleep_aggregator_logic(self):
        """
        Ensure our logic EXACTLY matches SleepAggregator.
        This prevents future mismatches.
        """
        from big_mood_detector.domain.services.sleep_aggregator import SleepAggregator

        test_cases = [
            # Normal sleep
            (datetime(2025, 6, 26, 22, 0), datetime(2025, 6, 27, 6, 0)),
            # Late sleep
            (datetime(2025, 6, 27, 2, 0), datetime(2025, 6, 27, 10, 0)),
            # Shift work
            (datetime(2025, 6, 27, 8, 0), datetime(2025, 6, 27, 16, 0)),
            # Edge case at 3pm
            (datetime(2025, 6, 27, 7, 0), datetime(2025, 6, 27, 15, 0)),
        ]

        aggregator = SleepAggregator()

        for start, end in test_cases:
            sleep = SleepRecord(
                source_name="Test",
                start_date=start,
                end_date=end,
                state=SleepState.ASLEEP
            )

            # Our assignment
            our_date = UniversalDateAssignment.assign_sleep_to_date(sleep)

            # Aggregator's assignment
            their_date = aggregator._determine_sleep_date(sleep)

            assert our_date == their_date, (
                f"Date assignment mismatch for {start} to {end}: "
                f"ours={our_date}, theirs={their_date}"
            )
