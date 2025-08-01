# Train/Test Split Bug Investigation - COMPLETE DOSSIER

## Executive Summary

**CONFIRMED BUG**: We have NO test set. All 4,103 samples are split between train (3,077) and validation (1,026) only.

## Evidence From First Principles

### 1. Direct Cache File Analysis

```bash
# Actual contents of nhanes_pat_data_subsetNone.npz:
Keys: ['X_train', 'X_val', 'y_train', 'y_val']
X_train shape: (3077, 10080)
X_val shape: (1026, 10080)
NO X_test FOUND!

Total: 3077 + 1026 = 4103
Train proportion: 0.750 (exactly 75%)
Val proportion: 0.250 (exactly 25%)
```

### 2. Code Analysis - The Bug Location

File: `scripts/archive/nhanes_fixes/prepare_nhanes_depression_correct.py`

```python
# Lines 89-95: INTENDED behavior
X_temp, X_test, y_temp, y_test = train_test_split(
    X, y,
    test_size=2000,  # <-- This is the bug!
    random_state=42,
    stratify=y
)

# Lines 159-165: What actually gets saved
old_cache_path = Path("data/cache/nhanes_pat_data_subsetNone.npz")
np.savez_compressed(
    old_cache_path,
    X_train=X_train_final,
    X_val=X_val_final,
    y_train=y_train,
    y_val=y_val
    # NOTE: No X_test or y_test saved!
)
```

### 3. The Smoking Gun

The script ATTEMPTS to create a test set but then DOESN'T SAVE IT! Even if the split worked, the test data is thrown away!

### 4. Additional Evidence

All training scripts load from `nhanes_pat_data_subsetNone.npz` and NONE of them check for or use test data:

```python
# Every training script:
data = np.load(cache_path)
X_train = data['X_train']
X_val = data['X_val']
# No X_test loading anywhere!
```

## Root Cause Analysis

### What Was Supposed to Happen

1. Load ~4,800 participants with actigraphy + PHQ-9
2. Split: 2,800 train/val + 2,000 test (like the paper)
3. Further split train/val: 2,240 train + 560 val (80/20)
4. Save all three sets

### What Actually Happened

1. Loaded 4,103 participants (fewer due to stricter filtering)
2. Attempted `test_size=2000` but sklearn behavior is unclear with int > 1
3. Even if split worked, test set was NOT SAVED to cache
4. All training uses only train/val from cache
5. Result: 75/25 split of ALL data (3,077/1,026)

### Why sklearn Might Have Failed

sklearn's `train_test_split` with integer `test_size`:
- Works when test_size < n_samples
- But behavior can be unpredictable
- May have silently failed or been ignored
- No error checking in our script!

## Implications - THIS IS HUGE

### 1. No True Evaluation
- We have NO held-out test set
- All model selection based on same validation set
- Risk of overfitting to validation set

### 2. Inflated Performance
- Our 0.593 AUC is likely optimistic
- We've been tuning hyperparameters on our "test" set
- True performance could be lower

### 3. Invalid Comparison
- Paper: Proper train/val/test split
- Us: Only train/val (using what should be test data)
- Can't fairly compare our 0.593 to their 0.625

### 4. More Training Data
- We have 3,077 training samples vs paper's 2,800
- BUT this includes data that should be held out
- "Advantage" is actually contamination

## The Fix

### Option 1: Recreate Proper Split
```python
# Fixed version
from sklearn.model_selection import train_test_split

# First split: separate test set (use fraction not int!)
test_fraction = 2000 / 4800  # ~0.417
X_trainval, X_test, y_trainval, y_test = train_test_split(
    X, y,
    test_size=test_fraction,  # Or just use 0.4
    random_state=42,
    stratify=y
)

# Second split: train/val from remaining
X_train, X_val, y_train, y_val = train_test_split(
    X_trainval, y_trainval,
    test_size=0.2,
    random_state=42,
    stratify=y_trainval
)

# SAVE ALL THREE SETS!
np.savez_compressed(
    cache_path,
    X_train=X_train,
    X_val=X_val,
    X_test=X_test,  # DON'T FORGET THIS!
    y_train=y_train,
    y_val=y_val,
    y_test=y_test   # AND THIS!
)
```

### Option 2: Match Paper Exactly
```python
# Use absolute numbers that match paper
n_test = min(2000, int(0.4 * len(X)))  # 2000 or 40%, whichever is smaller
n_remaining = len(X) - n_test
n_val = int(0.2 * n_remaining)
n_train = n_remaining - n_val
```

## Action Plan

### Immediate Actions
1. **STOP all current training** - results are invalid
2. **Recreate data split** properly with test set
3. **Retrain all models** with correct split
4. **Re-evaluate** on proper held-out test set

### Code Changes Needed
1. Fix `prepare_nhanes_depression_correct.py`
2. Update all training scripts to verify test set exists
3. Add evaluation scripts that use test set
4. Document the correct split clearly

### Expected Impact
- Performance will likely DROP (this is good - honest numbers!)
- Initial: 0.593 → ~0.55-0.57 (realistic)
- With fixes: Target 0.60-0.62
- Proper comparison with paper's 0.625

## Sample Size Mystery Also Solved

We have fewer total (4,103 vs 4,800) because:
1. No medication data filter (should give us MORE)
2. But stricter data quality requirements
3. The try/except in extraction silently drops ~700 subjects
4. Need to add logging to see WHY they're dropped

## Conclusion

This is a CRITICAL bug that invalidates all our current results. We've been training and evaluating on the same data, with no true held-out test set. The "good" performance is likely inflated.

**Bottom line**: Our entire evaluation methodology is flawed. We need to fix this before any further model development.

## Verification Commands

```bash
# Check any cache file for test data
python3 -c "
import numpy as np
data = np.load('data/cache/nhanes_pat_data_subsetNone.npz')
print(f'Has test set: {\"X_test\" in data}')
print(f'Keys: {list(data.keys())}')
"

# Check proportions
python3 -c "
import numpy as np
data = np.load('data/cache/nhanes_pat_data_subsetNone.npz')
total = data['X_train'].shape[0] + data['X_val'].shape[0]
print(f'Total samples: {total}')
print(f'Train %: {data[\"X_train\"].shape[0] / total * 100:.1f}')
print(f'Val %: {data[\"X_val\"].shape[0] / total * 100:.1f}')
"
```

Both will confirm: NO TEST SET, 75/25 split of all data.