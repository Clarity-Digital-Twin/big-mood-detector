"""Adapter for parsing unzipped Fitbit export directory structures."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from big_mood_detector.infrastructure.logging import get_module_logger

from .fitbit_parsers import FitbitJSONParser

logger = get_module_logger(__name__)


class FitbitDirectoryParser:
    """Parse Fitbit export folders into normalized domain records."""

    DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")

    def __init__(self) -> None:
        self.parser = FitbitJSONParser()

    def looks_like_fitbit_directory(self, directory: Path) -> bool:
        """Detect whether directory matches Fitbit export layout."""
        return any(
            [
                (directory / "profile.json").exists(),
                (directory / "activities").exists(),
                (directory / "heart_rate").exists(),
                (directory / "sleep").exists(),
            ]
        )

    def parse(self, directory: str | Path) -> dict[str, list[Any]]:
        """Parse Fitbit export directory into records."""
        root = Path(directory)
        payload = {
            "activities-steps": self._collect_steps(root / "activities"),
            "activities-heart": self._collect_heart(root / "heart_rate"),
            "sleep": self._collect_sleep(root / "sleep"),
        }
        return self.parser.parse(payload)

    def _collect_steps(self, steps_dir: Path) -> list[dict[str, Any]]:
        step_totals: dict[str, float] = defaultdict(float)
        if not steps_dir.exists():
            return []

        for json_file in sorted(steps_dir.glob("*.json")):
            default_date = self._extract_date_from_path(json_file)
            for entry in self._extract_step_entries(self._load_json(json_file), default_date):
                date_key = entry.get("dateTime")
                value = entry.get("value")
                if date_key and value is not None:
                    step_totals[date_key] += float(value)

        return [
            {"dateTime": day, "value": str(int(value))}
            for day, value in sorted(step_totals.items())
        ]

    def _collect_heart(self, heart_dir: Path) -> list[dict[str, Any]]:
        daily_values: dict[str, list[float]] = defaultdict(list)
        if not heart_dir.exists():
            return []

        for json_file in sorted(heart_dir.glob("*.json")):
            default_date = self._extract_date_from_path(json_file)
            entries = self._extract_heart_entries(self._load_json(json_file), default_date)
            for day, value in entries:
                daily_values[day].append(value)

        return [
            {
                "dateTime": day,
                "value": {"restingHeartRate": int(round(mean(values)))},
            }
            for day, values in sorted(daily_values.items())
            if values
        ]

    def _collect_sleep(self, sleep_dir: Path) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        if not sleep_dir.exists():
            return sessions

        for json_file in sorted(sleep_dir.glob("*.json")):
            payload = self._load_json(json_file)
            sessions.extend(self._extract_sleep_entries(payload))

        return sessions

    def _extract_step_entries(
        self, payload: Any, default_date: str | None
    ) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and "activities-steps" in payload:
            return payload.get("activities-steps", [])
        if isinstance(payload, dict) and "dateTime" in payload and "value" in payload:
            return [payload]
        if isinstance(payload, list):
            result: list[dict[str, Any]] = []
            for item in payload:
                if isinstance(item, dict) and "value" in item:
                    date_value = item.get("dateTime") or default_date
                    if date_value:
                        result.append({"dateTime": str(date_value)[:10], "value": item["value"]})
            return result
        return []

    def _extract_heart_entries(
        self, payload: Any, default_date: str | None
    ) -> list[tuple[str, float]]:
        entries: list[tuple[str, float]] = []
        if isinstance(payload, dict) and "activities-heart" in payload:
            for item in payload.get("activities-heart", []):
                day = str(item.get("dateTime", ""))[:10]
                value = item.get("value", {}).get("restingHeartRate")
                if day and value is not None:
                    entries.append((day, float(value)))
            return entries

        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if not isinstance(item, dict):
                continue

            date_value = item.get("dateTime") or item.get("date") or default_date
            if not date_value:
                continue

            day = str(date_value)[:10]
            value = None
            if isinstance(item.get("value"), (int, float, str)):
                try:
                    value = float(item["value"])
                except (TypeError, ValueError):
                    value = None
            elif isinstance(item.get("value"), dict):
                value_block = item["value"]
                if "restingHeartRate" in value_block:
                    value = float(value_block["restingHeartRate"])
                elif "bpm" in value_block:
                    value = float(value_block["bpm"])
            elif "restingHeartRate" in item:
                value = float(item["restingHeartRate"])
            elif "bpm" in item:
                value = float(item["bpm"])

            if value is not None:
                entries.append((day, value))

        return entries

    def _extract_sleep_entries(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and "sleep" in payload:
            return [
                item
                for item in payload.get("sleep", [])
                if isinstance(item, dict) and item.get("startTime") and item.get("endTime")
            ]
        if isinstance(payload, list):
            return [
                item
                for item in payload
                if isinstance(item, dict) and item.get("startTime") and item.get("endTime")
            ]
        if isinstance(payload, dict) and payload.get("startTime") and payload.get("endTime"):
            return [payload]
        return []

    def _extract_date_from_path(self, path: Path) -> str | None:
        match = self.DATE_PATTERN.search(path.name)
        return match.group(1) if match else None

    def _load_json(self, path: Path) -> Any:
        try:
            with open(path, encoding="utf-8") as file_handle:
                return json.load(file_handle)
        except (OSError, json.JSONDecodeError) as error:
            logger.debug("fitbit_file_load_error", file=str(path), error=str(error))
            return {}
