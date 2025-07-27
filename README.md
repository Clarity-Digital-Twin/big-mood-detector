# 🧠 Big Mood Detector

**Predict mood episodes from your wearable data — clinically informed, privacy-first, open-source.**

[![Version](https://img.shields.io/badge/version-0.5.0-blue)](CHANGELOG.md) [![Tests](https://img.shields.io/badge/tests-1230%20passing-brightgreen)](tests/) [![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](htmlcov/) [![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml) [![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

Big Mood Detector analyzes your Apple Health data to predict mood episode risk using AI. Two complementary models work together: PAT transformer screens for current depression while XGBoost predicts tomorrow's risk.

**Status**: Production-ready for research use. Not yet clinically validated.

[📊 Project Status](PROJECT_STATUS.md) | [🚀 Quick Start](#-quick-start) | [📚 Documentation](#-documentation) | [🤝 Contributing](CONTRIBUTING.md)

## Why Big Mood Detector?

**The Problem**: Mood episodes often escalate before clinical intervention. Current tools rely on subjective recall and intermittent assessments.

**Our Solution**:
- **Early Detection**: Identify risk patterns before symptoms spiral
- **Dual Approach**: Current state (PAT) + future risk (XGBoost)
- **Research Foundation**: Implements breakthrough papers from Nature Digital Medicine & Dartmouth
- **Privacy-First**: 100% local processing - your data never leaves your device

## 🚀 Quick Start

*2 minutes to insights*

```bash
# Install
pip install big-mood-detector

# Export Apple Health data
# iPhone: Settings → Health → Export All Health Data
# Place export.xml in: data/input/apple_export/

# Analyze (research purposes only)
big-mood predict data/input/apple_export/export.xml --report
```

See full output? Check `data/output/clinical_report.txt`

**Need help?** → [User Guide](docs/user/QUICK_START_GUIDE.md)

## How It Works

```
Your Health Data → Feature Extraction → AI Models → Risk Assessment
                    (36 biomarkers)     (PAT+XGB)    (Not diagnostic)
```

- **PAT**: Analyzes 7-day activity patterns for depression screening
- **XGBoost**: Uses 30-day circadian rhythms for next-day prediction
- **Ensemble**: Combines both for enhanced reliability

[Technical details →](docs/developer/ARCHITECTURE_OVERVIEW.md)

## 📊 Performance

| Metric | Value | Notes |
|--------|-------|-------|
| PAT Depression Detection | 0.593 AUC | NHANES validation |
| XGBoost Episode Prediction | 0.80-0.98 AUC | Korean cohort |
| Processing Speed | 33 MB/s | 500MB file in ~15s |
| Memory Usage | <100MB | Streaming architecture |
| Test Coverage | 90%+ | 1,230 tests |

## 📚 Documentation

### For Different Audiences
- **👤 Users**: [Quick Start](docs/user/QUICK_START_GUIDE.md) | [Apple Health Export](docs/user/APPLE_HEALTH_EXPORT.md)
- **💻 Developers**: [Architecture](docs/developer/ARCHITECTURE_OVERVIEW.md) | [API Reference](docs/developer/API_REFERENCE.md)
- **🔬 Researchers**: [Clinical Requirements](docs/clinical/CLINICAL_REQUIREMENTS_DOCUMENT.md) | [Model Training](docs/training/PAT_DEPRESSION_TRAINING.md)
- **🤖 AI Assistants**: [CLAUDE.md](CLAUDE.md)

### Key Documents
- [Roadmap to v1.0](ROADMAP_TO_MVP_V1.0.md)
- [Model Weights Guide](MODEL_WEIGHTS_GUIDE.md)
- [Latest Checkpoint](CHECKPOINT_2025_07_27.md)

## 🚀 What's Next?

### v0.6.0 (Q3 2025)
- [ ] XML Probe for data transparency ([Issue #64](https://github.com/Clarity-Digital-Twin/big-mood-detector/issues/64))
- [ ] PAT model improvements (target: 0.65 AUC)
- [ ] Real-time monitoring mode

### v1.0.0 (2026)
- [ ] Clinical validation studies
- [ ] FDA clearance pathway
- [ ] Multi-modal integration (voice, environment)

See [full roadmap →](ROADMAP_TO_MVP_V1.0.md)

## 🤝 Contributing

We welcome contributions! Areas of focus:
- **XML Processing**: Implement probe system for better UX
- **Model Training**: Improve PAT depression detection
- **Clinical Validation**: Partner on research studies
- **Documentation**: Help others use the tool

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## ⚖️ Legal & Ethics

- **License**: Apache 2.0 - use freely, even commercially
- **Privacy**: No data collection, 100% local processing
- **Clinical Use**: Research tool only - not for medical decisions
- **Citations**: Please cite original papers when publishing

## 🙏 Acknowledgments

Built on groundbreaking research:
- Seoul National University Hospital (XGBoost models)
- Dartmouth PAT team (foundation model)
- Open source community

---

*"Making mental health insights accessible to all"*

**Questions?** Open an [issue](https://github.com/Clarity-Digital-Twin/big-mood-detector/issues) or see [discussions](https://github.com/Clarity-Digital-Twin/big-mood-detector/discussions).