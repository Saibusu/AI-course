#!/usr/bin/env bash
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
set -euo pipefail

CONTAINER="waste-sorter"
PREV_TAG="${1:-}"

if [[ -z "$PREV_TAG" ]]; then
  echo "Usage: $0 <previous-image-tag>"
  echo "Example: $0 ghcr.io/saibusu/ai-course:abc1234"
  exit 1
fi

echo "[rollback] Rolling back to: $PREV_TAG"

docker stop "$CONTAINER" 2>/dev/null || true
docker rm "$CONTAINER" 2>/dev/null || true

docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  --runtime nvidia \
  -v ~/AI-course/models:/app/models:ro \
  -v ~/AI-course/logs:/app/logs \
  --network host \
  "$PREV_TAG" \
  python live_detect.py

echo "[rollback] Done. Container running with $PREV_TAG"
