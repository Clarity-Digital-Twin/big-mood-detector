"""Unit tests for Fitbit activity parser behavior and edge cases."""

from datetime import datetime

from big_mood_detector.domain.entities.activity_record import ActivityType
from big_mood_detector.infrastructure.parsers.json import FitbitActivityParser


class TestFitbitActivityParser:
    def test_parses_valid_daily_steps(self):
        parser = FitbitActivityParser()
        payload = {
            "activities-steps": [
                {"dateTime": "2026-03-01", "value": "10234"},
                {"dateTime": "2026-03-02", "value": 8765},
            ]
        }

        records = parser.parse(payload)

        assert len(records) == 2
        assert records[0].activity_type == ActivityType.STEP_COUNT
        assert records[0].value == 10234
        assert records[0].start_date == datetime(2026, 3, 1, 0, 0, 0)
        assert records[0].end_date == datetime(2026, 3, 1, 23, 59, 59)

    def test_parses_iso_datetime_by_truncating_to_day(self):
        parser = FitbitActivityParser()
        payload = {
            "activities-steps": [
                {"dateTime": "2026-03-05T12:30:45.000", "value": "4200"},
            ]
        }

        records = parser.parse(payload)

        assert len(records) == 1
        assert records[0].start_date == datetime(2026, 3, 5, 0, 0, 0)
        assert records[0].end_date == datetime(2026, 3, 5, 23, 59, 59)

    def test_skips_entries_with_invalid_or_missing_fields(self):
        parser = FitbitActivityParser()
        payload = {
            "activities-steps": [
                {"dateTime": "2026-03-10", "value": "1000"},
                {"dateTime": None, "value": "2500"},
                {"dateTime": "2026-03-11", "value": "not-a-number"},
                {"dateTime": "bad-date", "value": "3000"},
            ]
        }

        records = parser.parse(payload)

        assert len(records) == 1
        assert records[0].value == 1000
