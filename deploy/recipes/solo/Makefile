# DataHelix solo recipe — operator entry points. See README.md.

PROJECT_DIR ?= ./project
REPO_ROOT   := ../../..

.PHONY: init gate check-pins up down migrate logs backup

## Scaffold a project directory from the bundled example (no-op if it exists).
init:
	@if [ -e "$(PROJECT_DIR)/mosaic.yaml" ]; then \
		echo "$(PROJECT_DIR) already initialized"; \
	else \
		mkdir -p "$(PROJECT_DIR)"; \
		cp -a example-project/. "$(PROJECT_DIR)/"; \
		echo "project scaffolded at $(PROJECT_DIR) — edit $(PROJECT_DIR)/schemas/"; \
	fi

## Static pin check: Dockerfile digests == certified composition lock.
check-pins:
	python3 check_pins.py

## Certified-frontier pre-flight (platform ADR-0001): pins are a certified
## pair AND this bundle is built from exactly those pins.
gate: check-pins
	$(REPO_ROOT)/certification/scripts/deploy_gate.sh $(REPO_ROOT)/certification/composition.lock.json

up:
	docker compose up -d --build
	@echo "solo up — http://localhost:$${SOLO_PORT:-8080} (Aperture) /modeler/ (Modeler) /docs (API)"

down:
	docker compose down

## Apply schema edits: restart = pull (Mode R) + migrate + serve (§1.7).
migrate:
	docker compose restart solo
	docker compose logs --tail 30 solo

logs:
	docker compose logs -f solo

## SQLite backup: stop for a consistent copy, tar the data dir, restart.
backup:
	docker compose stop solo
	tar -C "$(PROJECT_DIR)" -czf "solo-backup-$$(date +%Y%m%d-%H%M%S).tar.gz" data schemas mosaic.yaml
	docker compose start solo
	@ls -t solo-backup-*.tar.gz | head -1
