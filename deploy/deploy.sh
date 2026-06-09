#!/usr/bin/env bash
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
set -euo pipefail

IMAGE="ghcr.io/saibusu/ai-course:latest"
CONTAINER="waste-sorter"

echo "[deploy] Pulling latest image..."
docker pull "$IMAGE"

echo "[deploy] Stopping existing container..."
docker stop "$CONTAINER" 2>/dev/null || true
docker rm "$CONTAINER" 2>/dev/null || true

echo "[deploy] Starting new container..."
docker compose -f "$(dirname "$0")/docker-compose.yml" up -d

echo "[deploy] Waiting for health check..."
sleep 5
docker inspect --format='{{.State.Health.Status}}' "$CONTAINER"

echo "[deploy] Done."
