# Changelog v0.5.6

## Release Date: 2025-07-29

## Overview
This release introduces intelligent auto-window selection for sparse Apple Health data, significantly improving usability for real-world datasets.

## ✨ Major Features

### Auto-Window Selection (`--auto-window`)
- **Smart Data Window Selection**: Automatically finds the best analysis window based on data density
- **Dual-Model Strategy**: Optimizes for both PAT (7 consecutive days) and XGBoost (30+ days, 50% coverage)
- **Sparse Data Handling**: Works with gaps in data (vacations, device changes, etc.)
- **CLI Integration**: Simple `--auto-window` flag for automatic optimization

### Window Selection Strategies
1. **SparseWindowStrategy**: For XGBoost - finds windows with ≥50% coverage
2. **DualModelWindowStrategy**: Balances requirements of both PAT and XGBoost models
3. **Intelligent Fallback**: Runs XGBoost-only when PAT requirements can't be met

## 🚀 Usage

```bash
# Automatic window selection
bigmood predict export.xml --auto-window

# Manual window selection still available
bigmood predict export.xml --date-range 2024-01-01:2024-12-31
```

## 📊 Technical Details

### Window Analysis Output
```
Analyzing data windows...
Found 335 days with data (50.0% coverage)
Max consecutive days: 25
Selected window: 2024-08-15 to 2025-07-15
Strategy: PAT requires 7 consecutive days (found 25 max). Running XGBoost only.
```

### Performance
- Efficient sliding window algorithm
- Minimal overhead (<1s for year of data)
- Memory-efficient implementation

## 🔧 Implementation Details

- Clean Architecture: Domain services for window selection
- Strategy Pattern: Extensible for future models
- Test Coverage: Comprehensive unit and integration tests
- Type-Safe: Full mypy compliance

## 📝 Documentation

- Updated CLI help text
- Added examples to README
- Comprehensive test suite
- Strategy documentation in code

## ⚠️ Known Limitations

- PAT requires exactly 7 consecutive days (strict requirement)
- XGBoost needs 30+ days with ≥50% coverage
- Window selection may fail with extremely sparse data

## 🐛 Bug Fixes

- Fixed date range validation
- Improved error messages for insufficient data
- Better handling of edge cases

## 🔜 Next Steps

- Progress indicators for large files
- Multiple window analysis (sliding windows)
- Confidence scoring based on data quality

---

For questions or issues, please open a GitHub issue.