# Action Plan: Closing the 0.041 Test AUC Gap

## Current Status
- **Our Test AUC**: 0.5840
- **Paper Test AUC**: 0.625  
- **Gap to Close**: 0.041

## Professional ML Experiment Structure ✅

Created a proper experiment tracking system:
```
experiments/
├── configs/           # Experiment configurations
├── runs/             # Timestamped run outputs  
├── results/          # Comparison tables
└── README.md         # Experiment guide
```

## Key Discrepancies Identified

From Franklin's email (Dartmouth PAT author):

| What | Paper | Ours | Priority |
|------|-------|------|----------|
| Pretrained weights | 21k (no NHANES 13-14) | ✅ Fixed | - |
| Conv1D kernel | 3 | 9 | HIGH |
| Conv1D padding | 'same' | 0 | HIGH |
| Conv1D activation | 'relu' | None | HIGH |
| Log(x+1) transform | NO | YES | HIGH |
| Early stop patience | 250 | 10-37 | MEDIUM |

## Experiment Priority

1. **fix_conv1d.yaml** - Just Conv1D fixes
2. **remove_log_transform.yaml** - Just remove log
3. **combined_fixes.yaml** - Everything together
4. **extended_training.yaml** - 250 patience

## How to Run Experiments

```bash
# Activate environment
source .venv-wsl/bin/activate

# Run experiment (creates modified training script)
python experiments/run_experiment.py experiments/configs/fix_conv1d.yaml

# Compare results
python experiments/compare_results.py
```

## What Each Experiment Tests

### Experiment A: Fix Conv1D
- Hypothesis: Architecture mismatch is main issue
- Expected gain: 0.01-0.02 AUC

### Experiment B: Remove Log Transform  
- Hypothesis: Unnecessary transform hurts learning
- Expected gain: 0.01-0.02 AUC

### Experiment C: Combined Fixes
- Hypothesis: All changes needed together
- Expected gain: 0.03-0.041 AUC

## Success Criteria
- Reproducible from config alone
- Clear tracking of what changed
- Steady progress toward 0.625
- Understanding which changes matter

## Next Immediate Steps
1. Run fix_conv1d experiment first
2. If < 0.02 improvement, try remove_log_transform
3. If still gap, run combined_fixes
4. Document learnings for each

The infrastructure is ready - now it's just systematic testing!