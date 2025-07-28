# Definitive Answers to Issue #65: XGBoost Model Requirements

**Date:** July 28, 2025  
**Status:** RESOLVED - Based on baseline removal investigation and code analysis

## Summary of What We Just Fixed

We completely removed the BaselineRepository system (1,139 lines of code) after discovering:
1. XGBoost models calculate baselines using **rolling windows** (30-60 days) in `AggregationPipeline`
2. The BaselineRepository was dead code - never actually used by the models
3. Personal normalization happens via rolling statistics, not persistent storage

## Definitive Answers to the 5 Critical Questions

### 1. Are the XGBoost weights population models or personalization frameworks?
**Answer: Population models**
- Pre-trained on pooled data from 168 Korean patients (44,787 total days)
- Work immediately with just sleep data (no individual training required)
- Line 88 confirms: "trained on the randomly sampled 80% of the entire dataset"

### 2. What does "60-day range where half represented episodic days" mean?
**Answer: Validation methodology, NOT a user requirement**
- Used for testing model generalization in the paper
- Researchers tested on windows containing mood episodes to measure accuracy
- New users do NOT need 60 days or labeled episodes to get predictions

### 3. Do the models need labeled episodes to function?
**Answer: NO**
- Models output risk scores with just 30+ days of sleep data
- Labels were used to TRAIN the original Korean model
- Labels can be used to TEST personal accuracy, but aren't required for predictions

### 4. Are Z-scores calculated separately or part of the 36 features?
**Answer: Part of the 36 features**
- Features 33-36 are Z-scores (sleep_duration_zscore, activity_zscore, hr_zscore, hrv_zscore)
- Calculated using rolling 30-60 day windows in `AggregationPipeline`
- Not stored separately - computed on demand

### 5. What's the difference between Figures 4-5 (AUC 0.925) and Figure 6 (AUC 0.80)?
**Answer: Different evaluation methods**
- Figures 4-5: Cross-validation on full dataset (higher AUC)
- Figure 6: Prospective validation on future data (realistic performance)
- The 0.80 AUC represents real-world expected performance

## Recommendations Based on Our Investigation

### 1. BaselineRepository System - **DEPRECATED** ✅
- Already removed in PR #66
- Models use rolling window calculations instead
- No need to fix the zero-hour sleep bug - entire system was unused

### 2. Labeling System - **KEEP FOR FUTURE** 
- NOT required for basic predictions
- Valuable for:
  - Users testing their personal accuracy
  - Future personalization features
  - Research and validation
- Document as "optional advanced feature"

### 3. Documentation Updates Needed
Remove these incorrect statements:
- ❌ "Models require 60 days with 30 episode days"
- ❌ "Must label episodes before predictions work"
- ❌ "Models learn your personal patterns"

Add these correct statements:
- ✅ "Models provide immediate predictions after 30 days of sleep data"
- ✅ "No mood labeling required to start"
- ✅ "Accuracy validated for Korean adults with mood disorders (AUC 0.80)"
- ✅ "Optional: Label past episodes to test personal accuracy"

## Technical Implementation Details

### How It Actually Works (Confirmed by Code)
```python
# 1. User uploads Apple Health data
data = parse_apple_health_export()

# 2. AggregationPipeline calculates rolling baselines (30-60 days)
features = aggregation_pipeline.aggregate_seoul_features(
    sleep_records=data.sleep,
    activity_records=data.activity,
    heart_records=data.heart_rate,
    start_date=target_date - timedelta(days=60),
    end_date=target_date
)

# 3. XGBoost makes predictions immediately
model = XGBoostMoodPredictor()
risk = model.predict(features)  # Works without any labels!
```

## Why We Were Confused

1. The paper uses academic language that conflates training and usage
2. "Baseline" meant two different things:
   - Statistical baselines (rolling means/stds) - USED
   - Episode baselines (labeled ground truth) - NOT REQUIRED
3. Multiple contradictory interpretations in our documentation

## Action Items

1. ✅ BaselineRepository removal - COMPLETE (PR #66)
2. 📝 Update all documentation to reflect correct understanding
3. 🏷️ Keep labeling system but document as optional
4. ⚠️ Add population disclaimer: "Validated for Korean cohort"

## Closing This Issue

The definitive answer is: **XGBoost models are population-based and work immediately with 30+ days of sleep data. No labeling required.**

The baseline removal we just completed (PR #66) was the correct action - the models use rolling window normalization, not the broken BaselineRepository system.