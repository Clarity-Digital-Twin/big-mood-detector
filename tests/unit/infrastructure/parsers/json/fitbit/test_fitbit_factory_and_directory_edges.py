"""Edge-case tests for Fitbit directory adapter and parser factory routing."""

import json

from big_mood_detector.infrastructure.parsers.json import FitbitDirectoryParser
from big_mood_detector.infrastructure.parsers.parser_factory import ParserFactory


def test_fitbit_directory_detection_variants(tmp_path):
    parser = FitbitDirectoryParser()

    assert parser.looks_like_fitbit_directory(tmp_path) is False

    (tmp_path / "activities").mkdir()
    assert parser.looks_like_fitbit_directory(tmp_path) is True


def test_fitbit_directory_aggregates_steps_and_heart_and_skips_bad_json(tmp_path):
    (tmp_path / "profile.json").write_text("{}", encoding="utf-8")
    activities = tmp_path / "activities"
    heart_rate = tmp_path / "heart_rate"
    sleep = tmp_path / "sleep"
    activities.mkdir()
    heart_rate.mkdir()
    sleep.mkdir()

    (activities / "steps-2026-04-01.json").write_text(
        json.dumps([{"value": 1000}, {"dateTime": "2026-04-01", "value": 500}]),
        encoding="utf-8",
    )
    (activities / "steps-extra-2026-04-01.json").write_text(
        json.dumps([{"dateTime": "2026-04-01", "value": 250}]),
        encoding="utf-8",
    )

    (heart_rate / "heart_rate-2026-04-01.json").write_text(
        json.dumps([
            {"dateTime": "2026-04-01T08:00:00", "value": 60},
            {"dateTime": "2026-04-01T12:00:00", "value": {"bpm": 66}},
            {"dateTime": "2026-04-01T18:00:00", "value": {"restingHeartRate": 63}},
        ]),
        encoding="utf-8",
    )
    (heart_rate / "broken.json").write_text("{not-json", encoding="utf-8")

    (sleep / "sleep-2026-04-01.json").write_text(
        json.dumps([
            {
                "startTime": "2026-03-31T23:00:00.000",
                "endTime": "2026-04-01T06:30:00.000",
                "isMainSleep": True,
            },
            {
                "startTime": "2026-04-01T14:00:00.000",
                "endTime": "2026-04-01T14:20:00.000",
                "isMainSleep": False,
            },
        ]),
        encoding="utf-8",
    )

    parsed = FitbitDirectoryParser().parse(tmp_path)

    assert len(parsed["activity_records"]) == 1
    assert parsed["activity_records"][0].value == 1750
    assert len(parsed["heart_rate_records"]) == 1
    assert parsed["heart_rate_records"][0].value == 63
    assert len(parsed["sleep_records"]) == 1


def test_parser_factory_detect_json_source_apple_vs_fitbit():
    fitbit_payload = {"activities-steps": [{"dateTime": "2026-04-05", "value": "1000"}]}
    apple_payload = {"data": {"metrics": []}}

    assert ParserFactory.detect_json_source(fitbit_payload) == "fitbit"
    assert ParserFactory.detect_json_source(apple_payload) == "apple"


def test_parser_factory_parse_file_routes_fitbit_activity_and_heart(tmp_path):
    payload = {
        "activities-steps": [{"dateTime": "2026-04-08", "value": "3210"}],
        "activities-heart": [
            {"dateTime": "2026-04-08", "value": {"restingHeartRate": 57}}
        ],
    }
    file_path = tmp_path / "export.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    activity = ParserFactory.parse_file(file_path, "activity")
    heart = ParserFactory.parse_file(file_path, "heart_rate")

    assert len(activity) == 1
    assert activity[0].value == 3210
    assert len(heart) == 1
    assert heart[0].value == 57


def test_parser_factory_composite_merges_apple_json_and_fitbit_directory(tmp_path):
    (tmp_path / "profile.json").write_text("{}", encoding="utf-8")
    (tmp_path / "activities").mkdir()
    (tmp_path / "heart_rate").mkdir()
    (tmp_path / "sleep").mkdir()

    (tmp_path / "activities" / "steps-2026-04-10.json").write_text(
        json.dumps([{"value": 5000}]), encoding="utf-8"
    )
    (tmp_path / "heart_rate" / "heart_rate-2026-04-10.json").write_text(
        json.dumps([{"value": 61}]), encoding="utf-8"
    )
    (tmp_path / "sleep" / "sleep-2026-04-10.json").write_text(
        json.dumps([
            {
                "startTime": "2026-04-09T23:30:00.000",
                "endTime": "2026-04-10T06:40:00.000",
                "isMainSleep": True,
            }
        ]),
        encoding="utf-8",
    )

    (tmp_path / "Step Count.json").write_text(
        json.dumps({
            "data": {
                "metrics": [
                    {
                        "name": "step_count",
                        "data": [{"date": "2026-04-10 00:00:00", "qty": 1234}],
                    }
                ]
            }
        }),
        encoding="utf-8",
    )

    parsed = ParserFactory.create_parser(tmp_path).parse(tmp_path)

    assert len(parsed["activity_records"]) == 2
    assert len(parsed["heart_rate_records"]) == 1
    assert len(parsed["sleep_records"]) == 1
