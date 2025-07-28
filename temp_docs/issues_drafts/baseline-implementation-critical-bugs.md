## Personal baseline implementation has critical bugs and doesn't improve predictions

### Summary
The personal baseline calibration feature has critical bugs that corrupt user baselines and the personalized Z-scores aren't used by the models anyway. We should disable it by default for v0.5.0.

### Current Behavior
- Zero sleep hours corrupt baselines when data is missing
- Z-scores calculated incorrectly after baseline reload  
- Models trained on raw features, not personalized Z-scores
- Baselines provide no actual benefit to predictions

### Critical Bugs Found

1. **Zero-hour sleep corruption** (`advanced_feature_engineering.py:394`):
```python
sleep_hours = sleep.total_sleep_hours if sleep else 0  # BUG: corrupts baseline!
self._update_individual_baseline("sleep", sleep_hours)
```

2. **Baseline reload issues** - incremental statistics not properly initialized from loaded baselines

3. **Feature mismatch** - Models expect Seoul paper features (sleep_percentage_MN, etc.), not our Z-scores

### Evidence
- Test showed sleep Z-scores of -1.70 becoming +2.24 after reload
- HR Z-scores reached impossible -39.81 due to corruption
- Models don't use sleep_duration_zscore, activity_zscore, etc.

### Business Impact
- Users with `enable_personal_calibration=True` get WORSE predictions
- 6-12 weeks to properly implement vs 3 hours to disable
- No evidence from papers that personal baselines improve accuracy

### Recommended Solution

**For v0.5.0 (Immediate):**
1. Set `enable_personal_calibration=False` by default in PipelineConfig
2. Add warning in CLI when --user-id is used
3. Document as "experimental - not recommended"
4. Fix zero-value bug to prevent corruption

**For v0.6.0+ (Future):**
- Only revisit if users specifically request personalization
- Would require model retraining and 30+ days of data

### Code Changes Needed

1. In `process_health_data_use_case.py`:
```python
class PipelineConfig:
    enable_personal_calibration: bool = False  # Change default
```

2. In `advanced_feature_engineering.py:394-402`:
```python
# Only update baseline with valid data
if sleep and sleep.total_sleep_hours > 0:
    self._update_individual_baseline("sleep", sleep.total_sleep_hours)
    
if activity and activity.total_steps > 0:
    self._update_individual_baseline("activity", activity.total_steps)
```

3. In CLI help text:
```
--user-id: (Experimental - not recommended) Enable personal calibration
```

### Why This Matters
- **Data Quality**: Current implementation corrupts baselines
- **User Trust**: Bad personalization is worse than no personalization  
- **Focus**: Ship working predictions, not broken features
- **Maintenance**: Less code = fewer bugs

### References
- Full analysis: `/BASELINE_IMPLEMENTATION_ANALYSIS.md`
- Test results showing corruption: `/data/output/baseline_functionality_test_results.json`
- Neither XGBoost nor PAT papers use personal baselines

### Labels
- bug
- critical
- baseline
- data-quality
- v0.5.0-blocker

### Checklist
- [ ] Change default to `enable_personal_calibration=False`
- [ ] Fix zero-value corruption bug
- [ ] Add experimental warning to CLI
- [ ] Update documentation
- [ ] Remove baseline promotion from README