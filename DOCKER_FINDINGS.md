# Docker Testing Findings

## Issue Found: Missing ML Dependencies

### Problem
The standard Docker image only installs `.[dev]` dependencies, which excludes PyTorch and TensorFlow needed for the PAT model. This causes:
- PAT model not available in Docker
- Only XGBoost predictions work
- Dual pipeline not fully functional

### Root Cause
In `Dockerfile` line 29:
```dockerfile
pip install --no-cache-dir -e ".[dev]" && \
```

Should be:
```dockerfile
pip install --no-cache-dir -e ".[dev,ml]" && \
```

### Solution
Created `Dockerfile.full` that includes ML dependencies for full dual-pipeline support.

## Test Results

### API Server ✅
- Health endpoint: Working
- OpenAPI docs: Working
- Model status: XGBoost loaded, PAT missing (in standard image)
- Predictions: Working with XGBoost only

### CLI Commands ✅
- Help command: Working
- Process command: Working (but slow on 521MB file)

### Mathematical Calculations ✅
- Sleep overlap detection: Working correctly
- Feature extraction: Working
- Aggregation: Working

## Performance Notes

1. **XML Processing**: 521MB file takes 3+ minutes (expected for large files)
2. **Memory Usage**: Docker container handles large files well
3. **ML Model Loading**: XGBoost loads quickly, PyTorch/TensorFlow add significant startup time

## Recommendations

1. **Production**: Use `Dockerfile` (lighter, XGBoost only)
2. **Development/Full Features**: Use `Dockerfile.full` (includes PAT)
3. **CI/CD**: Consider separate images for different use cases
4. **Documentation**: Update README to explain Docker image variants

## Docker Commands Reference

```bash
# Build standard image (XGBoost only)
docker build -t big-mood-detector:latest .

# Build full image (XGBoost + PAT)
docker build -f Dockerfile.full -t big-mood-detector:full .

# Run API server
docker run -d --name mood-api -p 8000:8000 -v $(pwd)/data:/data -v $(pwd)/model_weights:/app/model_weights big-mood-detector:latest

# Run CLI command
docker run --rm -v $(pwd)/data:/data -v $(pwd)/model_weights:/app/model_weights big-mood-detector:latest process /data/input/apple_export/export.xml

# Check logs
docker logs mood-api

# Stop and remove
docker stop mood-api && docker rm mood-api
```