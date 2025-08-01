# Experiment Tracking & Organization Plan

## Current Issues
1. Training outputs scattered across directories
2. No systematic experiment tracking
3. Hard to compare different runs
4. Risk of overwriting good models
5. Unclear which hyperparameters produced which results

## Professional ML Experiment Structure

```
experiments/
├── configs/                    # Experiment configurations
│   ├── baseline.yaml          # Our current best (0.5840 test)
│   ├── fix_conv1d.yaml        # kernel=3, padding=same
│   ├── remove_log_transform.yaml
│   └── combined_fixes.yaml    # All paper corrections
├── runs/                      # Experiment outputs
│   ├── 2025-08-01_baseline/
│   │   ├── config.yaml        # Copy of config used
│   │   ├── train.log
│   │   ├── metrics.json      # Val/test AUC, epochs, etc
│   │   ├── checkpoints/       # Model weights by epoch
│   │   └── plots/             # Training curves
│   └── 2025-08-01_fix_conv1d/
└── results/
    ├── comparison.md          # Side-by-side results
    └── best_models/           # Symlinks to best runs
```

## Key Discrepancies to Test

Based on Franklin's email vs our implementation:

| Component | Paper | Ours | Priority |
|-----------|-------|------|----------|
| Conv1D kernel | 3 | 9 | HIGH |
| Conv1D padding | 'same' | 0 | HIGH |
| Conv1D activation | 'relu' | None | HIGH |
| Log transform | NO | YES | HIGH |
| Early stop patience | 250 | 37 | MEDIUM |
| Pretrained weights | 21k | 29k | FIXED ✓ |

## Experiment Priority Order

1. **Experiment A**: Fix Conv1D (kernel=3, padding='same', relu)
   - Hypothesis: Major architecture difference causing gap
   
2. **Experiment B**: Remove Log(x+1) transform
   - Hypothesis: Unnecessary transform hurting performance
   
3. **Experiment C**: A + B combined
   - Hypothesis: Both needed together
   
4. **Experiment D**: Extend training (250 epoch patience)
   - Hypothesis: Undertrained model
   
5. **Experiment E**: All fixes combined
   - Target: 0.625 test AUC

## Implementation Plan

### Step 1: Create Experiment Infrastructure
```python
# experiments/run_experiment.py
import yaml
from pathlib import Path
from datetime import datetime

class ExperimentRunner:
    def __init__(self, config_path):
        self.config = yaml.load(open(config_path))
        self.run_dir = Path(f"experiments/runs/{datetime.now():%Y-%m-%d_%H%M%S}_{self.config['name']}")
        self.run_dir.mkdir(parents=True)
        
    def log_metrics(self, metrics):
        # Auto-save val/test AUC, hyperparams, etc
        pass
```

### Step 2: Config-Driven Training
```yaml
# experiments/configs/fix_conv1d.yaml
name: "fix_conv1d"
description: "Match paper Conv1D: kernel=3, padding=same, relu"

model:
  conv1d:
    kernel_size: 3
    padding: "same"
    activation: "relu"
    
data:
  log_transform: true  # Keep for now
  
training:
  patience: 50
  learning_rate: 0.0001
```

### Step 3: Automated Comparison
```python
# experiments/compare_results.py
def generate_comparison_table():
    """Creates markdown table of all experiments"""
    results = []
    for run_dir in Path("experiments/runs").iterdir():
        metrics = json.load(open(run_dir / "metrics.json"))
        results.append({
            "name": run_dir.name,
            "val_auc": metrics["best_val_auc"],
            "test_auc": metrics["test_auc"],
            "gap_to_paper": 0.625 - metrics["test_auc"]
        })
    # Generate markdown table
```

## Success Metrics
- Clear tracking of what was tested
- Reproducible experiments from configs
- Easy comparison of results
- No accidental overwrites
- Progress toward 0.625 test AUC

## Next Steps
1. Create directory structure
2. Move existing results to new structure
3. Create first config file
4. Run systematic experiments
5. Document findings