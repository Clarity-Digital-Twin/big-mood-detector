# XGBoost Paper - The Actual Truth

**Date:** July 27, 2025  
**Critical Clarification After Line-by-Line Analysis**

## What The XGBoost Weights Actually Are

The weights in `/model_weights/xgboost/` are **full trained models** from the Korean cohort. The JSON files contain:
- 560 trees (depression model)
- Split conditions, thresholds, leaf values
- Complete decision tree structures
- Trained on ALL 168 patients' data aggregated (44,787 days total)

**CRITICAL**: These are POPULATION MODELS, not personalized models!

## What The Paper Actually Did

### Main Analysis (Figures 4-5, AUC 0.925/0.984/0.985)
- **Purpose**: Show that mood episodes depend on sleep/circadian features
- **Data**: 80% of ALL 44,787 days from 168 patients mixed together
- **Method**: Train single XGBoost model on population data
- **Result**: Can classify episode vs non-episode days with high accuracy
- **THIS IS WHAT OUR WEIGHTS ARE FROM**

### Prediction Validation (Figure 6, AUC 0.80/0.98/0.95)
- **Purpose**: Test if models can predict future episodes
- **Data**: Selected 60-day windows with 50% episode days from EACH patient
- **Method**: Still trained on POOLED data, tested on future data
- **NOT personalized models** - just careful data selection

## Critical Insights

### 1. Z-scores ARE Part of the Features
The paper calculates 36 features:
- 12 base features (sleep_amplitude, long_ST, etc.)
- Mean, SD, and Z-score for EACH = 36 total

The Z-score represents individual variation from their own baseline.

### 2. Korean Weights ARE Complete Prediction Models
The weights are full XGBoost models that can make predictions directly:
- Trained on 168 patients' aggregated data
- High accuracy on Korean cohort (AUC 0.80-0.98)
- Population-based approach, not personalized

### 3. NO Individual Labeling Required for Basic Use
The "60-day windows" were for MODEL VALIDATION, not requirements:
- Models work with just sleep data input
- No episode labeling needed from new users
- Accuracy depends on similarity to Korean cohort

## What This Means

### How The Korean Study Worked
1. Psychiatrists labeled all episodes for 168 patients
2. Collected 44,787 total days of data
3. Trained ONE model on ALL patients' data mixed together
4. High accuracy because trained and tested on same population

### For New Users (Anyone)
1. NO labeling required - models work out-of-box
2. Input: Just your sleep/wake data
3. Output: Risk scores for depression/mania/hypomania
4. Accuracy: Best if similar to Korean cohort (age 18-35, mood disorder)

## The Actual Implementation

```python
# How the models work in our codebase:
def predict_mood_risk(sleep_wake_data):
    # 1. Extract 36 features from sleep/wake patterns
    features = extract_seoul_features(sleep_wake_data)
    # Including: ST_long_MN, ST_long_SD, ST_long_Zscore, etc.
    
    # 2. Load pre-trained Korean models
    models = load_xgboost_models()  # XGBoost_DE.json, etc.
    
    # 3. Get predictions directly
    depression_risk = models['depression'].predict(features)
    manic_risk = models['manic'].predict(features)
    
    # 4. Return risk scores (no labeling needed!)
    return MoodPrediction(depression_risk, manic_risk)
```

## Why We Got Confused

1. **Misread "60-day windows"**: This was for MODEL VALIDATION, not user requirements
2. **Conflated papers**: PAT paper discusses personalization, XGBoost doesn't
3. **Overthought Z-scores**: They're just features, not a separate baseline system

## The Bottom Line

**XGBoost CAN make predictions with just:**
1. Your sleep/wake data from wearables
2. No labeling required
3. Uses the pre-trained Korean weights
4. Works immediately, no training needed

**HOWEVER:**
- Best accuracy for similar populations (young adults with mood disorders)
- Less accurate for different demographics
- Personalized models (with YOUR labels) would be more accurate
- The 30 "episode days" confusion came from misreading validation methodology

## Answering Your Specific Questions

### Q: "Would the Korean cohort need labeling to use the weights?"
**A: NO.** The weights ARE the final trained model. Any Korean cohort member could use them directly without labeling.

### Q: "If a random person provides 30 days of labeled data, would it work?"
**A: The models don't need YOUR labels at all!** They're already trained. Just provide sleep data.

### Q: "What do these weights represent?"
**A: Complete trained XGBoost models** that learned patterns from 168 Korean patients. Think of it like a medical test developed on one population - it works for everyone, just most accurate for similar populations.

### Q: "How can you have 30 episode days?"
**A: You DON'T need them!** This was confusion from the paper's validation methodology. They selected test windows with 30/60 episode days to ensure robust testing. Users don't need any episode days.