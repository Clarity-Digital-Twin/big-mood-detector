# User Documentation

> [← Back to main README](../../README.md)

Quick guides for using Big Mood Detector to analyze your health data.

## 🚀 Quick Links

- **[Quick Start Guide](QUICK_START_GUIDE.md)** - Get running in 5 minutes
- **[Apple Health Export](APPLE_HEALTH_EXPORT.md)** - Export your data correctly
- **[Fitbit Export](FITBIT_EXPORT.md)** - Use unzipped Fitbit exports correctly
- **[Advanced Usage](ADVANCED_USAGE.md)** - Power user features

## What You'll Learn

### Getting Started

- Installing with `pip install big-mood-detector`
- Using the `big-mood` CLI commands
- Processing your first health export
- Understanding prediction reports

### Data Export

- Exporting from iPhone (XML format)
- Using Health Auto Export app (JSON format)
- Using Fitbit unzipped export folders
- Handling large exports efficiently
- Privacy considerations

### Advanced Features

- Personal baseline calibration
- Batch processing multiple files
- Using the REST API
- Labeling episodes for improvement

## CLI Command Reference

```bash
# Process health data
big-mood process data/input/apple_export/export.xml

# Get predictions with report
big-mood predict data/input/apple_export/export.xml --report --output data/output/clinical_report_apple.txt

# Fitbit prediction (unzipped folder)
big-mood predict data/input/fitbit --report --output data/output/clinical_report_fitbit.txt

# Start API server
big-mood serve

# Watch for new exports
big-mood watch ~/HealthExports/

# Label mood episodes
big-mood label episode --type depressive --start 2024-01-15

# Train personal model
big-mood train --model xgboost --data features.csv
```

## Understanding Your Results

Reports show two complementary views:

- **Current State** (PAT) - Your mood right now based on past 7 days
- **Tomorrow's Risk** (XGBoost) - Prediction for next 24 hours

Both are important for different reasons. Current state helps you understand where you are, future risk helps you prepare.

## Need Help?

- Check the [Quick Start Guide](QUICK_START_GUIDE.md) first
- See [Advanced Usage](ADVANCED_USAGE.md) for complex scenarios
- Review the [main README](../../README.md) for overview
- File issues on [GitHub](https://github.com/Clarity-Digital-Twin/big-mood-detector/issues)

---

_For clinical context, see [Clinical Documentation](../clinical/README.md)_  
_For technical details, see [Developer Documentation](../developer/README.md)_
