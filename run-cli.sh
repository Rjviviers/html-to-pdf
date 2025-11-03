#!/usr/bin/env bash
# Convenience script to rebuild and run the CLI
set -e

echo "Building Docker image with latest dependencies..."
docker compose build

echo "Starting CLI..."
docker compose run --rm cli
