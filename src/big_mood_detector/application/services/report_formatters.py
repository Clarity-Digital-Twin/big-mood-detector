"""
Report formatters for clinical output.

Following SOLID principles - each formatter has a single responsibility.
"""

from abc import ABC, abstractmethod

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineResult,
)


class ReportSection(ABC):
    """Abstract base for report sections."""

    @abstractmethod
    def format(self, result: PipelineResult) -> str:
        """Format this section of the report."""
        pass

    @abstractmethod
    def should_include(self, result: PipelineResult) -> bool:
        """Determine if this section should be included."""
        pass


class TemporalAssessmentSection(ReportSection):
    """Formats the temporal mood assessment section."""

    def should_include(self, result: PipelineResult) -> bool:
        """Include if any predictions have temporal data."""
        return any(
            'current_depression' in pred
            for pred in result.daily_predictions.values()
        )

    def format(self, result: PipelineResult) -> str:
        """Format temporal assessment section."""
        if not self.should_include(result):
            return ""

        lines = []
        lines.append("\nTEMPORAL MOOD ASSESSMENT (NOW vs TOMORROW)")
        lines.append("-" * 40)

        # Find most recent day with temporal data
        for date_key in sorted(result.daily_predictions.keys(), reverse=True):
            pred = result.daily_predictions[date_key]
            if 'current_depression' in pred:
                current = pred.get('current_depression', 0)
                future = pred.get('depression_risk', 0)
                concordance = pred.get('temporal_concordance', 0)

                lines.append(f"\nAssessment for {date_key}:")
                lines.append(f"NOW (Current State - PAT):      {self._format_risk(current)}")
                lines.append(f"TOMORROW (Future Risk - XGBoost):   {self._format_risk(future)}")
                if concordance is not None:
                    lines.append(f"Temporal Concordance:           {concordance:.1%}")
                else:
                    lines.append("Temporal Concordance:           N/A")

                # Add pattern interpretation
                pattern = self._interpret_pattern(current, future, concordance)
                lines.append(f"\nPattern: {pattern}")

                # Add clinical guidance
                guidance = self._get_clinical_guidance(current, future, pattern)
                lines.append(f"Clinical Action: {guidance}")

                break  # Show only most recent

        # Add overall temporal summary if available
        if 'avg_current_depression' in result.overall_summary:
            lines.append("\n" + "-" * 20)
            lines.append("Period Average:")
            avg_current = result.overall_summary.get('avg_current_depression', 0)
            avg_future = result.overall_summary.get('avg_depression_risk', 0)
            avg_concordance = result.overall_summary.get('avg_temporal_concordance', 0)

            lines.append(f"  Average Current State: {self._format_risk(avg_current)}")
            lines.append(f"  Average Future Risk:   {self._format_risk(avg_future)}")
            if avg_concordance:
                lines.append(f"  Average Concordance:   {avg_concordance:.1%}")

        return "\n".join(lines)

    def _format_risk(self, risk: float | None) -> str:
        """Format risk value with label."""
        if risk is None:
            return "N/A"
        percentage = f"{risk:.1%}"
        if risk < 0.3:
            return f"{percentage} [LOW]"
        elif risk < 0.6:
            return f"{percentage} [MODERATE]"
        elif risk < 0.8:
            return f"{percentage} [HIGH]"
        else:
            return f"{percentage} [CRITICAL]"

    def _interpret_pattern(self, current: float | None, future: float | None, concordance: float | None) -> str:
        """Interpret temporal pattern."""
        # Handle None values
        if current is None or future is None:
            return "Insufficient data for pattern analysis"

        # High current, lower future = improving (65% -> 42% is improving)
        if current > 0.5 and future < current - 0.1:
            return "Improving - Crisis resolving"
        # Low current, high future = deteriorating
        elif current < 0.3 and future > 0.5:
            return "Deteriorating - Early warning signs"
        # Both high = persistent elevation
        elif current > 0.5 and future > 0.5:
            return "Persistent elevation - Ongoing episode"
        # Both low with high concordance = stable
        elif concordance is not None and concordance > 0.8:
            return "Stable trajectory"
        # Low concordance = transitioning
        else:
            return "Transitioning state - Monitor closely"

    def _get_clinical_guidance(self, current: float | None, future: float | None, pattern: str) -> str:
        """Generate clinical guidance based on temporal pattern."""
        if "Improving" in pattern:
            return "Continue current interventions, monitor for sustained improvement"
        elif "Deteriorating" in pattern:
            return "Implement preventive strategies immediately"
        elif "Persistent elevation" in pattern:
            return "Consider immediate clinical assessment"
        elif "Stable" in pattern:
            return "Maintain current management plan"
        else:
            return "Increase monitoring frequency"


class DailyPredictionsSection(ReportSection):
    """Enhanced daily predictions section with temporal data."""

    def should_include(self, result: PipelineResult) -> bool:
        """Always include daily predictions."""
        return bool(result.daily_predictions)

    def format(self, result: PipelineResult) -> str:
        """Format daily predictions with temporal data if available."""
        lines = []
        lines.append("\nDETAILED DAILY ANALYSIS")
        lines.append("-" * 30)

        # Show first week of daily predictions
        for date_key, pred in list(result.daily_predictions.items())[:7]:
            lines.append(f"\n{date_key}:")

            # If we have temporal data, show it differently
            if 'current_depression' in pred:
                lines.append(f"  NOW:      {self._format_risk(pred.get('current_depression', 0))}")
                lines.append(f"  TOMORROW: {self._format_risk(pred.get('depression_risk', 0))}")

                # Show other risks for tomorrow
                if pred.get('hypomanic_risk', 0) > 0.3 or pred.get('manic_risk', 0) > 0.3:
                    lines.append(f"  Hypomania Risk: {self._format_risk(pred.get('hypomanic_risk', 0))}")
                    lines.append(f"  Mania Risk:     {self._format_risk(pred.get('manic_risk', 0))}")
            else:
                # Traditional format
                lines.append(f"  Depression: {self._format_risk(pred.get('depression_risk', 0))}")
                lines.append(f"  Hypomania: {self._format_risk(pred.get('hypomanic_risk', 0))}")
                lines.append(f"  Mania: {self._format_risk(pred.get('manic_risk', 0))}")

            lines.append(f"  Confidence: {pred.get('confidence', 0):.1%}")

            # Show models used
            if "models_used" in pred:
                lines.append(f"  Models: {', '.join(pred['models_used'])}")

        return "\n".join(lines)

    def _format_risk(self, risk: float | None) -> str:
        """Format risk value with label."""
        if risk is None:
            return "N/A"
        percentage = f"{risk:.1%}"
        if risk < 0.3:
            return f"{percentage} [LOW]"
        elif risk < 0.6:
            return f"{percentage} [MODERATE]"
        elif risk < 0.8:
            return f"{percentage} [HIGH]"
        else:
            return f"{percentage} [CRITICAL]"
