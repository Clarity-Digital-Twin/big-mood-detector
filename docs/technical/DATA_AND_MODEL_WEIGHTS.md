# Data and Model Weights Guide for OSS Contributors

**Version**: v0.5.0  
**Last Updated**: July 27, 2025

## ⚡ Quick Reference - What You Need

| What | Where to Get | Status | Use |
|------|--------------|--------|-----|
| **1. PAT Pretrained Weights** | [Dartmouth PAT Repo](https://github.com/njacobsonlab/Pretrained-Actigraphy-Transformer/) | External Download | Foundation model |
| **2. XGBoost Models (JSON)** | Already in repo | ✅ Included | Mood predictions |
| **3. Apple Health Export** | User provides their own | User Data | Input data |
| **4. Depression Head** | Private Google Drive | 🔒 Private (Clinical) | Depression detection |
| **5. NHANES Data** | CDC or Private Drive | Optional | Only for re-training |

## 📁 Required Directory Structure

```
big-mood-detector/
├── model_weights/
│   ├── pat/
│   │   ├── pretrained/              # Download PAT weights here
│   │   │   ├── PAT-L_29k_weights.h5 # Required (30.4 MB)
│   │   │   ├── PAT-M_29k_weights.h5 # Optional (5.2 MB)
│   │   │   └── PAT-S_29k_weights.h5 # Optional (1.1 MB)
│   │   └── production/              # Depression head (private)
│   │       ├── pat_conv_l_v0.5929.pth      # 🔒 Private - Request access
│   │       ├── pat_conv_l_v0.5929.json     # ✅ Already in repo
│   │       └── nhanes_scaler_stats.json    # ✅ Already in repo
│   └── xgboost/
│       └── converted/               # ✅ Already in repo
│           ├── XGBoost_DE.json
│           ├── XGBoost_HME.json
│           └── XGBoost_ME.json
└── data/
    ├── input/
    │   └── apple_export/
    │       └── export.xml          # User provides
    └── nhanes/                     # Optional - for re-training only
        └── 2013-2014/
            ├── PAXMIN_H.xpt        # Activity data (Required)
            ├── PAXDAY_H.xpt        # Day summaries (Required)
            ├── PAXHD_H.xpt         # Headers (Required)
            ├── DPQ_H.xpt           # Depression scores (Required)
            ├── DEMO_H.xpt          # Demographics (Optional)
            ├── RXQ_RX_H.xpt        # Medications (Optional)
            └── RXQ_DRUG.xpt        # Drug info (Optional)
```

## ⚠️ Important Note on Clinical Models

The Dartmouth team released PAT **foundation weights only** (encoder/backbone), not the fine-tuned clinical heads. This is deliberate:
- **Foundation models** = Research-safe feature extractors
- **Clinical heads** = Potential medical device regulatory concerns

Our depression detection head (`pat_conv_l_v0.5929.pth`) outputs clinical predictions and is therefore **not included in the public repository** to avoid regulatory/liability issues.

---

## Overview

This guide lists all external data and model weights required to run Big Mood Detector.

## Quick Start Checklist

### 1. User Data (Required for Testing)
- [ ] Apple Health export.xml (user provides their own)

### 2. Model Weights (Required for Predictions)
- [ ] PAT pretrained weights (external download)
- [x] PAT depression head (included in repo)
- [x] XGBoost models (included in repo)

### 3. Training Data (Optional - Only for Re-training)
- [ ] NHANES 2013-2014 datasets (external download)

---

## Detailed File Requirements

### 1. Apple Health Export Data

**Purpose**: User's personal health data for mood prediction  
**Required for**: Running predictions on personal data  
**Source**: User's own iPhone

```
data/input/apple_export/
└── export.xml  # Main health data file (50MB - 2GB typical)
```

**How to obtain**:
1. On iPhone: Health app → Profile → Export All Health Data
2. Transfer `export.zip` to computer
3. Extract and place `export.xml` in `data/input/apple_export/`

---

### 2. PAT Pretrained Weights (EXTERNAL DOWNLOAD REQUIRED)

**Purpose**: Foundation models pretrained on 29k participants  
**Required for**: All mood predictions  
**Source**: Dartmouth PAT Repository

```
model_weights/pat/pretrained/
├── PAT-S_29k_weights.h5  # Small (1.1 MB)
├── PAT-M_29k_weights.h5  # Medium (5.2 MB)
└── PAT-L_29k_weights.h5  # Large (30.4 MB) - REQUIRED for best accuracy
```

**Download options**:

Option A - Official Dartmouth Repository:
- Visit: https://github.com/njacobsonlab/Pretrained-Actigraphy-Transformer/releases
- Download the `.h5` files directly

Option B - Direct Google Drive (placeholder - maintainer to update):
```bash
# Placeholder links - will be updated by maintainer
PAT-L: https://drive.google.com/file/d/[PLACEHOLDER_PAT_L]/view
PAT-M: https://drive.google.com/file/d/[PLACEHOLDER_PAT_M]/view
PAT-S: https://drive.google.com/file/d/[PLACEHOLDER_PAT_S]/view
```

Option C - HuggingFace (future):
```bash
# Coming soon - maintainer setting up HF repository
huggingface-cli download big-mood/pat-weights --local-dir model_weights/pat/pretrained/
```

---

### 3. Fine-tuned Depression Head (PRIVATE - NOT IN REPO)

**Purpose**: Depression detection trained on NHANES  
**Status**: 🔒 Private distribution only (clinical model)
**Why private**: Outputs clinical depression predictions - potential regulatory concerns

```
model_weights/pat/production/
├── pat_conv_l_v0.5929.pth      # PyTorch weights (24.3 MB) - PRIVATE
├── pat_conv_l_v0.5929.json     # Model metadata - ✅ In repo
└── nhanes_scaler_stats.json    # Normalization stats - ✅ In repo
```

**Access for contributors** (placeholder - maintainer to update):
```bash
# Request access via email with research use case
# Google Drive (restricted access):
https://drive.google.com/file/d/[PLACEHOLDER_DEPRESSION_HEAD]/view
```

**Alternative**: Train your own using provided scripts:
```bash
python scripts/pat_training/train_depression_head.py \
    --nhanes-dir data/nhanes/2013-2014 \
    --output-dir model_weights/pat/production
```

---

### 4. XGBoost Models (INCLUDED IN REPO)

**Purpose**: Circadian rhythm-based mood episode prediction  
**Status**: ✅ Already included (converted from Seoul study)

```
model_weights/xgboost/converted/
├── XGBoost_DE.json   # Depression episodes (2.8 MB)
├── XGBoost_HME.json  # Hypomanic episodes (2.5 MB)
└── XGBoost_ME.json   # Manic episodes (2.6 MB)
```

**Original source**: https://github.com/mcqeen1207/mood_ml (PKL format)  
**Note**: We include pre-converted JSON versions for compatibility

---

### 5. NHANES Training Data (OPTIONAL - Only for Re-training)

**Purpose**: Training custom depression detection models  
**Required for**: Re-training PAT depression head only  
**Source**: CDC NHANES 2013-2014 (held out from PAT pretraining)

```
data/nhanes/2013-2014/
├── PAXMIN_H.xpt    # ⭐ Minute-level activity (CORE REQUIREMENT)
├── PAXDAY_H.xpt    # ⭐ Day summaries (CORE REQUIREMENT) 
├── PAXHD_H.xpt     # ⭐ Device headers (CORE REQUIREMENT)
├── DPQ_H.xpt       # ⭐ PHQ-9 depression scores (CORE REQUIREMENT)
├── DEMO_H.xpt      # Demographics (optional enrichment)
├── RXQ_RX_H.xpt    # Medications (for SSRI/benzo tasks)
└── RXQ_DRUG.xpt    # Drug details (for SSRI/benzo tasks)
```

**Core files needed for depression training**:
1. **PAXMIN_H.xpt** - Contains 10,080 minutes of activity per participant
2. **PAXDAY_H.xpt** - Links minutes to calendar days
3. **PAXHD_H.xpt** - Device metadata and wear validation
4. **DPQ_H.xpt** - PHQ-9 scores (labels for depression)

**Download from CDC**:
1. Visit: https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component=Examination&CycleBeginYear=2013
2. Download these specific files:
   - Physical Activity Monitor → PAXDAY_H, PAXMIN_H, PAXHD_H
   - Mental Health Depression Screener → DPQ_H
   - Demographics → DEMO_H
   - Prescription Medications → RXQ_RX_H, RXQ_DRUG

**Google Drive bundle** (placeholder - maintainer to update):
```bash
# All required NHANES files in one zip
https://drive.google.com/file/d/[PLACEHOLDER_NHANES_BUNDLE]/view
```

---

## Automated Download Script (Coming Soon)

```bash
# Future helper script
python scripts/download_required_files.py --pat --nhanes

# Or selective download
python scripts/download_required_files.py --pat-only
```

---

## File Size Summary

| Component | Size | Required | Included in Repo |
|-----------|------|----------|------------------|
| PAT Pretrained | ~37 MB total | Yes | No - External |
| Depression Head | ~25 MB | Yes | Yes |
| XGBoost Models | ~8 MB | Yes | Yes |
| NHANES Data | ~200 MB | No (training only) | No - External |
| Apple Health | 50MB-2GB | Yes (user's own) | No - User provides |

**Total external downloads needed**:
- **For basic use**: ~37 MB (PAT weights only)
- **For full depression detection**: ~61 MB (PAT + depression head via private access)
- **For re-training**: ~200 MB (above + NHANES data)

---

## Verification

After downloading all files, verify your setup:

```bash
python scripts/verify_setup.py --check-all
```

Expected output (without depression head):
```
✅ PAT pretrained weights found
⚠️  Depression head not found (private model - request access if needed)
✅ XGBoost models found
✅ Basic model weights verified
```

Expected output (with depression head access):
```
✅ PAT pretrained weights found
✅ Depression head weights found
✅ XGBoost models found
✅ All model weights verified
```

---

## For Maintainers

### Setting up HuggingFace Repository

1. Create HuggingFace account
2. Create new model repository: `big-mood/model-weights`
3. Upload structure:
```
big-mood/model-weights/
├── pat-pretrained/
│   ├── PAT-L_29k_weights.h5
│   ├── PAT-M_29k_weights.h5
│   └── PAT-S_29k_weights.h5
├── pat-finetuned/
│   └── pat_conv_l_v0.5929.pth
└── nhanes-2013-2014/
    └── nhanes_2013_2014_required.zip
```

4. Update this guide with actual HF download commands

### Google Drive Structure

Create shareable links with these folders:
- `PAT_Pretrained_Weights/` - Contains all 3 PAT .h5 files
- `Depression_Head_Production/` - Complete production folder backup
- `NHANES_2013_2014_Bundle/` - All required NHANES .xpt files

---

## License Compliance

- **PAT Weights**: MIT License (Dartmouth)
- **NHANES Data**: Public Domain (US Government)
- **XGBoost Models**: Check Seoul study license
- **Our Fine-tuned Models**: Apache 2.0

Always respect the original licenses when redistributing.