#!/bin/bash
# Test script to verify Docker path fixes

echo "Testing current Docker image path configuration..."

echo -e "\n1. Environment variables in container:"
docker run --rm big-mood-detector:latest bash -c "echo 'BIGMOOD_DATA_DIR: $BIGMOOD_DATA_DIR'; echo 'DATA_DIR: $DATA_DIR'"

echo -e "\n2. Python settings paths:"
docker run --rm big-mood-detector:latest python -c "from big_mood_detector.infrastructure.settings import get_settings; s = get_settings(); print(f'DATA_DIR: {s.DATA_DIR}'); print(f'OUTPUT_DIR: {s.OUTPUT_DIR}')"

echo -e "\n3. Testing with BIGMOOD_DATA_DIR set:"
docker run --rm -e BIGMOOD_DATA_DIR=/app/data big-mood-detector:latest python -c "from big_mood_detector.infrastructure.settings import get_settings; s = get_settings(); print(f'DATA_DIR: {s.DATA_DIR}'); print(f'OUTPUT_DIR: {s.OUTPUT_DIR}')"

echo -e "\n4. Testing CLI with environment variable:"
docker run --rm -e BIGMOOD_DATA_DIR=/app/data -v "$(pwd)/data:/app/data" big-mood-detector:latest process --help 2>&1 | grep -i "permission" || echo "No permission warnings!"

echo -e "\n5. Testing directory creation:"
docker run --rm -e BIGMOOD_DATA_DIR=/app/data -v "$(pwd)/data:/app/data" big-mood-detector:latest bash -c "ls -la /app/data/"