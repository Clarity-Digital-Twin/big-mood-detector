# Training Numbers Comparison - Paper vs Our Implementation

## The Confusion Explained

You're right to be confused! Here's the clear breakdown:

### Paper's Numbers (from the paper)
- **Total with actigraphy + PHQ-9**: ~4,800
- **After split**:
  - Test: 2,000 (41.7%)
  - Train/Val: 2,800 (58.3%)
    - Train: ~2,240 (80% of 2,800)
    - Val: ~560 (20% of 2,800)

### Our BUGGY Implementation (what we had)
- **Total**: 4,103 (fewer due to stricter filtering)
- **Buggy split** (NO TEST SET!):
  - Train: 3,077 (75% of ALL data)
  - Val: 1,026 (25% of ALL data)
  - Test: 0 (THIS WAS THE BUG!)

### Our FIXED Implementation (what we just created)
- **Total**: 4,103 (same as before)
- **Proper split**:
  - Test: 1,711 (41.7% - matching paper proportion)
  - Train: 1,913 (46.6%)
  - Val: 479 (11.7%)

## Why the Confusion?

### 1. The Email Said "~2,800"
This was the paper's TRAINING set size (after removing test set).

### 2. We Had "3,077" 
This was our training set BUT it included what should have been test data!

### 3. The Real Comparison

| Dataset | Paper | Our Buggy | Our Fixed |
|---------|-------|-----------|-----------|
| Total samples | 4,800 | 4,103 | 4,103 |
| Test set | 2,000 (41.7%) | 0 (0%) | 1,711 (41.7%) |
| Train set | ~2,240 | 3,077 | 1,913 |
| Val set | ~560 | 1,026 | 479 |

## The Key Insight

**We had MORE training data (3,077) than the paper (2,240) because we were training on data that should have been held out for testing!**

This is why our performance seemed good (0.593) but we couldn't reach their 0.625:
- We were overfitting on "test" data
- We had no true held-out evaluation
- Our metrics were inflated

## Summary

### Before Fix:
- Train: 3,077 (includes test data) ❌
- Val: 1,026 ❌
- Test: 0 ❌

### After Fix:
- Train: 1,913 (LESS than paper's 2,240) ✅
- Val: 479 (similar to paper's ~560) ✅
- Test: 1,711 (proportional to paper's 2,000) ✅

### Why We Have Fewer Total:
- Paper: 4,800 total → 2,800 train/val
- Us: 4,103 total → 2,392 train/val

We have ~700 fewer samples overall, likely due to:
1. Stricter data quality filters
2. No medication data (we can't filter by it)
3. Some subjects dropped during extraction

But the PROPORTIONS are now correct!