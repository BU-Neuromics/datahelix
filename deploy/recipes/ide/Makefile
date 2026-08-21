# DataHelix ide recipe — operator entry points. See README.md.
#
# There is deliberately no `gate` / `check-pins` target: `ide` is exempt from
# the ADR-0001 deploy gate (decision 1.10) because it builds from source.
# Nothing this recipe produces is a certified artifact.

PROJECT_DIR ?= ./project

# Profiles come in mutually exclusive pairs; each target below spells out both
# the profile list and the matching gateway upstreams. They are written out in
# full rather than spliced from variables: the upstream host must agree with
# the profile actually running, and a mismatch shows up as a 502 rather than as
# an error, so legibility beats brevity here.
#
# Vite listens on IDE_PORT so its HMR client's port assumption matches the
# public origin — no hmr.clientPort override needed at any port.
IDE_PORT ?= 8080

# Mosaic runs as the invoking user so the SQLite file it writes into the
# bind-mounted project dir is yours, not root's, and so the image's uid-999
# `mosaic` user isn't blocked from writing there at all.
DOCKER_UID := $(shell id -u)
DOCKER_GID := $(shell id -g)
IDS = DOCKER_UID=$(DOCKER_UID) DOCKER_GID=$(DOCKER_GID)

WEB_IMAGE   = APERTURE_UPSTREAM=aperture:80
WEB_SOURCE  = APERTURE_UPSTREAM=aperture-dev:$(IDE_PORT)
API_IMAGE   = MOSAIC_UPSTREAM=mosaic:8001
API_SOURCE  = MOSAIC_UPSTREAM=mosaic-dev:8001

.PHONY: init up dev dev-web dev-api down logs logs-web migrate reload-api ps clean help

## Scaffold a project directory from the bundled example (no-op if it exists).
init:
	@if [ -e "$(PROJECT_DIR)/mosaic.yaml" ]; then \
		echo "$(PROJECT_DIR) already initialized"; \
	else \
		mkdir -p "$(PROJECT_DIR)"; \
		cp -a example-project/. "$(PROJECT_DIR)/"; \
		echo "project scaffolded at $(PROJECT_DIR) — edit $(PROJECT_DIR)/schemas/"; \
	fi

## Both components from pinned images — the known-good baseline.
up: init
	env COMPOSE_PROFILES=aperture-image,mosaic-image \
		$(WEB_IMAGE) $(API_IMAGE) $(IDS) IDE_PORT=$(IDE_PORT) docker compose up -d
	@$(MAKE) --no-print-directory _ready

## Both components live from source: Aperture HMR + Mosaic --reload.
dev: init
	env COMPOSE_PROFILES=aperture-source,mosaic-source \
		$(WEB_SOURCE) $(API_SOURCE) $(IDS) IDE_PORT=$(IDE_PORT) docker compose up -d
	@$(MAKE) --no-print-directory _ready

## Aperture from source (HMR); Mosaic from its pinned image.
dev-web: init
	env COMPOSE_PROFILES=aperture-source,mosaic-image \
		$(WEB_SOURCE) $(API_IMAGE) $(IDS) IDE_PORT=$(IDE_PORT) docker compose up -d
	@$(MAKE) --no-print-directory _ready

## Mosaic from source (--reload); Aperture from its published image.
dev-api: init
	env COMPOSE_PROFILES=aperture-image,mosaic-source \
		$(WEB_IMAGE) $(API_SOURCE) $(IDS) IDE_PORT=$(IDE_PORT) docker compose up -d
	@$(MAKE) --no-print-directory _ready

_ready:
	@echo ""
	@echo "ide up — http://localhost:$(IDE_PORT)"
	@echo "  /graphql  data plane      /docs  API docs      /health  liveness"
	@echo ""
	@echo "Source profiles install node_modules into a named volume on first"
	@echo "run ('make logs-web' to watch); later starts are instant."

## Apply additive schema changes, then restart the API so it re-reads them.
## Mirrors solo's restart-on-migrate model (decision 1.7). Works against
## whichever mosaic service is running.
migrate:
	@svc=$$(docker compose ps --services --status running | grep -E '^mosaic(-dev)?$$' | head -1); \
	if [ -z "$$svc" ]; then echo "no mosaic service running — 'make up' or 'make dev' first" >&2; exit 1; fi; \
	echo "ide: migrating via $$svc"; \
	docker compose exec -w /project/schemas "$$svc" \
		mosaic migrate --schema-dir . --db-path /project/data/mosaic.db; \
	docker compose restart "$$svc"

## Pick up Mosaic source changes (~1s). Stands in for `mosaic serve --reload`,
## which exits the process as shipped — see the note in docker-compose.yml.
reload-api:
	@svc=$$(docker compose ps --services --status running | grep -E '^mosaic(-dev)?$$' | head -1); \
	if [ -z "$$svc" ]; then echo "no mosaic service running" >&2; exit 1; fi; \
	docker compose restart "$$svc"

## Follow everything.
logs:
	docker compose logs -f

## Follow just the Vite dev server (dependency install, HMR, build errors).
logs-web:
	docker compose logs -f aperture-dev

ps:
	docker compose ps

down:
	docker compose --profile aperture-image --profile aperture-source \
		--profile mosaic-image --profile mosaic-source down

## down + drop the node_modules volume (forces a clean reinstall).
clean:
	docker compose --profile aperture-image --profile aperture-source \
		--profile mosaic-image --profile mosaic-source down -v

help:
	@grep -E '^##' Makefile | sed 's/## //'
