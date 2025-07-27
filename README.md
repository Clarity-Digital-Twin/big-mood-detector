# 🧠 Big Mood Detector

**Objective mood-episode risk from your Apple Watch — clinically informed, privacy-first, open-source.**

> **The clinical problem:** No objective tool exists for predicting mood episodes or distinguishing unipolar from bipolar depression or borderline personality disorder. Clinicians rely on subjective recall; patients often seek help after crises begin.

[![Version](https://img.shields.io/badge/version-0.5.0-blue)](CHANGELOG.md) [![Tests](https://img.shields.io/badge/tests-1230%20passing-brightgreen)](tests/) [![Coverage](https://img.shields.io/badge/coverage-72%25-yellow)](htmlcov/) [![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml) [![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

Big Mood Detector analyzes your Apple Health data to predict mood episode risk using AI. Two complementary models: 
- PAT transformer screens for current depression. 
- XGBoost predicts tomorrow's depression/mania/hypomania risk. 
Built by a clinical psychiatrist, implementing published research — runs 100% on-device, no cloud, no signup.

**Current status**: Research prototype — the first of its kind, but not yet clinically validated.

## Why Use Big Mood Detector?

**Our breakthrough**:
- **Early detection**: Spot mood episode risk before symptoms spiral
- **Two applications**: Current depression screening (PAT) + next-day episode prediction (XGBoost)
- **Objective data**: Complement clinical assessment with continuous behavioral biomarkers
- **Research foundation**: First implementation combining two breakthrough papers:
  - XGBoost: [Nature Digital Medicine 2024](https://github.com/KAIST-Behavioral-AI-Lab/MoodML_NatureDM2024)
  - PAT: [Dartmouth Foundation Model](https://github.com/Computational-Psychiatry/pat)
- **Privacy-first**: Runs entirely on your device — your data never leaves your machine

**For researchers**: Validate these approaches across populations, build the evidence base for digital mental health. See [PAT model training details](docs/training/PAT_DEPRESSION_TRAINING.md) for replication.

## 🚀 Quick Start

*Takes 2 minutes on any Mac/PC*

```bash
# 1. Install
pip install big-mood-detector

# 2. Export Apple Health data (Settings → Health → Export)
#    Place export.xml in: data/input/apple_export/

# 3. Analyze your data (research purposes)
big-mood predict data/input/apple_export/export.xml --report
```

See full output in `data/output/clinical_report.txt`

## How It Works

```
Your Apple Health Data
      ↓
┌─────────────────────┐
│   Past 7 Days       │ ← PAT (transformer) analyzes activity patterns
├─────────────────────┤
│   Past 30 Days      │ ← XGBoost models circadian rhythms  
└─────────────────────┘
      ↓
Research Risk Scores (Not Diagnostic)
```

PAT = transformer AI, XGBoost = gradient boosting, ensemble = enhanced reliability.

## Technical Features

| Component | Status | Performance |
|-----------|---------|-------------|
| Apple Health XML parsing | ✅ | 33MB/s, <100MB RAM |
| PAT transformer model | ✅ | 0.593 AUC depression (NHANES) |
| XGBoost circadian model | ✅ | 0.80-0.98 AUC (Korean cohort) |
| Privacy-first processing | ✅ | 100% local, no data sharing |
| Clinical feature extraction | ✅ | DSM-5 aligned thresholds |
| REST API | ✅ | Real-time predictions |

## Performance Benchmarks

**Processing Speed**:
- 365 days of data: 17 seconds
- Memory usage: <100MB for any file size
- Parsing throughput: 33MB/s

**Model Accuracy** (from original research):
- Current depression screening (PAT, general population):
  - Depression detection: 0.593 AUC (US NHANES 2013-14)¹
- Next-day episode prediction (XGBoost, mood disorder patients):
  - Depression episodes: 0.80 AUC (Korean cohort, MDD+BD patients)²
  - Manic episodes: 0.98 AUC (Korean cohort, BD patients)²
  - Hypomanic episodes: 0.95 AUC (Korean cohort, BD patients)²

¹Ruan et al., 2024 | ²Lim et al., 2024

## What Makes This Different

1. **Clinical innovation**: First open-source tool combining two state-of-the-art approaches to predict mood episodes from wearable data

2. **Scientific rigor**: Faithful implementation of published algorithms:
   - XGBoost circadian model from Seoul National University (Nature Digital Medicine 2024)
   - PAT transformer from Dartmouth (first foundation model for actigraphy)

3. **Privacy breakthrough**: No cloud dependency, no data collection — your mental health data stays private

4. **Open research**: Complete transparency enables validation, improvement, and trust

## ⚠️ Research Limitations

**Population specificity**:
- XGBoost: Trained on 168 Korean adults (18-35y) with mood disorders
- PAT: Pre-trained on 21,538 US adults, fine-tuned on 2,800 with PHQ-9 scores

**Performance constraints**:
- Current depression screening: Moderate accuracy (0.593 AUC)
- Next-day episode prediction: High accuracy but limited to Korean cohort (0.80-0.98 AUC)
- No validation across ethnicities, age groups, or comorbid conditions
- Research tool only — not FDA approved or clinically validated

## 📚 Documentation

| Audience | Start Here |
|----------|------------|
| **Users** | [Quick Start Guide](docs/user/QUICK_START_GUIDE.md) |
| **Developers** | [Architecture Overview](docs/developer/ARCHITECTURE_OVERVIEW.md) |
| **Researchers** | [Clinical Requirements](docs/clinical/CLINICAL_REQUIREMENTS_DOCUMENT.md) • [PAT Training Details](docs/training/PAT_DEPRESSION_TRAINING.md) |
| **AI Assistants** | [CLAUDE.md](CLAUDE.md) |

## Contributing

Critical research needs:
- 🏥 Clinical validation across diverse populations
- 🌍 Multi-ethnic, multi-age cohort studies
- 📱 Integration with additional wearable devices
- 🧪 Improving transformer model accuracy

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - Use freely, even commercially. See [LICENSE](LICENSE).

## Acknowledgments

Built on pioneering research:
- **XGBoost models**: Seoul National University, Korea University, KAIST ([Lim et al., 2024](https://doi.org/10.1038/s41746-024-01333-z))
- **PAT foundation model**: Dartmouth College ([Ruan et al., 2024](https://arxiv.org/abs/2411.15240))

---

**Have feedback?** Open an [issue](https://github.com/Clarity-Digital-Twin/big-mood-detector/issues) or see [discussions](https://github.com/Clarity-Digital-Twin/big-mood-detector/discussions).