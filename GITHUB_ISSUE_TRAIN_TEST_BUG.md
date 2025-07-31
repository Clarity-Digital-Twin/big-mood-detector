# GitHub Issue #86: CRITICAL - No Test Set in Model Training

## Summary
All our models have been trained WITHOUT a proper test set. The entire dataset (4,103 samples) was split only between train/val, with no held-out test data.

## Impact
- **All reported performance metrics are invalid**
- Current 0.593 AUC for PAT is inflated (no true evaluation)
- Cannot compare fairly with paper's 0.625 AUC
- Risk of overfitting to validation set

## Root Cause
The data preparation script (`prepare_nhanes_depression_correct.py`) creates a test set but then saves a different cache file (`nhanes_pat_data_subsetNone.npz`) WITHOUT the test set. All training scripts use this incomplete cache.

## Evidence
```python
# Current cache inspection
data = np.load('data/cache/nhanes_pat_data_subsetNone.npz')
print(list(data.keys()))
# Output: ['X_train', 'X_val', 'y_train', 'y_val']  # NO X_test!
```

## Fix Applied
Created `scripts/nhanes_fixes/fix_train_test_split.py` which properly splits:
- Test: 1,711 (41.7%) - matching paper proportion
- Train: 1,913 (46.6%)
- Val: 479 (11.7%)

New cache: `data/cache/nhanes_pat_data_with_test.npz`

## Action Items
- [ ] Update all training scripts to use new cache with test set
- [ ] Retrain all models with proper evaluation
- [ ] Use 21k pretrained weights (not 29k) to fix data leakage
- [ ] Report honest performance metrics

## Related Issues
- #85: PAT Data Leakage (using wrong pretrained weights)

## Severity
**CRITICAL** - Invalidates all current results

## Labels
`bug`, `critical`, `data-quality`, `machine-learning`