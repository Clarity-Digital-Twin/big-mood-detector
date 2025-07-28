# Baseline Implementation Analysis - Big Mood Detector

**Date:** July 27, 2025  
**Version:** v0.5.0  
**Analysis by:** Claude (Acting as Co-founder)

## Executive Summary

After comprehensive analysis of the baseline implementation in Big Mood Detector, I've found that:

1. **Infrastructure exists** - BaselineRepositoryInterface, FileBaselineRepository, and AdvancedFeatureEngineer support baselines
2. **Baselines are calculated but underutilized** - Z-scores use population defaults, not personal baselines  
3. **Critical bug** - Sleep values of 0 hours corrupt baselines (as seen in testing)
4. **Models don't use Z-scores** - XGBoost models expect raw features, not normalized ones

**Recommendation:** Fix the critical bugs first, then decide if baseline implementation adds value. Current state is **worse than nothing** due to bugs.

## Current State Analysis

### What's Implemented

1. **Domain Layer** (`domain/repositories/baseline_repository_interface.py`)
   - Clean interface for baseline persistence
   - UserBaseline value object with all necessary fields
   - Supports sleep, activity, HR, HRV baselines

2. **Infrastructure Layer**
   - FileBaselineRepository - JSON file storage
   - TimescaleBaselineRepository - Database storage
   - Both handle user ID hashing for privacy

3. **Feature Engineering** (`domain/services/advanced_feature_engineering.py`)
   - Calculates incremental statistics
   - Persists baselines after feature extraction
   - Z-score normalization using baselines

4. **Pipeline Integration**
   - MoodPredictionPipeline accepts baseline_repository
   - CLI supports --user-id for personalization
   - persist_baselines() called after batch processing

### What's NOT Working

1. **Critical Bug: Zero Sleep Values**
   ```python
   # In _calculate_normalized_features():
   sleep_hours = sleep.total_sleep_hours if sleep else 0  # BUG: 0 corrupts baseline!
   self._update_individual_baseline("sleep", sleep_hours)
   ```
   This means missing data adds 0-hour sleep to baselines, completely destroying personalization.

2. **Z-scores Not Used by Models**
   - XGBoost models trained on raw features (sleep_percentage_MN, long_ST_SD, etc.)
   - Z-score features (sleep_duration_zscore, etc.) are calculated but ignored
   - Models never see the personalized values!

3. **Baseline Loading Issues**
   - Baselines load from repository but don't initialize incremental stats correctly
   - After restart, Z-scores change dramatically (see test results)

4. **No Validation**
   - No checks for reasonable baseline values
   - No minimum data requirements before creating baseline
   - No outlier detection

## Test Results Analysis

Our comprehensive test revealed:

### Baseline Creation ✓
- Athlete: 8.8h sleep, 18.5k steps, 43 bpm
- Sedentary: 5.9h sleep, 4.4k steps, 64 bpm
- Baselines correctly reflect user patterns

### Z-score Personalization ✗
With identical input (7.5h sleep, 10k steps, 65 bpm):
- Sleep Z-scores nearly identical (-1.70 vs -1.69) despite different baselines
- Activity Z-scores correct (athlete: -1.72, sedentary: +1.71)
- HR Z-scores incorrect pattern

### Persistence ✗
After restart with same data:
- Z-scores changed dramatically (athlete sleep: -1.70 → +2.24)
- Clear evidence of baseline corruption from 0 values
- HR Z-scores became nonsensical (-39.81)

### Model Impact ✗
- Could not test because models expect different features
- Even if working, models don't use Z-score features

## Root Cause Analysis

### Why Baselines Aren't Adding Value

1. **Feature Mismatch**
   - Models trained on Seoul paper features (mean, SD, Z-score for 12 indexes)
   - Our implementation creates different Z-scores (for individual metrics)
   - Features don't align with model expectations

2. **Implementation Bugs**
   ```python
   # Bug 1: Zero values corrupt baselines
   sleep_hours = sleep.total_sleep_hours if sleep else 0
   
   # Bug 2: Wrong calculation after loading
   if baseline.get("count", 0) == 0 and baseline.get("mean", 0.0) != 0:
       # This path has issues with sum_sq calculation
   ```

3. **Conceptual Mismatch**
   - Seoul paper uses population Z-scores within their dataset
   - We're trying to add individual personalization on top
   - Models weren't trained with this personalization

## Literature Review Results

### XGBoost Paper (Seoul National University)
- Uses Z-scores but **within-dataset normalization**, not personal baselines
- "We calculated mean, standard deviation, and Z-score for each of 12 indexes"
- No mention of individual baseline calibration
- Focus on population-level patterns

### PAT Paper (Dartmouth)
- No baseline or personalization mentioned
- Uses raw activity sequences
- Relies on deep learning to learn patterns implicitly

### Conclusion from Literature
**Neither paper uses personal baselines**. They rely on:
- Population statistics for normalization
- Model's ability to learn from patterns
- Large datasets to capture variability

## Business Impact Assessment

### If We Fix Baselines

**Potential Benefits:**
- More accurate predictions for individuals with unusual patterns
- Better handling of athletes vs sedentary users
- Improved user trust through personalization

**Required Work:**
1. Fix zero-value bug (1 hour)
2. Fix baseline loading/persistence (2-4 hours)
3. Retrain models with personalized features (2-4 weeks)
4. Validate improvement with clinical data (4-8 weeks)

**Total: 6-12 weeks of work**

### If We Remove Baselines

**Benefits:**
- Simpler, more maintainable code
- No risk of baseline corruption
- Focus on core value prop (predictions)

**Work Required:**
1. Remove baseline code paths (2 hours)
2. Update documentation (1 hour)

**Total: 3 hours**

## Recommendation

As your co-founder, here's my honest assessment:

### Short Term (v0.5.0): REMOVE BASELINES

**Why:**
1. Current implementation is **actively harmful** due to bugs
2. Models don't use the personalized features anyway
3. No evidence from papers that baselines improve accuracy
4. 6-12 weeks to maybe improve accuracy by 2-3%? Not worth it.

**Action Items:**
1. Set `enable_personal_calibration=False` by default
2. Document as "experimental feature"
3. Fix critical bugs if keeping code
4. Focus on shipping core value

### Long Term (v0.6+): REVISIT IF USERS REQUEST

**When baselines might matter:**
1. Users complain about inaccurate predictions
2. We have 100+ users with longitudinal data
3. Clinical partners request personalization
4. We have resources for proper implementation

**Proper implementation would require:**
1. Minimum 30 days of data before creating baseline
2. Outlier detection and robust statistics
3. Model retraining with personalized features
4. A/B testing to prove value

## Code Quality Assessment

### Good Patterns
- Clean domain interface (BaselineRepositoryInterface)
- Privacy-first with user ID hashing
- Incremental statistics for efficiency
- Repository pattern for storage flexibility

### Issues
- No tests for baseline accuracy
- No validation of baseline values
- Complex incremental stats code prone to bugs
- Mismatch between domain ideal and ML reality

## Final Verdict

**Baselines are a good idea implemented at the wrong time.**

The current implementation is buggy and doesn't improve predictions. We should:

1. **Disable by default** - Prevent user confusion
2. **Fix critical bugs** - In case someone enables it
3. **Document as experimental** - Set expectations
4. **Revisit in 6 months** - When we have real user data

Remember: **Perfect is the enemy of good.** Ship v0.5.0 without baselines as a core feature. Let users tell us if they need personalization, rather than assuming they do.

## Appendix: Test Results

### Baseline Calculation Results
```json
{
  "athlete": {
    "sleep_mean": 8.8,
    "activity_mean": 18561,
    "hr_mean": 43
  },
  "sedentary": {
    "sleep_mean": 5.9,
    "activity_mean": 4355,
    "hr_mean": 64
  }
}
```

### Z-score Issues
- Sleep Z-scores nearly identical despite 3-hour difference in baselines
- Values corrupted after restart due to zero-hour bug
- HR Z-scores became -39.81 (impossible value)

### Critical Code Sections

Bug location in `advanced_feature_engineering.py:394`:
```python
sleep_hours = sleep.total_sleep_hours if sleep else 0  # BUG!
self._update_individual_baseline("sleep", sleep_hours)
```

Should be:
```python
if sleep and sleep.total_sleep_hours > 0:
    self._update_individual_baseline("sleep", sleep.total_sleep_hours)
```

---

**The path forward is clear: Fix the bugs, disable by default, and ship. Don't let perfect baselines block good predictions.**