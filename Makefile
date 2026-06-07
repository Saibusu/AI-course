# Makefile — 常用指令快速鍵
# 使用方式：make <目標>

.PHONY: help dev dev-headless dev-shell dev-test-gpio test \
        jetson-build jetson-up jetson-logs jetson-shell jetson-stop \
        train export-trt clean logs

# ── 說明 ─────────────────────────────────────────────────────
help:
	@echo ""
	@echo "智慧零接觸垃圾分類系統 — 快速指令"
	@echo "======================================"
	@echo ""
	@echo "【PC 開發】"
	@echo "  make dev              啟動 PC 開發模式（含預覽視窗）"
	@echo "  make dev-headless     啟動 PC 開發模式（無視窗，看 log）"
	@echo "  make dev-shell        進入開發容器 bash shell"
	@echo "  make dev-test-gpio    在容器內執行 GPIO Mock 測試"
	@echo "  make test             執行單元測試（pytest）"
	@echo ""
	@echo "【Jetson 部署】（在 Jetson 上執行）"
	@echo "  make jetson-build     建立 Jetson Docker 映像"
	@echo "  make jetson-up        啟動 Jetson 容器（背景常駐）"
	@echo "  make jetson-logs      追蹤 Jetson 容器 log"
	@echo "  make jetson-shell     進入 Jetson 容器 bash shell"
	@echo "  make jetson-stop      停止 Jetson 容器"
	@echo ""
	@echo "【模型工具】"
	@echo "  make download-data KEY=xxx  下載 Roboflow 廢棄物資料集"
	@echo "  make train                  訓練廢棄物分類 YOLO26 模型"
	@echo "  make export-trt             轉換 .pt → TensorRT engine（Jetson 上執行）"
	@echo ""
	@echo "【其他】"
	@echo "  make logs             顯示辨識記錄 CSV"
	@echo "  make clean            清除 Docker 映像與容器"
	@echo ""

# ── PC 開發模式 ──────────────────────────────────────────────
dev:
	@echo ">>> 啟動 PC 開發模式（ENV=dev，MockGPIO）"
	@# Linux X11 授權
	@xhost +local:docker 2>/dev/null || true
	docker-compose up --build

dev-headless:
	@echo ">>> 啟動 PC 無頭模式"
	SHOW_PREVIEW=false docker-compose up --build

dev-shell:
	docker-compose run --rm app bash

dev-test-gpio:
	docker-compose run --rm app python test_gpio.py

test:
	@echo ">>> 執行單元測試"
	docker-compose run --rm app python -m pytest tests/ -v

# ── Jetson 部署 ──────────────────────────────────────────────
jetson-build:
	@echo ">>> 建立 Jetson Docker 映像（需在 Jetson 上執行）"
	docker-compose -f docker-compose.jetson.yml build

jetson-up:
	@echo ">>> 啟動 Jetson 容器（背景常駐）"
	docker-compose -f docker-compose.jetson.yml up -d

jetson-logs:
	docker-compose -f docker-compose.jetson.yml logs -f

jetson-shell:
	docker-compose -f docker-compose.jetson.yml exec app bash

jetson-stop:
	docker-compose -f docker-compose.jetson.yml down

# ── 模型工具 ─────────────────────────────────────────────────
download-data:
	@[ -n "$(KEY)" ] || (echo "使用方式：make download-data KEY=your_roboflow_api_key" && exit 1)
	@echo ">>> 下載 Roboflow 廢棄物資料集（TACO，6 類）"
	docker-compose run --rm app python scripts/download_dataset.py --key $(KEY)

train:
	@echo ">>> 訓練廢棄物分類 YOLO26 模型"
	docker-compose run --rm app python train.py --data dataset/data.yaml

export-trt:
	@echo ">>> 轉換 TensorRT engine（需在 Jetson 容器內執行）"
	docker-compose -f docker-compose.jetson.yml run --rm app \
		python3 export_tensorrt.py --model models/waste_classifier.pt

# ── 其他 ─────────────────────────────────────────────────────
logs:
	@if [ -f logs/predictions.csv ]; then \
		echo "=== 最近 20 筆辨識記錄 ==="; \
		tail -20 logs/predictions.csv; \
	else \
		echo "尚無辨識記錄（logs/predictions.csv 不存在）"; \
	fi

clean:
	docker-compose down --rmi local -v 2>/dev/null || true
	docker-compose -f docker-compose.jetson.yml down --rmi local -v 2>/dev/null || true
	@echo "已清除本地 Docker 映像與容器"
