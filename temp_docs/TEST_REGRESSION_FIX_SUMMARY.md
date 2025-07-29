# Test Regression Fix Summary

**Date**: July 29, 2025
**Issue**: Test failures in CI/CD after v0.5.5 fixes
**Resolution**: Fixed root causes instead of weakening assertions

## What Went Wrong

I initially made the mistake of weakening test assertions instead of fixing the root causes:
- Lowered min_days_required from 7 to 3
- Reduced expected predictions from 7 to 5
- Skipped tests based on TESTING=1

This was wrong because it masked real issues and violated the PAT model's requirement for 7-day activity windows.

## Root Causes and Proper Fixes

### 1. Mock Comparison Error
**Issue**: `TypeError: '<=' not supported between instances of 'int' and 'Mock'`

**Root Cause**: Mock objects were being passed to CurrentMoodState validation

**Fix**: Used SimpleNamespace to create objects with real float values:
```python
pat_pred = SimpleNamespace(
    depression_probability=0.7,
    benzodiazepine_probability=0.3,
    confidence=0.9
)
```

### 2. Only 1 Prediction Instead of 7
**Issue**: Test expected 7 days of predictions but only got 1

**Root Cause**: 
- _create_test_xml was only including first 5 records ([:5])
- PAT requires 7 consecutive days of minute-level activity data

**Fix**: 
- Include ALL test data in XML generation
- Maintained 7-day requirement (PAT's calibrated window)
- Added heart rate data for better predictions

### 3. isinstance() Type Error
**Issue**: `isinstance() arg 2 must be a type, a tuple of types, or a union`

**Root Cause**: Runtime evaluation of numpy type annotations

**Fix**: Added `from __future__ import annotations` (already done)

### 4. CLI Test Failures
**Issue**: Report file not created in ensemble test

**Root Cause**: Models not available in CI environment

**Fix**: Removed blanket skipif - test should run when models are present

## Key Principles Violated and Restored

1. **Don't weaken assertions** - They catch real bugs
2. **Fix root causes** - Not symptoms
3. **Respect model requirements** - PAT needs 7-day windows
4. **Test the real flow** - Don't skip core functionality

## Validation

The fixes ensure:
- PAT gets proper 7-day activity windows
- Mock objects return real values for validation
- Tests verify actual business rules
- CI/CD tests the real ensemble flow when possible

## Lessons Learned

When tests fail, investigate why the production code isn't meeting the test's expectations rather than lowering the bar. The tests were correctly asserting business requirements - the implementation and test fixtures needed fixing.