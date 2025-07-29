# 🚀 Big Mood Detector - Quick Start Guide

This guide will help you get started with Big Mood Detector in 5 minutes.

## 📋 Prerequisites

- Python 3.12+
- Apple Health data (either XML export or JSON from Health Auto Export app)
- 8GB RAM minimum

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/Clarity-Digital-Twin/big-mood-detector.git
cd big-mood-detector

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e ".[dev,ml,monitoring]"
```

## 📊 Basic Usage - Process and Predict

### Step 1: Process Your Health Data

```bash
# Process JSON data (from Health Auto Export app)
big-mood process data/health_auto_export/

# Process Apple Health XML export
big-mood process data/apple_export/export.xml

# Process with date range
big-mood process data/health_auto_export/ \
    --start-date 2024-01-01 \
    --end-date 2024-03-31 \
    -o features.json
```

### Step 2: Generate Mood Predictions

```bash
# Basic prediction
big-mood predict data/health_auto_export/

# Generate detailed report
big-mood predict data/health_auto_export/ \
    --report \
    -o mood_report.txt

# Use ensemble model (XGBoost + PAT)
big-mood predict data/health_auto_export/ \
    --ensemble \
    -o predictions.json

# Use ensemble with temporal analysis and report
big-mood predict data/health_auto_export/ \
    --ensemble \
    --report \
    -o temporal_analysis.txt
```

## 📈 Example Output

### Basic Prediction Report
```
Big Mood Detector - Clinical Report
Generated: 2025-07-18 10:30:00

Period: 2024-01-01 to 2024-03-31
Days analyzed: 90

RISK SUMMARY:
- Depression Risk: MODERATE (0.65)
- Mania Risk: LOW (0.12)
- Hypomania Risk: LOW (0.18)

KEY FINDINGS:
✓ Sleep duration: 6.2 hours average (below optimal 7-9 hours)
✓ Sleep efficiency: 85% (normal)
✓ Activity level: 5,800 steps/day (normal range)
✓ Circadian rhythm: Mild phase delay detected

CLINICAL FLAGS:
⚠️ Decreased sleep duration trend over past 2 weeks
⚠️ Increased sleep fragmentation (3+ awakenings/night)

RECOMMENDATIONS:
- Monitor sleep patterns closely
- Consider sleep hygiene interventions
- Follow up if symptoms worsen
```

### Temporal Analysis Report (with --ensemble)
```
TEMPORAL MOOD ASSESSMENT (NOW vs TOMORROW)
-------------------------------------------
NOW (Current State - PAT):      65% [MODERATE]
TOMORROW (Future Risk - XGBoost):   42% [MODERATE]
Temporal Concordance:           75.0%

Pattern: Improving (current risk decreasing)

CLINICAL INSIGHTS:
- Current depression screening: MODERATE (PAT transformer)
- Tomorrow's predicted risk: MODERATE but decreasing
- High concordance (75%) indicates stable pattern
- Consider preventive interventions while risk is decreasing

DAILY PREDICTIONS WITH TEMPORAL CONTEXT:
2024-03-31:
  NOW:      65% [MODERATE]
  TOMORROW: 42% [MODERATE]
  Confidence: 89%
  
2024-03-30:
  NOW:      72% [HIGH]
  TOMORROW: 65% [MODERATE]
  Confidence: 91%
```

## 🏷️ Label Your Episodes (Optional)

Create ground truth labels for personalized model training:

```bash
# Label a depressive episode
big-mood label episode \
    --date-range 2024-01-15:2024-01-29 \
    --mood depressive \
    --severity moderate

# Label baseline (stable) period
big-mood label baseline \
    --date-range 2024-02-01:2024-02-28

# View your labels
big-mood label stats
```

## 🎯 Train a Personalized Model

Once you have labeled data:

```bash
# Prepare training data
big-mood process data/health_auto_export/ \
    -o training_features.csv

# Train personalized XGBoost model
big-mood train \
    --model-type xgboost \
    --user-id "user123" \
    --data training_features.csv \
    --labels my_labels.csv
```

## 🔄 Automatic Monitoring

Watch a directory for new health data files:

```bash
# Start file watcher
big-mood watch data/health_auto_export/

# The watcher will:
# - Detect new JSON/XML files
# - Automatically process them
# - Generate predictions
# - Save results to data/output/
```

## 🌐 API Server

Start the REST API for integrations:

```bash
# Start API server
big-mood serve --port 8000

# API will be available at http://localhost:8000
# Documentation at http://localhost:8000/docs
```

### Example API Usage

```bash
# Upload and process file
curl -X POST "http://localhost:8000/api/v1/upload/file" \
  -F "file=@sleep_data.json"

# Get predictions
curl "http://localhost:8000/api/v1/results/latest"
```

## 📁 Data Formats

### Health Auto Export JSON Format
Place your JSON files in `data/health_auto_export/`:
- `Sleep Analysis.json`
- `Heart Rate.json`
- `Step Count.json`
- `Heart Rate Variability.json`

### Apple Health XML Format
Place your `export.xml` in `data/apple_export/`

## 🚨 Clinical Thresholds

The system uses validated thresholds from research:
- **Depression**: PHQ-8 ≥ 10 equivalent
- **Mania**: ASRM ≥ 6 equivalent
- **Sleep Duration**: <3 hours (mania risk), >12 hours (depression risk)
- **Activity**: <5,000 steps (depression), >15,000 steps (mania)

## 🆘 Troubleshooting

### "No data found" Error
- Check your data is in the correct directory
- Ensure JSON files have the expected names
- For XML, ensure it's a valid Apple Health export

### "Model not found" Error
- Models are in `model_weights/xgboost/converted/`
- Run `make setup` to download models

### Memory Issues
- The streaming parser handles large files efficiently
- For very large exports, use date ranges to process in chunks

## 📚 Next Steps

- Read the [Clinical Documentation](../clinical/CLINICAL_DOSSIER.md) to understand the science
- Check the [API Documentation](../developer/API_REFERENCE.md) for integration
- See [Advanced Usage](./ADVANCED_USAGE.md) for complex workflows

## 🤝 Getting Help

- GitHub Issues: Report bugs or request features
- Documentation: Full guides in the `docs/` directory
- Clinical Questions: See clinical references in documentation

---

Remember: This tool provides risk assessments, not diagnoses. Always consult healthcare providers for clinical decisions.