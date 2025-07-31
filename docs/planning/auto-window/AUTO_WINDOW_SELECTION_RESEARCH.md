# Auto Window Selection Research Report

## Executive Summary

The Big Mood Detector currently requires users to manually specify date ranges, but PAT and XGBoost models have different data window requirements:
- **PAT Model**: Requires exactly 7 consecutive days of minute-level activity data
- **XGBoost Model**: Requires 30-60 days of data (sparse is OK, not strictly consecutive)

This creates friction for new users who may not understand these requirements. An auto-window selection feature would automatically find eligible windows for both models.

## Current State Analysis

### 1. CLI Date Range Handling

The CLI currently accepts date ranges via multiple options:
- `--start-date` and `--end-date`: Explicit date range
- `--days-back`: Process last N days
- `--date-range`: Format YYYY-MM-DD:YYYY-MM-DD
- `--auto-find-window`: Recently added flag for automatic window selection

From `src/big_mood_detector/interfaces/cli/commands.py`:
```python
@click.option("--window-strategy", type=click.Choice(["recent", "best", "all"]), default=None)
@click.option("--auto-find-window", is_flag=True, default=False)
```

### 2. PAT Model Requirements

From `src/big_mood_detector/infrastructure/ml_models/pat_model.py` and `domain/services/pat_sequence_builder.py`:

- **Fixed window**: Exactly 10,080 minutes (7 days × 24 hours × 60 minutes)
- **Consecutive requirement**: Must have 7 consecutive days of data
- **Data format**: Minute-level activity values
- **Quality score**: Based on completeness (missing days reduce quality)
- **Normalization**: Z-score normalization applied to the sequence

Key constants:
```python
SEQUENCE_DAYS = 7
MINUTES_PER_DAY = 1440
TOTAL_MINUTES = 10080  # 7 × 1440
```

### 3. XGBoost Model Requirements

From `src/big_mood_detector/application/pipelines/xgboost_pipeline.py` and validation files:

- **Minimum window**: 30 days of data
- **Optimal window**: 30-60 days for circadian rhythm analysis
- **Sparsity tolerance**: Does NOT require consecutive days
- **Features**: 36 Seoul features including sleep timing, circadian phase, etc.
- **Purpose**: Predicts tomorrow's mood risk (24-hour lookahead)

From validation logic:
```python
# XGBoost requires 30-60 days of data for optimal circadian rhythm analysis
```

### 4. Window Selection Infrastructure

The system already has a `WindowSelectionStrategy` interface with three implementations:

1. **MostRecentValidWindowStrategy**: Finds the most recent valid consecutive window
2. **BestQualityWindowStrategy**: Finds the window with highest data quality/consistency
3. **AllValidWindowsStrategy**: Returns all valid windows in the dataset

These strategies are currently used but require minimum consecutive days, which works for PAT but not optimal for XGBoost's sparse data tolerance.

## Key Findings

### 1. Different Window Requirements Create Complexity

- PAT needs strict 7-day consecutive windows
- XGBoost can work with sparse 30+ day windows
- Current window selection strategies assume consecutive requirements

### 2. Window Selection Already Partially Implemented

The `--auto-find-window` flag exists but:
- Only works with consecutive window strategies
- Doesn't differentiate between PAT and XGBoost requirements
- Doesn't show both PAT-eligible and XGBoost-eligible windows

### 3. Ensemble Mode Complexity

When `--ensemble` is enabled, both models need valid windows:
- Need to find overlapping periods where both models can run
- PAT provides "current state" assessment
- XGBoost provides "tomorrow's risk" prediction

## Proposed Solution

### Phase 1: Enhanced Auto Window Detection

1. **Dual Window Analysis**
   - Scan data for PAT-eligible windows (7 consecutive days)
   - Scan data for XGBoost-eligible windows (30+ days, sparse OK)
   - Report both sets of windows to user

2. **Smart Default Selection**
   - If both models have valid windows, select the most recent overlapping period
   - If only one model has valid data, run that model and note the limitation
   - Show clear messaging about what's available

3. **Enhanced CLI Output**
   ```
   📊 Auto Window Analysis Complete:
   
   PAT Model (Current State):
   ✅ Found 3 eligible windows:
      1. 2024-12-15 to 2024-12-21 (7 days, quality: 1.00)
      2. 2024-11-01 to 2024-11-07 (7 days, quality: 0.95)
      3. 2024-10-20 to 2024-10-26 (7 days, quality: 1.00)
   
   XGBoost Model (Tomorrow's Risk):
   ✅ Found 2 eligible windows:
      1. 2024-10-01 to 2024-12-21 (82 days, 68% coverage)
      2. 2024-07-15 to 2024-09-10 (58 days, 71% coverage)
   
   🎯 Auto-selected: 2024-12-15 to 2024-12-21
      - PAT: ✅ Full 7-day window available
      - XGBoost: ✅ Using 82 days of historical data
   ```

## Next Steps

1. Run the application to trace CDS (Clinical Decision Support) flow
2. Identify exact code paths for window selection
3. Design implementation that minimizes changes to existing architecture
4. Test with various data scenarios

## CDS (Clinical Decision Support) Report Flow

### Report Generation Path

1. **Entry Point**: `interfaces/cli/commands.py`
   - Function: `generate_clinical_report(result: PipelineResult, output_path: Path)`
   - Called when `--report` flag is used
   - Generates the "CLINICAL DECISION SUPPORT (CDS) REPORT"

2. **Report Structure**:
   - Patient Data Summary (days analyzed, records processed, quality score)
   - Clinical Risk Assessment (Depression, Hypomanic, Manic risks)
   - Clinical Recommendations (based on risk levels)
   - Data Quality Warnings
   - Detailed Daily Analysis

3. **Current Behavior with Sample Data**:
   - The system processed 738,946 records but only found 1 day for analysis
   - Data quality was 35% due to sparse coverage (3/7 days)
   - Auto-find-window reported "No valid 7-day windows found"
   - System needs consecutive days for PAT, which the sparse data doesn't provide

## Implementation Architecture

### Proposed Changes

1. **Enhanced Window Selection Strategy**
   ```python
   class SparseWindowStrategy(WindowSelectionStrategy):
       """Finds windows for XGBoost that allow sparse data"""
       def find_windows(self, records, min_days=30, min_coverage=0.5):
           # Find periods with at least min_coverage of days having data
           # Don't require consecutive days
   ```

2. **Dual Pipeline Analysis**
   ```python
   class AutoWindowAnalyzer:
       def analyze(self, health_data):
           pat_windows = self.find_pat_windows()  # 7 consecutive days
           xgboost_windows = self.find_xgboost_windows()  # 30+ sparse days
           return WindowAnalysisResult(pat_windows, xgboost_windows)
   ```

3. **Enhanced CLI Output**
   - Modify `predict_command` to show both PAT and XGBoost eligible windows
   - Auto-select the best overlapping window when possible
   - Provide clear feedback when only one model can run

### Key Files to Modify

1. **`interfaces/cli/commands.py`**
   - Enhance `predict_command` to show dual analysis
   - Update report generation to indicate which models ran

2. **`domain/services/window_selection_strategy.py`**
   - Add `SparseWindowStrategy` for XGBoost
   - Add `DualModelWindowStrategy` for ensemble

3. **`application/use_cases/process_health_data_use_case.py`**
   - Add window analysis before processing
   - Coordinate between PAT and XGBoost requirements

4. **`application/services/report_formatters.py`**
   - Add window availability section to reports
   - Show which models contributed to predictions

### Implementation Phases

1. **Phase 1**: Add sparse window detection for XGBoost
2. **Phase 2**: Implement dual window analysis 
3. **Phase 3**: Auto-selection algorithm
4. **Phase 4**: Enhanced reporting with window info

The solution maintains backward compatibility while providing clear feedback about data requirements for new users.

## Summary and Recommendations

### Core Problem
The current system requires users to understand that:
- PAT needs exactly 7 consecutive days of minute-level activity data
- XGBoost needs 30-60 days of data (sparse is acceptable)
- Manual date range selection is error-prone for new users

### Proposed Solution
Implement an auto-window selection feature that:
1. **Automatically scans** the entire dataset for eligible windows
2. **Reports separately** on PAT-eligible and XGBoost-eligible windows
3. **Auto-selects** the best window when both models have valid data
4. **Provides clear feedback** about what's available and why

### Benefits
- **Reduced friction** for new users and contributors
- **Clear visibility** into data requirements
- **Automatic optimization** of window selection
- **Educational value** - users learn the requirements through usage

### Next Steps
1. Create GitHub issue for "Auto Window Selection Feature"
2. Implement Phase 1: Sparse window detection for XGBoost
3. Test with various real-world data scenarios
4. Iterate based on user feedback

This approach provides a foundation for future enhancements like:
- Processing multiple windows in one run
- Automatic batch processing of all eligible windows
- Smart window selection based on data quality metrics