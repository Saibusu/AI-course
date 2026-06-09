#!/usr/bin/env bash
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
set -euo pipefail

CONTAINER="waste-sorter"

STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "not_found")

case "$STATUS" in
  healthy)   echo "✅ Container healthy"; exit 0 ;;
  starting)  echo "⏳ Container starting..."; exit 0 ;;
  unhealthy) echo "❌ Container unhealthy"; exit 1 ;;
  *)         echo "❓ Container status: $STATUS"; exit 1 ;;
esac
