# Contributing to Big Mood Detector

We love your input! We want to make contributing to Big Mood Detector as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## We Develop with Github

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## We Use [Github Flow](https://guides.github.com/introduction/flow/index.html)

Pull requests are the best way to propose changes to the codebase:

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## Any contributions you make will be under the Apache 2.0 Software License

In short, when you submit code changes, your submissions are understood to be under the same [Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](https://github.com/Clarity-Digital-Twin/big-mood-detector/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/Clarity-Digital-Twin/big-mood-detector/issues/new); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Use a Consistent Coding Style

* Run `make format` before committing
* Run `make lint` to check for issues
* Run `make test` to ensure tests pass

## Git Hooks and CI/CD

This project uses Git hooks to maintain code quality:

### Pre-commit Hook
- Runs automatically on every commit
- Executes `ruff --fix` for automatic formatting
- Checks for problematic imports in test files

### Pre-push Hook (Lightweight)
- Runs quick smoke tests before pushing (~30 seconds)
- Includes: ruff check, mypy on core modules, fast unit tests
- Full test suite runs in GitHub Actions CI

### Bypassing Hooks (Emergency Use Only)
If you need to bypass hooks in an emergency:
```bash
# Skip pre-commit hook
git commit --no-verify -m "Emergency fix"

# Skip pre-push hook
git push --no-verify
```

**Note:** Use bypass only when necessary. CI will still run full checks.
* Follow the existing code style (Clean Architecture patterns)

## 🎯 Current Status (v0.5.0)

### ✅ COMPLETED: True Ensemble Predictions Now Live!
**What's New:** Both XGBoost AND PAT models now make clinical predictions together.

**What We Built:**
- ✅ PAT depression detection head trained on NHANES 2013-2014
- ✅ Temporal ensemble that combines XGBoost (future risk) + PAT (current state)
- ✅ Production-ready API with both models integrated
- ✅ Docker support for easy deployment

**Current Architecture:**
```python
# v0.5.0 - Full ensemble predictions!
xgboost_risk = xgboost.predict_tomorrow(circadian_features)  # 0.75 risk
pat_current = pat.predict_depression(activity_sequence)       # 0.82 risk
ensemble = temporal_ensemble.combine(xgboost_risk, pat_current)  # 0.79 final
```

### Current Priorities for Contributors

1. **Improve Depression Detection** (ML/Research)
   - Current PAT head achieves 0.593 AUC on NHANES
   - Goal: Match or exceed published benchmarks (0.70+ AUC)
   - Ideas: Better data augmentation, ensemble methods, feature engineering

2. **Multi-device Support** (Engineering)
   - Extend beyond Apple Health to Fitbit, Garmin, Oura
   - Standardize activity data formats across devices
   - See issue #[TBD] for device API specifications

3. **Performance Optimization** (Systems)
   - Current: 33MB/s XML parsing, <100MB RAM for 500MB files
   - Goal: Handle 2GB+ exports without memory issues
   - Profile and optimize the streaming parser

4. **Clinical Validation** (Research/Medical)
   - Test on diverse populations beyond NHANES
   - Partner with clinical researchers for real-world validation
   - Document performance across demographics

## Development Setup

### Prerequisites
- Python 3.12 or higher (we test on Python 3.12 in CI)
- Git
- Make (optional but recommended)
- Docker (for containerized development)

### Local Development

```bash
# Clone the repository
git clone https://github.com/Clarity-Digital-Twin/big-mood-detector.git
cd big-mood-detector

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Windows WSL2 users: Use separate venv to avoid conflicts
python3.12 -m venv .venv-wsl
source .venv-wsl/bin/activate

# CRITICAL: Install numpy first to avoid dependency conflicts
pip install 'numpy<2.0'

# Install with all dependencies
pip install -e ".[dev,ml,monitoring]"

# Download model weights (see Model Weights Setup section)
python scripts/verify_setup.py --check-models

# Run fast tests (2 minutes)
export TESTING=1
make test

# Start development server
make dev
```

### Docker Development

Docker is the recommended way to ensure consistent environments:

```bash
# 1. Create .env file with secure secrets (REQUIRED)
cat > .env << EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
API_KEY_SALT=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
EOF

# 2. Build full ML image (includes both XGBoost and PAT)
docker build --build-arg INSTALL_ML=true -t big-mood-detector:latest .

# 3. Start services
docker-compose up -d api redis

# 4. Test the setup
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/predictions/status

# 5. Process Apple Health data
docker run --rm \
  -e BIGMOOD_DATA_DIR=/app/data \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/model_weights:/app/model_weights:ro" \
  big-mood-detector:latest \
  process /app/data/input/apple_export/export.xml --progress
```

### Model Weights Setup

You MUST have model weights in place before running:

```bash
# Required files:
model_weights/
├── xgboost/converted/
│   ├── XGBoost_DE.json      # ✅ Already in repo
│   ├── XGBoost_HME.json     # ✅ Already in repo
│   └── XGBoost_ME.json      # ✅ Already in repo
├── pat/
│   ├── pretrained/
│   │   └── PAT-L_29k_weights.h5  # ⬇️ Download from Dartmouth
│   └── production/
│       └── pat_conv_l_v0.5929.pth  # 🔒 Private - request access
```

**Getting Model Weights:**

1. **Quick Setup (Recommended)**: Request the complete model bundle
   - Email maintainer with your use case
   - Get access to pre-packaged Google Drive bundle (~140MB)
   - Extract to project root - all files go to correct locations

2. **Manual Setup**: Download individually
   - PAT weights: [Dartmouth PAT Repo](https://github.com/njacobsonlab/Pretrained-Actigraphy-Transformer/)
   - Depression head: Private distribution (clinical model)
   - See [`DATA_AND_MODEL_WEIGHTS.md`](DATA_AND_MODEL_WEIGHTS.md) for detailed instructions

**Note on Clinical Models**: The depression detection head outputs clinical predictions and is distributed privately to ensure research-only use. By requesting access, you agree not to use it for clinical diagnosis without proper regulatory approval.

## Testing

- Write tests for any new functionality
- Ensure all tests pass with `make test`
- Add integration tests for new features
- Test with real Apple Health data when possible

### Test Organization

We organize tests into two categories:

1. **Fast tests** (default) - Run in CI and locally:
   - Unit tests
   - Light integration tests
   - Must complete in < 5 minutes total
   - Run with: `pytest -m "not slow"`

2. **Slow tests** - Run nightly or manually:
   - Performance benchmarks
   - Large data processing tests
   - Tests that load real ML models
   - Run with: `pytest -m slow`

### TESTING Environment Variable

To prevent model loading during tests (which can cause timeouts), we use the `TESTING` environment variable:

```bash
# Run fast tests without loading models
export TESTING=1
pytest -m "not slow"

# Run all tests including slow ones (loads real models)
pytest --runslow
```

The `TESTING=1` flag:
- Skips loading PAT model weights
- Uses mock predictors in tests
- Prevents subprocess tests from hanging
- Is automatically set in CI for fast test runs

### Adding New Tests

When adding tests:
- Mark performance/integration tests with `@pytest.mark.slow`
- Use `MoodPredictionPipeline.for_testing()` for pipeline tests
- Avoid subprocess calls that might load models
- Keep individual test runtime under 10 seconds for fast tests

## Documentation

- Update the README.md if needed
- Add docstrings to all public functions
- Update API documentation for new endpoints
- Include examples in documentation

## License

By contributing, you agree that your contributions will be licensed under its Apache License 2.0.

## References

This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md)