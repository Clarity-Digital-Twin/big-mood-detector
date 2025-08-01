# CRITICAL PAT IMPLEMENTATION NOTES - READ THIS FIRST!!!

## THE TRUTH ABOUT OUR PAT PERFORMANCE

### ACTUAL HONEST PERFORMANCE (NO DATA LEAKAGE)
- **Validation AUC: 0.6708**
- **Test AUC: 0.5840** ← THIS IS THE REAL NUMBER
- **Paper claims: 0.625 test AUC**
- **Gap to close: 0.041**

### HISTORY OF CONFUSION
1. Original model claimed 0.5929 AUC but had TEST DATA IN TRAINING SET
2. Fixed the data leak → honest test AUC dropped to 0.5840
3. Extended training experiment got 0.5883 (slight improvement)

## CRITICAL IMPLEMENTATION DETAILS

### ✅ WHAT WORKS (USE THESE!)
- **PyTorch Implementation**: `src/big_mood_detector/infrastructure/ml_models/pat_pytorch.py`
- **Production Model**: `src/big_mood_detector/infrastructure/ml_models/pat_conv_depression_model.py`
- **Trained Weights**: `model_weights/pat/production/pat_conv_l_v0.5929.pth` (actually 0.5840 honest)

### ❌ WHAT'S BROKEN (AVOID!)
- `experiments/train_with_config.py` - doesn't load pretrained weights
- `experiments/train_with_pretrained.py` - wrong weight loading logic
- Any experiment that gets 0.5 AUC - it's not loading weights!

### 🔑 KEY ARCHITECTURE DETAILS
```python
# PAT-Conv-L Architecture (WHAT WORKS)
- Conv1D: kernel_size=9, stride=9, no padding
- Embedding dim: 96
- Transformer: 6 layers, 8 heads
- Classification head: 96 → 1
- Pretrained on 21k subjects (no NHANES overlap)
```

### ⚠️ PRETRAINED WEIGHTS FORMAT
The pretrained weights are in TensorFlow/Keras HDF5 format:
- Located at: `model_weights/pat/pretrained/PAT-L_21k_weights.h5`
- Contains transformer weights ONLY (no conv1d weights)
- Conv1D is initialized randomly (by design)

## HOW TO TRAIN PAT CORRECTLY

1. **Use the production implementation**:
   ```python
   from big_mood_detector.infrastructure.ml_models.pat_conv_depression_model import SimplePATConvLModel
   model = SimplePATConvLModel(model_size='large')
   ```

2. **Load pretrained transformer weights**:
   ```python
   success = model.encoder.load_tf_weights('model_weights/pat/pretrained/PAT-L_21k_weights.h5')
   ```

3. **Training settings that work**:
   - Learning rate: 0.001 (10x higher than paper)
   - Patience: 250 epochs
   - Log transform: YES (keep it!)
   - Optimizer: AdamW (no weight decay)

## EXPERIMENTS THAT ACTUALLY IMPROVED

| Experiment | Test AUC | What Changed |
|------------|----------|--------------|
| baseline | 0.5840 | Fixed data leak |
| extended_training | 0.5883 | LR=0.001, patience=250 |

## WHY OTHER EXPERIMENTS FAILED

- They used broken training scripts that don't load pretrained weights
- Without pretrained transformer, model starts from scratch → 0.5 AUC
- Paper's exact settings (WD=1e-4, beta2=0.95) made it worse

## NEVER FORGET

1. **The paper's 0.625 test AUC is our target**
2. **Our honest baseline is 0.5840 (gap: 0.041)**
3. **Always use the production PyTorch implementation**
4. **Always load pretrained transformer weights**
5. **Conv1D starts from random (this is correct)**

## TODO: CLOSE THE 0.041 GAP

Best ideas based on what worked:
1. Try LR in [0.0005, 0.002, 0.005] with patience=250
2. Add dropout tuning (current: 0.5, try: 0.3)
3. Try sqrt class weighting instead of linear
4. Ensemble multiple seeds

---
LAST UPDATED: 2025-08-01
NEVER DELETE THIS FILE