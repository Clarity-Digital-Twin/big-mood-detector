# Big Mood Detector - AI Assistant Guide

Clinical-grade mood episode prediction (depression, mania, hypomania) using Apple Health data and ML models.

## Quick Start

```bash
# macOS/Linux
python3.12 -m venv .venv
source .venv/bin/activate

# Windows WSL2
# IMPORTANT: Use .venv-wsl for WSL to avoid Python version conflicts
python3.12 -m venv .venv-wsl
source .venv-wsl/bin/activate

# Install (all platforms)
pip install 'numpy<2.0'  # CRITICAL: Install first
pip install -e ".[dev,ml,monitoring]"
```

## Core Commands

```bash
# Process health data
python src/big_mood_detector/main.py process data/input/apple_export/export.xml

# Make predictions
python src/big_mood_detector/main.py predict data/input/apple_export/export.xml --report

# Start API server
make dev  # or: python src/big_mood_detector/main.py serve

# Test & Quality
export TESTING=1  # Fast tests only (2 min)
make test         # Run fast test suite
make quality      # Lint + type + test
```

## Architecture (Clean + DDD)

```
CLI/API → Use Cases → Domain ← Infrastructure
         (orchestrate) (pure)   (implementations)
```

- **Domain**: Pure Python, no dependencies
- **Use Cases**: Orchestrate domain services
- **Infrastructure**: ML models, parsers, DB
- **Interfaces**: CLI commands, FastAPI routes

## Current Capabilities (v0.5.7)

### ✅ Production Ready
- **XGBoost**: Depression/mania risk (36 Seoul features)
- **PAT-Conv-L**: Depression detection (0.593 AUC)
- **Temporal Ensemble**: XGBoost (tomorrow) + PAT (now)
- **XML Parser**: 521MB files in <100MB RAM
- **Fast CI/CD**: 2-minute test runs with TESTING=1
- **Auto-Window Selection**: Smart data window selection for sparse/dense data
- **Window-Level Predictions**: Proper aggregation for XGBoost-only scenarios
- **Dynamic Timeout**: File-size based timeout (2min/5min/unlimited)
- **Cross-Platform**: Windows WSL2 compatibility

### 🔧 Key Features
- Process Apple Health export.xml
- Clinical-grade mood predictions
- Rolling window normalization (30-60 days)
- FastAPI with /predictions/depression endpoint
- Docker deployment ready

## Model Status

| Model | Purpose | Status | Accuracy |
|-------|---------|--------|----------|
| XGBoost | Future risk (circadian) | ✅ Ready | AUC 0.80-0.98 |
| PAT-Conv-L | Current state (activity) | ✅ Ready | AUC 0.593 |
| Ensemble | Temporal separation | ✅ Ready | Improved |

### Required Files
```
model_weights/
├── xgboost/converted/*.json    # XGBoost models
├── pat/pretrained/PAT-*.h5     # PAT pretrained weights
└── production/pat_conv_l_v0.5929.pth  # Trained depression head
```

## Development Guidelines

### Testing Strategy
```bash
# Fast tests (every commit) - 2 min
export TESTING=1
pytest -m "not slow"

# Full suite (nightly) - includes ML
pytest  # No TESTING=1
```

### Adding Features
1. Define in `domain/` (pure logic)
2. Create use case in `application/`
3. Implement in `infrastructure/`
4. Add CLI/API in `interfaces/`
5. Write tests first (TDD)

### Common Issues & Solutions

**Test Hangs**
- Always use `export TESTING=1` for local development
- This prevents loading heavy ML libraries during test collection

**Import Errors**
- Run `pip install -e .` after cloning
- Set `export PYTHONPATH="$PWD/src:$PYTHONPATH"`

**Missing Weights**
```bash
# Copy from data-dump if needed
cp data-dump/model_weights/pat/pretrained/PAT-*.h5 model_weights/pat/pretrained/
```

## Critical Constants

- **Sleep merging**: 3.75 hours
- **Activity sequence**: 1440 min/day (7 days = 10,080)
- **Seoul features**: 36 statistical
- **PAT embeddings**: 96 dimensional
- **Clinical threshold**: PHQ-9 ≥ 10

## Performance Targets

- XML parsing: 33MB/s
- Feature extraction: <1s/year
- Model inference: <100ms
- API response: <200ms
- Memory: <100MB for any file size

## Don't Modify Without Review

- `domain/value_objects/clinical_thresholds.py` - DSM-5 validated
- `infrastructure/parsers/xml/streaming_parser.py` - Memory optimization
- `core/config.py` - Critical paths
- Model weight files - Trained on clinical data

## Useful Patterns

### Process Large XML
```python
from big_mood_detector.application.services.optimized_aggregation_pipeline import OptimizedAggregationPipeline

config = AggregationConfig(
    enable_dlmo_calculation=False,  # Skip expensive
    enable_circadian_analysis=False
)
pipeline = OptimizedAggregationPipeline(config=config)
```

### Enable Personal Normalization
```python
# Personal baselines are now calculated using rolling windows in AggregationPipeline
# The pipeline automatically maintains 30-60 day rolling windows for Z-score normalization
pipeline = MoodPredictionPipeline(
    config=PipelineConfig(
        use_seoul_features=True  # Uses AggregationPipeline with rolling windows
    )
)
```

## Debug Commands

```bash
# Verbose logging
export LOG_LEVEL=DEBUG

# Profile memory
mprof run python src/big_mood_detector/main.py process large.xml
mprof plot

# Trace slow code
python -m cProfile -s cumtime src/big_mood_detector/main.py process data/
```

## Context Budget Tips

When analyzing code, prioritize:
1. Domain layer (small, pure)
2. Specific use case
3. Relevant infrastructure
4. Related tests

Avoid loading:
- All infrastructure files
- Reference repos
- Large fixtures
- Old documentation

---
**Remember**: Clinical accuracy > Feature complexity > Performance

**Python**: 3.12+ required | **Coverage**: 73%+ | **Type-safe**: mypy clean