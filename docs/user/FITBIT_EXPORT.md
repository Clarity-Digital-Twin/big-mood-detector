# 🏃 Fitbit Export Guide

> Using Apple Health XML instead? See [Apple Health Data Export Guide](APPLE_HEALTH_EXPORT.md).

## Overview

Big Mood Detector supports Fitbit exports when they are unzipped into the expected folder layout.
This workflow is designed for folder-based Fitbit exports (not a single XML file).

---

## 1) Get Fitbit Export Data

Export your Fitbit data from your Fitbit account as a ZIP archive, then unzip it locally.

After unzipping, copy the relevant folders/files into:

- `data/input/fitbit/`

---

## 2) Required Folder Layout

Expected structure:

```text
data/input/fitbit/
├── profile.json
├── activities/
│   └── steps-YYYY-MM-DD.json
├── heart_rate/
│   └── heart_rate-YYYY-MM-DD.json
└── sleep/
    └── sleep-YYYY-MM-DD.json
```

Minimum practical data for predictions:

- PAT window: 7 consecutive days
- XGBoost window: 30+ days with sufficient coverage

---

## 3) Validate Input Layout

### Windows PowerShell

```powershell
Get-ChildItem data/input/fitbit -Recurse -File
```

### macOS/Linux

```bash
find data/input/fitbit -type f
```

You should see daily files under `activities/`, `heart_rate/`, and `sleep/`.

---

## 4) Run Processing and Prediction

```bash
# Process Fitbit data
big-mood process data/input/fitbit

# Generate Fitbit clinical report (use explicit output name)
big-mood predict data/input/fitbit --report --output data/output/clinical_report_fitbit.txt
```

Docker example:

```bash
docker run --rm \
    -e BIGMOOD_DATA_DIR=/app/data \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/model_weights:/app/model_weights:ro" \
    big-mood-detector:latest \
    predict /app/data/input/fitbit --report --output /app/data/output/clinical_report_fitbit.txt
```

---

## 5) Output Files

- Fitbit report: `data/output/clinical_report_fitbit.txt`
- Apple report (separate): `data/output/clinical_report_apple.txt`

Using separate outputs avoids accidental overwrite between providers.

---

## 6) Troubleshooting

### "Total Records Processed: 0"

Check:

1. You passed folder path `data/input/fitbit` (not just `profile.json`)
2. Subfolders exist: `activities/`, `heart_rate/`, `sleep/`
3. Daily JSON files are present in those subfolders

### "Insufficient data for both models"

Usually means date coverage is too short or too sparse.
Add more recent daily exports and rerun.

### Output looks stale/old

Always pass explicit output:

```bash
--output data/output/clinical_report_fitbit.txt
```

---

## 7) Security & Privacy

- Keep Fitbit export data in `data/` (gitignored in this repo)
- Never commit personal health data
- Share only anonymized/synthetic samples in issues or PRs
