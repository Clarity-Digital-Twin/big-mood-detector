# 🚀 Feature: Intelligent Auto-Window Selection for PAT and XGBoost Models

**Labels**: `enhancement`, `ux`, `good-first-issue`, `high-priority`

## Problem Statement

Currently, users must manually specify date ranges without understanding the different requirements:
- **PAT Model**: Requires exactly 7 consecutive days of minute-level activity data
- **XGBoost Model**: Requires 30-60 days of data (sparse coverage acceptable)

This creates significant friction for new users who often get poor results or errors on their first run.

### Current User Experience
```bash
$ python main.py predict export.xml
# Silently fails or uses inappropriate window
# User gets low confidence scores without understanding why
```

## Proposed Solution

Implement intelligent auto-window selection that automatically analyzes data and selects optimal prediction windows for each model.

### Desired User Experience

```bash
$ python main.py predict export.xml --auto

📊 Analyzing data availability...

PAT Model (Current State Assessment):
✅ Found 3 eligible windows (7 consecutive days each):
   • 2024-12-15 to 2024-12-21 (quality: 100%)
   • 2024-11-01 to 2024-11-07 (quality: 95%)
   • 2024-10-10 to 2024-10-16 (quality: 100%)

XGBoost Model (Tomorrow's Risk Prediction):
✅ Found 2 eligible windows (30+ days, ≥50% coverage):
   • 2024-09-01 to 2024-12-21 (112 days, 71% coverage)
   • 2024-05-15 to 2024-08-20 (98 days, 65% coverage)

🎯 Auto-selected optimal window: 2024-12-15 to 2024-12-21
   ├─ PAT: Using full 7-day consecutive window
   └─ XGBoost: Using 112 days of historical context

Generating predictions...
```

## Technical Requirements

### 1. New Window Selection Strategies

Create sparse data window strategy for XGBoost:
```python
class SparseWindowStrategy(WindowSelectionStrategy):
    """Finds windows with sparse data coverage (for XGBoost)."""
    
    def find_windows(self, records, min_days=30, min_coverage=0.5):
        # Find windows with at least 50% data coverage
        # Don't require consecutive days
```

### 2. Dual Model Coordination

```python
class DualModelWindowStrategy:
    """Coordinates window selection for both models."""
    
    def find_optimal_window(self, health_data) -> WindowSelectionResult:
        pat_windows = self.find_pat_windows()  # 7 consecutive
        xgboost_windows = self.find_xgboost_windows()  # 30+ sparse
        
        # Prefer overlapping windows when available
        # Fall back to model-specific windows if needed
        return self.select_best_overlap(pat_windows, xgboost_windows)
```

### 3. Enhanced CLI Interface

Add `--auto` flag (or make it default):
```bash
# Automatic window selection
$ python main.py predict export.xml --auto

# Manual override still available
$ python main.py predict export.xml --date-range 2024-01-01:2024-03-31
```

## Implementation Plan

### Phase 1: Domain Layer (Week 1)
- [ ] Create `SparseWindowStrategy` class
- [ ] Create `DualModelWindowStrategy` class
- [ ] Add comprehensive unit tests

### Phase 2: Application Layer (Week 2)
- [ ] Create `WindowAnalysisService`
- [ ] Integrate into `MoodPredictionPipeline`
- [ ] Add integration tests

### Phase 3: Interface Layer (Week 3)
- [ ] Add `--auto` flag to CLI
- [ ] Create `WindowAnalysisFormatter` for output
- [ ] Update help documentation

### Phase 4: Polish & Release (Week 4)
- [ ] Performance optimization for large files
- [ ] Beta testing with contributors
- [ ] Documentation updates

## Acceptance Criteria

- [ ] Auto-selection works with no user input required
- [ ] Clear feedback about what windows were found/selected
- [ ] Graceful handling when no valid windows exist
- [ ] Performance: Analysis completes in <5 seconds for typical export
- [ ] Backward compatibility: Manual date ranges still work
- [ ] 95% test coverage for new code
- [ ] Updated README with examples

## Testing Strategy

### Unit Tests
```python
def test_sparse_window_finds_non_consecutive_data():
    """XGBoost should work with gaps in data."""
    
def test_dual_strategy_prefers_overlapping_windows():
    """Should select windows where both models can run."""
    
def test_clear_feedback_when_no_windows_found():
    """Should explain why and what's needed."""
```

### Integration Tests
```python
def test_auto_window_end_to_end():
    """Complete flow from XML parsing to predictions."""
    
def test_performance_with_large_export():
    """Should complete in reasonable time."""
```

## Benefits

1. **Reduced Friction**: New users get results immediately
2. **Better Predictions**: Optimal windows automatically selected
3. **Educational**: Users learn requirements through clear feedback
4. **Future-Proof**: Foundation for batch processing multiple windows

## Related Issues

- Depends on completion of #79-#82 (critical bug fixes)
- Enhances #83 (temporal integration)
- Improves overall UX mentioned in multiple user reports

## Resources

- [Research Document](AUTO_WINDOW_SELECTION_RESEARCH.md)
- [Implementation Plan](AUTO_WINDOW_IMPLEMENTATION_PLAN.md)
- [PAT Paper](docs/literature/converted_markdown/pretrained-actigraphy-transformer/pretrained-actigraphy-transformer.md)
- [XGBoost Paper](docs/literature/converted_markdown/xgboost-mood/xgboost-mood.md)

---

**Note for Contributors**: This is an excellent issue for learning the codebase as it touches all architectural layers. The implementation plan provides clear guidance, and the research documents contain detailed analysis.
