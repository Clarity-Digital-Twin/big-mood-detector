"""Fitbit heart-rate JSON parser."""

from datetime import datetime
from typing import Any

from big_mood_detector.domain.entities.heart_rate_record import (
    HeartMetricType,
    HeartRateRecord,
    MotionContext,
)
from big_mood_detector.infrastructure.logging import get_module_logger

logger = get_module_logger(__name__)


class FitbitHeartRateParser:
    """Parse Fitbit resting heart-rate exports into HeartRateRecord entities."""

    def parse(self, data: dict[str, Any]) -> list[HeartRateRecord]:
        records: list[HeartRateRecord] = []
        for entry in data.get("activities-heart", []):
            try:
                value_block = entry.get("value", {})
                if not isinstance(value_block, dict):
                    continue
                resting = value_block.get("restingHeartRate")
                if resting is None:
                    continue
                timestamp = self._parse_date(entry.get("dateTime"))
                records.append(
                    HeartRateRecord(
                        source_name="Fitbit",
                        timestamp=timestamp,
                        metric_type=HeartMetricType.HEART_RATE,
                        value=float(resting),
                        unit="count/min",
                        motion_context=MotionContext.SEDENTARY,
                    )
                )
            except (ValueError, TypeError, AttributeError) as error:
                logger.debug("fitbit_heart_rate_parse_error", error=str(error))
        return records

    def _parse_date(self, value: str | None) -> datetime:
        if not value:
            raise ValueError("Missing Fitbit date")
        return datetime.strptime(value[:10], "%Y-%m-%d")
