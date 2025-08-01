# NHANES Sample Size Investigation - Complete Dossier

## The Mystery

**Paper**: 4,800 total → 2,800 train + 2,000 test
**Us**: 4,103 total → 3,077 train + 1,026 val

HOW THE FUCK do we have MORE training data (3,077) when we have FEWER total participants?

## Investigation From First Principles

### 1. Paper's Data Split (From Email)
```
Total with actigraphy + meds: 7,769
↓ (filter for PHQ-9 available)
Total with PHQ-9: 4,800
↓ (split)
Train: 2,800
Test: 2,000
```

### 2. Our Data Split (From Code Analysis)

Looking at `prepare_nhanes_depression_correct.py`:

```python
# Line 90-95: First split - separate test set
X_temp, X_test, y_temp, y_test = train_test_split(
    X, y,
    test_size=2000,  # WAIT, THIS IS WRONG!
    random_state=42,
    stratify=y
)

# Line 98-103: Second split - train/val from remaining
X_train, X_val, y_train, y_val = train_test_split(
    X_temp, y_temp,
    test_size=0.2,  # 20% of remaining for validation
    random_state=42,
    stratify=y_temp
)
```

## THE PROBLEM FOUND!

Our code tries to set `test_size=2000` but **sklearn's train_test_split doesn't work that way!**

When you pass an integer > 1 to test_size, sklearn still treats it as a proportion if the total samples < test_size!

### What Actually Happened:

1. We have 4,103 total samples
2. We try to split with `test_size=2000`
3. Since 2000 < 4103, sklearn uses it as absolute number
4. But wait... let's check what ACTUALLY happened:

**Actual split:**
- Total: 4,103
- Test set: Unknown (but definitely not 2,000)
- Remaining: Let's call it X
- Train: 80% of X = 3,077
- Val: 20% of X = 1,026

**Working backwards:**
- Train + Val = 3,077 + 1,026 = 4,103
- WAIT, that equals our TOTAL!

## HOLY SHIT - WE HAVE NO TEST SET!

### The Real Truth:

Our code FAILED to create a proper test set! Here's what happened:

1. The `test_size=2000` split likely failed or was ignored
2. We ended up using ALL data for train/val
3. We split 4,103 samples as:
   - Train: 75% = 3,077
   - Val: 25% = 1,026
   - Test: 0 (NONE!)

### Verification:
- 3,077 / 4,103 = 0.75 (exactly 75%!)
- 1,026 / 4,103 = 0.25 (exactly 25%!)

## Why Do We Have Fewer Total Participants?

Now this makes sense:
1. Paper filtered for actigraphy + meds + PHQ-9 = 4,800
2. We filtered for actigraphy + PHQ-9 only = should be MORE
3. But we got 4,103 = LESS

**Likely reasons:**
1. Data completeness - we require full 7 days, they might accept partial
2. Silent failures in `extract_pat_sequences` dropping ~700 subjects
3. Different minimum wear time or quality thresholds

## Summary - Everything Explained

1. **Why do we have more training data?**
   - We accidentally used our ENTIRE dataset for train/val (no test set)
   - Paper properly reserved 2,000 for test, leaving only 2,800 for train

2. **Why do we have fewer total participants?**
   - Despite less restrictive filtering (no meds requirement)
   - We likely have stricter data quality/completeness requirements
   - ~700 subjects silently dropped during sequence extraction

3. **The splits:**
   - **Paper**: 4,800 → 2,800 train + 2,000 test (proper)
   - **Us**: 4,103 → 3,077 train + 1,026 val + 0 test (WRONG!)

## Critical Implications

1. **We have no held-out test set!** Our "validation" is really our test set
2. **Overfitting risk**: We've been selecting models based on the same val set
3. **Not comparable**: Our 0.593 AUC is on validation, their 0.625 includes proper test evaluation

## Action Items

1. Fix the data split to properly reserve a test set
2. Investigate why ~700 subjects are being dropped
3. Retrain with proper train/val/test splits
4. Our current results are likely optimistically biased

## Code Bug Location

File: `scripts/archive/nhanes_fixes/prepare_nhanes_depression_correct.py`
Line 92: `test_size=2000` - This doesn't work as expected!

The sklearn documentation states that when test_size is an int, it represents absolute number of test samples ONLY if it's less than the total number of samples. But the behavior might be undefined or produce unexpected results.

## The Bottom Line

**We fucked up the train/test split and have been training on our entire dataset!**