# Hardcoded Values Investigation: Medical Numbers That Lie
**Date**: 2025-07-29  
**Focus**: Hardcoded medical predictions and magic numbers

## Executive Summary

The codebase contains **hardcoded medical values** used as fallbacks when systems fail. These values are presented to users as real predictions, creating dangerous false confidence in non-functional systems.

## Critical Hardcoded Medical Values

### In temporal_ensemble_orchestrator.py:
```python
# When PAT fails:
current_state = CurrentMoodState(
    depression_probability=0.5,          # 50% - completely arbitrary!
    on_benzodiazepine_probability=0.5,  # 50% - no basis in reality!
    confidence=0.0,
)

# When XGBoost fails:
future_risk = FutureMoodRisk(
    depression_risk=0.33,    # 33.3% - why this number?
    hypomanic_risk=0.33,     # 33.3% - equal distribution?
    manic_risk=0.34,         # 33.4% - adds to 100%
    confidence=0.0,
)
```

**Impact**: Users see 56.3% (0.5 → 0.563 after display rounding) for ALL predictions

### In aggregation_pipeline.py:
```python
# Default "clinical" values:
sleep_efficiency=0.9,              # 90% - too high for clinical population
sleep_regularity_index=90.0,       # 90 - arbitrary
sleep_onset_hour=21.0,             # 9 PM - assumes everyone sleeps at 9
wake_time_hour=7.0,                # 7 AM - assumes 10-hour sleep
circadian_phase_advance=0.0,       # No phase shift - incorrect
pat_hour=14.0,                     # 2 PM - middle of day
dlmo_confidence=0.8,               # 80% - fake confidence
data_completeness=0.8,             # 80% - always same
```

**These are presented as personalized health metrics!**

## Magic Numbers Throughout

### Time-Related Magic Numbers:
```python
MINUTES_PER_DAY = 1440      # Ok - actual constant
sleep_merge_threshold = 3.75 # hours - why 3.75?
lookback_days = 14          # Why 14?
min_days_required = 7       # Why 7?
confidence_threshold = 0.7  # Why 70%?
```

### ML-Related Magic Numbers:
```python
# In PAT configurations:
"encoder_rate": 0.1,        # Dropout rate - affects predictions
"patch_size": 18,           # Why 18?
"embed_dim": 96,            # Why 96?

# In predictions:
threshold = mean_activity * 0.5  # Why 50% of mean?
```

## The Fallback Value Pattern

### Pattern Found Throughout:
```python
try:
    real_value = calculate_something()
except:
    real_value = HARDCODED_FALLBACK  # User never knows!
```

### Examples:
1. **Sleep Duration**: Falls back to 8 hours
2. **Activity Level**: Falls back to 5000 steps  
3. **Heart Rate**: Falls back to 70 bpm
4. **Confidence**: Falls back to 0.0 (then ignored)

## Clinical Implications

### Scenario: Depression Risk Assessment
```
Real calculation fails → Returns 0.5 → Displays as 56.3%
Doctor sees: "Moderate depression risk (56.3%)"
Reality: Complete system failure, arbitrary number
```

### Scenario: Sleep Efficiency
```
No sleep data → Returns 0.9 → Displays as "90% efficiency"
User sees: "Excellent sleep quality!"
Reality: No sleep data at all
```

### Scenario: Circadian Rhythm
```
DLMO calculation fails → Returns 21.0 → "Your melatonin onset is 9 PM"
User adjusts medication timing based on fake data
```

## Why These Specific Numbers?

### 0.5 (50%)
- Middle of probability range
- "Neutral" prediction
- Hides complete failure

### 0.33/0.33/0.34
- Splits probability three ways
- Sums to 1.0
- No clinical basis

### 0.9 (90%)
- Sounds good for efficiency
- Not too perfect (100%)
- Completely fabricated

### 14.0 (2 PM)
- Middle of waking day
- Seems reasonable
- No personalization

## The Confidence Lie

### What Users See:
```
Confidence: 91.3%
```

### What Code Does:
```python
confidence=0.0,  # Set to 0 when failing
# Later:
confidence = some_other_calculation()  # Overwritten!
```

**Fake confidence scores hide system failures!**

## Testing's Complicity

### Tests Validate Hardcoded Values:
```python
def test_pat_failure_returns_neutral():
    # Force failure
    mock_pat.side_effect = Exception()
    
    result = orchestrator.predict()
    
    # Test PASSES with hardcoded value!
    assert result.depression_probability == 0.5
```

**Tests ensure fake values are returned consistently!**

## The Normalization Excuse

### Code Comments Found:
```python
# Use normalized values
value = 0.5  # Normalized to 0-1 range
```

### Reality:
- Not normalized from anything
- Just picked 0.5 as middle
- No actual normalization performed

## Required Changes

### 1. Remove ALL Medical Hardcodes
```python
# DELETE:
depression_probability=0.5

# REPLACE WITH:
raise PredictionFailedError("PAT model unavailable")
```

### 2. Use Clinical Defaults Carefully
```python
# IF you must have defaults:
DEFAULT_SLEEP_EFFICIENCY = 0.75  # Based on clinical studies
# WITH clear indication:
sleep_efficiency = DEFAULT_SLEEP_EFFICIENCY  # (default used)
```

### 3. Make Constants Configurable
```python
# Instead of:
magic_number = 3.75

# Use:
SLEEP_MERGE_THRESHOLD_HOURS = config.get(
    "sleep_merge_threshold", 
    3.75  # WHO recommendation
)
```

### 4. Document Every Magic Number
```python
# BAD:
threshold = 0.7

# GOOD:
# Threshold based on validation study (n=1000)
# achieving 85% sensitivity for depression detection
DEPRESSION_RISK_THRESHOLD = 0.7
```

## The Bigger Picture

These hardcoded values represent:
1. **Lack of domain knowledge**: Real clinical values not researched
2. **Poor error handling**: Fake data instead of errors
3. **False precision**: 56.3% sounds exact but is meaningless
4. **Hidden failures**: System broken but appears functional

## Recommendations

1. **IMMEDIATE**: Audit all medical predictions for hardcodes
2. **URGENT**: Replace fallbacks with errors
3. **IMPORTANT**: Document all thresholds with citations
4. **CRITICAL**: Add "default used" indicators
5. **ESSENTIAL**: Validate against clinical literature

---

**The Bottom Line**: Every hardcoded medical value is a lie told to vulnerable users. In mental health applications, false data is worse than no data. These "neutral" values could lead to missed interventions, incorrect treatments, or false reassurance during critical periods.