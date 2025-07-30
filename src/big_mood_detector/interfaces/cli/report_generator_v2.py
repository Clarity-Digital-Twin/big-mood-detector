"""
Report generator v2 - Clean architecture implementation.

This module demonstrates proper SOLID principles and clean code.
"""

from pathlib import Path

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineResult,
)
from big_mood_detector.interfaces.cli.report_factory import ReportFormatterFactory


def generate_clinical_report_v2(
    result: PipelineResult,
    output_path: Path,
    format_type: str = "clinical"
) -> None:
    """
    Generate a clinical report using clean architecture.

    This function follows the Dependency Inversion Principle by depending
    on abstractions (ReportFormatterInterface) rather than concrete implementations.

    Args:
        result: Pipeline processing result
        output_path: Where to save the report
        format_type: Type of report format (default: "clinical")
    """
    # Use factory to create formatter (supports future formats)
    formatter = ReportFormatterFactory.create_formatter(format_type)

    # Delegate to formatter
    formatter.save(result, output_path)
