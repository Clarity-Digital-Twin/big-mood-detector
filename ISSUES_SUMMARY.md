# Production Issues Summary

## Critical Issues Found

### 1. ❌ **Timezone Type Mismatch** 
- **Error**: `TypeError: can't subtract offset-naive and offset-aware datetimes`
- **Impact**: Blocks ALL real data processing
- **Root Cause**: Parser outputs UTC-aware datetimes, feature extraction expects naive

### 2. ❌ **Duplicate Daily Predictions**
- **Symptom**: Same risk values (3.6%) repeated for each day
- **Impact**: Misleading report suggesting daily variation when there is none
- **Root Cause**: XGBoost makes ONE prediction per 30-day window, but we're displaying it daily

### 3. ⚠️ **Missing Window Information**
- **Symptom**: CDS report doesn't show which window was analyzed
- **Impact**: Users don't know what data period the prediction covers
- **Root Cause**: Window metadata not properly passed to report writer

### 4. ⚠️ **Timeout on Large Files**
- **Symptom**: 520MB files timeout after 2 minutes
- **Impact**: Cannot process real Apple Health exports
- **Root Cause**: Fixed 2-minute timeout too short for large files

### 5. ⚠️ **Confusing Model Availability**
- **Symptom**: When PAT can't run, report still shows PAT fields as "N/A"
- **Impact**: Unclear why certain models aren't available
- **Root Cause**: Report format assumes both models usually available

## What's Actually Happening

When you run the tool on sparse Apple Watch data:

1. ✅ Auto-window correctly finds a 30-day sparse window (e.g., Jan 1-31 with 65% coverage)
2. ✅ Correctly determines only XGBoost can run (PAT needs 7 consecutive days)
3. ❌ Crashes during feature extraction due to timezone mismatch
4. ❌ If it didn't crash, would show same prediction repeated 31 times
5. ⚠️ No clear indication of what window was analyzed

## The Conceptual Gap

**What we built**: A system assuming daily predictions from both models
**Reality**: XGBoost makes window-level predictions, PAT rarely has enough consecutive data

## Next Steps

1. Fix timezone issue (immediate blocker)
2. Redesign report for window-level predictions
3. Improve timeout and progress indication
4. Clear messaging about model availability

See `PRODUCTION_ISSUES_INVESTIGATION.md` for detailed analysis and `TDD_IMPLEMENTATION_PLAN.md` for the fix strategy.