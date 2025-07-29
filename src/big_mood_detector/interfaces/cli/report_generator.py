"""
Clinical report generation with temporal support.

This module provides clean separation of concerns for report generation.
"""

from pathlib import Path

from big_mood_detector.application.services.report_formatters import (
    DailyPredictionsSection,
    TemporalAssessmentSection,
)
from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineResult,
)


def generate_clinical_report_with_temporal(result: PipelineResult, output_path: Path) -> None:
    """
    Generate clinical report with temporal assessment support.
    
    This is a temporary implementation that adds temporal sections
    to the existing report format. Will be refactored to use
    proper formatter abstraction in the future.
    """
    # Import the original function
    from big_mood_detector.interfaces.cli.commands import generate_clinical_report
    
    # First generate the standard report
    generate_clinical_report(result, output_path)
    
    # Now enhance it with temporal sections if available
    temporal_section = TemporalAssessmentSection()
    if temporal_section.should_include(result):
        # Read the existing report
        content = output_path.read_text()
        
        # Find where to insert temporal section (after clinical assessment)
        assessment_end = content.find("\nCLINICAL RECOMMENDATIONS")
        if assessment_end > 0:
            # Insert temporal section
            temporal_content = temporal_section.format(result)
            new_content = (
                content[:assessment_end] +
                temporal_content +
                "\n" +
                content[assessment_end:]
            )
            
            # Also update daily predictions section
            daily_section = DailyPredictionsSection()
            daily_start = new_content.find("\nDETAILED DAILY ANALYSIS")
            if daily_start > 0:
                daily_end = new_content.find("\n=====", daily_start)
                if daily_end > 0:
                    # Replace daily section with enhanced version
                    enhanced_daily = daily_section.format(result)
                    new_content = (
                        new_content[:daily_start] +
                        enhanced_daily +
                        "\n" +
                        new_content[daily_end:]
                    )
            
            # Write enhanced report
            output_path.write_text(new_content)