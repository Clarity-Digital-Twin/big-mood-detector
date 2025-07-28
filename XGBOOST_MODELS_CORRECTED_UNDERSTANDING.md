# XGBoost Models - CORRECTED Understanding

**Date:** July 27, 2025  
**Status:** Major correction after careful paper re-reading

## 🔄 Complete Reversal: XGBoost Models ARE Population Models

After careful re-reading of the paper and examining the methodology, I must correct our previous understanding:

## What The XGBoost Models Actually Are

The models in `/model_weights/xgboost/` are:
- **Population models** trained on aggregated data from 168 Korean patients
- **Fully functional** predictors that work "out of the box"  
- **No labeling required** from users
- **Complete XGBoost trees** with 560 decision trees for depression model

## Key Evidence from the Paper

### The Training Data
- 168 patients total
- 44,787 days of data collected
- 6,955 days with mood episodes
- **All pooled together** for training

### The Main Results (AUC 0.925/0.984/0.985)
From the paper:
> "The XGBoost classifier was trained on the randomly sampled 80% of the entire dataset"

This means they mixed ALL patients' data together - classic population modeling!

### The "60-day window" Confusion
The quote that confused us:
> "we selected a specific 60-day range for each patient where half of the range represented episodic days"

This was for **validation testing**, not a user requirement! They wanted robust test windows.

## How The Models Actually Work

```python
# Step 1: User provides sleep data (no labels needed!)
sleep_data = parse_apple_health_export()

# Step 2: Extract 36 features
features = calculate_seoul_features(sleep_data)
# Includes: ST_long_MN, ST_long_SD, ST_long_Zscore, etc.

# Step 3: Use pre-trained models directly
depression_risk = xgboost_model.predict(features)
# Works immediately!
```

## Answering Your Questions Directly

### Q: "Are the pretrained weights good for anything?"
**YES!** They are complete, functional models that can predict mood risk immediately.

### Q: "What do these weights represent?"
**Population-level patterns** learned from 168 Korean patients with mood disorders. Think of it like a diagnostic test developed on one population.

### Q: "Would a random person need to provide labeling?"
**NO!** The models work with just sleep/wake data. No labeling required.

### Q: "How can you have 30 episode days?"
**You don't need them!** This was the researchers selecting balanced test windows for validation. Users need zero episode days.

### Q: "Would Korean cohort members need labeling?"
**NO!** The models would work for them (or anyone) immediately with just sleep data.

## Important Caveats

### Accuracy Considerations
- **Best for:** Korean adults age 18-35 with diagnosed mood disorders
- **Less accurate for:** Different demographics, ages, or populations
- **Still useful for:** General screening in any population

### Why Personalization Exists in Codebase
The labeling functionality exists for **future improvements**:
- Personal models would be more accurate
- Transfer learning from Korean weights
- Fine-tuning for specific populations

## The Statistical Baseline Investigation

Our investigation into `BaselineRepositoryInterface` found:
- It has bugs (zero-hour sleep corruption)
- It's not used by the models anyway
- Z-scores are calculated as part of the 36 features, not separately

## Summary

**Previous Understanding (WRONG):**
- Models require user labeling ❌
- Need 60 days with episodes ❌  
- Personalized training required ❌

**Correct Understanding:**
- Models work immediately ✓
- Just need sleep/wake data ✓
- Population-based approach ✓
- Labeling optional for personalization ✓

The confusion arose from misreading the validation methodology as user requirements. The XGBoost models are ready-to-use population models, not frameworks requiring personalization.