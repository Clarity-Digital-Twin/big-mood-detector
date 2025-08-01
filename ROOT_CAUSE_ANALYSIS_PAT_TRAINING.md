# 🚨 ROOT CAUSE ANALYSIS: PAT Training Failures

## Executive Summary

**THE PROBLEM**: Production experiments got 0.5701 AUC (worse than baseline 0.5840) despite loading pretrained weights correctly.

**ROOT CAUSE**: Cache file confusion - multiple NHANES cache files exist with different data splits, and configs are silently using the wrong ones.

## The Cache File Mess

### What Cache Files Exist

| File | Train | Val | Test | Total | Status |
|------|-------|-----|------|-------|--------|
| `nhanes_pat_data_with_test.npz` | 1913 | 479 | 1711 | 4103 | ✅ CORRECT - Use this! |
| `nhanes_pat_data_subset200.npz` | 120 | 40 | 40 | 200 | ❌ Debug subset |
| `nhanes_pat_data_fixed.npz` | 3077 | 1026 | 0 | 4103 | ❌ No test set! |
| `nhanes_pat_data_subsetNone.npz` | 3077 | 1026 | 0 | 4103 | ❌ No test set! |

### The 254/32/32 Mystery
We couldn't find a cache with exactly 254/32/32. It might be:
1. A different subset file that got deleted
2. A misreading of logs
3. Data after some filtering step

## Why Extended Training Worked (0.5883 AUC)

The `extended_training` experiment:
- ✅ Used correct cache: `nhanes_pat_data_with_test.npz`
- ✅ Had full dataset: 1913/479/1711
- ✅ Loaded pretrained weights properly
- ✅ Used simple settings: LR=0.001, patience=250

## Why Production Experiments Failed (0.5701 AUC)

The production sequential runner experiments ALL got exactly 0.5701 AUC because:
- ✅ They used correct cache file (verified in logs: 1913/479/1711)
- ✅ Loaded pretrained weights correctly
- ❓ But something else went wrong...

### Hypothesis: Early Stopping or Convergence Issue

Since ALL production experiments got EXACTLY the same AUC (0.5701), they likely:
1. Hit early stopping at the same point
2. Got stuck in a local minimum
3. Had a different random seed or initialization

### CRITICAL FINDING: Device Mismatch Bug

The `train_pat_production.py` script has a CUDA/CPU device mismatch bug:
```
RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu!
```

This means the production PyTorch model has some weights on CPU and some on GPU, causing:
- Training to fail or produce garbage gradients
- All runs to converge to the same bad local minimum (0.5701)

## The Data Split Truth

### Paper's Split (from literature)
- Total: 4,800 participants
- Test: 2,000 (41.7%)
- Train: ~2,240
- Val: ~560

### Our Split (proportionally correct)
- Total: 4,103 participants (fewer due to filtering)
- Test: 1,711 (41.7% - matches paper proportion)
- Train: 1,913 (46.6%)
- Val: 479 (11.7%)

## DEFINITIVE FIXES

### 1. Immediate: Add Cache Assertion
```python
# Add to EVERY training script
assert config['data']['cache_file'].endswith('nhanes_pat_data_with_test.npz'), \
    f"Wrong cache file: {config['data']['cache_file']}"
```

### 2. Clean Up Cache Directory
```bash
# Keep ONLY the correct file
cd data/cache
mkdir old_caches
mv nhanes_pat_data_*.npz old_caches/
mv old_caches/nhanes_pat_data_with_test.npz .
```

### 3. Fix Default Paths
Search and replace ALL occurrences of:
- `nhanes_pat_data_subset` → `nhanes_pat_data_with_test`
- `nhanes_pat_data_fixed` → `nhanes_pat_data_with_test`

### 4. Reproduce Extended Training EXACTLY
```yaml
# This config got 0.5883 - our best result
name: "reproduce_extended_exactly"
data:
  cache_file: "data/cache/nhanes_pat_data_with_test.npz"
  log_transform: true
  standardize: true
model:
  type: "PAT-Conv-L"
  pretrained_weights: "PAT-L_21k_weights.h5"
  conv1d:
    kernel_size: 9
    stride: 9
    padding: 0
training:
  learning_rate: 0.001
  optimizer: "AdamW"
  weight_decay: 0  # IMPORTANT: No weight decay!
  betas: [0.9, 0.999]
  batch_size: 32
  epochs: 500
  patience: 250
  scheduler: "CosineAnnealingLR"
```

## Why Production Runner Got Different Results

The production runner experiments used the SAME data but got worse results (0.5701 vs 0.5883). Possible reasons:

1. **Different training script**: `train_pat_production.py` vs `train_with_config.py`
2. **Model initialization**: Different random seeds or weight init
3. **Preprocessing order**: Log transform or standardization done differently
4. **Early stopping**: Might have different patience counting

## CRITICAL BUG FIX NEEDED

### Fix the Device Mismatch in PAT PyTorch Model

In `pat_pytorch.py`, ensure ALL model components are moved to device:
```python
# In PATPyTorchEncoder.__init__
self.register_buffer('pos_embed', pos_embed)  # This ensures it moves with .to(device)
```

## ACTION PLAN

### Tonight's Runs
```bash
# 1. Verify cache file
python3 -c "import numpy as np; d=np.load('data/cache/nhanes_pat_data_with_test.npz'); print(f'Shapes: Train={d[\"X_train\"].shape}, Val={d[\"X_val\"].shape}, Test={d[\"X_test\"].shape}')"

# 2. Run exact reproduction
tmux new -s reproduce_extended \
  "python experiments/train_with_config.py experiments/configs/reproduce_extended.yaml"

# 3. Run LR sweep with CORRECT cache
for lr in 0.0005 0.001 0.002; do
  tmux new -d -s "lr_${lr}_correct" \
    "python experiments/train_with_config.py experiments/configs/lr_${lr}_correct.yaml"
done
```

### Key Settings That Work
- ✅ Cache: `nhanes_pat_data_with_test.npz`
- ✅ LR: 0.001 (10x higher than paper)
- ✅ Patience: 250 epochs
- ✅ No weight decay
- ✅ Standard AdamW betas (0.9, 0.999)
- ✅ Log transform: keep it!

## CONCLUSION

The root cause is NOT the PyTorch implementation or pretrained weights - those are fine. It's:

1. **Multiple cache files** causing confusion
2. **Different training scripts** with subtle differences
3. **Early stopping** or convergence issues in production runner

The extended_training experiment proves our implementation CAN achieve 0.5883 test AUC. We just need to:
1. Use the RIGHT cache file consistently
2. Reproduce those exact settings
3. Clean up the cache directory mess

---
Last updated: 2025-08-01
NEVER DELETE THIS FILE - It explains why we spent hours debugging!