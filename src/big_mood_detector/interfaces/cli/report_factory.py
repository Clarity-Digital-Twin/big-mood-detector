"""
Report formatter factory following SOLID principles.

This allows for easy extension with new formatter types.
"""

from big_mood_detector.application.services.clinical_report_formatter import ClinicalReportFormatter
from big_mood_detector.domain.services.report_formatter_interface import ReportFormatterInterface


class ReportFormatterFactory:
    """Factory for creating report formatters."""
    
    @staticmethod
    def create_formatter(format_type: str = "clinical") -> ReportFormatterInterface:
        """
        Create a report formatter based on type.
        
        Args:
            format_type: Type of formatter to create
            
        Returns:
            Report formatter instance
            
        Raises:
            ValueError: If format_type is not recognized
        """
        if format_type == "clinical":
            return ClinicalReportFormatter()
        # Future formats can be added here without modifying existing code
        # elif format_type == "pdf":
        #     return PDFReportFormatter()
        # elif format_type == "json":
        #     return JSONReportFormatter()
        else:
            raise ValueError(f"Unknown report format: {format_type}")