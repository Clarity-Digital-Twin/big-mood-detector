# PAT TRAINING PIPELINE - THE DEFINITIVE GUIDE

## STOP! READ THIS FIRST

This document exists because we wasted HOURS on broken training scripts.
Follow this EXACTLY or you'll get 0.5 AUC (random predictions).

## THE ONLY PIPELINE THAT WORKS

### 1. Data Preparation
```python
# Already done - cached at:
data/cache/nhanes_pat_data_with_test.npz

# Contains HONEST train/val/test split (no leakage!)
# Train: 254 subjects
# Val: 32 subjects  
# Test: 32 subjects
```

### 2. Model Architecture
```python
from big_mood_detector.infrastructure.ml_models.pat_conv_depression_model import SimplePATConvLModel

# This is the ONLY model that works properly
model = SimplePATConvLModel(model_size='large')

# Architecture:
# - Conv1D: kernel=9, stride=9 (NOT 3!)
# - Transformer: 6 layers, 8 heads, embed_dim=96
# - Head: Linear(96, 1)
```

### 3. Pretrained Weights
```python
# Load transformer weights (Conv1D stays random)
success = model.encoder.load_tf_weights('model_weights/pat/pretrained/PAT-L_21k_weights.h5')

# CRITICAL: This loads ONLY transformer weights
# Conv1D is initialized randomly (by design)
```

### 4. Training Settings That Work
```yaml
training:
  learning_rate: 0.001  # 10x higher than paper!
  optimizer: "AdamW"
  weight_decay: 0      # No weight decay!
  betas: [0.9, 0.999]  # Standard betas
  batch_size: 32
  epochs: 500
  patience: 250        # Long patience crucial
  scheduler: "CosineAnnealingLR"

data:
  log_transform: true  # KEEP THIS!
  standardize: true
```

### 5. The ONLY Training Script That Works
```bash
python experiments/train_pat_production.py <config.yaml>
```

## WHAT DOESN'T WORK (AVOID!)

### ❌ Broken Scripts
- `train_with_config.py` - no pretrained weights
- `train_with_pretrained.py` - wrong weight format
- Any script that gets 0.5 AUC

### ❌ Bad Settings
- Paper's optimizer (WD=1e-4, beta2=0.95) → worse
- Low learning rate (0.0001) → slow/poor
- Short patience (10-30) → underfits
- No log transform → worse performance

## PERFORMANCE TRACKING

| Version | Val AUC | Test AUC | Notes |
|---------|---------|----------|-------|
| Buggy | 0.6024 | 0.5929 | Had test data in training! |
| Honest | 0.6708 | 0.5840 | Fixed split, real baseline |
| Extended | 0.6474 | 0.5883 | LR=0.001, patience=250 |
| Target | - | 0.6250 | Paper's claimed performance |

**Current gap: 0.625 - 0.5883 = 0.0367**

## HOW TO RUN NEW EXPERIMENTS

### 1. Create Config
```yaml
# experiments/configs/my_experiment.yaml
name: "my_experiment"
model:
  type: "PAT-Conv-L"
  pretrained_weights: "PAT-L_21k_weights.h5"
  conv1d:
    kernel_size: 9  # DON'T CHANGE
    stride: 9       # DON'T CHANGE
data:
  log_transform: true  # KEEP!
  standardize: true
  cache_file: "data/cache/nhanes_pat_data_with_test.npz"
training:
  learning_rate: 0.002  # Try 0.0005-0.005
  patience: 250         # Keep high!
  # ... other settings
```

### 2. Run with Production Script
```bash
python experiments/train_pat_production.py experiments/configs/my_experiment.yaml
```

### 3. Monitor Progress
```bash
# Watch training
tail -f experiments/runs/*/training.log | grep AUC

# Compare results
python experiments/compare_results.py
```

## SYSTEMATIC EXPERIMENT PLAN

To close the 0.0367 gap:

1. **Learning Rate Sweep**: [0.0005, 0.002, 0.005]
2. **Dropout Tuning**: [0.3, 0.7] vs current 0.5
3. **Class Weights**: Try sqrt(pos/neg)
4. **Multi-seed Ensemble**: Average 5 runs

Use the sequential runner:
```bash
python experiments/sequential_runner_production.py
```

## CRITICAL REMINDERS

1. **ALWAYS use production PyTorch implementation**
2. **ALWAYS load pretrained transformer weights**
3. **NEVER change Conv1D architecture (k=9)**
4. **KEEP log transform enabled**
5. **Use patience >= 250**

## IF YOU GET 0.5 AUC

You're not loading pretrained weights! Check:
1. Using `train_pat_production.py`?
2. Weights file exists at path?
3. See "Loading pretrained weights" in log?
4. Model has `load_tf_weights()` call?

---
**This pipeline is the result of painful trial and error.**
**Follow it exactly or suffer the consequences.**

Last updated: 2025-08-01
Never delete this file.