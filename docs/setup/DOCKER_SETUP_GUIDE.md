# Docker Setup Guide

This guide covers everything you need to run Big Mood Detector in Docker, including troubleshooting common issues.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- 10GB+ free disk space (for full ML image)
- Python 3.x (for generating secrets)

## Quick Start

### 1. Generate Security Credentials

Production mode requires secure secrets. Generate them once:

```bash
# Create .env file with secure secrets
cat > .env << EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
API_KEY_SALT=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
POSTGRES_USER=bigmood
POSTGRES_PASSWORD=changeme
POSTGRES_DB=bigmood
EOF
```

**Important**: Never commit the `.env` file to version control!

### 2. Build Docker Image

Choose your configuration:

```bash
# Full ML support (9.2GB - includes XGBoost + PAT)
docker build --build-arg INSTALL_ML=true -t big-mood-detector:latest .

# Lightweight (2.2GB - XGBoost only, faster CI/CD)
docker build --build-arg INSTALL_ML=false -t big-mood-detector:lite .
```

Build times:
- Full ML: 5-10 minutes (downloads PyTorch/TensorFlow)
- Lightweight: 2-3 minutes

### 3. Start Services

```bash
# Start API and Redis
docker-compose up -d api redis

# Check health
docker logs mood-api
curl http://localhost:8000/health
```

Wait ~90 seconds for the full ML image to load all models.

## Using the Application

### Process Apple Health Data

```bash
# Process entire export
docker run --rm \
  -e BIGMOOD_DATA_DIR=/app/data \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/model_weights:/app/model_weights:ro" \
  big-mood-detector:latest \
  process /app/data/input/apple_export/export.xml \
  -o /app/data/output/features.json --progress

# Process last 30 days only (faster)
docker run --rm \
  -e BIGMOOD_DATA_DIR=/app/data \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/model_weights:/app/model_weights:ro" \
  big-mood-detector:latest \
  process /app/data/input/apple_export/export.xml \
  --days-back 30 -o /app/data/output/features_30d.json
```

### Make Predictions

```bash
# Generate clinical report
docker run --rm \
  -e BIGMOOD_DATA_DIR=/app/data \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/model_weights:/app/model_weights:ro" \
  big-mood-detector:latest \
  predict /app/data/input/apple_export/export.xml --report
```

### API Endpoints

```bash
# Check model status
curl http://localhost:8000/api/v1/predictions/status

# PAT depression prediction (requires 7-day activity data)
curl -X POST http://localhost:8000/predictions/depression \
  -H "Content-Type: application/json" \
  -d '{"activity_sequence": [/* 10,080 minute-level values */]}'

# XGBoost predictions
curl -X POST http://localhost:8000/api/v1/predictions/predict \
  -H "Content-Type: application/json" \
  -d '{
    "sleep_duration": 7.5,
    "sleep_efficiency": 0.85,
    "sleep_timing_variance": 1.2,
    "daily_steps": 8500,
    "activity_variance": 2500,
    "sedentary_hours": 10.5
  }'
```

## Volume Mounts Explained

```yaml
volumes:
  - ./data:/app/data           # Your health data files
  - ./model_weights:/app/model_weights:ro  # ML model weights (read-only)
  - logs:/app/logs            # Application logs
```

The `BIGMOOD_DATA_DIR=/app/data` environment variable tells the app where to find mounted data.

## Troubleshooting

### "No write permission" Warnings

**Symptom**: CLI shows warnings about `/data/output` permissions

**Fix**: Already resolved in latest image. Ensure you're using:
```bash
-e BIGMOOD_DATA_DIR=/app/data
```

### API Won't Start

**Symptom**: Container exits with "SECURITY ERROR"

**Fix**: Create `.env` file with secure secrets (see step 1)

### Model Not Found

**Symptom**: "Model file not found" errors

**Fix**: Ensure model weights are mounted:
```bash
# Check model files exist
ls -la model_weights/xgboost/converted/
ls -la model_weights/pat/pretrained/

# Mount them read-only
-v "$(pwd)/model_weights:/app/model_weights:ro"
```

### Processing Timeouts

**Symptom**: Large XML files timeout in shell

**Fix**: Run directly in container:
```bash
# Enter container
docker run --rm -it \
  -e BIGMOOD_DATA_DIR=/app/data \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/model_weights:/app/model_weights:ro" \
  big-mood-detector:latest \
  bash

# Inside container, process without timeout
big-mood process /app/data/input/apple_export/export.xml --progress
```

### Memory Issues

**Symptom**: Container killed during processing

**Fix**: Increase Docker memory limit:
- Docker Desktop: Settings → Resources → Memory → 8GB+
- Linux: Use `--memory=8g` flag

## Production Deployment

### Environment Variables

```bash
# Required for production
ENVIRONMENT=production
SECRET_KEY=<secure-random-string>
API_KEY_SALT=<secure-random-string>

# Optional configuration
LOG_LEVEL=INFO
WORKERS=4
ENSEMBLE_PAT_TIMEOUT=10.0
ENSEMBLE_XGBOOST_TIMEOUT=5.0
```

### Health Checks

The container includes health checks that verify:
- API is responding
- Models are loaded
- Database connections (if configured)

Adjust start period for slow environments:
```yaml
healthcheck:
  start_period: 180s  # 3 minutes for very slow systems
```

### Resource Requirements

| Component | CPU | Memory | Disk |
|-----------|-----|--------|------|
| API (XGBoost only) | 2 cores | 2GB | 2.5GB |
| API (Full ML) | 4 cores | 8GB | 10GB |
| Redis | 1 core | 512MB | 1GB |
| Processing 500MB XML | 2 cores | 2GB | - |

## Advanced Usage

### Custom Model Paths

Override model locations:
```bash
docker run --rm \
  -e XGBOOST_MODEL_PATH=/models/custom/xgboost \
  -e PAT_MODEL_PATH=/models/custom/pat \
  -v "$(pwd)/custom_models:/models:ro" \
  big-mood-detector:latest
```

### Development Mode

Mount source code for hot reload:
```bash
docker run --rm -it \
  -e ENVIRONMENT=development \
  -e LOG_LEVEL=DEBUG \
  -v "$(pwd)/src:/app/src" \
  -v "$(pwd)/data:/app/data" \
  -p 8000:8000 \
  big-mood-detector:latest \
  bash
```

### Multi-Stage Builds

Build specific stages:
```bash
# Builder stage only (for CI caching)
docker build --target builder -t big-mood-builder .

# Runtime without ML
docker build --build-arg INSTALL_ML=false --target runtime -t big-mood-runtime .
```

## Security Notes

1. **Never use default secrets in production** - Always generate new ones
2. **Mount model weights read-only** - Use `:ro` flag
3. **Run as non-root** - Container uses `appuser` (UID 1000)
4. **Network isolation** - Use Docker networks for service communication

## Performance Tips

1. **Use `.dockerignore`** - Excludes unnecessary files from build context
2. **Layer caching** - Dependencies installed before code for faster rebuilds
3. **Multi-stage builds** - Reduces final image size by ~40%
4. **Parallel service startup** - Redis and API start concurrently

## Updating

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker build --build-arg INSTALL_ML=true -t big-mood-detector:latest .

# Restart services
docker-compose down
docker-compose up -d api redis
```

## Support

- **Issues**: [GitHub Issues](https://github.com/Clarity-Digital-Twin/big-mood-detector/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Clarity-Digital-Twin/big-mood-detector/discussions)
- **Logs**: `docker logs mood-api` or check `./logs/` volume