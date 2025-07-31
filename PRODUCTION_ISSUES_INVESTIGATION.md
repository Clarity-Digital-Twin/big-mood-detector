# Production Issues Investigation Report
_Date: 2025-07-30_
_Version: 0.5.6 Post-Release Investigation_

## Executive Summary

After implementing the auto-window selection feature, we've discovered several critical production issues that prevent the application from being truly production-ready. This document thoroughly investigates each issue, provides root cause analysis, and outlines TDD-based solutions.

## Issue #1: Timezone Type Mismatch Errors

### Symptoms
```
TypeError: can't subtract offset-naive and offset-aware datetimes
```

### Root Cause Analysis
1. **Parser Output**: The XML parser (using Python's `datetime.fromisoformat()`) correctly parses Apple Health timestamps as timezone-aware (UTC):
   ```python
   # Example: "2025-01-27T22:30:00+00:00" → datetime with tzinfo=UTC
   ```

2. **Feature Extraction**: Some feature extraction code strips timezone info:
   ```python
   df['start_datetime'] = df['start_datetime'].dt.tz_localize(None)
   ```

3. **Mixed Operations**: When aggregation code tries to compute durations:
   ```python
   duration = end_datetime - start_datetime  # BOOM! One aware, one naive
   ```

### Investigation Method
```bash
# Find all timezone-related operations
grep -r "tz_localize\|tz_convert\|timezone" src/
```

### Impact
- Prevents processing of any real Apple Health data
- Shows window analysis successfully but crashes during feature extraction

## Issue #2: Duplicate Daily Predictions in CDS Report

### Symptoms
```
2025-01-27: Depression: 3.6% [LOW]
2025-01-28: Depression: 3.6% [LOW]  # Same values!
2025-01-29: Depression: 3.6% [LOW]  # Same values!
```

### Root Cause Analysis

1. **XGBoost Model Behavior**: 
   - XGBoost uses aggregated features over a 30-60 day window
   - It produces ONE prediction for the ENTIRE window
   - This is by design - it's predicting based on circadian patterns over the full period

2. **Report Generation Logic**:
   ```python
   # Current flawed logic in process_health_data_use_case.py
   for seoul_feature in seoul_features_list:
       feature_date = seoul_feature.date
       feature_vector = seoul_feature.to_model_dict()
       prediction = self.mood_predictor.predict(feature_vector)
       daily_predictions[feature_date] = { ... }  # WRONG! Same prediction repeated
   ```

3. **Conceptual Mismatch**:
   - We're treating XGBoost like it makes daily predictions
   - But it actually makes window-level predictions
   - The loop creates the illusion of daily variation when there is none

### Impact
- Misleading clinical report suggesting daily monitoring when it's actually static
- Confusion about what the model is actually predicting

## Issue #3: Missing Window Information in CDS Report

### Symptoms
- Report shows predictions but doesn't indicate:
  - Which window was analyzed
  - Why PAT wasn't run
  - What the data coverage was

### Root Cause Analysis
```python
# In commands.py write_report()
if result.metadata and "window_analysis" in result.metadata:
    # This code exists but the metadata isn't being passed through
```

The window analysis is generated but not properly propagated to the report writer.

## Issue #4: Performance/Timeout Issues

### Symptoms
- 520MB XML file processing times out
- No progress indication during long operations

### Root Cause Analysis
1. **Default Timeout**: Set to 2 minutes in CLI
2. **Actual Processing Time**: ~10-15 minutes for 520MB
3. **No Progress Feedback**: User has no idea if it's working or hung

## Issue #5: Incorrect Model Coordination

### Symptoms
- When only XGBoost can run, we still show "PAT: N/A" rows
- Ensemble mode expectations vs reality

### Root Cause Analysis
- The system was designed assuming both models would usually be available
- Sparse data reality means PAT rarely has 7 consecutive days
- UI/UX hasn't adapted to this reality

## Test-Driven Development Plan

### 1. Timezone Fix Tests

```python
# tests/unit/infrastructure/parsers/test_timezone_consistency.py
def test_parser_output_is_always_utc_aware():
    """Parser MUST output timezone-aware datetimes."""
    
def test_pipeline_handles_mixed_timezone_data():
    """Pipeline should handle both aware and naive inputs gracefully."""
    
def test_feature_extraction_preserves_timezone_consistency():
    """Feature extraction must not mix aware/naive operations."""
```

### 2. Window-Level Prediction Tests

```python
# tests/unit/application/use_cases/test_window_prediction_logic.py
def test_xgboost_generates_single_prediction_per_window():
    """XGBoost should produce ONE prediction per window, not per day."""
    
def test_report_shows_window_level_prediction_correctly():
    """Report should show date range for window predictions."""
```

### 3. Metadata Propagation Tests

```python
# tests/integration/test_window_metadata_flow.py
def test_window_analysis_appears_in_final_report():
    """Window selection details must appear in CDS report."""
```

### 4. Performance Tests

```python
# tests/integration/test_large_file_handling.py
@pytest.mark.slow
def test_500mb_file_completes_without_timeout():
    """Large files should process successfully with appropriate timeout."""
```

## Proposed Solutions

### Solution 1: Timezone Consistency Contract

```python
# domain/contracts/timezone_contract.py
class TimezoneContract:
    """
    All datetime objects in the domain layer MUST be timezone-naive.
    Conversion happens at infrastructure boundaries.
    """
    
    @staticmethod
    def ensure_naive(dt: datetime) -> datetime:
        """Convert any datetime to naive (implicitly UTC)."""
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
```

### Solution 2: Window-Level Predictions

```python
# application/use_cases/process_health_data_use_case.py
if window_analysis and window_analysis.can_run_xgboost:
    # Generate ONE prediction for the entire window
    window_features = self.aggregation_pipeline.aggregate_window_features(
        sleep_records, activity_records, heart_records,
        window_analysis.optimal_window.start_date,
        window_analysis.optimal_window.end_date
    )
    
    prediction = self.mood_predictor.predict(window_features)
    
    # Store as window-level prediction, not daily
    window_key = (window_analysis.optimal_window.start_date, 
                  window_analysis.optimal_window.end_date)
    window_predictions[window_key] = prediction
```

### Solution 3: Enhanced CDS Report Format

```
CLINICAL DECISION SUPPORT (CDS) REPORT
==================================================

PATIENT DATA SUMMARY
Analysis Period: 2025-01-27 to 2025-01-31 (5 days)
Total Records Processed: 161,663
Data Quality Score: 50.0%

DATA WINDOW SELECTION
------------------------------
Strategy: Auto-selected sparse window for XGBoost
Window: 2025-01-01 to 2025-01-31 (31 days, 65% coverage)
Models Available: XGBoost only (PAT requires 7 consecutive days)

CLINICAL RISK ASSESSMENT
------------------------------
Window Period: January 2025
  Depression Risk: 3.6% [LOW]
  Hypomanic Risk: 0.3% [LOW]
  Manic Risk: 0.0% [LOW]
  Confidence: 50.0%
  
Note: Risk assessment based on 30-day circadian pattern analysis
```

### Solution 4: Progressive Timeout Strategy

```python
# interfaces/cli/commands.py
def calculate_timeout(file_size_mb: float) -> int:
    """
    Dynamic timeout based on file size.
    ~2 min per 100MB + 60s buffer
    """
    if file_size_mb < 50:
        return 120  # 2 minutes for small files
    elif file_size_mb < 200:
        return 300  # 5 minutes for medium files
    else:
        return 0    # No timeout for large files
```

## Implementation Priority

1. **CRITICAL - Timezone Fix** (Blocks all real data processing)
2. **HIGH - Window Prediction Logic** (Core functionality incorrect)
3. **HIGH - Report Format** (User-facing clarity)
4. **MEDIUM - Timeout Handling** (UX improvement)
5. **MEDIUM - Progress Indication** (UX improvement)

## Regression Prevention

1. **Integration Test Suite**: Create `tests/e2e/test_real_apple_export.py` with small but real Apple Health exports
2. **Type Contracts**: Enforce timezone consistency at type level
3. **CI/CD Enhancement**: Add test stage with 50MB synthetic export

## Next Steps

1. Create feature branch: `feature/fix-production-issues`
2. Write failing tests for each issue (TDD)
3. Implement fixes one at a time
4. Ensure all tests pass
5. Manual test with 520MB export
6. Update documentation

## Conclusion

These issues represent a gap between our mental model (daily predictions, both models available) and reality (window predictions, sparse data). The fixes require both technical corrections and conceptual alignment in how we present results to users.