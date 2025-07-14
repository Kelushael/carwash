#!/bin/bash

# Production startup script for Car Wash Mixer

set -e

echo "Starting Car Wash Mixer in production mode..."

# Check if Redis is available
if command -v redis-cli &> /dev/null; then
    echo "Checking Redis connection..."
    if redis-cli ping > /dev/null 2>&1; then
        echo "✓ Redis is available"
    else
        echo "⚠ Redis is not available, caching will be disabled"
    fi
else
    echo "⚠ Redis client not found, caching will be disabled"
fi

# Set production environment variables
export FLASK_ENV=production
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Create necessary directories
mkdir -p logs
mkdir -p output

# Start the application with Gunicorn
echo "Starting Gunicorn server..."
gunicorn \
    --config gunicorn.conf.py \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    server:app

echo "Application started successfully!"