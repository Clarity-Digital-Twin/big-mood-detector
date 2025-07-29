"""
Universal Date Assignment Service

SINGLE SOURCE OF TRUTH for how dates are assigned to health records.
This is CRITICAL for correct functioning of the entire pipeline.

Following the Seoul National University paper and Apple Health conventions.
"""

from datetime import date, timedelta

from big_mood_detector.domain.entities.sleep_record import SleepRecord


class UniversalDateAssignment:
    """
    Centralized date assignment logic following Apple Health conventions.

    ALL components MUST use this service to ensure consistency.
    The bug in v0.5.3 was caused by different components using different logic.

    Apple Health Convention:
    - Sleep is assigned to the date you WAKE UP
    - If you wake before 3pm: assigned to wake date
    - If you wake at/after 3pm: assigned to next date

    This matches clinical practice where a "night's sleep" belongs to
    the following day's assessment.
    """

    AFTERNOON_CUTOFF_HOUR = 15  # 3 PM cutoff per Apple Health

    @staticmethod
    def assign_sleep_to_date(record: SleepRecord) -> date:
        """
        Assign a sleep record to its clinical date.

        Args:
            record: Sleep record to assign

        Returns:
            The date this sleep belongs to for clinical assessment

        Example:
            Sleep from June 26 22:00 to June 27 06:00 -> June 27
            Sleep from June 27 08:00 to June 27 16:00 -> June 28 (shift worker)
        """
        wake_time = record.end_date

        # If wake time is at or before 3pm (15:00), assign to wake date
        # Using <= 15 to include 3:00pm exactly as same day
        if wake_time.hour < UniversalDateAssignment.AFTERNOON_CUTOFF_HOUR or (
            wake_time.hour == UniversalDateAssignment.AFTERNOON_CUTOFF_HOUR
            and wake_time.minute == 0
        ):
            return wake_time.date()
        else:
            # Wake time is after 3pm, assign to next date
            return (wake_time + timedelta(days=1)).date()

    @staticmethod
    def find_sleep_for_date(
        records: list[SleepRecord],
        target_date: date
    ) -> list[SleepRecord]:
        """
        Find all sleep records that belong to a specific date.

        This is the CORRECT way to find sleep for a date, replacing
        the broken pattern of checking start_date == target_date.

        Args:
            records: List of sleep records to search
            target_date: Date to find sleep for

        Returns:
            All sleep records assigned to the target date

        Example:
            For June 27, finds sleep that ended on June 27 morning
            (typically started June 26 night)
        """
        matching_records = []

        for record in records:
            assigned_date = UniversalDateAssignment.assign_sleep_to_date(record)
            if assigned_date == target_date:
                matching_records.append(record)

        return matching_records

    @staticmethod
    def group_records_by_date(
        records: list[SleepRecord]
    ) -> dict[date, list[SleepRecord]]:
        """
        Group sleep records by their assigned clinical date.

        Args:
            records: List of sleep records to group

        Returns:
            Dictionary mapping dates to their sleep records
        """
        grouped: dict[date, list[SleepRecord]] = {}

        for record in records:
            assigned_date = UniversalDateAssignment.assign_sleep_to_date(record)

            if assigned_date not in grouped:
                grouped[assigned_date] = []

            grouped[assigned_date].append(record)

        return grouped

    @staticmethod
    def validate_date_assignment(record: SleepRecord) -> str:
        """
        Explain how a sleep record is assigned for debugging.

        Args:
            record: Sleep record to validate

        Returns:
            Human-readable explanation of the assignment
        """
        wake_time = record.end_date
        assigned_date = UniversalDateAssignment.assign_sleep_to_date(record)

        explanation = (
            f"Sleep from {record.start_date.strftime('%Y-%m-%d %H:%M')} "
            f"to {record.end_date.strftime('%Y-%m-%d %H:%M')} "
        )

        if wake_time.hour < UniversalDateAssignment.AFTERNOON_CUTOFF_HOUR:
            explanation += (
                f"(wake at {wake_time.strftime('%H:%M')}, before 3pm) "
                f"-> assigned to {assigned_date}"
            )
        else:
            explanation += (
                f"(wake at {wake_time.strftime('%H:%M')}, after 3pm) "
                f"-> assigned to next day {assigned_date}"
            )

        return explanation
