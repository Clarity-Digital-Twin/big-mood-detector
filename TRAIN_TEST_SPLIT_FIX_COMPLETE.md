# Train/Test Split Bug - FIXED

## Summary

**BUG CONFIRMED AND FIXED**: We had NO test set. All 4,103 samples were incorrectly split between train/val only.

## What Was Wrong

1. **No Test Set**: Cache file `nhanes_pat_data_subsetNone.npz` contained only train/val splits
2. **Wrong Split**: 75% train (3,077) / 25% val (1,026) of ALL data
3. **Hidden Bug**: The preparation script created a test set but then saved a version WITHOUT it
4. **All Training Affected**: Every model trained used the buggy cache

## Evidence

```python
# Original cache inspection
data = np.load('data/cache/nhanes_pat_data_subsetNone.npz')
print(data.keys())  # ['X_train', 'X_val', 'y_train', 'y_val'] - NO TEST!
```

## The Fix Applied

Created proper split matching paper's methodology:
- **Test**: 1,711 samples (41.7%) - HELD OUT
- **Train**: 1,913 samples (46.6%)
- **Val**: 479 samples (11.7%)

New file: `data/cache/nhanes_pat_data_with_test.npz`

## Next Steps

### 1. Update All Training Scripts
Replace:
```python
cache_path = Path("data/cache/nhanes_pat_data_subsetNone.npz")
```

With:
```python
cache_path = Path("data/cache/nhanes_pat_data_with_test.npz")
# And load X_test, y_test
```

### 2. Retrain All Models
- PAT-Conv-L with correct split
- Use 21k weights (not 29k) to avoid data leakage
- Evaluate ONLY on test set

### 3. Expected Impact
- Performance will DROP (this is good - honest evaluation)
- Current: 0.593 AUC (inflated, no test set)
- Expected: ~0.55-0.57 AUC (realistic)
- Target: 0.60+ with proper training

## Verification

```bash
# Check new cache has test set
python3 -c "
import numpy as np
data = np.load('data/cache/nhanes_pat_data_with_test.npz')
print(f'Has test set: {\"X_test\" in data}')
print(f'Test size: {data[\"X_test\"].shape}')
"
```

## Scripts Created

1. `scripts/nhanes_fixes/fix_train_test_split.py` - Creates proper split
2. `scripts/pat_training/train_pat_conv_l_corrected.py` - Training with correct data

## Critical Insight

Our 0.593 AUC was achieved by:
1. Training on what should be test data
2. Using 29k pretrained weights that include our test years (data leakage)
3. No held-out evaluation

The paper's 0.625 AUC used:
1. Proper train/val/test split
2. 21k pretrained weights (no leakage)
3. Evaluation on true held-out test set

This explains why we couldn't reach 0.625 - we were already overfitting!