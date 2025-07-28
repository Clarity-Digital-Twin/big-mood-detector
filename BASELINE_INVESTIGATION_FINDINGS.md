# Baseline Investigation Findings

**Date:** July 28, 2025  
**Status:** Complete Investigation

## Executive Summary

After thorough investigation, here's the definitive answer about baselines in Big Mood Detector:

### Two Different "Baseline" Systems

1. **Rolling Window Baselines (WORKING ✅)**
   - Used by XGBoost pipeline in `AggregationPipeline`
   - Calculates personal mean/std from 30-60 day windows
   - This is what the paper intended
   - Located in: `calculate_statistics()` method

2. **BaselineRepository System (BROKEN ❌)**
   - Separate persistence layer for long-term baselines
   - Has critical bugs (zero-hour sleep corruption)
   - NOT used by XGBoost models
   - Can be safely deprecated

## The Source of Confusion

The confusion arose because:
- We have TWO different baseline implementations
- Documentation conflated them
- AI agents saw the broken BaselineRepository and assumed the whole baseline system was broken
- But XGBoost actually uses the working rolling window approach

## What Actually Happens

### Current XGBoost Pipeline (CORRECT)
```python
# For each day's prediction:
1. Get previous 30-60 days of data
2. Calculate mean/std for each feature over that window
3. Calculate Z-score: (today - window_mean) / window_std
4. Create 36-feature vector with mean, std, and Z-score
5. Run pre-trained XGBoost model
```

### BaselineRepository (UNUSED/BROKEN)
```python
# Was supposed to:
1. Store long-term personal baselines
2. Update incrementally with new data
3. Provide stable baseline for new users

# But actually:
- Corrupts baselines with zero values
- Not integrated with XGBoost pipeline
- Creates confusion
```

## Critical Findings

### 1. XGBoost Implementation is Correct ✅
- Properly calculates personal baselines from rolling windows
- Matches the paper's methodology
- Features are correctly extracted
- Models load and run properly

### 2. BaselineRepository Should Be Removed ❌
- Not used by production pipeline
- Has unfixable design flaws
- Causes confusion
- No benefit to keeping it

### 3. Documentation Needs Clarity 📝
- Must distinguish rolling baselines from persistent baselines
- Remove references to "60-day requirements"
- Clarify that labeling is optional

## Test Results

### What We Tested
1. **Feature Vector Length**: ✅ 36 features as expected
2. **Z-score Calculation**: ✅ Uses personal rolling statistics
3. **Model Execution**: ✅ Runs end-to-end
4. **BaselineRepository**: ❌ Broken but irrelevant

### The "Bug" That Wasn't
The AI agent mentioned baseline calculation bugs, but this was referring to the UNUSED BaselineRepository system, not the actual XGBoost pipeline.

## Recommendations

### Immediate Actions
1. **Delete BaselineRepository** - It's broken and unused
2. **Update Documentation** - Clarify rolling window approach
3. **Add Tests** - Verify Z-score calculations

### Code to Remove
```
- domain/repositories/baseline_repository_interface.py
- infrastructure/repositories/file_baseline_repository.py
- infrastructure/repositories/timescale_baseline_repository.py
- All related tests
```

### Code to Keep
```
+ application/services/aggregation_pipeline.py (working baseline calculation)
+ All XGBoost model infrastructure
+ Rolling window statistics
```

## FAQ

**Q: Do we need a database for baselines?**
A: No. Rolling windows are calculated on-demand from available data.

**Q: Is the 30-day baseline requirement real?**
A: Yes. You need 30+ days to calculate stable statistics for Z-scores.

**Q: Can we do fine-tuning without BaselineRepository?**
A: Yes. Fine-tuning uses labeled episodes, not baseline statistics.

**Q: Why did multiple AI agents get confused?**
A: They saw two baseline systems and conflated them. The broken one is visible in tests.

## Bottom Line

**The XGBoost pipeline works correctly.** It calculates personal baselines using rolling windows exactly as the paper describes. The BaselineRepository system is a red herring that should be removed to prevent future confusion.

### What Users Need to Know
- Provide 30+ days of sleep data
- System calculates your personal baseline automatically
- Predictions work immediately (no labeling required)
- Accuracy validated for Korean cohort only