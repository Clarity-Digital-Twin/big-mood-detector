"""Unit tests for Fitbit heart-rate parser behavior and edge cases."""

from datetime import datetime

from big_mood_detector.domain.entities.heart_rate_record import (
    HeartMetricType,
    MotionContext,
)
from big_mood_detector.infrastructure.parsers.json import FitbitHeartRateParser


class TestFitbitHeartRateParser:
    def test_parses_resting_heart_rate_entries(self):
        parser = FitbitHeartRateParser()
        payload = {
            "activities-heart": [
                {"dateTime": "2026-03-01", "value": {"restingHeartRate": 61}},
                {"dateTime": "2026-03-02", "value": {"restingHeartRate": "64"}},
            ]
        }

        records = parser.parse(payload)

        assert len(records) == 2
        assert records[0].metric_type == HeartMetricType.HEART_RATE
        assert records[0].motion_context == MotionContext.SEDENTARY
        assert records[0].value == 61
        assert records[1].value == 64

    def test_parses_iso_datetime_by_truncating_to_day(self):
        parser = FitbitHeartRateParser()
        payload = {
            "activities-heart": [
                {"dateTime": "2026-03-06T08:20:00", "value": {"restingHeartRate": 58}},
            ]
        }

        records = parser.parse(payload)

        assert len(records) == 1
        assert records[0].timestamp == datetime(2026, 3, 6, 0, 0, 0)

    def test_skips_entries_without_resting_value_or_invalid_payload(self):
        parser = FitbitHeartRateParser()
        payload = {
            "activities-heart": [
                {"dateTime": "2026-03-10", "value": {"restingHeartRate": 59}},
                {"dateTime": "2026-03-11", "value": {}},
                {"dateTime": None, "value": {"restingHeartRate": 60}},
                {"dateTime": "2026-03-12", "value": "invalid-type"},
                {"dateTime": "bad-date", "value": {"restingHeartRate": 62}},
            ]
        }

        records = parser.parse(payload)

        assert len(records) == 1
        assert records[0].value == 59
