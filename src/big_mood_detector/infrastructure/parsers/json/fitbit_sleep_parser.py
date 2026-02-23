"""Fitbit sleep JSON parser."""

from datetime import datetime
from typing import Any

from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.infrastructure.logging import get_module_logger

logger = get_module_logger(__name__)


class FitbitSleepParser:
    """Parse Fitbit sleep sessions into SleepRecord entities."""

    def parse(self, data: dict[str, Any]) -> list[SleepRecord]:
        records: list[SleepRecord] = []
        for entry in data.get("sleep", []):
            try:
                if entry.get("isMainSleep") is not True:
                    continue
                start = self._parse_datetime(entry.get("startTime"))
                end = self._parse_datetime(entry.get("endTime"))
                records.append(
                    SleepRecord(
                        source_name="Fitbit",
                        start_date=start,
                        end_date=end,
                        state=SleepState.ASLEEP,
                    )
                )
            except (ValueError, TypeError) as error:
                logger.debug("fitbit_sleep_parse_error", error=str(error))
        return records

    def _parse_datetime(self, value: str | None) -> datetime:
        if not value:
            raise ValueError("Missing datetime")
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
