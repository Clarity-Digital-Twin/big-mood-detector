# Big Mood Detector - Definitive Refactoring Plan

**Date:** July 28, 2025  
**Purpose:** Remove confusion and technical debt while preserving working functionality

## Phase 1: Remove Broken/Unused Code (Week 1)

### 1.1 Delete BaselineRepository System
```bash
# Files to delete:
rm src/big_mood_detector/domain/repositories/baseline_repository_interface.py
rm src/big_mood_detector/infrastructure/repositories/file_baseline_repository.py
rm src/big_mood_detector/infrastructure/repositories/timescale_baseline_repository.py
rm -rf tests/unit/infrastructure/repositories/test_*baseline*.py
rm -rf tests/integration/storage/test_baseline*.py
```

### 1.2 Remove Deprecated Classes
```bash
# Delete deprecated feature extractors:
# - Remove SeoulXGBoostFeatures class (wrong features)
# - Remove references to "60-day requirements"
# - Remove unused calibration code
```

### 1.3 Clean Up Dead Code Paths
- Remove baseline_repository parameters from pipelines
- Remove --user-id flags that don't do anything
- Remove persist_baselines() calls

## Phase 2: Clarify Working Implementation (Week 1)

### 2.1 Document Rolling Window Approach
```python
# Add clear documentation to AggregationPipeline:
"""
Baseline Calculation:
- Uses rolling 30-60 day windows
- Calculates personal mean/std for each feature
- Z-scores computed as: (today - personal_mean) / personal_std
- No database required - calculated on demand
"""
```

### 2.2 Add Validation Tests
```python
def test_zscore_calculation():
    """Verify Z-scores use personal rolling statistics"""
    # Create 40 days of consistent data
    # Today's value = mean → Z-score should be ~0
    
def test_feature_vector_format():
    """Verify 36 features in correct order"""
    # Check against XGBoostModelLoader.FEATURE_NAMES
    
def test_no_baseline_persistence():
    """Verify we're NOT using BaselineRepository"""
    # Ensure pipeline works without any baseline DB
```

## Phase 3: Update Documentation (Week 2)

### 3.1 Update User Documentation
- Remove references to "baseline repository"
- Clarify 30-day requirement is for statistics, not training
- Explain rolling window approach
- Mark labeling as optional enhancement

### 3.2 Update Technical Documentation
- Document the actual XGBoost pipeline flow
- Remove architecture diagrams showing BaselineRepository
- Update API documentation

### 3.3 Fix Misleading Comments
```python
# Search and update all comments mentioning:
# - "60-day training requirement"
# - "baseline repository"
# - "personalized training"
```

## Phase 4: Enhance Core Pipeline (Week 2)

### 4.1 Add Pipeline Validation
```python
class XGBoostPipeline:
    def validate_baseline_window(self, data):
        """Ensure sufficient data for stable statistics"""
        if len(data) < 30:
            raise InsufficientDataError(
                f"Need 30+ days for baseline, got {len(data)}"
            )
```

### 4.2 Improve Error Messages
```python
# Instead of: "Failed to extract features"
# Use: "Insufficient data: XGBoost needs 30+ days to calculate personal baselines"
```

### 4.3 Add Baseline Quality Metrics
```python
@dataclass
class BaselineQuality:
    days_available: int
    coverage_percentage: float
    stability_score: float  # How consistent the data is
```

## Phase 5: Future Enhancements (Optional)

### 5.1 Keep Labeling for Fine-Tuning
- Labeling system works and is valuable
- Can be used for future personalization
- Keep as "optional enhancement"

### 5.2 Add Fine-Tuning Pipeline
```python
def fine_tune_with_labels(base_model, user_labels):
    """Warm-start XGBoost with user's labeled episodes"""
    # This is what the AI agent suggested
    # Completely separate from baseline calculation
```

## Testing Strategy

### Before Any Changes
1. Run full test suite, document failures
2. Create integration test with real data
3. Benchmark current predictions

### After Each Phase
1. Ensure predictions unchanged
2. Verify 36-feature vector identical
3. Check memory usage (should decrease)

### Final Validation
1. Process same test file before/after
2. Compare predictions - should be identical
3. Verify faster execution (less code)

## Success Criteria

### Technical
- [ ] All BaselineRepository code removed
- [ ] Tests pass without baseline persistence
- [ ] XGBoost predictions unchanged
- [ ] Documentation accurate

### User Experience
- [ ] Clear error messages
- [ ] No confusing "60-day" requirements
- [ ] Labeling clearly marked optional
- [ ] Faster processing (less overhead)

## Rollback Plan

All changes in separate PR with:
1. Tag current version before changes
2. Keep deleted files in archive branch
3. Document why code was removed

## Timeline

**Week 1**: Remove broken code, clarify implementation
**Week 2**: Update documentation, enhance pipeline
**Future**: Consider fine-tuning implementation

## Key Principle

**"Make the working path obvious, remove the broken paths entirely"**

The goal is to have ONE clear way the system works, well-documented and well-tested, with no confusing alternatives.