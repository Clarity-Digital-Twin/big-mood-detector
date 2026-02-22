"""Tests for Fitbit directory parser adapter."""

import json

from big_mood_detector.domain.entities.activity_record import ActivityType
from big_mood_detector.domain.entities.heart_rate_record import HeartMetricType
from big_mood_detector.domain.entities.sleep_record import SleepState
from big_mood_detector.infrastructure.parsers.json import FitbitDirectoryParser
from big_mood_detector.infrastructure.parsers.parser_factory import ParserFactory


def test_fitbit_directory_parser_reads_zip_layout(tmp_path):
    (tmp_path / "profile.json").write_text("{}", encoding="utf-8")
    activities = tmp_path / "activities"
    heart_rate = tmp_path / "heart_rate"
    sleep = tmp_path / "sleep"
    activities.mkdir()
    heart_rate.mkdir()
    sleep.mkdir()

    (activities / "steps-2026-01-01.json").write_text(
        json.dumps([{"value": 8000}]), encoding="utf-8"
    )
    (activities / "steps-2026-01-02.json").write_text(
        json.dumps([{"value": 9000}]), encoding="utf-8"
    )

    (heart_rate / "heart_rate-2026-01-01.json").write_text(
        json.dumps([
            {"dateTime": "2026-01-01T08:00:00", "value": 60},
            {"dateTime": "2026-01-01T12:00:00", "value": 66},
        ]),
        encoding="utf-8",
    )

    (sleep / "sleep-2026-01-01.json").write_text(
        json.dumps(
            {
                "sleep": [
                    {
                        "startTime": "2025-12-31T23:20:00.000",
                        "endTime": "2026-01-01T06:50:00.000",
                        "isMainSleep": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    parser = FitbitDirectoryParser()
    parsed = parser.parse(tmp_path)

    assert len(parsed["activity_records"]) == 2
    assert parsed["activity_records"][0].activity_type == ActivityType.STEP_COUNT
    assert len(parsed["heart_rate_records"]) == 1
    assert parsed["heart_rate_records"][0].metric_type == HeartMetricType.HEART_RATE
    assert len(parsed["sleep_records"]) == 1
    assert parsed["sleep_records"][0].state == SleepState.ASLEEP


def test_parser_factory_parses_fitbit_directory_layout(tmp_path):
    (tmp_path / "profile.json").write_text("{}", encoding="utf-8")
    activities = tmp_path / "activities"
    heart_rate = tmp_path / "heart_rate"
    sleep = tmp_path / "sleep"
    activities.mkdir()
    heart_rate.mkdir()
    sleep.mkdir()

    (activities / "steps-2026-01-03.json").write_text(
        json.dumps([{"value": 7123}]), encoding="utf-8"
    )
    (heart_rate / "hr-2026-01-03.json").write_text(
        json.dumps([{"value": 62}]), encoding="utf-8"
    )
    (sleep / "sleep-2026-01-03.json").write_text(
        json.dumps(
            [
                {
                    "startTime": "2026-01-02T23:10:00.000",
                    "endTime": "2026-01-03T06:10:00.000",
                    "isMainSleep": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    parser = ParserFactory.create_parser(tmp_path)
    parsed = parser.parse(tmp_path)

    assert len(parsed["activity_records"]) == 1
    assert parsed["activity_records"][0].activity_type == ActivityType.STEP_COUNT
    assert len(parsed["heart_rate_records"]) == 1
    assert parsed["heart_rate_records"][0].metric_type == HeartMetricType.HEART_RATE
    assert len(parsed["sleep_records"]) == 1
    assert parsed["sleep_records"][0].state == SleepState.ASLEEP
