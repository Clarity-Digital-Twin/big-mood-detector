# XGBoost Models

## Status
XGBoost models from Seoul National University study have been converted from PKL to JSON format for security and portability.

## Models Included
The `converted/` directory contains:
- `XGBoost_DE.json` - Depression episode prediction (AUC 0.80)
- `XGBoost_ME.json` - Manic episode prediction (AUC 0.98)  
- `XGBoost_HME.json` - Hypomanic episode prediction (AUC 0.95)

These models expect 36 features as described in the Nature Digital Medicine paper.

## How to Obtain

### Option 1: Download Pre-trained (When Available)
```bash
# Future: Download from model registry
# curl -O https://models.bigmooddetector.com/xgboost/v1.0/models.tar.gz
# tar -xzf models.tar.gz -C model_weights/xgboost/pretrained/
```

### Option 2: Train Your Own
```python
from big_mood_detector.infrastructure.fine_tuning.population_trainer import PopulationTrainer

trainer = PopulationTrainer(task_name="depression")
trainer.train_xgboost(X_train, y_train)
trainer.save_model("model_weights/xgboost/production/depression_model.pkl")
```

## Integration Status

- ✅ PAT-Conv-L (0.5929 AUC) - Current state assessment
- ⏳ XGBoost - Future risk prediction (not required for MVP)
- 🔮 Temporal Ensemble - Combines both (future feature)

For MVP, we're using PAT-Conv-L only. XGBoost integration can be added later without breaking changes.