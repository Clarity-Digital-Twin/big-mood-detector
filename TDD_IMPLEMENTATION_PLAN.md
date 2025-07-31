# Test-Driven Development Implementation Plan
_For Production Issues Fix - v0.5.7_

## Overview

This document outlines the TDD approach for fixing the production issues identified in `PRODUCTION_ISSUES_INVESTIGATION.md`. Each fix will follow the red-green-refactor cycle.

## Issue #1: Timezone Type Mismatch

### Step 1: Write Failing Tests

```python
# tests/unit/infrastructure/parsers/test_timezone_contract.py
import pytest
from datetime import datetime, timezone
from big_mood_detector.infrastructure.parsers.xml.streaming_adapter import StreamingXMLParser
from big_mood_detector.domain.contracts.timezone_contract import TimezoneContract

class TestTimezoneContract:
    def test_parser_always_outputs_naive_datetimes(self):
        """XML parser must convert all datetimes to naive (UTC)."""
        xml_content = """
        <HealthData>
            <Record type="HKCategoryTypeIdentifierSleepAnalysis" 
                    startDate="2025-01-27 22:30:00 +0000"
                    endDate="2025-01-28 06:30:00 +0000"/>
        </HealthData>
        """
        parser = StreamingXMLParser()
        result = parser.parse_from_string(xml_content)
        
        sleep_record = result.sleep_records[0]
        assert sleep_record.start_date.tzinfo is None
        assert sleep_record.end_date.tzinfo is None
    
    def test_contract_converts_aware_to_naive(self):
        """Contract should convert aware datetimes to naive."""
        aware_dt = datetime(2025, 1, 27, 22, 30, tzinfo=timezone.utc)
        naive_dt = TimezoneContract.ensure_naive(aware_dt)
        
        assert naive_dt.tzinfo is None
        assert naive_dt == datetime(2025, 1, 27, 22, 30)
    
    def test_contract_preserves_naive(self):
        """Contract should leave naive datetimes unchanged."""
        naive_dt = datetime(2025, 1, 27, 22, 30)
        result = TimezoneContract.ensure_naive(naive_dt)
        
        assert result == naive_dt
        assert result.tzinfo is None
```

```python
# tests/integration/test_timezone_robustness.py
class TestTimezoneRobustness:
    def test_pipeline_handles_mixed_timezone_data(self):
        """Pipeline should handle both aware and naive inputs gracefully."""
        # Create records with mixed timezones
        records = [
            SleepRecord(
                start_date=datetime(2025, 1, 27, 22, 0, tzinfo=timezone.utc),
                end_date=datetime(2025, 1, 28, 6, 0, tzinfo=timezone.utc),
                state=SleepState.ASLEEP
            ),
            SleepRecord(
                start_date=datetime(2025, 1, 28, 22, 0),  # Naive
                end_date=datetime(2025, 1, 29, 6, 0),      # Naive
                state=SleepState.ASLEEP
            )
        ]
        
        pipeline = MoodPredictionPipeline()
        # This should not raise TypeError
        result = pipeline.process_health_data(
            sleep_records=records,
            activity_records=[],
            heart_records=[],
            target_date=date(2025, 1, 29)
        )
        
        assert result.has_errors is False
```

### Step 2: Implement TimezoneContract

```python
# src/big_mood_detector/domain/contracts/timezone_contract.py
from datetime import datetime
from typing import TypeVar

T = TypeVar('T', bound=datetime)

class TimezoneContract:
    """
    Enforces timezone consistency throughout the domain layer.
    
    Contract: All datetime objects in the domain MUST be timezone-naive,
    representing UTC time implicitly.
    """
    
    @staticmethod
    def ensure_naive(dt: T) -> T:
        """
        Convert any datetime to naive (implicitly UTC).
        
        Args:
            dt: Datetime object (aware or naive)
            
        Returns:
            Naive datetime representing the same moment in UTC
        """
        if dt.tzinfo is not None:
            # Convert to UTC then make naive
            utc_dt = dt.astimezone(timezone.utc)
            return utc_dt.replace(tzinfo=None)
        return dt
    
    @staticmethod
    def validate_domain_datetime(dt: datetime) -> None:
        """
        Validate that a datetime meets domain requirements.
        
        Raises:
            ValueError: If datetime is timezone-aware
        """
        if dt.tzinfo is not None:
            raise ValueError(
                f"Domain layer requires timezone-naive datetimes. "
                f"Got aware datetime: {dt}"
            )
```

### Step 3: Fix Parser

```python
# src/big_mood_detector/infrastructure/parsers/xml/streaming_adapter.py
# In the parse method, after creating records:

from big_mood_detector.domain.contracts.timezone_contract import TimezoneContract

# ... existing code ...

# When creating SleepRecord
start_date = TimezoneContract.ensure_naive(parsed_start_date)
end_date = TimezoneContract.ensure_naive(parsed_end_date)

record = SleepRecord(
    source_name=source_name,
    start_date=start_date,  # Now guaranteed naive
    end_date=end_date,      # Now guaranteed naive
    state=state
)
```

## Issue #2: Window-Level Predictions

### Step 1: Write Failing Tests

```python
# tests/unit/application/use_cases/test_window_predictions.py
class TestWindowPredictions:
    def test_xgboost_generates_single_prediction_per_window(self):
        """XGBoost should produce ONE prediction per window, not per day."""
        # Setup
        window = DateWindow(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            days_count=31,
            data_quality=0.65
        )
        
        pipeline = MoodPredictionPipeline(
            config=PipelineConfig(use_seoul_features=True)
        )
        
        # Create 31 days of features
        features = [create_mock_daily_features(date(2025, 1, i)) 
                   for i in range(1, 32)]
        
        # Process window
        predictions = pipeline._generate_window_predictions(
            features, window, model_type="xgboost"
        )
        
        # Should have ONE prediction, not 31
        assert len(predictions) == 1
        assert predictions[0].window == window
        assert predictions[0].model_type == "xgboost"
```

```python
# tests/unit/interfaces/cli/test_window_report_format.py
class TestWindowReportFormat:
    def test_report_shows_window_prediction_not_daily(self):
        """Report should show window-level prediction correctly."""
        result = PipelineResult(
            window_predictions={
                (date(2025, 1, 1), date(2025, 1, 31)): {
                    "depression_risk": 0.036,
                    "hypomanic_risk": 0.003,
                    "manic_risk": 0.000,
                    "confidence": 0.5,
                    "model": "xgboost",
                    "window_coverage": 0.65
                }
            },
            daily_predictions={},  # Empty - no daily predictions!
            overall_summary={...},
            metadata={
                "window_analysis": WindowAnalysisResult(...)
            }
        )
        
        report = format_cds_report(result)
        
        # Should show window period, not individual days
        assert "Window Period: 2025-01-01 to 2025-01-31" in report
        assert "Depression Risk: 3.6%" in report
        assert "2025-01-27:" not in report  # No daily entries
```

### Step 2: Implement Window Predictions

```python
# src/big_mood_detector/application/use_cases/process_health_data_use_case.py

@dataclass
class PipelineResult:
    """Result of mood prediction pipeline processing."""
    
    daily_predictions: dict[date, dict[str, Any]]
    window_predictions: dict[tuple[date, date], dict[str, Any]]  # NEW!
    overall_summary: dict[str, Any]
    # ... rest of fields

def process_health_data(self, ...):
    # ... existing code ...
    
    window_predictions = {}
    
    if window_analysis and window_analysis.can_run_xgboost and not window_analysis.can_run_pat:
        # XGBoost-only mode: generate ONE prediction for the window
        
        # Aggregate features across the entire window
        window_features = self.aggregation_pipeline.aggregate_window_features(
            sleep_records=filtered_sleep,
            activity_records=filtered_activity,
            heart_records=filtered_heart,
            start_date=window_analysis.optimal_window.start_date,
            end_date=window_analysis.optimal_window.end_date
        )
        
        # Single prediction for the window
        prediction = self.mood_predictor.predict(window_features)
        
        window_key = (
            window_analysis.optimal_window.start_date,
            window_analysis.optimal_window.end_date
        )
        
        window_predictions[window_key] = {
            "depression_risk": prediction.depression_risk,
            "hypomanic_risk": prediction.hypomanic_risk,
            "manic_risk": prediction.manic_risk,
            "confidence": prediction.confidence,
            "model": "xgboost",
            "window_coverage": window_analysis.optimal_window.data_quality,
            "days_analyzed": window_analysis.optimal_window.days_count
        }
```

### Step 3: Update Report Formatter

```python
# src/big_mood_detector/interfaces/cli/commands.py

def write_report(result: PipelineResult, output_path: Path) -> None:
    """Write clinical decision support report."""
    
    with open(output_path, "w") as f:
        # ... header ...
        
        # Check if we have window predictions
        if result.window_predictions:
            f.write("\nWINDOW-LEVEL ANALYSIS\n")
            f.write("-" * 30 + "\n")
            
            for (start, end), pred in result.window_predictions.items():
                f.write(f"\nPeriod: {start} to {end}\n")
                f.write(f"  Model: {pred['model'].upper()}\n")
                f.write(f"  Coverage: {pred['window_coverage']:.0%}\n")
                f.write(f"  Days Analyzed: {pred['days_analyzed']}\n")
                f.write(f"\n  Depression Risk: {pred['depression_risk']:.1%} ")
                f.write(f"[{categorize_risk(pred['depression_risk'])}]\n")
                # ... other risks ...
        
        # Only show daily predictions if we have them
        if result.daily_predictions:
            f.write("\nDAILY ANALYSIS\n")
            f.write("-" * 30 + "\n")
            # ... existing daily code ...
```

## Issue #3: Window Metadata in Report

### Step 1: Write Failing Test

```python
# tests/integration/test_window_metadata_flow.py
class TestWindowMetadataFlow:
    def test_window_analysis_appears_in_final_report(self):
        """Window selection details must appear in CDS report."""
        # Create sparse data scenario
        records = create_sparse_sleep_records(days=35, coverage=0.6)
        
        # Run full pipeline
        result = run_cli_command([
            "predict", "test_data.xml", "--report", "--auto-window"
        ])
        
        report_content = read_file("data/output/clinical_report.txt")
        
        # Must contain window selection info
        assert "DATA WINDOW SELECTION" in report_content
        assert "Auto-selected sparse window" in report_content
        assert "Models Available:" in report_content
        assert "30+ days" in report_content
```

### Step 2: Ensure Metadata Propagation

```python
# src/big_mood_detector/application/use_cases/process_health_data_use_case.py

# In process_health_data method:
metadata["window_analysis"] = window_analysis  # Already exists

# Ensure it's passed through to result:
return PipelineResult(
    daily_predictions=daily_predictions,
    window_predictions=window_predictions,
    overall_summary=overall_summary,
    metadata=metadata,  # This MUST include window_analysis
    # ...
)
```

## Issue #4: Dynamic Timeout

### Step 1: Write Failing Test

```python
# tests/unit/interfaces/cli/test_timeout_calculation.py
class TestTimeoutCalculation:
    def test_small_files_get_standard_timeout(self):
        """Files under 50MB should have 2 minute timeout."""
        assert calculate_timeout(10) == 120
        assert calculate_timeout(49) == 120
    
    def test_medium_files_get_extended_timeout(self):
        """Files 50-200MB should have 5 minute timeout."""
        assert calculate_timeout(50) == 300
        assert calculate_timeout(199) == 300
    
    def test_large_files_get_no_timeout(self):
        """Files over 200MB should have no timeout."""
        assert calculate_timeout(200) == 0
        assert calculate_timeout(500) == 0
```

### Step 2: Implement Dynamic Timeout

```python
# src/big_mood_detector/interfaces/cli/commands.py

def calculate_timeout(file_size_mb: float) -> int:
    """Calculate appropriate timeout based on file size."""
    if file_size_mb < 50:
        return 120  # 2 minutes
    elif file_size_mb < 200:
        return 300  # 5 minutes
    else:
        return 0    # No timeout for large files

@click.command(name="predict")
def predict_command(...):
    # Get file size
    file_size_mb = input_path_obj.stat().st_size / (1024 * 1024)
    timeout = calculate_timeout(file_size_mb)
    
    if timeout == 0:
        click.echo(f"Large file detected ({file_size_mb:.0f}MB). "
                  f"Processing may take 10-15 minutes...")
```

## Testing Strategy

### 1. Unit Test Suite
- Each issue gets its own test module
- Tests are written BEFORE implementation
- Tests document expected behavior

### 2. Integration Test Suite
```python
# tests/integration/test_production_scenarios.py
class TestProductionScenarios:
    def test_sparse_window_xgboost_only(self):
        """Most common scenario: sparse data, only XGBoost can run."""
        
    def test_consecutive_window_both_models(self):
        """Ideal scenario: 7+ consecutive days, both models run."""
        
    def test_insufficient_data_graceful_failure(self):
        """Edge case: not enough data for either model."""
```

### 3. End-to-End Test
```python
# tests/e2e/test_real_export_processing.py
@pytest.mark.slow
class TestRealExportProcessing:
    def test_50mb_export_completes_successfully(self):
        """Medium-sized export should process without errors."""
        # Use synthetic but realistic 50MB export
        # Verify:
        # - No timezone errors
        # - Correct window-level predictions
        # - Proper report format
        # - Reasonable processing time
```

## Implementation Order

1. **Day 1**: Timezone fixes (Critical blocker)
   - Write tests
   - Implement TimezoneContract
   - Fix parser and feature extraction
   
2. **Day 2**: Window predictions (Core logic)
   - Write tests
   - Refactor prediction generation
   - Update report format
   
3. **Day 3**: Metadata and UX
   - Window info in reports
   - Dynamic timeout
   - Progress indication

## Definition of Done

- [ ] All tests pass
- [ ] No mypy errors
- [ ] No ruff warnings
- [ ] 520MB export processes successfully
- [ ] CDS report is clear and accurate
- [ ] Documentation updated
- [ ] CHANGELOG.md updated