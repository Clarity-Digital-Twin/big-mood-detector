"""
Clinical report formatter implementation.

Follows SOLID principles with composable sections.
"""

from pathlib import Path

from big_mood_detector.application.services.report_formatters import (
    ReportSection,
    TemporalAssessmentSection,
)
from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineResult,
)
from big_mood_detector.domain.services.report_formatter_interface import (
    ReportFormatterInterface,
)
from big_mood_detector.interfaces.cli.commands import format_risk_level


class HeaderSection(ReportSection):
    """Report header section."""

    def should_include(self, result: PipelineResult) -> bool:
        return True

    def format(self, result: PipelineResult) -> str:
        lines = []
        lines.append("CLINICAL DECISION SUPPORT (CDS) REPORT")
        lines.append("=" * 50)
        lines.append("")
        lines.append("PATIENT DATA SUMMARY")
        lines.append(f"Analysis Period: {len(result.daily_predictions)} days")
        lines.append(f"Total Records Processed: {result.records_processed}")
        lines.append(f"Data Quality Score: {result.confidence_score:.1%}")

        if result.metadata.get("personal_calibration_used"):
            lines.append(f"\nPersonalized Model: Active (User: {result.metadata.get('user_id')})")

        return "\n".join(lines)


class ClinicalRiskSection(ReportSection):
    """Clinical risk assessment section."""

    def should_include(self, result: PipelineResult) -> bool:
        return bool(result.overall_summary)

    def format(self, result: PipelineResult) -> str:
        if not self.should_include(result):
            return ""

        lines = []
        lines.append("\nCLINICAL RISK ASSESSMENT")
        lines.append("-" * 30)

        summary = result.overall_summary
        dep_risk = summary.get("avg_depression_risk", 0)
        hypo_risk = summary.get("avg_hypomanic_risk", 0)
        manic_risk = summary.get("avg_manic_risk", 0)

        lines.append(f"Depression Risk: {format_risk_level(dep_risk)}")
        lines.append(f"Hypomanic Risk: {format_risk_level(hypo_risk)}")
        lines.append(f"Manic Risk: {format_risk_level(manic_risk)}")

        # PAT assessment if available
        if 'avg_pat_depression_probability' in summary:
            pat_score = summary['avg_pat_depression_probability']
            lines.append(f"\nPAT Depression Assessment: {format_risk_level(pat_score)}")
            lines.append("  (Based on PHQ-9 ≥ 10 threshold)")

        return "\n".join(lines)


class RecommendationsSection(ReportSection):
    """Clinical recommendations section."""

    def should_include(self, result: PipelineResult) -> bool:
        return bool(result.overall_summary)

    def format(self, result: PipelineResult) -> str:
        if not self.should_include(result):
            return ""

        lines = []
        lines.append("\nCLINICAL RECOMMENDATIONS")
        lines.append("-" * 30)

        summary = result.overall_summary
        dep_risk = summary.get("avg_depression_risk", 0)
        hypo_risk = summary.get("avg_hypomanic_risk", 0)
        manic_risk = summary.get("avg_manic_risk", 0)

        # Depression recommendations
        if dep_risk > 0.7:
            lines.append("⚠️  HIGH DEPRESSION RISK DETECTED")
            lines.append("• Consider immediate clinical evaluation")
            lines.append("• Review sleep patterns and activity levels")
            lines.append("• Monitor for suicidal ideation")
            lines.append("• Assess functional impairment")
        elif dep_risk > 0.4:
            lines.append("⚠️  MODERATE DEPRESSION RISK")
            lines.append("• Schedule follow-up within 2 weeks")
            lines.append("• Assess sleep hygiene and daily routines")
            lines.append("• Consider therapy referral")
            lines.append("• Monitor symptom progression")
        else:
            lines.append("✓ Low depression risk")
            lines.append("• Continue regular monitoring")
            lines.append("• Maintain healthy sleep schedule")

        # Mania/hypomania recommendations
        if hypo_risk > 0.5 or manic_risk > 0.3:
            lines.append("\n⚠️  ELEVATED MOOD EPISODE RISK")
            lines.append("• Monitor for decreased sleep need")
            lines.append("• Track activity levels and goal-directed behavior")
            lines.append("• Review medication compliance")
            lines.append("• Assess for impulsive behaviors")

        return "\n".join(lines)


class DataQualitySection(ReportSection):
    """Data quality warnings section."""

    def should_include(self, result: PipelineResult) -> bool:
        return bool(result.warnings)

    def format(self, result: PipelineResult) -> str:
        if not self.should_include(result):
            return ""

        lines = []
        lines.append("\nDATA QUALITY WARNINGS")
        lines.append("-" * 30)
        for warning in result.warnings:
            lines.append(f"• {warning}")

        return "\n".join(lines)


class FooterSection(ReportSection):
    """Report footer section."""

    def should_include(self, result: PipelineResult) -> bool:
        return True

    def format(self, result: PipelineResult) -> str:
        lines = []
        lines.append("\n" + "=" * 50)
        lines.append("Generated by Big Mood Detector")
        lines.append("This report is for clinical decision support only.")
        lines.append("Not a substitute for professional diagnosis.")

        return "\n".join(lines)


class ClinicalReportFormatter(ReportFormatterInterface):
    """
    Main clinical report formatter.

    Composes multiple sections following the Open/Closed principle.
    New sections can be added without modifying this class.
    """

    def __init__(self, sections: list[ReportSection] | None = None):
        """Initialize with customizable sections."""
        if sections is None:
            # Default sections in order
            from big_mood_detector.application.services.report_formatters import (
                DailyPredictionsSection,
            )

            self.sections = [
                HeaderSection(),
                ClinicalRiskSection(),
                TemporalAssessmentSection(),  # New temporal section
                RecommendationsSection(),
                DataQualitySection(),
                DailyPredictionsSection(),  # Enhanced with temporal support
                FooterSection(),
            ]
        else:
            self.sections = sections

    def format(self, result: PipelineResult) -> str:
        """Format report by combining all sections."""
        report_parts = []

        for section in self.sections:
            if section.should_include(result):
                content = section.format(result)
                if content:
                    report_parts.append(content)

        return "\n".join(report_parts)

    def save(self, result: PipelineResult, output_path: Path) -> None:
        """Save formatted report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.format(result)
        output_path.write_text(content)
