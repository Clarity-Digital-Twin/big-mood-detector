# Future Work & Technical Debt

Last Updated: 2025-07-29

## Recently Completed (v0.5.5)
- ✅ Fixed all hardcoded values (dlmo_confidence, data_completeness)
- ✅ Renamed dlmo_hour → estimated_dlmo_hour throughout codebase
- ✅ Fixed PAT integration method name bug
- ✅ Implemented proper error handling (fail fast, no fake data)
- ✅ Added comprehensive integration tests
- ✅ Fixed date handling to use actual data dates

## High Priority Improvements

### 1. Implement Principal Activity Time (PAT hour)
**Current Status**: Placeholder field with hardcoded value of 0.0

**What it is**: Principal Activity Time – the 24-hour "center of mass" of a day's activity curve (circadian midpoint of movement).

**Implementation**:
```python
# One-pass reduction over per-minute step count array:
PAT = sum(activity[t] * t for t in range(1440)) / sum(activity)
# Convert to hours with wraparound handling
```

**Benefits**:
- Quantify circadian phase shifts from baseline
- Feed compact phase feature into classifiers  
- Sanity-check DLMO estimates (PAT typically trails CBT minimum by ~4 hours)

**Tasks**:
- [ ] Implement calculation in `CircadianFeatureCalculator`
- [ ] Remove hardcoded 0.0 default
- [ ] Add to feature extraction pipeline
- [ ] Update tests to verify real calculation

### 2. CLI/API Error Wrapper
**Current Status**: Raw exceptions bubble up to users

**Goal**: User-friendly error messages with actionable guidance

**Implementation**:
```python
class UserFriendlyError:
    """Wrapper for common errors with helpful messages."""
    
    ERROR_MESSAGES = {
        "insufficient_data": "Need at least 7 days of data. Upload more health records.",
        "missing_models": "ML models not found. Run 'bigmood download-models' first.",
        "invalid_xml": "Cannot parse health export. Ensure it's from Apple Health.",
    }
```

**Benefits**:
- Better user experience
- Reduced support tickets
- Clear action steps for resolution

### 3. Optional DLMO Calculation
**Current Status**: DLMO calculation can be slow for large datasets

**Improvement**: Make DLMO calculation optional/lazy
- Add `--skip-dlmo` flag to CLI
- Only calculate when specifically needed
- Cache results for repeated analysis

## Medium Priority

### 4. Performance Optimizations
- [ ] Parallel processing for multi-day aggregation
- [ ] Streaming JSON output for large result sets
- [ ] Memory-mapped file support for huge XMLs

### 5. Enhanced Reporting
- [ ] PDF report generation
- [ ] Visualization charts (sleep patterns, mood trends)
- [ ] Export to clinical formats (HL7 FHIR)

### 6. Model Improvements
- [ ] Retrain PAT-L to reach paper's 0.610 AUC
- [ ] Add mania/hypomania heads to PAT
- [ ] Personal baseline calibration

## Low Priority / Nice to Have

### 7. Additional Features
- [ ] Support for other wearables (Fitbit, Garmin)
- [ ] Integration with EHR systems
- [ ] Real-time monitoring mode
- [ ] Mobile app companion

### 8. Developer Experience
- [ ] Interactive documentation site
- [ ] Example notebooks
- [ ] Model interpretation tools
- [ ] Debugging visualizations

## Technical Debt to Address

1. **Remove Placeholder Fields**: Either implement or remove `pat_hour` from v0.6.0
2. **Consolidate Date Handling**: All date logic through `UniversalDateAssignment`
3. **Standardize Error Handling**: Consistent exception hierarchy
4. **Document Model Assumptions**: Clear docs on what each model expects

## Research Opportunities

1. **Multimodal Fusion**: Better ways to combine PAT + XGBoost
2. **Uncertainty Quantification**: Confidence intervals, not just point estimates
3. **Longitudinal Adaptation**: Models that learn from user feedback
4. **Explainability**: Why did the model make this prediction?

---

**Note**: This document tracks work that was identified during the v0.5.5 polish phase but deemed non-critical for immediate release. All items here would improve the system but are not blocking production use.