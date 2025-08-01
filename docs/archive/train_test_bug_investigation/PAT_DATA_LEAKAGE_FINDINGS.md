# PAT Fine-Tuning Data Leakage - Critical Findings

## Executive Summary

We have discovered a **critical data leakage issue** in our PAT depression head fine-tuning that explains why we cannot exceed 0.593 AUC. We're using PAT models pretrained on 29k participants (which includes NHANES 2013-2014) and then fine-tuning on the same NHANES 2013-2014 data for depression detection. This violates fundamental ML principles and creates overly optimistic results.

## The Data Leakage Problem

### Current State (INCORRECT)
- **Pretrained weights**: PAT-L_29k_weights.h5 (includes NHANES 2013-2014)
- **Fine-tuning dataset**: NHANES 2013-2014 PHQ-9 depression labels
- **Result**: Model has already "seen" the test data during pretraining

### Email Confirmation
From the PAT authors:
> "For NHANES data, we actually used the PAT models trained with (21k participants) instead of (29k participants)"
> 
> "This dataset excludes participants from 2013-2014 NHANES so that there wouldn't be data leakage during the finetuning/evaluation period."

### Impact
1. **Inflated performance**: Our 0.593 AUC may be artificially high
2. **Limited improvement**: The model can't learn new patterns - it's already memorized the data
3. **Invalid evaluation**: We're not truly testing generalization

## Code Evidence

### 1. Current Model Loading (WRONG)
```python
# src/big_mood_detector/infrastructure/ml_models/pat_model.py:137
weights_path = Path(env_dir) / f"PAT-{size_suffix}_29k_weights.h5"

# Lines 383-385
"small": "PAT-S_29k_weights.h5",
"medium": "PAT-M_29k_weights.h5", 
"large": "PAT-L_29k_weights.h5",
```

### 2. Population Trainer Default (WRONG)
```python
# src/big_mood_detector/infrastructure/fine_tuning/population_trainer.py:292
base_model_path: str = "weights/PAT-S_29k_weights.h5",
```

## Solution: Use 21k Weights

### Available Correct Weights
We already have the correct pretrained weights:
- `PAT-L_21k_weights.h5` - Excludes NHANES 2013-2014
- `PAT-M_21k_weights.h5` - Excludes NHANES 2013-2014
- `PAT-S_21k_weights.h5` - Excludes NHANES 2013-2014

### Required Changes
1. Update model loading logic to use 21k weights
2. Retrain depression head from scratch with 21k base
3. Re-evaluate performance metrics

## Other Findings from Email

### 1. No Log Transform
> "We did not use a Log(x+1) transform, though you are on the money for using StandardScaler!"

Our current pipeline uses log transform - this might be hurting performance.

### 2. Conv1D Differences
PAT authors use:
```python
layers.Conv1D(
    filters=embed_dim,  # embed_dim = 96
    kernel_size=3,
    padding='same',
    activation='relu'
)
```

We use:
- kernel_size=9
- padding=0
- No activation

### 3. Training Protocol
- **Early stopping patience**: 250 epochs (we might be stopping too early)
- **Best epoch at 2**: Suggests our learning rate might be too high
- **Lower learning rate**: Consider reducing from 1e-4

### 4. Performance Expectations
> "Our best performance for the depression task was actually only an AUC of 0.610 for PAT Conv-L"

**CRITICAL CLARIFICATION**: This 0.610 is the AVERAGE across all training sizes (500, 1000, 2500, 2800). 
Looking at Supplemental Table 5, for n=2,800 training samples:
- **PAT Conv-L (FT)**: 0.624 AUC
- **PAT Conv-L (LP)**: 0.625 AUC

So our target of 0.625 AUC is correct! We're currently at 0.593 with data leakage.

## Action Plan

### Phase 1: Fix Data Leakage (CRITICAL)
1. [ ] Update all model loading code to use 21k weights
2. [ ] Create configuration flag for weight selection
3. [ ] Document the data leakage issue prominently

### Phase 2: Retrain Depression Head
1. [ ] Train new depression head using PAT-L_21k as base
2. [ ] Remove log transform from preprocessing
3. [ ] Adjust Conv1D parameters to match paper
4. [ ] Use longer early stopping patience (250 epochs)
5. [ ] Try lower learning rates (5e-5, 1e-5)

### Phase 3: Additional Improvements
1. [ ] Implement proper cross-validation
2. [ ] Try ensemble of different PAT sizes
3. [ ] Experiment with data augmentation
4. [ ] Add regularization (dropout, weight decay)

## Expected Outcomes

After fixing data leakage:
- **Initial drop**: Performance may decrease to ~0.55-0.58 AUC
- **Target**: Achieve 0.625 AUC (matching paper's n=2,800 result)
- **Honest baseline**: Valid for clinical deployment

## Sample Size Discrepancy Explained

**Email states**: 
- "The big dataset we used was the original 7,769 participants who provided actigraphy and medication data"
- "we had 4,800 total [with PHQ-9], and reserved 2000 for the test set, leaving us with 2,800 in the training set"

**We have**: 3,077 train / 1,026 val (total ~4,103)

**Key Difference Identified**: 
- **Paper**: Required actigraphy AND medication data → 7,769 → then filtered to 4,800 with PHQ-9
- **Us**: Required only actigraphy AND PHQ-9 → ~4,100 total
- We likely didn't filter by medication data availability

**Result**:
- Paper has more participants total (4,800 vs 4,103) 
- But we have MORE training data (3,077 vs 2,800) due to different train/test split
- This is actually beneficial for us!

**Important Note**: It's counterintuitive that we have FEWER participants without the medication requirement. This suggests we likely have additional filtering:
- Stricter data completeness requirements (all 7 days?)
- Higher wear time thresholds
- Silent failures in `extract_pat_sequences` dropping ~700 subjects
- Worth investigating but doesn't affect our ability to compare results

## Connection to Issue #60

**Issue #60**: "Fine-tune PAT-Conv-L to reach 0.625 AUC for depression (3.2% gap)"
- Current status: 0.5929 AUC (stuck)
- Target: 0.625 AUC
- **Root cause**: Data leakage preventing improvement

This data leakage discovery **explains why we can't close the 3.2% gap**. We've been trying various techniques but the model has already memorized the test data during pretraining!

## GitHub Issue Draft

**Title**: Critical: PAT Fine-Tuning Uses Wrong Pretrained Weights (Data Leakage)

**Description**: 
We've discovered why we can't improve PAT depression detection beyond 0.593 AUC (Issue #60). We're using PAT models pretrained on 29k participants which **includes NHANES 2013-2014**, then fine-tuning on the same NHANES 2013-2014 dataset. This creates severe data leakage.

**The PAT authors confirmed**:
> "For NHANES data, we actually used the PAT models trained with (21k participants) instead of (29k participants). This dataset excludes participants from 2013-2014 NHANES so that there wouldn't be data leakage."

**Impact**:
- Model has memorized test data during pretraining
- Cannot learn new patterns or improve
- Current 0.593 AUC is artificially inflated
- Blocks Issue #60 resolution

**Solution**:
1. Switch to 21k pretrained weights (we already have them)
2. Retrain depression head from scratch
3. Expect initial performance drop (this is good!)
4. Target realistic 0.60-0.61 AUC

**Related to**: #60 

**Priority**: CRITICAL - This affects all PAT-based predictions and blocks further improvements

---

## Implementation Differences Summary

### What We Do (Wrong)
1. **Pretrained weights**: 29k (includes test data)
2. **Log transform**: Applied (paper doesn't use)
3. **Conv1D**: kernel=9, no activation, padding=0
4. **Early stopping**: Too early (we stop at epoch 2)

### What Paper Does (Correct)
1. **Pretrained weights**: 21k (excludes test data)
2. **No log transform**: Just StandardScaler
3. **Conv1D**: kernel=3, ReLU activation, padding='same'
4. **Early stopping**: Patience of 250 epochs

## Key Takeaways

1. **Data leakage is real**: We've been evaluating on data the model saw during pretraining
2. **Performance will drop initially**: This is expected and healthy
3. **0.593 → 0.61 is achievable**: With proper training on clean data
4. **Transparency matters**: We need to document this clearly for users

This finding explains why we plateaued at 0.593 AUC and couldn't improve further. The model had already memorized the test set!

## Next Steps

1. **Create new GitHub issue** documenting the data leakage
2. **Update Issue #60** explaining why we can't reach 0.625 with current setup
3. **Fix model loading** to use 21k weights
4. **Retrain everything** with correct configuration
5. **Update documentation** to warn about this issue