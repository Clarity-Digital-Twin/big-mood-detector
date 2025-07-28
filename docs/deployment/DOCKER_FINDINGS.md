# Docker Testing Findings

## ✅ RESOLVED: Missing ML Dependencies

### Problem
The standard Docker image only installs `.[dev]` dependencies, which excludes PyTorch and TensorFlow needed for the PAT model. This causes:
- PAT model not available in Docker
- Only XGBoost predictions work
- Dual pipeline not fully functional

### Solution
Updated Dockerfile with build args to support both configurations:
```dockerfile
ARG INSTALL_ML=true  # Full ML support by default
pip install --no-cache-dir -e ".[dev,ml,monitoring]"  # When INSTALL_ML=true
```

## ✅ RESOLVED: Path Permission Issues

### Problem
CLI commands showed "No write permission" warnings because:
- App expected data in `/data` but Docker mounted to `/app/data`
- No environment variable told the app where to find mounted volumes

### Solution
Added environment variables in Dockerfile:
```dockerfile
ENV BIGMOOD_DATA_DIR=/app/data \
    DATA_DIR=/app/data
```

## 🔑 CRITICAL: Production Security Requirements

### Problem
Production mode requires secure secrets or the API won't start.

### Solution
Create `.env` file with secure secrets:
```bash
# Generate secure secrets
python3 -c 'import secrets; print(f"SECRET_KEY={secrets.token_urlsafe(32)}"); print(f"API_KEY_SALT={secrets.token_urlsafe(32)}")'

# Add to .env file
SECRET_KEY=your-generated-secret-here
API_KEY_SALT=your-generated-salt-here
```

## Test Results

### API Server ✅
- Health endpoint: Working
- OpenAPI docs: Working  
- Model status: Both XGBoost AND PAT loaded with full image
- Depression predictions: Working with PAT model
- Ensemble predictions: Working with both models

### CLI Commands ✅
- Process command: Working without permission warnings
- 521MB XML file: Processes successfully (takes ~3-4 minutes)
- Output files: Saved correctly to mounted volumes

### Container Features ✅
- Sleep overlap detection: Working correctly
- Feature extraction: Working
- Memory-efficient XML streaming: Confirmed
- Model loading: Both XGBoost and PAT operational

## Performance & Image Sizes

| Image Type | Size | Models | Startup Time | Use Case |
|------------|------|--------|--------------|----------|
| Standard (`INSTALL_ML=false`) | 2.2GB | XGBoost only | ~10s | Production API, CI/CD |
| Full ML (`INSTALL_ML=true`) | 9.2GB | XGBoost + PAT | ~90s | Research, full predictions |

### Processing Performance
- **521MB XML**: 3-4 minutes (memory peaks at 1.2GB)
- **API Response**: <200ms for predictions
- **Health checks**: Need 90s+ start period for full ML image

## Docker Quick Start

```bash
# 1. Create .env file with secure secrets (REQUIRED for production)
cat > .env << EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
API_KEY_SALT=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
EOF

# 2. Build full ML image (both models)
docker build --build-arg INSTALL_ML=true -t big-mood-detector:latest .

# 3. Start services
docker-compose up -d api redis

# 4. Test API
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/predictions/status

# 5. Process Apple Health data
docker run --rm \
  -e BIGMOOD_DATA_DIR=/app/data \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/model_weights:/app/model_weights:ro" \
  big-mood-detector:latest \
  process /app/data/input/apple_export/export.xml \
  -o /app/data/output/features.json --progress

# 6. Make PAT depression prediction
curl -X POST http://localhost:8000/predictions/depression \
  -H "Content-Type: application/json" \
  -d '{"activity_sequence": [<10080 activity values>]}'
```

## Integration Test (521MB file)

```bash
# Full end-to-end test with real Apple Health export
docker run --rm \
  -e BIGMOOD_DATA_DIR=/app/data \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/model_weights:/app/model_weights:ro" \
  big-mood-detector:latest \
  process /app/data/input/apple_export/export.xml --progress

# Expected: Completes in ~3-4 minutes without errors
```