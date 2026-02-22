"""Unit tests for Fitbit sleep parser behavior and edge cases."""

from datetime import datetime

from big_mood_detector.domain.entities.sleep_record import SleepState
from big_mood_detector.infrastructure.parsers.json import FitbitSleepParser


class TestFitbitSleepParser:
    def test_parses_main_sleep_sessions(self):
        parser = FitbitSleepParser()
        payload = {
            "sleep": [
                {
                    "startTime": "2026-03-01T23:15:00.000",
                    "endTime": "2026-03-02T06:45:00.000",
                    "isMainSleep": True,
                },
                {
                    "startTime": "2026-03-02T23:30:00Z",
                    "endTime": "2026-03-03T06:30:00Z",
                    "isMainSleep": True,
                },
            ]
        }

        records = parser.parse(payload)

        assert len(records) == 2
        assert records[0].state == SleepState.ASLEEP
        assert records[0].start_date == datetime(2026, 3, 1, 23, 15, 0)
        assert records[1].end_date == datetime(2026, 3, 3, 6, 30, 0)

    def test_filters_out_non_main_sleep(self):
        parser = FitbitSleepParser()
        payload = {
            "sleep": [
                {
                    "startTime": "2026-03-05T23:00:00.000",
                    "endTime": "2026-03-06T06:00:00.000",
                    "isMainSleep": False,
                }
            ]
        }

        records = parser.parse(payload)

        assert records == []

    def test_skips_entries_with_invalid_or_missing_datetimes(self):
        parser = FitbitSleepParser()
        payload = {
            "sleep": [
                {
                    "startTime": "2026-03-10T23:00:00.000",
                    "endTime": "2026-03-11T07:00:00.000",
                    "isMainSleep": True,
                },
                {
                    "startTime": None,
                    "endTime": "2026-03-12T07:00:00.000",
                    "isMainSleep": True,
                },
                {
                    "startTime": "2026-03-12T23:00:00.000",
                    "endTime": None,
                    "isMainSleep": True,
                },
                {
                    "startTime": "bad-date",
                    "endTime": "2026-03-13T07:00:00.000",
                    "isMainSleep": True,
                },
            ]
        }

        records = parser.parse(payload)

        assert len(records) == 1
        assert records[0].start_date == datetime(2026, 3, 10, 23, 0, 0)
