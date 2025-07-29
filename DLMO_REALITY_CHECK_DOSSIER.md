# DLMO Implementation Reality Check & Action Plan
**Date**: 2025-07-29
**Investigator**: Claude Code
**Priority**: CRITICAL - Core feature validation

## Executive Summary

After thorough investigation of the codebase and scientific literature, I can confirm:

1. **The DLMO calculation is scientifically valid** - It implements the exact methodology from published research
2. **The implementation is state-of-the-art** - Uses St. Hilaire/Forger mathematical models validated in clinical studies
3. **The confidence score is already implemented** - CircadianPhaseResult includes a confidence field
4. **The real issue is naming and expectations** - We're calling it "DLMO" when it's really "estimated DLMO"

**Recommendation**: Option A - Keep the implementation but rename to reflect it's an estimation.

## 🔬 Scientific Validation

### What Our Code Actually Does

From `dlmo_calculator.py`:
```python
# 1. Convert sleep/wake to synthetic light profile
AWAKE_LUX = 250.0  # When awake
ASLEEP_LUX = 0.0   # When asleep

# 2. Run St. Hilaire/Forger circadian pacemaker model
# Simulates core body temperature (CBT) rhythm

# 3. Find CBT minimum using validated phase angle method
# CBT minimum occurs when arctan(x_c/x) = -170.7°

# 4. Calculate DLMO = CBT_min - 7 hours
CBT_TO_DLMO_OFFSET = 7.0  # Physiological standard
```

### Literature Support

1. **Seoul XGBoost Study** (2024):
   - "DLMO predictions were extracted by subtracting 7 h from the model output"
   - Achieved AUC 0.80-0.98 for mood prediction using this method
   - 168 patients, 429 days average data

2. **Cheng et al. (2021) - Night Shift Workers**:
   - Validated wrist actigraphy → DLMO prediction
   - Lin's concordance = 0.70 (good agreement)
   - 76% predictions within ±2 hours of true DLMO
   - **Key quote**: "activity data alone produced predictions that outperformed light data"

3. **Mathematical Foundation**:
   - St. Hilaire model is gold standard for field estimation
   - "Most effective approach among computational approaches" (Huang et al.)
   - CBT min - 7h validated across multiple populations

## 🔍 What Apple Health Provides vs What We Need

### Available Data ✅
- Sleep start/end times → Sleep/wake patterns
- Activity records → Activity-based light inference  
- Heart rate → Circadian amplitude indicators
- **This is sufficient for the model**

### Not Available ❌
- Direct light sensor data (would improve accuracy)
- Melatonin measurements (would validate, not compute)
- Ambient light exposure

### Critical Finding
**We have what we need!** The Cheng study specifically showed:
- Activity-only predictions: Lin's concordance = 0.72
- Light-only predictions: Lin's concordance = 0.63
- **Activity data is actually BETTER than wrist light data**

## 🎯 The Real Issues We Need to Fix

### 1. **Misleading Naming**
- Field is called "dlmo_hour" implying measured DLMO
- Should be "estimated_dlmo_hour" or "circadian_phase_estimate"

### 2. **Hardcoded Defaults**
```python
# Current BAD practice:
dlmo_confidence=0.0  # Hardcoded!
pat_hour=0.0        # Hardcoded!
data_completeness=1.0  # Hardcoded!
```

### 3. **Silent Failures**
- When DLMO calculation fails, it returns None but gets converted to 0.0
- No user visibility into estimation confidence

### 4. **Missing Documentation**
- Users don't know this is model-based
- No explanation of confidence scores
- No citation of validation studies

## 📋 Action Plan: Option A Implementation

### Phase 1: Honest Naming (High Priority)
1. **Rename fields** throughout codebase:
   ```python
   # OLD
   dlmo_hour: float
   dlmo_confidence: float
   
   # NEW  
   estimated_dlmo_hour: float | None
   estimated_dlmo_confidence: float  # 0-1 from CircadianPhaseResult
   ```

2. **Update all references**:
   - Domain models
   - API responses  
   - Report generation
   - Test assertions

### Phase 2: Fix Confidence Calculation (High Priority)
1. **Use actual confidence from CircadianPhaseResult**:
   ```python
   # The calculator ALREADY provides confidence!
   result = self.dlmo_calculator.calculate_dlmo(...)
   if result:
       dlmo_confidence = result.confidence  # USE THIS!
   ```

2. **Calculate data_completeness properly**:
   - Already being worked on
   - Should reflect actual data availability

### Phase 3: Handle Failures Gracefully (High Priority)
1. **Return None, not 0.0**:
   ```python
   # When DLMO can't be calculated
   estimated_dlmo_hour=None
   estimated_dlmo_confidence=0.0
   ```

2. **Surface warnings to users**:
   - "Circadian phase estimation requires 3+ days of sleep data"
   - "Confidence: Low/Medium/High based on data quality"

### Phase 4: Documentation (Medium Priority)
1. **Add to CLAUDE.md**:
   ```markdown
   ## Circadian Phase Estimation (DLMO)
   
   Uses validated St. Hilaire/Forger mathematical model to estimate
   Dim Light Melatonin Onset from sleep/wake patterns.
   
   - Accuracy: ±2 hours in 76% of cases (Cheng 2021)
   - Requires: 3+ days of sleep data
   - Confidence: 0-1 score based on data quality and phase stability
   
   Note: This is a model-based estimation, not direct measurement.
   ```

2. **Update API docs** to clarify estimation vs measurement

### Phase 5: Enhance Reports (Low Priority)
1. **Show confidence visually**:
   ```
   Estimated Circadian Phase (DLMO): 21:30 [High Confidence]
   Based on 14 days of sleep/wake data
   ```

2. **Add tooltips/help text** explaining the estimation

## 🚫 What NOT to Do

1. **Don't remove DLMO estimation** - It's scientifically valid and useful
2. **Don't require light sensor data** - Activity alone works well  
3. **Don't claim it's "measured"** - Always clarify it's estimated
4. **Don't use 0.0 as default** - Use None for missing values

## ✅ Validation Checklist

Before marking this complete:
- [ ] All "dlmo_hour" renamed to "estimated_dlmo_hour"
- [ ] Confidence comes from CircadianPhaseResult, not hardcoded
- [ ] Failed calculations return None, not 0.0
- [ ] Documentation explains it's model-based
- [ ] Tests updated for new field names
- [ ] API schema reflects optional/estimated nature

## 🎓 Scientific References

1. Lim et al. (2024). "Accurately predicting mood episodes using wearable sleep and circadian rhythm features". npj Digital Medicine.

2. Cheng et al. (2021). "Predicting circadian misalignment with wearable technology". SLEEP.

3. St. Hilaire et al. (2007). "Addition of a non-photic component to a light-based mathematical model". J Theor Biol.

## Conclusion

**The implementation is scientifically sound**. We're using the best available methods for estimating DLMO from wearable data. The real issues are:
1. Misleading naming (easy fix)
2. Hardcoded confidence values (already have real ones available)
3. Poor error handling (return None, not 0.0)
4. Missing documentation (add explanation)

This is a **labeling and communication problem**, not a fundamental flaw. Fix the names, use the real confidence scores, handle errors properly, and document clearly. The math and science are solid.