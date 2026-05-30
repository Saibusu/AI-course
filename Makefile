# ============================================================
# Smart Waste Sorter — ASP Makefile
# ============================================================

ADR_DIR   := docs/adr
SPEC_DIR  := docs/specs
ADR_COUNT := $(shell ls $(ADR_DIR)/ADR-*.md 2>/dev/null | wc -l)
SPEC_COUNT:= $(shell ls $(SPEC_DIR)/SPEC-*.md 2>/dev/null | wc -l)

# ── ADR helpers ─────────────────────────────────────────────
.PHONY: adr-new adr-list spec-new spec-list audit-quick

adr-new:
	@if [ -z "$(TITLE)" ]; then echo "Usage: make adr-new TITLE=\"...\""; exit 1; fi
	@N=$$(printf "%03d" $$(( $(ADR_COUNT) + 1 ))); \
	FILE="$(ADR_DIR)/ADR-$$N-$(subst ' ','-',$(TITLE)).md"; \
	echo "Creating $$FILE"; \
	cp docs/adr/_template-adr.md "$$FILE"; \
	sed -i "s/{{TITLE}}/$(TITLE)/g" "$$FILE"; \
	sed -i "s/{{DATE}}/$(shell date +%Y-%m-%d)/g" "$$FILE"; \
	echo "✅  ADR created: $$FILE (Status: Draft)"

adr-list:
	@echo "=== ADR List ==="; \
	for f in $(ADR_DIR)/ADR-*.md; do \
	  [ -f "$$f" ] || continue; \
	  STATUS=$$(grep "^Status:" "$$f" | head -1 | awk '{print $$2}'); \
	  echo "  $$f  [$$STATUS]"; \
	done

spec-new:
	@if [ -z "$(TITLE)" ]; then echo "Usage: make spec-new TITLE=\"...\""; exit 1; fi
	@N=$$(printf "%03d" $$(( $(SPEC_COUNT) + 1 ))); \
	FILE="$(SPEC_DIR)/SPEC-$$N-$(subst ' ','-',$(TITLE)).md"; \
	echo "Creating $$FILE"; \
	cp docs/specs/_template-spec.md "$$FILE"; \
	sed -i "s/{{TITLE}}/$(TITLE)/g" "$$FILE"; \
	sed -i "s/{{DATE}}/$(shell date +%Y-%m-%d)/g" "$$FILE"; \
	echo "✅  SPEC created: $$FILE"

spec-list:
	@echo "=== SPEC List ==="; \
	for f in $(SPEC_DIR)/SPEC-*.md; do \
	  [ -f "$$f" ] || continue; \
	  echo "  $$f"; \
	done

audit-quick:
	@echo "=== Quick Audit ==="; \
	DRAFTS=$$(grep -rl "Status: Draft" $(ADR_DIR)/ 2>/dev/null | wc -l); \
	echo "Draft ADRs: $$DRAFTS"; \
	[ "$$DRAFTS" -gt 0 ] && echo "⚠️  Blocked: Draft ADRs must be Accepted before implementation" || echo "✅  No blockers"

# ── Jetson deploy ────────────────────────────────────────────
JETSON_IP   := 172.20.10.2
JETSON_USER := jetson
REMOTE_DIR  := /home/$(JETSON_USER)/final

deploy:
	scp -r src/ requirements.txt setup.sh $(JETSON_USER)@$(JETSON_IP):$(REMOTE_DIR)/

ssh:
	ssh $(JETSON_USER)@$(JETSON_IP)
