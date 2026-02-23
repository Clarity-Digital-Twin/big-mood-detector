"""Fitbit parser composition and source detection utilities."""

import json
from pathlib import Path
from typing import Any

from .fitbit_activity_parser import FitbitActivityParser
from .fitbit_heart_rate_parser import FitbitHeartRateParser
from .fitbit_sleep_parser import FitbitSleepParser


def is_fitbit_payload(data: dict[str, Any]) -> bool:
    """Return True when JSON payload looks like Fitbit export schema."""
    if not isinstance(data, dict):
        return False
    fitbit_keys = {"activities-steps", "activities-heart"}
    return any(key in data for key in fitbit_keys)


def is_fitbit_sleep_payload(data: dict[str, Any]) -> bool:
    """Return True when payload looks like Fitbit sleep-only export data."""
    if not isinstance(data, dict) or "sleep" not in data:
        return False
    sleep_data = data.get("sleep")
    if isinstance(sleep_data, list) and sleep_data:
        first = sleep_data[0]
        return isinstance(first, dict) and {
            "startTime",
            "endTime",
        }.issubset(first.keys())
    if isinstance(sleep_data, dict):
        return {"startTime", "endTime"}.issubset(sleep_data.keys())
    return False


class FitbitJSONParser:
    """Parser for Fitbit daily export JSON files."""

    def __init__(self) -> None:
        self.sleep_parser = FitbitSleepParser()
        self.activity_parser = FitbitActivityParser()
        self.heart_rate_parser = FitbitHeartRateParser()

    def parse(self, data: dict[str, Any]) -> dict[str, list[Any]]:
        """Parse Fitbit JSON payload into domain records."""
        return {
            "sleep_records": self.sleep_parser.parse(data),
            "activity_records": self.activity_parser.parse(data),
            "heart_rate_records": self.heart_rate_parser.parse(data),
        }

    def parse_file(self, file_path: str | Path) -> dict[str, list[Any]]:
        """Parse Fitbit data from a JSON file path."""
        try:
            with open(file_path, encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Failed to parse Fitbit JSON file: {file_path}") from error
        return self.parse(payload)
