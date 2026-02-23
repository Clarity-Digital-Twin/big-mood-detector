"""Fitbit activity JSON parser."""

from datetime import datetime
from typing import Any

from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.infrastructure.logging import get_module_logger

logger = get_module_logger(__name__)


class FitbitActivityParser:
    """Parse Fitbit daily step exports into ActivityRecord entities."""

    def parse(self, data: dict[str, Any]) -> list[ActivityRecord]:
        records: list[ActivityRecord] = []
        for entry in data.get("activities-steps", []):
            try:
                day = self._parse_date(entry.get("dateTime"))
                value = float(entry.get("value", 0))
                records.append(
                    ActivityRecord(
                        source_name="Fitbit",
                        start_date=day.replace(hour=0, minute=0, second=0, microsecond=0),
                        end_date=day.replace(hour=23, minute=59, second=59, microsecond=0),
                        activity_type=ActivityType.STEP_COUNT,
                        value=value,
                        unit="count",
                    )
                )
            except (ValueError, TypeError) as error:
                logger.debug("fitbit_activity_parse_error", error=str(error))
        return records

    def _parse_date(self, value: str | None) -> datetime:
        if not value:
            raise ValueError("Missing Fitbit date")
        return datetime.strptime(value[:10], "%Y-%m-%d")
