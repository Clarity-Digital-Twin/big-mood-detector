# PAT Training Comprehensive Findings

## Executive Summary

Based on thorough investigation of training logs, scripts, and email correspondence, we've identified multiple critical issues preventing us from achieving the target 0.625 AUC for depression detection:

1. **Data Leakage** (PRIMARY): Using 29k weights that include test data
2. **Implementation Differences**: Multiple deviations from paper's approach
3. **Early Stopping**: Model peaks at epoch 2 then declines

## Training Infrastructure Audit

### Current Training Scripts

```
scripts/pat_training/
├── train_pat_conv_l_simple.py  # Main training script (got 0.5929 AUC)
└── archive/                     # Historical attempts
```

### Training Log Analysis (pat_conv_l_v0.5929_20250725.log)

**Key Observations:**
- **Peak Performance**: Epoch 2 with 0.5929 AUC
- **Early Peak**: Indicates learning rate too high or model memorization
- **Performance Decline**: After epoch 2, AUC drops to 0.56-0.57 range
- **Training Duration**: ~2 hours on GPU
- **Data Stats**: 3,077 train / 1,026 val samples, 282/3077 positive (9.2%)

## Critical Implementation Differences

### 1. Pretrained Weights (CRITICAL BUG)

**Current (WRONG):**
```python
# Line 62: train_pat_conv_l_simple.py
weights_path = Path("model_weights/pat/pretrained/PAT-L_29k_weights.h5")

# Line 292: population_trainer.py  
base_model_path: str = "weights/PAT-S_29k_weights.h5",
```

**Should Be:**
```python
weights_path = Path("model_weights/pat/pretrained/PAT-L_21k_weights.h5")
base_model_path: str = "weights/PAT-S_21k_weights.h5",
```

**Available Correct Weights:**
- PAT-L_21k_weights.h5 ✅
- PAT-M_21k_weights.h5 ✅
- PAT-S_21k_weights.h5 ✅

### 2. Conv1D Implementation Differences

**Our Implementation:**
```python
# src/big_mood_detector/infrastructure/ml_models/pat_pytorch.py:38-40
kernel_size=patch_size,      # patch_size = 9
stride=patch_size,           # 9 (non-overlapping)
padding=0                    # No padding
```

**Paper's Implementation (from email):**
```python
layers.Conv1D(
    filters=embed_dim,       # embed_dim = 96
    kernel_size=3,          # DIFFERENT: 3 vs our 9
    padding='same',         # DIFFERENT: 'same' vs our 0
    activation='relu'       # DIFFERENT: ReLU vs our None
)
```

### 3. Data Preprocessing

**Our Pipeline:**
- Log(x+1) transform ❌ (Paper doesn't use this!)
- StandardScaler ✅ (Correct)

**Paper's Pipeline:**
- No log transform ✅
- StandardScaler only ✅

### 4. Training Hyperparameters

**Our Settings:**
- Learning rate: 1e-4 (might be too high)
- Early stopping patience: 10 epochs
- Optimizer: AdamW with cosine annealing

**Paper's Settings:**
- Early stopping patience: 250 epochs (!!)
- Best epoch at 2 suggests we need lower LR
- Consider 5e-5 or 1e-5

## Performance Analysis

### Current Results
- **Our best**: 0.5929 AUC (with data leakage)
- **Paper's PAT-Conv-L average**: 0.610 AUC (across all training sizes)
- **Paper's PAT-Conv-L at n=2,800**: 0.625 AUC (LP) / 0.624 AUC (FT)
- **Our target**: 0.625 AUC (correct and achievable!)

### Expected After Fixes
1. **Initial drop**: 0.55-0.58 AUC (removing data leakage)
2. **With corrections**: 0.60-0.62 AUC (approaching paper)
3. **Target**: 0.625 AUC (matching paper's n=2,800 result)

## Comprehensive Action Plan

### Phase 1: Fix Critical Bugs (IMMEDIATE)

```python
# 1. Update model loading to use 21k weights
def load_pat_model():
    if "2013-2014" in dataset_name:
        weights_file = f"PAT-{size}_21k_weights.h5"  # Exclude test data
    else:
        weights_file = f"PAT-{size}_29k_weights.h5"  # Full dataset OK

# 2. Remove log transform
# In data preprocessing pipeline:
# DELETE: data = np.log1p(data)
# KEEP: scaler.fit_transform(data)

# 3. Fix Conv1D parameters
self.conv = nn.Conv1d(
    in_channels=1,
    out_channels=embed_dim,
    kernel_size=3,           # Changed from 9
    stride=3,                # Adjust stride accordingly
    padding='same'           # PyTorch equivalent: padding=1
)
# Add ReLU activation after conv
```

### Phase 2: Training Protocol Updates

```python
# 1. Lower learning rates
learning_rates = [5e-5, 1e-5, 5e-6]  # Test multiple

# 2. Longer patience
early_stopping = EarlyStopping(patience=250, verbose=True)

# 3. More epochs
max_epochs = 500  # With early stopping

# 4. Better scheduler
scheduler = CosineAnnealingWarmRestarts(
    optimizer, T_0=50, T_mult=2, eta_min=1e-6
)
```

### Phase 3: Additional Improvements

1. **Data Augmentation**
   - Time shifting
   - Gaussian noise
   - Scaling variations

2. **Regularization**
   - Dropout layers (0.3-0.5)
   - Weight decay (0.01-0.1)
   - Gradient clipping

3. **Ensemble Methods**
   - Train PAT-S, PAT-M, PAT-L separately
   - Average predictions

## Training Script Location

Main training happens in:
```bash
# Simple training script that achieved 0.5929
python scripts/pat_training/train_pat_conv_l_simple.py

# Uses infrastructure from:
src/big_mood_detector/infrastructure/fine_tuning/population_trainer.py
src/big_mood_detector/infrastructure/ml_models/pat_pytorch.py
```

## NHANES Data Location

```
data/nhanes/2013-2014/
├── DEMO_H.xpt      # Demographics
├── DPQ_H.xpt       # Depression (PHQ-9)
├── PAXDAY_H.xpt    # Daily summary
├── PAXHD_H.xpt     # Header info
├── PAXMIN_H.xpt    # Minute-level activity
├── RXQ_DRUG.xpt    # Medications
└── RXQ_RX_H.xpt    # Prescriptions
```

## Model Weights Structure

```
model_weights/
├── pat/
│   ├── pretrained/
│   │   ├── PAT-L_21k_weights.h5  # USE THIS!
│   │   ├── PAT-L_29k_weights.h5  # WRONG - includes test
│   │   └── ...
│   ├── production/
│   │   └── pat_conv_l_v0.5929.pth  # Current best (with leakage)
│   └── pytorch/
└── xgboost/
```

## Key Takeaways

1. **Data leakage is blocking progress** - We must use 21k weights
2. **Implementation differs significantly** - Conv params, no log transform
3. **Training stops too early** - Need patience of 250+ epochs
4. **Target 0.625 is correct** - Paper achieved this with n=2,800 samples
5. **Initial performance drop expected** - This is healthy!

## Sample Size Note

- **Paper**: 4,800 total → 2,800 train + 2,000 test
- **Ours**: ~4,100 total → 3,077 train + 1,026 val
- **Difference**: We have ~277 more training samples (good!)
- **Reason**: Different data cleaning/exclusion criteria

## Recommended Training Command

```bash
# After implementing fixes:
python scripts/pat_training/train_pat_conv_l_fixed.py \
    --weights PAT-L_21k_weights.h5 \
    --no-log-transform \
    --conv-kernel 3 \
    --lr 5e-5 \
    --patience 250 \
    --epochs 500
```

## Next Steps

1. Create `train_pat_conv_l_fixed.py` with all corrections
2. Run ablation studies on each change
3. Document performance at each step
4. Update production model once improved

---

**Remember**: The 0.593 → 0.55 drop after fixing leakage is GOOD - it means we're evaluating honestly!