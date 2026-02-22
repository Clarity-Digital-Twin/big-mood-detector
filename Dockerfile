# Multi-stage build for optimized image size - 2025 best practices
# Build args for flexibility (default: full ML support)
ARG INSTALL_ML=true

# Stage 1: Builder with all dependencies
FROM python:3.12-slim-bookworm AS builder

# Accept build args
ARG INSTALL_ML

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser

# Install system dependencie
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first (better caching)
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies based on build arg
# Default: Full ML support (both XGBoost and PAT)
# Override with --build-arg INSTALL_ML=false for lighter image
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    if [ "$INSTALL_ML" = "true" ]; then \
        echo "Installing with ML support (PyTorch + TensorFlow)..." && \
        pip install --no-cache-dir -e ".[dev,ml,monitoring]"; \
    else \
        echo "Installing without ML support (XGBoost only)..." && \
        pip install --no-cache-dir -e ".[dev,monitoring]"; \
    fi && \
    pip install --no-cache-dir gunicorn

# Stage 2: Runtime image (smaller, secure)
FROM python:3.12-slim-bookworm AS runtime

# Install only required runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser model_weights/ ./model_weights/

# Create required directories
RUN mkdir -p /app/logs /app/data /app/uploads && \
    chown -R appuser:appuser /app

# Copy and setup entrypoint
COPY --chown=appuser:appuser docker/entrypoint.sh /entrypoint.sh
COPY --chown=appuser:appuser docker/healthcheck.py /healthcheck.py
RUN chmod +x /entrypoint.sh /healthcheck.py

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Default to production settings
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    # Set data directory to match volume mount
    BIGMOOD_DATA_DIR=/app/data \
    DATA_DIR=/app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /healthcheck.py || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Volumes for persistent data
VOLUME ["/app/data", "/app/logs", "/app/model_weights"]

# Use entrypoint for flexible execution
ENTRYPOINT ["/entrypoint.sh"]

# Default command (can be overridden)
CMD ["serve"]