# End-to-End Testing Guide

## Overview
This guide helps verify Big Mood Detector works correctly with real data.

## Quick Test Commands

### 1. Basic Functionality Test
```bash
# Process last 30 days
big-mood process data/input/apple_export/export.xml --days-back 30

# Generate predictions with report
big-mood predict data/input/apple_export/export.xml --report
```

### 2. Performance Test
```bash
# Time the processing
time big-mood process export.xml --verbose
```

### 3. Memory Test
```bash
# Monitor memory usage
/usr/bin/time -v big-mood process large_export.xml
```

## Expected Results

### Processing Output
- Features saved to: `data/output/features.csv`
- Clinical report: `data/output/clinical_report.txt`
- Processing time: ~2 min for 500MB file

### Clinical Report Format
```
Depression Risk: X.X% [LOW/MEDIUM/HIGH]
Hypomanic Risk: X.X% [LOW/MEDIUM/HIGH]
Manic Risk: X.X% [LOW/MEDIUM/HIGH]
```

## Common Issues

### Missing Model Weights
- Error: "Model not found at model_weights/pat/production/"
- Solution: Download weights per [Model Weights Guide](../../MODEL_WEIGHTS_GUIDE.md)

### Memory Issues
- Error: "MemoryError" on large files
- Solution: Use --days-back to limit date range

### No Predictions
- Issue: All risks show 0% or N/A
- Check: Sufficient data (>7 days for PAT, >30 days for XGBoost)

## Full Test Suite
For comprehensive testing, see the [archived checklist](../archive/E2E_TESTING_CHECKLIST.md)