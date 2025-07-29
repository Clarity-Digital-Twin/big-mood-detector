# Release v0.5.3 - Smart Window Selection & Critical Fixes

## 🎯 Highlights

This release fixes critical bugs that prevented predictions for users with sparse Apple Watch data. The system now intelligently finds valid data windows and provides meaningful feedback.

## 🐛 Bug Fixes

### Date Window Selection Bug (#67)
- **Problem**: System only checked last 7 days, causing 0 predictions despite having valid historical data
- **Solution**: Implemented smart window selection strategies that scan all available data
- **Impact**: Users with sporadic Apple Watch usage can now get predictions

### PAT Integration in CLI (#68)
- **Problem**: PAT model loaded but wasn't connected through dependency injection
- **Solution**: CLI now properly passes DI container when `--ensemble` flag is used
- **Impact**: Temporal separation (NOW vs TOMORROW) works as designed

### XML Date Filter Bug (#38)
- **Problem**: TypeError when filtering large XML files by date range
- **Solution**: Fixed date/datetime comparison in FastStreamingXMLParser
- **Impact**: Faster parsing with date filters, no more crashes

### Misleading Density Warnings (#69)
- **Problem**: "1.5% density" warnings even when user had valid dense windows
- **Solution**: Calculate density within analysis window, not entire data span
- **Impact**: Accurate warnings that reflect actual data availability

## ✨ New Features

### Smart Window Selection
```bash
# Automatically find best data window
big-mood predict export.xml --auto-find-window --report

# Choose window selection strategy
big-mood predict export.xml --window-strategy best --report
```

### Temporal Ensemble in CLI
```bash
# Get NOW (PAT) vs TOMORROW (XGBoost) predictions
big-mood predict export.xml --ensemble --verbose
```

## 📊 Technical Improvements

- 15 new tests added using Test-Driven Development
- Clean code with minimal mocking
- Backward compatibility maintained
- All tests passing (1,245 tests)
- Type checking and linting clean

## 🔧 For Developers

The `WindowSelectionStrategy` pattern provides extensible window finding:
```python
from big_mood_detector.domain.services.window_selection_strategy import (
    MostRecentValidWindowStrategy,
    BestQualityWindowStrategy,
    AllValidWindowsStrategy
)
```

## 🚀 Upgrade Instructions

```bash
pip install --upgrade big-mood-detector==0.5.3
```

Or with Docker:
```bash
docker pull big-mood-detector:v0.5.3
```

## 📝 Compatibility

- Backward compatible with v0.5.x
- Python 3.12+ required
- No model retraining needed

## 🙏 Acknowledgments

Thanks to our trial run testers who identified these critical issues with real-world Apple Health data spanning 6+ years.