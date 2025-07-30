"""
Quick performance sanity check for temporal predictions.
"""

import time
from pathlib import Path

from big_mood_detector.application.use_cases.process_health_data_use_case import (
    PipelineResult,
)
from big_mood_detector.interfaces.cli.commands import generate_clinical_report


def test_temporal_report_formatting_performance():
    """Verify temporal report formatting is fast."""
    # Create a mock pipeline result with temporal data
    result = PipelineResult(
        daily_predictions={
            "2025-07-29": {
                "depression_risk": 0.42,
                "hypomanic_risk": 0.1,
                "manic_risk": 0.05,
                "confidence": 0.89,
                "current_depression": 0.65,  # Temporal data
                "temporal_concordance": 0.75,
                "models_used": ["xgboost", "pat"],
            }
        },
        overall_summary={
            "avg_depression_risk": 0.42,
            "avg_hypomanic_risk": 0.1,
            "avg_manic_risk": 0.05,
            "days_analyzed": 30,
            "current_depression": 0.65,
            "temporal_concordance": 0.75,
        },
        confidence_score=0.89,
        processing_time_seconds=0.5,
        records_processed=1000,
    )

    # Time report generation (the new temporal feature)
    tmp_path = Path("/tmp/test_report.txt")

    start_time = time.perf_counter()
    generate_clinical_report(result, tmp_path)
    end_time = time.perf_counter()

    elapsed = end_time - start_time

    # Report formatting should be instant (< 0.1s)
    assert elapsed < 0.1, f"Report formatting took {elapsed:.3f}s, expected < 0.1s"

    # Verify temporal content was written
    content = tmp_path.read_text()
    assert "TEMPORAL MOOD ASSESSMENT" in content
    assert "NOW" in content
    assert "TOMORROW" in content

    print(f"\n✅ Report formatting performance: {elapsed*1000:.1f}ms")
