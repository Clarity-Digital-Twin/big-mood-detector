# XGBoost Paper - The Actual Truth

**Date:** July 27, 2025  
**Critical Clarification After Line-by-Line Analysis**

## The Two Systems in the Paper

### System 1: Feature Importance Analysis (Figures 4-5)
- **Purpose**: Identify which features matter
- **Data**: 80% random sample of ALL patients aggregated
- **Result**: Circadian phase Z-score most important
- **This is likely what our weights represent**

### System 2: Personal Prediction Models (Figure 6)
- **Purpose**: Predict individual patient's episodes
- **Data**: Each patient's own 60-day window
- **Method**: Train XGBoost on THAT patient's data
- **This is what actually makes predictions**

## Critical Insights

### 1. Z-scores ARE Calculated, But Not How We Thought
The paper calculates 36 features:
- 12 base features (sleep_amplitude, long_ST, etc.)
- Mean, SD, and Z-score for EACH = 36 total

The Z-score for a feature on day X uses that patient's historical mean/std for that feature.

### 2. Korean Weights Can't Predict Directly
The weights we have are probably from System 1 (feature importance), not personalized models. They tell us WHAT to look for, not HOW to predict for YOU.

### 3. Every Patient Needs Their Own Model
Quote from methods:
> "we selected a specific 60-day range for each patient where half of the range represented episodic days"

Even Korean patients needed personalized training!

## What This Means

### For Korean Cohort Members
1. Their episodes were labeled by psychiatrists
2. 60-day windows were selected with 50% episode days
3. Models trained on THEIR data
4. Future predictions based on THEIR patterns

### For New Users (Non-Korean)
1. Must label their own episodes
2. Need 60 days with ~30 episode days
3. Train model on their data
4. Korean weights provide feature guidance only

## The Correct Implementation

```python
# For each patient:
def train_personal_model(patient_data, episode_labels):
    # 1. Find 60-day window with 30 episode days
    window = find_training_window(patient_data, episode_labels)
    
    # 2. Extract 12 base features daily
    base_features = extract_base_features(window)
    
    # 3. Calculate mean, SD, Z-score (36 features)
    features = []
    for feature in base_features:
        features.append(feature.mean())  # Feature_MN
        features.append(feature.std())   # Feature_SD
        features.append(feature.zscore()) # Feature_Z
    
    # 4. Train XGBoost on THIS patient
    model = XGBoost.train(features, labels)
    
    # 5. Return personalized model
    return model
```

## Why We Got Confused

1. **"Baseline" Ambiguity**: The paper uses patient means/stds for Z-scores, which could be called "baselines"
2. **Population vs Personal**: Feature analysis uses population, predictions use personal
3. **Korean Weights**: We assumed they were ready-to-use models, but they're likely just feature importances

## The Bottom Line

**You CANNOT use XGBoost for predictions without:**
1. Labeling your episodes
2. Having 60 days of data with episodes
3. Training a model on YOUR data
4. The Korean weights alone won't predict anything

**The statistical calculations (mean/SD/Z-score) are part of feature engineering, not a separate baseline system.**