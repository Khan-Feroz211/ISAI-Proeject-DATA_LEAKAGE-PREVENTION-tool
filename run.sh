#!/bin/bash

echo "====================================="
echo "      🔐 Starting DLP System"
echo "====================================="

# Step 1: Check if running inside Docker
if [ -f "/.dockerenv" ]; then
    echo "Running inside Docker container..."
    python3 main.py
    exit 0
fi

# Step 2: Check if Docker image exists
IMAGE_NAME="dlp_app"

if ! docker image inspect $IMAGE_NAME > /dev/null 2>&1; then
    echo "⚠ Docker image not found. Building now..."
    docker build -t $IMAGE_NAME .
fi

# Step 3: Run container
echo "🚀 Launching Docker container..."
docker run -p 5000:5000 \
    -v $(pwd)/data:/app/data \
    $IMAGE_NAME
