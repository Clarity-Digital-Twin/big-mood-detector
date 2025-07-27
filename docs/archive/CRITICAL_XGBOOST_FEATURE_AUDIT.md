# CRITICAL XGBOOST FEATURE AUDIT

## Executive Summary

**CRITICAL FINDING**: Our implementation DOES NOT match the paper's 36 features. We have a fundamental mismatch that will prevent the XGBoost models from working correctly.

## Paper's 36 Features (From Nature Digital Medicine 2024)

The paper clearly states:
> "we extracted 10 sleep and 2 circadian indexes to identify sleep and circadian rhythm features relevant to mood episodes. Furthermore, we calculated the mean, standard deviation, and Z-score of each index for each patient to express the inter-daily variation in sleep and circadian rhythm features for each individual more accurately (Fig. 3b). Thus, in total 36 features were extracted to predict mood episodes"

### The 12 Base Indexes:

**Sleep Indexes (10):**
1. **Sleep amplitude** - coefficient of variation of wake amounts every 10 min
2. **Sleep percentage** - percentage of total sleep time
3. **Long Num** - number of long sleep windows (>3.75h)
4. **Long Len** - total length of long windows
5. **Long ST** - sleep time in long windows
6. **Long WT** - wake time in long windows
7. **Short Num** - number of short sleep windows (<3.75h)
8. **Short Len** - total length of short windows
9. **Short ST** - sleep time in short windows
10. **Short WT** - wake time in short windows

**Circadian Indexes (2):**
11. **Circadian phase** (DLMO) - estimated from CBT minimum - 7h
12. **Circadian amplitude** - amplitude of simulated CBT rhythm

**For EACH index: Mean (MN), Standard Deviation (SD), Z-score = 36 total features**

### Critical Paper Details:

1. **Sleep Window Construction**:
   - "aggregating sleep periods less than an hour apart"
   - "disregarding awakenings and sleep durations under 10 min"
   - "categorized as either long or short based on a threshold length of 3.75 h"

2. **Circadian Phase Calculation**:
   - Uses mathematical model of core body temperature (CBT)
   - DLMO = CBT_min - 7 hours
   - Light profile: 250 lux when awake, 0 lux when sleeping

3. **Z-score Calculation**:
   - "Z-score of each individual's estimated circadian phase distribution"
   - Uses PATIENT'S OWN baseline, not population norms

## Our Current Implementation

### What We Have:
```python
class SeoulXGBoostFeatures:
    # Basic Sleep Features (1-5)
    sleep_duration_hours: float
    sleep_efficiency: float
    sleep_onset_hour: float
    wake_time_hour: float
    sleep_fragmentation: float
    
    # Advanced Sleep Features (6-10)
    sleep_regularity_index: float
    short_sleep_window_pct: float  # % < 6 hours (NOT PAPER'S <3.75h!)
    long_sleep_window_pct: float   # % > 10 hours (NOT PAPER'S >3.75h!)
    sleep_onset_variance: float
    wake_time_variance: float
    
    # Circadian Rhythm Features (11-18)
    interdaily_stability: float
    intradaily_variability: float
    relative_amplitude: float
    l5_value: float
    m10_value: float
    l5_onset_hour: float
    m10_onset_hour: float
    dlmo_hour: float
    
    # Activity Features (19-24)
    total_steps: int
    activity_variance: float
    sedentary_hours: float
    activity_fragmentation: float
    sedentary_bout_mean: float
    activity_intensity_ratio: float
    
    # Heart Rate Features (25-28)
    avg_resting_hr: float
    hrv_sdnn: float
    hr_circadian_range: float
    hr_minimum_hour: float
    
    # Phase Features (29-32)
    circadian_phase_advance: float
    circadian_phase_delay: float
    dlmo_confidence: float
    pat_hour: float
    
    # Z-Score Features (33-36)
    sleep_duration_zscore: float
    activity_zscore: float
    hr_zscore: float
    hrv_zscore: float
```

## CRITICAL DIFFERENCES

### 1. **COMPLETELY DIFFERENT FEATURES**
- **Paper**: 12 indexes × 3 statistics = 36 features
- **Our code**: 36 different features mixing clinical, activity, heart rate

### 2. **MISSING PAPER'S KEY FEATURES**
- ❌ Sleep amplitude (coefficient of variation)
- ❌ Sleep percentage
- ❌ Long/Short window metrics with 3.75h threshold
- ❌ Proper circadian phase calculation from CBT model
- ❌ Mean/SD/Z-score for EACH feature

### 3. **ADDED FEATURES NOT IN PAPER**
- ✗ Activity features (steps, sedentary hours)
- ✗ Heart rate features 
- ✗ Interdaily stability, intradaily variability
- ✗ L5/M10 values
- ✗ Phase advance/delay

### 4. **WRONG CALCULATIONS**
- Using 6h/10h thresholds instead of 3.75h
- Using population norms for Z-scores instead of patient baseline
- Not implementing sleep window merging algorithm

## Can We Extract Paper's Features from Apple XML?

### YES, we can extract most features:

**From Apple Health XML we have:**
- ✅ Sleep records (HKCategoryTypeIdentifierSleepAnalysis)
- ✅ Sleep stages (asleep, awake, inBed)
- ✅ Timestamps for sleep/wake periods

**What we CAN calculate:**
1. ✅ Sleep amplitude - coefficient of variation of wake amounts
2. ✅ Sleep percentage - we already calculate this
3. ✅ Long/Short windows - need to implement 3.75h threshold logic
4. ✅ Sleep/Wake times within windows
5. ⚠️ Circadian phase - need to implement CBT model
6. ⚠️ Circadian amplitude - need to implement CBT model

**What we CANNOT get directly:**
- Light exposure data (paper assumes 250 lux when awake, 0 when sleeping)
- Core body temperature (paper uses mathematical model)

## We DO Have Infrastructure:

### 1. **Baseline Repository** ✅
```python
from big_mood_detector.infrastructure.repositories.file_baseline_repository import FileBaselineRepository
```
We HAVE this for patient-specific baselines!

### 2. **Sleep Window Merging** ✅
We just implemented overlap merging in SleepAggregator!

### 3. **Aggregation Pipeline** ✅
We have the infrastructure, just need correct features.

## IMPLEMENTATION PLAN

### Phase 1: Implement Paper's Exact Features
1. Create new `SeoulPaperFeatures` dataclass with 12 base indexes
2. Implement sleep window algorithm with 3.75h threshold
3. Calculate coefficient of variation for sleep amplitude
4. Implement CBT circadian model

### Phase 2: Calculate Statistics
1. Use BaselineRepository for patient-specific mean/SD
2. Calculate Z-scores using patient's own baseline
3. Generate exact 36-feature vector

### Phase 3: Test with XGBoost Models
1. Verify feature order matches paper
2. Test with converted JSON models
3. Validate predictions match paper's AUCs

## CONCLUSION - UPDATE AFTER DEEPER INVESTIGATION

We have a CRITICAL ROUTING ERROR, not a missing implementation!

**THE GOOD NEWS - WE ALREADY HAVE THE CORRECT IMPLEMENTATION:**
- ✅ `DailyFeatures` in `AggregationPipeline` has the EXACT paper features
- ✅ `aggregate_seoul_features()` method generates the correct 36 features
- ✅ The XGBoost models expect features with _MN, _SD, _Z suffixes (which DailyFeatures provides)

**THE BAD NEWS - WRONG PIPELINE IS BEING USED:**
- ❌ `XGBoostPipeline` uses `SeoulFeatureExtractor` → `SeoulXGBoostFeatures` (wrong features)
- ❌ Should use `AggregationPipeline.aggregate_seoul_features()` → `DailyFeatures` (correct features)

**THE FIX IS SIMPLE:**
1. Fix the immediate division by zero bug in SeoulFeatureExtractor
2. Modify XGBoostPipeline to use AggregationPipeline.aggregate_seoul_features()
3. Convert DailyFeatures to the format XGBoostMoodPredictor expects

**What we DON'T need to do:**
- ❌ Reimplement the 36 features (we have them!)
- ❌ Create new feature extraction logic (it exists!)
- ❌ Modify the paper's methodology (we already match it!)