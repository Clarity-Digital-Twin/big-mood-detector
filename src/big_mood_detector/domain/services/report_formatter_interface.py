"""
Report formatter interface following SOLID principles.

This defines the contract for all report formatters.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineResult,
)


class ReportFormatterInterface(ABC):
    """Interface for clinical report formatters."""

    @abstractmethod
    def format(self, result: PipelineResult) -> str:
        """
        Format a pipeline result into a clinical report.

        Args:
            result: The pipeline processing result

        Returns:
            Formatted report content as a string
        """
        pass

    @abstractmethod
    def save(self, result: PipelineResult, output_path: Path) -> None:
        """
        Format and save a report to file.

        Args:
            result: The pipeline processing result
            output_path: Where to save the report
        """
        pass
