"""Tests for Fitbit JSON parser support."""

import json
from datetime import date

from big_mood_detector.domain.entities.activity_record import ActivityType
from big_mood_detector.domain.entities.heart_rate_record import HeartMetricType
from big_mood_detector.domain.entities.sleep_record import SleepState
from big_mood_detector.infrastructure.parsers.json import FitbitJSONParser
from big_mood_detector.infrastructure.parsers.parser_factory import ParserFactory


class TestFitbitJSONParser:
    def test_parse_fitbit_payload(self):
        parser = FitbitJSONParser()
        payload = {
            "activities-steps": [
                {"dateTime": "2026-01-01", "value": "10234"},
                {"dateTime": "2026-01-02", "value": "9876"},
            ],
            "activities-heart": [
                {"dateTime": "2026-01-01", "value": {"restingHeartRate": 61}},
                {"dateTime": "2026-01-02", "value": {"restingHeartRate": 64}},
            ],
            "sleep": [
                {
                    "dateOfSleep": "2026-01-01",
                    "startTime": "2025-12-31T23:30:00.000",
                    "endTime": "2026-01-01T06:45:00.000",
                    "isMainSleep": True,
                }
            ],
        }

        result = parser.parse(payload)

        assert len(result["activity_records"]) == 2
        assert len(result["heart_rate_records"]) == 2
        assert len(result["sleep_records"]) == 1

        assert result["activity_records"][0].activity_type == ActivityType.STEP_COUNT
        assert result["heart_rate_records"][0].metric_type == HeartMetricType.HEART_RATE
        assert result["sleep_records"][0].state == SleepState.ASLEEP
        assert result["sleep_records"][0].start_date.date() == date(2025, 12, 31)

    def test_parse_fitbit_file(self, tmp_path):
        parser = FitbitJSONParser()
        fitbit_file = tmp_path / "fitbit_daily.json"
        payload = {
            "activities-steps": [{"dateTime": "2026-01-03", "value": "4321"}],
            "activities-heart": [{"dateTime": "2026-01-03", "value": {"restingHeartRate": 58}}],
            "sleep": [
                {
                    "dateOfSleep": "2026-01-03",
                    "startTime": "2026-01-02T23:45:00.000",
                    "endTime": "2026-01-03T07:15:00.000",
                    "isMainSleep": True,
                }
            ],
        }
        fitbit_file.write_text(json.dumps(payload), encoding="utf-8")

        result = parser.parse_file(fitbit_file)

        assert len(result["activity_records"]) == 1
        assert result["activity_records"][0].value == 4321
        assert len(result["heart_rate_records"]) == 1
        assert result["heart_rate_records"][0].value == 58
        assert len(result["sleep_records"]) == 1


class TestParserFactoryFitbitSupport:
    def test_create_parser_merges_fitbit_json_in_directory(self, tmp_path):
        parser = ParserFactory.create_parser(tmp_path)

        fitbit_payload = {
            "activities-steps": [{"dateTime": "2026-01-04", "value": "7654"}],
            "activities-heart": [{"dateTime": "2026-01-04", "value": {"restingHeartRate": 63}}],
            "sleep": [
                {
                    "dateOfSleep": "2026-01-04",
                    "startTime": "2026-01-03T23:10:00.000",
                    "endTime": "2026-01-04T06:20:00.000",
                    "isMainSleep": True,
                }
            ],
        }
        (tmp_path / "my_fitbit_export.json").write_text(
            json.dumps(fitbit_payload), encoding="utf-8"
        )

        parsed = parser.parse(tmp_path)

        assert len(parsed["activity_records"]) == 1
        assert parsed["activity_records"][0].activity_type == ActivityType.STEP_COUNT
        assert len(parsed["heart_rate_records"]) == 1
        assert parsed["heart_rate_records"][0].metric_type == HeartMetricType.HEART_RATE
        assert len(parsed["sleep_records"]) == 1
        assert parsed["sleep_records"][0].state == SleepState.ASLEEP

    def test_create_parser_detects_fitbit_by_schema_not_filename(self, tmp_path):
        parser = ParserFactory.create_parser(tmp_path)

        fitbit_payload = {
            "activities-steps": [{"dateTime": "2026-01-04", "value": "7654"}],
            "activities-heart": [{"dateTime": "2026-01-04", "value": {"restingHeartRate": 63}}],
            "sleep": [
                {
                    "dateOfSleep": "2026-01-04",
                    "startTime": "2026-01-03T23:10:00.000",
                    "endTime": "2026-01-04T06:20:00.000",
                    "isMainSleep": True,
                }
            ],
        }
        (tmp_path / "daily_export.json").write_text(json.dumps(fitbit_payload), encoding="utf-8")

        parsed = parser.parse(tmp_path)

        assert len(parsed["activity_records"]) == 1
        assert len(parsed["heart_rate_records"]) == 1
        assert len(parsed["sleep_records"]) == 1

    def test_parse_file_routes_fitbit_sleep_by_schema(self, tmp_path):
        payload = {
            "sleep": [
                {
                    "dateOfSleep": "2026-01-04",
                    "startTime": "2026-01-03T23:10:00.000",
                    "endTime": "2026-01-04T06:20:00.000",
                    "isMainSleep": True,
                }
            ]
        }
        file_path = tmp_path / "health_data.json"
        file_path.write_text(json.dumps(payload), encoding="utf-8")

        records = ParserFactory.parse_file(file_path, "sleep")

        assert len(records) == 1
        assert records[0].state == SleepState.ASLEEP
