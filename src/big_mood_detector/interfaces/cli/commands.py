"""
Unified CLI Commands

All CLI commands consolidated into the interfaces layer following Clean Architecture.
This module contains all command implementations for the Big Mood Detector.
"""

import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict

import click

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    MoodPredictionPipeline,
    PipelineConfig,
    PipelineResult,
)
from big_mood_detector.domain.value_objects.feature_requirements import FEATURE_REQUIREMENTS


class ProcessingMetadata(TypedDict, total=False):
    """Metadata structure for processing results."""

    records_processed: int
    processing_time: float
    warnings: list[str]
    errors: list[str]
    features_extracted: int
    has_warnings: bool
    has_errors: bool


def calculate_timeout(file_size_mb: float) -> int:
    """
    Calculate appropriate timeout based on file size.
    
    Args:
        file_size_mb: File size in megabytes
        
    Returns:
        Timeout in seconds (0 = no timeout)
    """
    from big_mood_detector.core.constants import (
        LARGE_FILE_THRESHOLD_MB,
        MEDIUM_FILE_TIMEOUT_SECONDS,
        NO_TIMEOUT,
        SMALL_FILE_THRESHOLD_MB,
        SMALL_FILE_TIMEOUT_SECONDS,
    )
    
    if file_size_mb < SMALL_FILE_THRESHOLD_MB:
        return SMALL_FILE_TIMEOUT_SECONDS
    elif file_size_mb < LARGE_FILE_THRESHOLD_MB:
        return MEDIUM_FILE_TIMEOUT_SECONDS
    else:
        return NO_TIMEOUT


def validate_input_path(input_path: Path) -> None:
    """Validate input path and provide helpful error messages."""
    if not input_path.exists():
        raise click.BadParameter(f"Path does not exist: {input_path}")

    # Check if it's a directory with health data files
    if input_path.is_dir():
        json_files = list(input_path.glob("*.json"))
        xml_files = list(input_path.glob("*.xml"))

        if not json_files and not xml_files:
            raise click.BadParameter(
                f"No JSON or XML health data files found in directory: {input_path}\n"
                "Expected files like 'Sleep Analysis.json', 'Heart Rate.json', or 'export.xml'"
            )

        click.echo(f"📁 Found {len(json_files)} JSON and {len(xml_files)} XML files")

        # Warn about large XML files
        for xml_file in xml_files:
            size_mb = xml_file.stat().st_size / (1024 * 1024)
            if size_mb > 100:
                click.echo(
                    f"⚠️  Large file detected: {xml_file.name} ({size_mb:.1f} MB)"
                )
                click.echo("   Processing may take several minutes...")

    # Check if it's a single file
    elif input_path.is_file():
        if input_path.suffix.lower() not in [".xml", ".json"]:
            raise click.BadParameter(
                f"Unsupported file type: {input_path.suffix}\n"
                "Supported formats: .xml (Apple Health export), .json (Health Auto Export)"
            )

        size_mb = input_path.stat().st_size / (1024 * 1024)
        if size_mb > 500:
            click.echo(f"⚠️  Very large file: {size_mb:.1f} MB")
            click.echo(
                "   Processing may take 10+ minutes. Consider using smaller date ranges."
            )
            click.echo(
                "   Consider using --days-back or --date-range to reduce processing time:"
            )
            click.echo(
                "   Example: --days-back 90  or  --date-range 2024-01-01:2024-03-31"
            )
            click.echo(
                "   Note: The app uses memory-efficient streaming for XML files."
            )
            click.echo(
                "   If CLI times out, try running directly: python3 src/big_mood_detector/main.py process <file>"
            )


def validate_date_range(start_date: datetime | None, end_date: datetime | None) -> None:
    """Validate that date range makes sense."""
    if start_date and end_date:
        if start_date.date() >= end_date.date():
            raise click.BadParameter(
                f"Start date ({start_date.date()}) must be before end date ({end_date.date()})"
            )

        # Warn about very long date ranges
        days_diff = (end_date.date() - start_date.date()).days
        if days_diff > 365:
            click.echo(f"⚠️  Long date range: {days_diff} days")
            click.echo("   Consider smaller ranges for faster processing")


def validate_ensemble_requirements(ensemble: bool, model_dir: Path | None) -> None:
    """Validate ensemble model requirements."""
    if ensemble:
        if model_dir:
            pat_weights = model_dir / "pat"
            if not pat_weights.exists():
                click.echo(
                    "⚠️  PAT model directory not found, falling back to XGBoost only"
                )
        else:
            click.echo("⚠️  Ensemble requested but no model directory specified")
            click.echo("   Using default model weights (may not include PAT)")


def validate_user_id(user_id: str | None) -> None:
    """Validate user ID format and provide warnings."""
    if user_id:
        # Check for common formatting issues
        if " " in user_id:
            raise click.BadParameter(
                f"User ID cannot contain spaces: '{user_id}'\n"
                "Use underscores or hyphens instead (e.g., 'john_doe' or 'user-123')"
            )

        if len(user_id) < 3:
            raise click.BadParameter(
                f"User ID too short: '{user_id}'\n"
                "Please use at least 3 characters for user identification"
            )

        if len(user_id) > 64:
            raise click.BadParameter(
                f"User ID too long: '{user_id}'\n"
                "Please use 64 characters or less"
            )

        # Validate characters (alphanumeric, dash, underscore, @)
        import re
        if not re.match(r'^[a-zA-Z0-9_\-@]+$', user_id):
            raise click.BadParameter(
                f"Invalid user ID format: '{user_id}'\n"
                "Use only letters, numbers, underscores, hyphens, and @"
            )

        # Warn about potential PII
        if "@" in user_id:
            click.echo("⚠️  User ID contains '@' - avoid using email addresses")
            click.echo("   User IDs will be hashed for privacy protection")


def format_risk_level(risk_score: float | None) -> str:
    """Format risk score with clinical level."""
    if risk_score is None:
        return "N/A"
    if risk_score >= 0.7:
        return f"{risk_score:.1%} [HIGH]"
    elif risk_score >= 0.4:
        return f"{risk_score:.1%} [MODERATE]"
    else:
        return f"{risk_score:.1%} [LOW]"


def print_summary(result: PipelineResult, verbose: bool = False) -> None:
    """Print analysis summary to console."""
    # Check if using default models (no PAT ensemble)
    using_default_models = False
    partial_pat_coverage = False
    if result.daily_predictions:
        # Count predictions with PAT
        total_predictions = len(result.daily_predictions)
        pat_predictions = sum(
            1 for pred in result.daily_predictions.values()
            if pred.get("models_used", []) == ["xgboost", "pat"]
        )
        
        if pat_predictions == 0:
            using_default_models = True
        elif pat_predictions < total_predictions:
            partial_pat_coverage = True
    
    # Display warning banner if using default models
    if using_default_models:
        click.echo("\n" + "="*60)
        click.echo("⚠️  WARNING: Using default models (XGBoost only)")
        click.echo("PAT ensemble models not available or not loaded")
        click.echo("Results may have reduced accuracy")
        click.echo("="*60)
    elif partial_pat_coverage and verbose:
        # Only show partial coverage warning in verbose mode
        click.echo("\n" + "="*60)
        click.echo("⚠️  NOTE: PAT ensemble partially available")
        click.echo(f"PAT used for {pat_predictions}/{total_predictions} predictions")
        click.echo("="*60)
    
    if result.overall_summary:
        click.echo("\n📊 Analysis Complete!")
        click.echo(
            f"Depression Risk: {format_risk_level(result.overall_summary.get('avg_depression_risk', 0))}"
        )
        click.echo(
            f"Hypomanic Risk: {format_risk_level(result.overall_summary.get('avg_hypomanic_risk', 0))}"
        )
        click.echo(
            f"Manic Risk: {format_risk_level(result.overall_summary.get('avg_manic_risk', 0))}"
        )

        # Display PAT depression score if available
        if 'avg_pat_depression_probability' in result.overall_summary:
            pat_score = result.overall_summary['avg_pat_depression_probability']
            click.echo(
                f"PAT Depression Risk: {format_risk_level(pat_score)}"
            )

        click.echo(f"\nDays analyzed: {result.overall_summary.get('days_analyzed', 0)}")
        click.echo(f"Confidence: {result.confidence_score:.1%}")

        # Display PAT confidence if available and verbose
        if verbose and 'avg_pat_confidence' in result.overall_summary:
            pat_confidence = result.overall_summary['avg_pat_confidence']
            click.echo(f"PAT Confidence: {pat_confidence:.1%}")

        if verbose and result.metadata:
            click.echo("\nMetadata:")
            for key, value in result.metadata.items():
                if key == "window_used":
                    # Format window information nicely
                    window = value
                    click.echo(f"  Window used: {window.start_date} to {window.end_date} ({window.days_count} days, quality: {window.data_quality:.2f})")
                else:
                    click.echo(f"  {key}: {value}")

    if result.warnings and verbose:
        click.echo("\n⚠️  Warnings:")
        for warning in result.warnings:
            click.echo(f"  • {warning}")


def save_json_output(result: PipelineResult, output_path: Path) -> None:
    """Save results in JSON format."""
    import json

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build metadata dict with proper typing
    metadata: dict[str, Any] = {
        "records_processed": result.records_processed,
        "processing_time": result.processing_time_seconds,
        "warnings": result.warnings,
        "errors": result.errors,
    }

    # Merge additional metadata if present
    if result.metadata:
        metadata.update(result.metadata)

    output_data = {
        "summary": result.overall_summary,
        "confidence": result.confidence_score,
        "daily_predictions": {
            str(date): pred for date, pred in result.daily_predictions.items()
        },
        "metadata": metadata,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2, default=str)


def save_csv_output(result: PipelineResult, output_path: Path) -> None:
    """Save results in CSV format."""
    import pandas as pd

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert predictions to DataFrame
    rows = []
    for pred_date, prediction in result.daily_predictions.items():
        row: dict[str, Any] = {"date": pred_date}
        row.update(prediction)
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("date")

    # Save to CSV
    df.to_csv(output_path, index=False)


def generate_clinical_report(result: PipelineResult, output_path: Path) -> None:
    """Generate a detailed clinical report."""
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Import temporal formatter
    from big_mood_detector.application.services.report_formatters import (
        TemporalAssessmentSection,
    )

    with open(output_path, "w") as f:
        f.write("CLINICAL DECISION SUPPORT (CDS) REPORT\n")
        f.write("=" * 50 + "\n\n")

        f.write("PATIENT DATA SUMMARY\n")
        # Handle both daily and window predictions
        if result.daily_predictions:
            f.write(f"Analysis Period: {len(result.daily_predictions)} days\n")
        elif result.metadata and "data_start_date" in result.metadata:
            start = result.metadata["data_start_date"]
            end = result.metadata["data_end_date"]
            f.write(f"Analysis Period: {start} to {end}\n")
        f.write(f"Total Records Processed: {result.records_processed}\n")
        f.write(f"Data Quality Score: {result.confidence_score:.1%}\n")

        # Add window analysis information if available
        if result.metadata and "window_analysis" in result.metadata:
            window_analysis = result.metadata["window_analysis"]
            f.write("\nDATA WINDOW SELECTION\n")
            f.write("-" * 30 + "\n")
            if window_analysis.optimal_window:
                opt = window_analysis.optimal_window
                f.write(f"Window Period: {opt.start_date} to {opt.end_date} ({opt.days_count} days)\n")
                f.write(f"Data Coverage: {opt.data_quality:.0%}\n")
            f.write(f"Strategy: {window_analysis.selection_reason}\n")
            if window_analysis.can_run_ensemble:
                f.write("Models Available: Ensemble (PAT + XGBoost)\n")
            elif window_analysis.can_run_pat:
                f.write("Models Available: PAT only\n")
            elif window_analysis.can_run_xgboost:
                f.write("Models Available: XGBoost only\n")

        if result.metadata.get("personal_calibration_used"):
            f.write(
                f"\nPersonalized Model: Active (User: {result.metadata.get('user_id')})\n"
            )

        # Check if we have window predictions
        if result.window_predictions:
            f.write("\nWINDOW-LEVEL ANALYSIS\n")
            f.write("-" * 30 + "\n")

            for (start, end), pred in result.window_predictions.items():
                f.write(f"\nPeriod: {start} to {end}\n")
                f.write(f"  Model: {pred.get('model', 'Unknown').upper()}\n")
                if 'window_coverage' in pred:
                    f.write(f"  Coverage: {pred['window_coverage']:.0%}\n")
                if 'days_analyzed' in pred:
                    f.write(f"  Days Analyzed: {pred['days_analyzed']}\n")
                f.write(f"\n  Depression Risk: {format_risk_level(pred['depression_risk'])}\n")
                f.write(f"  Hypomanic Risk: {format_risk_level(pred['hypomanic_risk'])}\n")
                f.write(f"  Manic Risk: {format_risk_level(pred['manic_risk'])}\n")
                f.write(f"  Confidence: {pred['confidence']:.0%}\n")

        f.write("\nCLINICAL RISK ASSESSMENT\n")
        f.write("-" * 30 + "\n")

        if result.overall_summary:
            dep_risk = result.overall_summary.get("avg_depression_risk", 0)
            hypo_risk = result.overall_summary.get("avg_hypomanic_risk", 0)
            manic_risk = result.overall_summary.get("avg_manic_risk", 0)

            f.write(f"Depression Risk: {format_risk_level(dep_risk)}\n")
            f.write(f"Hypomanic Risk: {format_risk_level(hypo_risk)}\n")
            f.write(f"Manic Risk: {format_risk_level(manic_risk)}\n")

            # Add PAT Depression Assessment if available
            if 'avg_pat_depression_probability' in result.overall_summary:
                pat_score = result.overall_summary['avg_pat_depression_probability']
                f.write(f"\nPAT Depression Assessment: {format_risk_level(pat_score)}\n")
                f.write("  (Based on PHQ-9 ≥ 10 threshold)\n")

            # Add temporal assessment section if available
            temporal_section = TemporalAssessmentSection()
            if temporal_section.should_include(result):
                f.write(temporal_section.format(result))
                f.write("\n")

            f.write("\nCLINICAL RECOMMENDATIONS\n")
            f.write("-" * 30 + "\n")

            # Clinical decision logic based on DSM-5 criteria
            if dep_risk > 0.7:
                f.write("⚠️  HIGH DEPRESSION RISK DETECTED\n")
                f.write("• Consider immediate clinical evaluation\n")
                f.write("• Review sleep patterns and activity levels\n")
                f.write("• Monitor for suicidal ideation\n")
                f.write("• Assess functional impairment\n")
            elif dep_risk > 0.4:
                f.write("⚠️  MODERATE DEPRESSION RISK\n")
                f.write("• Schedule follow-up within 2 weeks\n")
                f.write("• Assess sleep hygiene and daily routines\n")
                f.write("• Consider therapy referral\n")
                f.write("• Monitor symptom progression\n")
            else:
                f.write("✓ Low depression risk\n")
                f.write("• Continue regular monitoring\n")
                f.write("• Maintain healthy sleep schedule\n")

            if hypo_risk > 0.5 or manic_risk > 0.3:
                f.write("\n⚠️  ELEVATED MOOD EPISODE RISK\n")
                f.write("• Monitor for decreased sleep need\n")
                f.write("• Track activity levels and goal-directed behavior\n")
                f.write("• Review medication compliance\n")
                f.write("• Assess for impulsive behaviors\n")

        if result.warnings:
            f.write("\nDATA QUALITY WARNINGS\n")
            f.write("-" * 30 + "\n")
            for warning in result.warnings:
                f.write(f"• {warning}\n")

        # Only show daily analysis if we have daily predictions
        if result.daily_predictions:
            f.write("\nDETAILED DAILY ANALYSIS\n")
            f.write("-" * 30 + "\n")

        # Show first week of daily predictions
        for date, pred in list(result.daily_predictions.items())[:7]:
            f.write(f"\n{date}:\n")

            # Check if we have temporal data
            if 'current_depression' in pred:
                # Show temporal format
                f.write(f"  NOW:      {format_risk_level(pred.get('current_depression', 0))}\n")
                f.write(f"  TOMORROW: {format_risk_level(pred['depression_risk'])}\n")
                # Show other tomorrow risks if elevated
                if pred.get('hypomanic_risk', 0) > 0.3 or pred.get('manic_risk', 0) > 0.3:
                    f.write(f"  Hypomania Tomorrow: {format_risk_level(pred['hypomanic_risk'])}\n")
                    f.write(f"  Mania Tomorrow: {format_risk_level(pred['manic_risk'])}\n")
            else:
                # Traditional format
                f.write(f"  Depression: {format_risk_level(pred['depression_risk'])}\n")
                f.write(f"  Hypomania: {format_risk_level(pred['hypomanic_risk'])}\n")
                f.write(f"  Mania: {format_risk_level(pred['manic_risk'])}\n")

            f.write(f"  Confidence: {pred['confidence']:.1%}\n")

            # Add PAT scores if available (but not if already shown as NOW)
            if 'pat_depression_probability' in pred and 'current_depression' not in pred:
                f.write(f"  PAT Depression: {format_risk_level(pred['pat_depression_probability'])}\n")
                if 'pat_confidence' in pred:
                    f.write(f"  PAT Confidence: {pred['pat_confidence']:.1%}\n")

            # Add model info if ensemble was used
            if "models_used" in pred:
                f.write(f"  Models: {', '.join(pred['models_used'])}\n")

        f.write("\n" + "=" * 50 + "\n")
        f.write("Generated by Big Mood Detector\n")
        f.write("This report is for clinical decision support only.\n")
        f.write("Not a substitute for professional diagnosis.\n")


@click.command(name="process")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (format based on extension)",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for analysis (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date for analysis (YYYY-MM-DD)",
)
@click.option(
    "--days-back",
    type=int,
    help="Process only the last N days of data (reduces memory usage for large files)",
)
@click.option(
    "--date-range",
    type=str,
    help="Date range in format YYYY-MM-DD:YYYY-MM-DD (e.g., 2024-01-01:2024-03-31)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--progress", is_flag=True, help="Show progress bar for large files")
@click.option(
    "--max-records", type=int, help="Maximum records to process (for testing)"
)
@click.option(
    "--scan", is_flag=True, help="Quick scan to show available data without processing"
)
def process_command(
    input_path: str,
    output: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
    days_back: int | None,
    date_range: str | None,
    verbose: bool,
    progress: bool,
    max_records: int | None,
    scan: bool,
) -> None:
    """Process health data to extract features for mood prediction."""
    try:
        # Validate inputs
        input_path_obj = Path(input_path)
        validate_input_path(input_path_obj)

        # Handle date range parameters
        if days_back and date_range:
            raise click.BadParameter("Cannot use both --days-back and --date-range")

        # Parse date range if provided
        if date_range:
            try:
                date_parts = date_range.split(":")
                if len(date_parts) != 2:
                    raise ValueError()
                start_date = datetime.strptime(date_parts[0], "%Y-%m-%d")
                end_date = datetime.strptime(date_parts[1], "%Y-%m-%d")
            except (ValueError, IndexError):
                raise click.BadParameter(
                    "Invalid date range format. Use YYYY-MM-DD:YYYY-MM-DD"
                ) from None

        # Calculate dates from days_back if provided
        if days_back:
            if days_back <= 0:
                raise click.BadParameter("--days-back must be a positive number")
            end_date = datetime.now(tz=UTC)
            start_date = end_date - timedelta(days=days_back)

        validate_date_range(start_date, end_date)

        # Handle --scan flag for quick data availability check
        if scan:
            # Only scan XML files
            if input_path_obj.suffix.lower() != '.xml':
                click.echo("⚠️  Scan is only available for XML files")
                return
            
            file_size_mb = input_path_obj.stat().st_size / (1024 * 1024)
            click.echo(f"\n📊 Scanning {input_path_obj.name} ({file_size_mb:.1f} MB)...")
            
            # Create data parsing service
            from big_mood_detector.application.services.data_parsing_service import DataParsingService
            data_service = DataParsingService()
            
            start_time = time.time()
            availability = data_service.check_feature_availability(input_path_obj)
            
            click.echo(f"✅ Scan complete in {availability.scan_duration_seconds:.1f}s\n")
            
            # Display available data types
            click.echo("Available Data:")
            major_types = availability.get_major_types()
            if major_types:
                for type_name, count in major_types:
                    click.echo(f"✅ {type_name}: {count:,} records")
            else:
                click.echo("⚠️  No recognized data types found")
            
            # Display missing data
            missing_summary = availability.format_missing_data_summary()
            if missing_summary != "All data types available!":
                click.echo(f"\n⚠️  {missing_summary}")
            
            # Display available features
            click.echo("\nProcessable Features:")
            if availability.available_features:
                for feature_name, description in availability.available_features:
                    click.echo(f"✅ {description}")
            else:
                click.echo("⚠️  No features can be processed with available data")
            
            # Display unavailable features if any
            if availability.unavailable_features:
                click.echo("\nUnavailable Features:")
                for feature_name, reason in availability.unavailable_features:
                    req = FEATURE_REQUIREMENTS.get(feature_name)
                    desc = req.description if req else feature_name
                    click.echo(f"⚠️  {desc}: {reason}")
            
            click.echo(f"\nTotal records found: {availability.total_records:,}")
            
            # Exit after scan
            return

        click.echo(f"Processing health data from: {input_path}")

        # Create progress callback if requested
        progress_callback = None
        pbar = None
        if progress:
            try:
                from tqdm import tqdm

                pbar = tqdm(total=100, desc="Processing", unit="%")

                def progress_callback(message: str, progress: float) -> None:
                    pbar.set_description(message)
                    pbar.update(int(progress * 100) - pbar.n)

            except ImportError:
                # Fall back to simple text progress
                click.echo("Note: Install tqdm for progress bars (pip install tqdm)")

                def progress_callback(message: str, progress: float) -> None:
                    percent = int(progress * 100)
                    click.echo(f"\r{message}: {percent}%", nl=False)
                    if progress >= 1.0:
                        click.echo()  # New line at completion

        # Initialize pipeline
        pipeline = MoodPredictionPipeline()

        # Convert datetime to date at the edge for clean internal APIs
        start_date_param: date | None = start_date.date() if start_date else None
        end_date_param: date | None = end_date.date() if end_date else None

        # Process health export
        import os

        data_dir = os.environ.get(
            "BIGMOOD_DATA_DIR", os.environ.get("DATA_DIR", "data")
        )
        output_path = (
            Path(output) if output else Path(data_dir) / "output" / "features.csv"
        )

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df = pipeline.process_health_export(
            export_path=Path(input_path),
            output_path=output_path,
            start_date=start_date_param,
            end_date=end_date_param,
        )

        click.echo(f"\n✅ Features extracted: {len(df)} days")
        click.echo(f"Output saved to: {output_path}")

        if verbose and not df.empty:
            click.echo("\nFeature Summary:")
            click.echo(f"  Columns: {len(df.columns)}")
            click.echo(f"  Date range: {df.index.min()} to {df.index.max()}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@click.command(name="predict")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (.json, .csv, or .txt for report)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv", "summary"]),
    default="summary",
    help="Output format",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for analysis (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date for analysis (YYYY-MM-DD)",
)
@click.option(
    "--days-back",
    type=int,
    help="Process only the last N days of data (reduces memory usage for large files)",
)
@click.option(
    "--date-range",
    type=str,
    help="Date range in format YYYY-MM-DD:YYYY-MM-DD (e.g., 2024-01-01:2024-03-31)",
)
@click.option(
    "--ensemble/--no-ensemble",
    default=False,
    help="Use ensemble model (PAT + XGBoost)",
)
@click.option(
    "--user-id",
    help="User ID for personalized predictions",
)
@click.option(
    "--model-dir",
    type=click.Path(exists=True),
    help="Directory containing model weights",
)
@click.option(
    "--report/--no-report",
    default=False,
    help="Generate clinical report",
)
@click.option(
    "--window-strategy",
    type=click.Choice(["recent", "best", "all"], case_sensitive=False),
    default=None,
    help="Strategy for finding data windows: recent (most recent valid window), best (highest quality), all (show all valid windows)",
)
@click.option(
    "--auto-find-window",
    is_flag=True,
    default=False,
    help="Automatically find the most recent valid data window",
)
@click.option(
    "--auto-window/--no-auto-window",
    default=True,
    help="Automatically analyze and select optimal windows for both models (default: on)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--scan", is_flag=True, help="Quick scan to show available data without prediction"
)
def predict_command(
    input_path: str,
    output: str | None,
    format: str,
    start_date: datetime | None,
    end_date: datetime | None,
    days_back: int | None,
    date_range: str | None,
    ensemble: bool,
    user_id: str | None,
    model_dir: str | None,
    report: bool,
    window_strategy: str | None,
    auto_find_window: bool,
    auto_window: bool,
    verbose: bool,
    scan: bool,
) -> None:
    """Generate mood predictions from health data."""
    try:
        # Validate inputs
        input_path_obj = Path(input_path)
        validate_input_path(input_path_obj)

        # Handle date range parameters
        if days_back and date_range:
            raise click.BadParameter("Cannot use both --days-back and --date-range")

        # Parse date range if provided
        if date_range:
            try:
                date_parts = date_range.split(":")
                if len(date_parts) != 2:
                    raise ValueError()
                start_date = datetime.strptime(date_parts[0], "%Y-%m-%d")
                end_date = datetime.strptime(date_parts[1], "%Y-%m-%d")
            except (ValueError, IndexError):
                raise click.BadParameter(
                    "Invalid date range format. Use YYYY-MM-DD:YYYY-MM-DD"
                ) from None

        # Calculate dates from days_back if provided
        if days_back:
            if days_back <= 0:
                raise click.BadParameter("--days-back must be a positive number")
            end_date = datetime.now(tz=UTC)
            start_date = end_date - timedelta(days=days_back)

        validate_date_range(start_date, end_date)
        validate_user_id(user_id)

        # Handle --scan flag for quick data availability check
        if scan:
            # Only scan XML files
            if input_path_obj.suffix.lower() != '.xml':
                click.echo("⚠️  Scan is only available for XML files")
                return
            
            file_size_mb = input_path_obj.stat().st_size / (1024 * 1024)
            click.echo(f"\n📊 Scanning {input_path_obj.name} ({file_size_mb:.1f} MB)...")
            
            # Create data parsing service
            from big_mood_detector.application.services.data_parsing_service import DataParsingService
            data_service = DataParsingService()
            
            start_time = time.time()
            availability = data_service.check_feature_availability(input_path_obj)
            
            click.echo(f"✅ Scan complete in {availability.scan_duration_seconds:.1f}s\n")
            
            # Display available data types
            click.echo("Available Data:")
            major_types = availability.get_major_types()
            if major_types:
                for type_name, count in major_types:
                    click.echo(f"✅ {type_name}: {count:,} records")
            else:
                click.echo("⚠️  No recognized data types found")
            
            # Display missing data
            missing_summary = availability.format_missing_data_summary()
            if missing_summary != "All data types available!":
                click.echo(f"\n⚠️  {missing_summary}")
            
            # Display available features
            click.echo("\nPredictable Conditions:")
            if availability.available_features:
                for feature_name, description in availability.available_features:
                    click.echo(f"✅ {description}")
            else:
                click.echo("⚠️  No predictions can be made with available data")
            
            # Display unavailable features if any
            if availability.unavailable_features and verbose:
                click.echo("\nUnavailable Predictions:")
                for feature_name, reason in availability.unavailable_features:
                    req = FEATURE_REQUIREMENTS.get(feature_name)
                    desc = req.description if req else feature_name
                    click.echo(f"⚠️  {desc}: {reason}")
            
            click.echo(f"\nTotal records found: {availability.total_records:,}")
            
            # Show recommendation if data is insufficient
            if not availability.has_minimum_features():
                click.echo("\n💡 Recommendation: Ensure your Apple Health export includes:")
                click.echo("   - Sleep data (7+ days)")
                click.echo("   - Step count data (7+ days)")
                click.echo("   - Heart rate data (optional but improves accuracy)")
            
            # Exit after scan
            return

        model_dir_obj = Path(model_dir) if model_dir else None
        validate_ensemble_requirements(ensemble, model_dir_obj)

        # For large XML files, offer to scan first
        if input_path_obj.suffix.lower() == '.xml' and not scan:
            file_size_mb = input_path_obj.stat().st_size / (1024 * 1024)
            if file_size_mb > 100:  # Files larger than 100MB
                click.echo(f"\n⚠️  Large file detected: {file_size_mb:.1f} MB")
                click.echo("Processing may take several minutes...")
                
                if click.confirm("Would you like to scan the file first to see available data?"):
                    # Recursively call with --scan flag
                    ctx = click.get_current_context()
                    ctx.params['scan'] = True
                    return predict_command(**ctx.params)

        click.echo(f"Processing health data from: {input_path}")

        # Set up window selection strategy
        from typing import Any

        from big_mood_detector.domain.services.window_selection_strategy import (
            WindowSelectionStrategy,
        )
        strategy: WindowSelectionStrategy | Any = None

        # Use dual model analysis if auto_window is enabled (default)
        if auto_window and not (start_date or end_date or days_back or date_range):
            from big_mood_detector.domain.services.dual_model_window_strategy import (
                DualModelWindowStrategy,
            )
            strategy = DualModelWindowStrategy()
            if verbose:
                click.echo("Using automatic dual-model window selection")
        elif auto_find_window or window_strategy:
            from big_mood_detector.domain.services.window_selection_strategy import (
                AllValidWindowsStrategy,
                BestQualityWindowStrategy,
                MostRecentValidWindowStrategy,
            )

            if window_strategy == "all":
                strategy = AllValidWindowsStrategy()
            elif window_strategy == "best":
                strategy = BestQualityWindowStrategy()
            else:  # "recent" or auto_find_window
                strategy = MostRecentValidWindowStrategy()

            if verbose:
                click.echo(f"Using window selection strategy: {strategy.__class__.__name__}")

        # Configure pipeline
        config = PipelineConfig(
            include_pat_sequences=ensemble,
            model_dir=model_dir_obj,
            enable_personal_calibration=bool(user_id),
            user_id=user_id,
            window_selection_strategy=strategy,
        )

        # Get DI container if ensemble is enabled
        di_container = None
        if ensemble:
            try:
                from big_mood_detector.infrastructure.di import get_container
                di_container = get_container()
                if verbose:
                    click.echo("Using DI container for PAT integration")
            except Exception as e:
                if verbose:
                    click.echo(f"Warning: Could not initialize DI container: {e}")

        # Initialize pipeline
        pipeline = MoodPredictionPipeline(config=config, di_container=di_container)

        # Calculate timeout based on file size
        file_size_mb = input_path_obj.stat().st_size / (1024 * 1024)
        timeout = calculate_timeout(file_size_mb)

        if timeout == 0:
            click.echo(f"📁 Large file detected ({file_size_mb:.0f}MB). Processing may take 10-15 minutes...")
        elif file_size_mb > 50:
            click.echo(f"📁 Processing {file_size_mb:.0f}MB file (timeout: {timeout//60} minutes)...")

        # Convert datetime to date at the edge for clean internal APIs
        start_date_param: date | None = start_date.date() if start_date else None
        end_date_param: date | None = end_date.date() if end_date else None

        # Process data with dynamic timeout
        import platform
        import signal
        from collections.abc import Iterator
        from contextlib import contextmanager

        @contextmanager
        def timeout_handler(seconds: int) -> Iterator[None]:
            """Cross-platform timeout handler."""
            if seconds > 0 and platform.system() != "Windows":
                # Unix-based systems: use signal-based timeout
                def timeout_error(signum: int, frame: Any) -> None:
                    raise TimeoutError(f"Processing timed out after {seconds} seconds")

                signal.signal(signal.SIGALRM, timeout_error)
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    signal.alarm(0)
            else:
                # Windows or no timeout: just proceed
                if seconds > 0 and platform.system() == "Windows":
                    click.echo("⚠️  Note: Timeout protection not available on Windows")
                yield

        try:
            with timeout_handler(timeout):
                result = pipeline.process_apple_health_file(
                    file_path=Path(input_path),
                    start_date=start_date_param,
                    end_date=end_date_param,
                )
        except TimeoutError as e:
            click.echo(f"❌ {str(e)}", err=True)
            click.echo("💡 Tip: Try processing a smaller date range or use --start-date and --end-date", err=True)
            sys.exit(1)

        # Display window analysis if dual model strategy was used
        if auto_window and result.metadata and "window_analysis" in result.metadata:
            window_analysis = result.metadata["window_analysis"]
            click.echo("\n📊 Data Window Analysis:")
            click.echo("=" * 50)

            # PAT windows
            if window_analysis.pat_windows:
                click.echo(f"\n✅ PAT Model: {len(window_analysis.pat_windows)} valid window(s)")
                for i, window in enumerate(window_analysis.pat_windows[:3], 1):
                    click.echo(
                        f"   {i}. {window.start_date} to {window.end_date} "
                        f"({window.days_count} days, quality: {window.data_quality:.2f})"
                    )
                if len(window_analysis.pat_windows) > 3:
                    click.echo(f"   ... and {len(window_analysis.pat_windows) - 3} more")
            else:
                click.echo("\n❌ PAT Model: No valid windows (requires 7 consecutive days)")

            # XGBoost windows
            if window_analysis.xgboost_windows:
                click.echo(f"\n✅ XGBoost Model: {len(window_analysis.xgboost_windows)} valid window(s)")
                for i, window in enumerate(window_analysis.xgboost_windows[:3], 1):
                    click.echo(
                        f"   {i}. {window.start_date} to {window.end_date} "
                        f"({window.total_days} days, {window.days_with_data} days with data, "
                        f"coverage: {window.coverage_ratio:.1%})"
                    )
                if len(window_analysis.xgboost_windows) > 3:
                    click.echo(f"   ... and {len(window_analysis.xgboost_windows) - 3} more")
            else:
                click.echo("\n❌ XGBoost Model: No valid windows (requires 30+ days with ≥50% coverage)")

            # Selected window
            click.echo(f"\n🎯 Selected Strategy: {window_analysis.selection_reason}")
            if window_analysis.optimal_window:
                opt = window_analysis.optimal_window
                click.echo(
                    f"   Using: {opt.start_date} to {opt.end_date} "
                    f"({opt.days_count} days)"
                )

            # Model availability
            click.echo("\n📈 Model Availability:")
            if window_analysis.can_run_ensemble:
                click.echo("   ✅ Ensemble (PAT + XGBoost) available")
            else:
                if window_analysis.can_run_pat:
                    click.echo("   ✅ PAT model available")
                else:
                    click.echo("   ❌ PAT model unavailable")
                if window_analysis.can_run_xgboost:
                    click.echo("   ✅ XGBoost model available")
                else:
                    click.echo("   ❌ XGBoost model unavailable")

            click.echo("=" * 50 + "\n")

        # Special handling for "all" strategy - show all windows found
        if window_strategy == "all" and strategy is not None and strategy.__class__.__name__ == "AllValidWindowsStrategy":
            # Parse the file to get sleep records
            from big_mood_detector.application.services.data_parsing_service import (
                DataParsingService,
            )
            parser = DataParsingService()
            parsed_data = parser.parse_health_data(
                Path(input_path),
                start_date=start_date_param,
                end_date=end_date_param,
            )
            sleep_records = parsed_data["sleep_records"]

            # Find all windows
            all_windows = strategy.find_windows(sleep_records)

            if all_windows:
                click.echo(f"\n📊 Found {len(all_windows)} valid prediction windows:")
                for i, window in enumerate(all_windows[:10], 1):  # Show max 10
                    click.echo(
                        f"  {i}. {window.start_date} to {window.end_date} "
                        f"({window.days_count} days, quality: {window.data_quality:.2f})"
                    )
                if len(all_windows) > 10:
                    click.echo(f"  ... and {len(all_windows) - 10} more windows")
                click.echo("\nUse --date-range to analyze a specific window.")
                return  # Exit early for "all" strategy

        # Handle output based on format
        if format == "summary":
            print_summary(result, verbose=verbose)
        elif output:
            output_path = Path(output)
            if format == "json" or output_path.suffix == ".json":
                save_json_output(result, output_path)
                click.echo(f"✅ JSON output saved to: {output_path}")
            elif format == "csv" or output_path.suffix == ".csv":
                save_csv_output(result, output_path)
                click.echo(f"✅ CSV output saved to: {output_path}")

        # Generate clinical report if requested
        if report:
            import os

            data_dir = os.environ.get(
                "BIGMOOD_DATA_DIR", os.environ.get("DATA_DIR", "data")
            )
            report_path = (
                Path(output).with_suffix(".txt")
                if output
                else Path(data_dir) / "output" / "clinical_report.txt"
            )
            generate_clinical_report(result, report_path)
            click.echo(f"✅ Clinical report saved to: {report_path}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
