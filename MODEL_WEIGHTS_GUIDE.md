# Model Weights Guide

**Version**: v0.5.0  
**Last Updated**: July 27, 2025

## Overview

Big Mood Detector requires pre-trained model weights to function. This guide explains what model weights you need, where to get them, and how to set them up.

## Required Model Weights

### 1. PAT (Pretrained Actigraphy Transformer) Weights

**What**: Foundation model pretrained on 29k participants' actigraphy data  
**Source**: [Dartmouth PAT GitHub](https://github.com/njacobsonlab/Pretrained-Actigraphy-Transformer/)  
**Required Files**:
```
model_weights/pat/pretrained/
├── PAT-S_29k_weights.h5  (Small model - 285k params)
├── PAT-M_29k_weights.h5  (Medium model - 1.3M params)
└── PAT-L_29k_weights.h5  (Large model - 7.6M params)
```

**Download Instructions**:
1. Visit [PAT GitHub Releases](https://github.com/njacobsonlab/Pretrained-Actigraphy-Transformer/releases)
2. Download the pretrained weights (`.h5` files)
3. Place in `model_weights/pat/pretrained/`

### 2. Depression Detection Head

**What**: Fine-tuned classification head for depression detection  
**Training**: Trained on NHANES 2013-14 data  
**Required File**:
```
model_weights/production/
└── pat_conv_l_v0.5929.pth  (AUC 0.593 on NHANES)
```

**Note**: This file is included in the repository as it's our custom training.

### 3. XGBoost Models

**What**: Circadian rhythm models for mood episode prediction  
**Source**: [Seoul National University Study](https://github.com/mcqeen1207/mood_ml)  
**Required Files**:
```
model_weights/xgboost/converted/
├── XGBoost_DE.json   (Depression episodes)
├── XGBoost_HME.json  (Hypomanic episodes)
└── XGBoost_ME.json   (Manic episodes)
```

**Conversion from Original PKL Files**:
If you have the original `.pkl` files from the Seoul study:
```bash
python scripts/maintenance/convert_xgboost_models.py \
    --input-dir path/to/pkl/files \
    --output-dir model_weights/xgboost/converted
```

### 4. NHANES Scaler Statistics

**What**: Normalization statistics for consistent feature scaling  
**Required File**:
```
model_weights/production/
└── nhanes_scaler_stats.json
```

**Note**: This file is included in the repository.

## Quick Setup

```bash
# 1. Create directories
mkdir -p model_weights/pat/pretrained
mkdir -p model_weights/xgboost/converted
mkdir -p model_weights/production

# 2. Download PAT weights
# Visit: https://github.com/njacobsonlab/Pretrained-Actigraphy-Transformer/
# Download PAT-S_29k_weights.h5, PAT-M_29k_weights.h5, PAT-L_29k_weights.h5
# Place in model_weights/pat/pretrained/

# 3. Verify setup
python scripts/verify_setup.py
```

## Model Weight Sizes

| Model | Size | Purpose |
|-------|------|---------|
| PAT-S_29k_weights.h5 | ~1.1 MB | Small PAT model |
| PAT-M_29k_weights.h5 | ~5.2 MB | Medium PAT model |
| PAT-L_29k_weights.h5 | ~30.4 MB | Large PAT model (best accuracy) |
| pat_conv_l_v0.5929.pth | ~118 KB | Depression detection head |
| XGBoost_*.json | ~2-3 MB each | Mood episode prediction |

## Directory Structure

```
model_weights/
├── README.md                    # Model weights documentation
├── pat/
│   ├── pretrained/             # Original PAT foundation models
│   │   ├── PAT-L_29k_weights.h5
│   │   ├── PAT-M_29k_weights.h5
│   │   └── PAT-S_29k_weights.h5
│   └── pytorch/                # PyTorch training artifacts
│       └── archive/            # Old training runs
├── production/                 # Production-ready models
│   ├── nhanes_scaler_stats.json
│   ├── pat_conv_l_v0.5929.json
│   └── pat_conv_l_v0.5929.pth
└── xgboost/
    ├── converted/              # JSON format for deployment
    │   ├── XGBoost_DE.json
    │   ├── XGBoost_HME.json
    │   └── XGBoost_ME.json
    └── pretrained/             # Original PKL files (gitignored)
```

## Troubleshooting

### Missing PAT Weights
```
FileNotFoundError: PAT-L_29k_weights.h5 not found
```
**Solution**: Download from [PAT GitHub](https://github.com/njacobsonlab/Pretrained-Actigraphy-Transformer/)

### XGBoost Model Format Error
```
ValueError: Invalid XGBoost model format
```
**Solution**: Ensure you have JSON format, not PKL. Use conversion script if needed.

### Model Loading Failures
Run the verification script to check all models:
```bash
python scripts/verify_setup.py --check-models
```

## For Researchers

If you're training custom models:

1. **PAT Fine-tuning**: See `docs/training/PAT_DEPRESSION_TRAINING.md`
2. **XGBoost Training**: Original code at [mood_ml repo](https://github.com/mcqeen1207/mood_ml)
3. **Training Scripts**: Check `scripts/pat_training/`

## License Notes

- PAT weights: Check Dartmouth's license terms
- XGBoost models: Licensed under Seoul study terms
- Our fine-tuned models: Apache 2.0 (same as this project)