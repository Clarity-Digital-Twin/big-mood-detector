# Changelog v0.5.7

## Release Date: 2025-07-30

## Overview
This release addresses critical production issues discovered during real-world testing of the auto-window selection feature, improving robustness and user experience.

## 🐛 Bug Fixes

### Timezone Handling
- **Fixed**: TypeError with timezone-aware vs naive datetime operations
- **Solution**: Implemented `TimezoneContract` to ensure all datetimes are naive (UTC) throughout the domain layer
- **Impact**: All real Apple Health export files now process correctly

### Window-Level Predictions
- **Fixed**: Duplicate daily predictions in XGBoost-only mode
- **Solution**: Added proper window-level aggregation for sparse data scenarios
- **Impact**: Clinical reports now show accurate single predictions for entire analysis windows

### Cross-Platform Compatibility
- **Fixed**: Windows WSL2 timeout handling using SIGALRM
- **Solution**: Implemented platform-aware timeout with graceful degradation on Windows
- **Impact**: Windows users can now process large files without crashes

## ✨ New Features

### Dynamic Timeout
- Small files (<50MB): 2-minute timeout
- Medium files (50-200MB): 5-minute timeout  
- Large files (>200MB): No timeout
- Clear progress messages for user awareness

### Enhanced Clinical Reports
- Added DATA WINDOW SELECTION section showing:
  - Window period and coverage percentage
  - Model availability reasoning
  - Data quality indicators
- Window-level vs daily analysis clearly differentiated

### Summary Calculator Service
- Refactored overall summary calculation into dedicated service
- Improved code organization and testability
- Consistent handling of daily vs window predictions

## 📊 Technical Improvements

### Test Coverage
- Added regression tests for PAT-only scenarios
- Added unit tests for all new features
- Coverage maintained at 73% with fast test suite

### Code Quality
- Centralized timezone conversion in parsers
- Removed code duplication in summary calculations
- All mypy type errors resolved
- Ruff linting clean

## 🔧 Configuration

### Required Model Files
No changes to model requirements from v0.5.4

### Dependencies
No new dependencies added

## 📝 Documentation

### Updated Files
- CLAUDE.md: Updated version and capabilities
- Added comprehensive production issue documentation
- TDD implementation plan for all fixes

## 🚀 Upgrade Instructions

```bash
# Update code
git pull origin main

# Reinstall (no new dependencies)
pip install -e ".[dev,ml,monitoring]"

# Run tests
export TESTING=1
make test
```

## ⚠️ Breaking Changes
None

## 🔜 Next Steps
- Performance benchmarking on 500MB+ files
- Progress bar implementation for better UX
- Coverage improvements to reach 75%+

---

For questions or issues, please open a GitHub issue.