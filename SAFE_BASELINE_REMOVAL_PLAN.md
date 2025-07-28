# Safe Baseline Removal Plan with TDD

**Date:** July 28, 2025  
**Approach:** Test-Driven Refactoring to ensure nothing breaks

## Files That Use BaselineRepository

### Core Files (9 files)
1. `domain/repositories/baseline_repository_interface.py` - The interface
2. `infrastructure/repositories/file_baseline_repository.py` - File implementation
3. `infrastructure/repositories/timescale_baseline_repository.py` - DB implementation
4. `infrastructure/repositories/baseline_repository_factory.py` - Factory
5. `infrastructure/di/container.py` - Dependency injection
6. `application/use_cases/process_health_data_use_case.py` - Uses baseline
7. `application/adapters/orchestrator_adapter.py` - Adapter layer
8. `domain/services/advanced_feature_engineering.py` - Feature engineering
9. `domain/services/clinical_feature_extractor.py` - Clinical features

## TDD Approach: Test First, Then Remove

### Step 1: Create Golden Test
```bash
# Create test that captures current behavior
cat > tests/test_golden_behavior.py << 'EOF'
"""
Golden test to ensure behavior doesn't change during refactoring.
Run this before and after each removal step.
"""

import json
from pathlib import Path
from datetime import date

def capture_prediction_behavior():
    """Capture current prediction output as golden reference."""
    
    # Test data
    test_file = "tests/fixtures/minimal_export.xml"
    
    # Run prediction
    from big_mood_detector.interfaces.cli.main import app
    from typer.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(app, ["predict", test_file, "--output", "golden_output.json"])
    
    # Save output
    with open("golden_behavior.json", "w") as f:
        json.dump({
            "exit_code": result.exit_code,
            "output": result.stdout,
            "predictions": json.loads(Path("golden_output.json").read_text()) if result.exit_code == 0 else None
        }, f, indent=2)
    
    return result.exit_code == 0

if __name__ == "__main__":
    if capture_prediction_behavior():
        print("✓ Golden behavior captured")
    else:
        print("✗ Failed to capture behavior")
EOF
```

### Step 2: Create Removal Tests
```bash
# Test that verifies baseline is NOT used
cat > tests/test_baseline_not_used.py << 'EOF'
"""
Tests to verify BaselineRepository is not actually used.
"""

def test_xgboost_runs_without_baseline():
    """XGBoost should work without BaselineRepository."""
    from big_mood_detector.application.pipelines.xgboost_pipeline import XGBoostPipeline
    # Mock and verify no baseline calls
    
def test_aggregation_uses_rolling_window():
    """AggregationPipeline should use rolling windows, not baseline."""
    from big_mood_detector.application.services.aggregation_pipeline import AggregationPipeline
    # Verify calculate_statistics is used
    
def test_no_baseline_in_critical_path():
    """Critical prediction path should not touch baseline."""
    # Trace execution path
    # Verify no baseline imports
EOF
```

### Step 3: Iterative Removal Process

#### 3.1 Remove from Tests First
```bash
# Remove test files (safe - won't break production)
rm tests/unit/infrastructure/repositories/test_*baseline*.py
rm tests/integration/storage/test_baseline*.py

# Run golden test
python tests/test_golden_behavior.py
# Should still pass
```

#### 3.2 Remove from DI Container
```python
# In infrastructure/di/container.py, comment out:
# - baseline_repository provider
# - Any references in other providers

# Run golden test again
```

#### 3.3 Remove from Use Cases
```python
# In process_health_data_use_case.py:
# 1. Remove baseline_repository parameter
# 2. Remove persist_baselines() calls
# 3. Test after each change
```

#### 3.4 Remove Core Files
```bash
# Only after all references removed:
rm src/big_mood_detector/domain/repositories/baseline_repository_interface.py
rm src/big_mood_detector/infrastructure/repositories/*baseline*.py
```

## Safe Refactoring Checklist

### Before Each Removal
- [ ] Run `python tests/test_golden_behavior.py`
- [ ] Save output to `before_change.txt`
- [ ] Create git commit

### After Each Removal
- [ ] Run `python tests/test_golden_behavior.py`
- [ ] Compare with `before_change.txt`
- [ ] Run pytest on affected modules
- [ ] Commit if tests pass

### Critical Tests to Run
```bash
# After each step, run:
export TESTING=1

# Unit tests for core functionality
pytest tests/unit/application/services/test_aggregation_pipeline.py -v
pytest tests/unit/infrastructure/ml_models/test_xgboost_models.py -v

# Integration tests
pytest tests/integration/test_xgboost_feature_mismatch.py -v

# CLI smoke test
big-mood predict tests/fixtures/minimal_export.xml
```

## Verification Tools

### 1. Coverage Analysis
```bash
# See what code is actually executed
coverage run -m pytest tests/integration/test_xgboost_*.py
coverage report -m | grep baseline
# Should show 0% coverage for baseline files
```

### 2. Import Analysis
```python
# Check if baseline is imported anywhere critical
import sys
import importlib

critical_modules = [
    "big_mood_detector.application.pipelines.xgboost_pipeline",
    "big_mood_detector.application.services.aggregation_pipeline",
]

for module in critical_modules:
    mod = importlib.import_module(module)
    if any("baseline" in str(v) for v in sys.modules.values()):
        print(f"WARNING: {module} may depend on baseline")
```

### 3. Grep Verification
```bash
# After removal, verify no references remain
grep -r "baseline_repository\|BaselineRepository" src/ --include="*.py" | grep -v test
# Should return nothing
```

## Rollback Plan

### If Something Breaks
```bash
# Tag before starting
git tag before-baseline-removal

# If needed, rollback
git reset --hard before-baseline-removal
```

### Keep Archive Branch
```bash
# Before deletion, create archive
git checkout -b archive/baseline-repository
git add -A
git commit -m "Archive baseline repository before removal"
git checkout main
```

## Success Criteria

1. **All tests pass** - No test failures
2. **Predictions unchanged** - Golden test outputs match
3. **Performance improved** - Faster execution
4. **Code cleaner** - No dead code warnings
5. **Documentation updated** - No mentions of baseline repository

## Timeline

1. **Hour 1**: Set up golden tests and verification
2. **Hour 2**: Remove from tests and DI
3. **Hour 3**: Remove from use cases
4. **Hour 4**: Remove core files and verify
5. **Hour 5**: Update documentation

Total: ~5 hours of careful refactoring