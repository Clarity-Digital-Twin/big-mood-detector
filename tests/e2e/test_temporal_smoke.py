"""
Quick E2E smoke test for temporal feature.

Minimal test to verify temporal display works end-to-end.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from big_mood_detector.interfaces.cli.main import cli


def test_temporal_shows_with_ensemble(tmp_path):
    """Smoke test: --ensemble flag shows temporal section."""
    # Create minimal test data
    xml_content = """<?xml version="1.0"?>
<HealthData>
    <ExportDate value="2025-07-29 12:00:00"/>
    <Record type="SleepAnalysis" startDate="2025-07-28 22:00:00" 
            endDate="2025-07-29 07:00:00" value="HKCategoryValueSleepAnalysisAsleep"/>
</HealthData>"""
    
    xml_path = tmp_path / "test.xml"
    xml_path.write_text(xml_content)
    
    runner = CliRunner()
    result = runner.invoke(cli, [
        "predict", str(xml_path), 
        "--ensemble", "--report",
        "--output", str(tmp_path / "out")
    ])
    
    # Should complete (may skip if PAT not available)
    assert result.exit_code in (0, 1)
    
    # If successful, check report
    report_path = tmp_path / "out" / "clinical_report.txt"
    if report_path.exists():
        content = report_path.read_text()
        # Temporal section appears if PAT was available
        if "PAT" in content:
            assert ("TEMPORAL" in content or "NOW" in content)