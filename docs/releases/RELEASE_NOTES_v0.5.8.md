# Release Notes - v0.5.8

## 🚀 New Features

### XML Data Scanning (Issue #64)
- **Fast data preview**: Scan large Apple Health exports in seconds instead of minutes
- **Feature availability checking**: Know exactly what predictions are possible before processing
- **User-friendly CLI**: New `--scan` flag for both `process` and `predict` commands
- **Auto-prompts**: Files over 100MB automatically suggest scanning first

## 🎯 User Experience Improvements

### Before v0.5.8:
```bash
$ python main.py predict export.xml --report
⚠️  Very large file: 520.1 MB
Processing may take 10+ minutes...
[... user waits 10 minutes ...]
✅ Clinical report saved

[User opens report]
HRV: N/A (no data)
Respiratory Rate: N/A (no data)
```

### With v0.5.8:
```bash
$ python main.py predict export.xml --scan

Scanning Apple Health data...
✅ Scan completed in 12.5 seconds

📊 Data Summary:
• Total records: 8,755,251
• Heart Rate: 5,074,424 records
• Step Count: 3,513,756 records
• Sleep Analysis: 3,608 records

✅ Available Features:
• depression_risk: Depression risk prediction (XGBoost)
• mania_risk: Mania/hypomania risk prediction (XGBoost)
• hrv_analysis: Heart rate variability trends

⚠️ Unavailable Features:
• respiratory_analysis: Missing required type: HKQuantityTypeIdentifierRespiratoryRate
```

## 🏗️ Technical Details

### New Components:
- `FeatureRequirements`: Clinical feature mappings
- `FeatureAvailability`: Scan results and availability checking
- Enhanced XML parsers with `count_records_by_type()` method
- Comprehensive test coverage for new functionality

### Performance:
- Scan 500MB+ files in 10-15 seconds
- Zero object allocation during scanning
- Memory-efficient streaming maintained

## 🐛 Bug Fixes
- Fixed type annotations in DataParsingService
- Added missing `count_records_by_type` to StreamingXMLParser for interface compatibility
- Fixed return type issue in CLI predict command

## 📝 Documentation
- Added detailed implementation notes
- Updated CLI help text
- Created integration test examples

## 🔧 Development
- Added `py.typed` marker for better type checking
- All tests passing
- Linting clean

---

This release significantly improves the user experience for processing large Apple Health exports by providing visibility into available data before committing to full processing.