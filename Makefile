# BASS Platform Test Runner
# See TESTING.md for the full test strategy and failure protocol.

.PHONY: test test-unit test-contracts test-platform test-all help

PYTHONPATH := hippo/src:canon/src
export PYTHONPATH

## Run all tiers in order (fails fast at each stage)
test: test-unit test-contracts test-platform
	@echo ""
	@echo "✅ All tiers passed."

## Tier 1: Component unit tests
test-unit:
	@echo "── Tier 1: Hippo unit tests ──────────────────────────────────"
	cd hippo && uv run pytest tests/ -v --tb=short -q
	@echo "── Tier 1: Canon unit tests ──────────────────────────────────"
	cd canon && uv run pytest tests/ -v --tb=short -q

## Tier 2: Contract tests (behavioral API specs)
test-contracts:
	@echo "── Tier 2: Contract tests ────────────────────────────────────"
	uv run pytest tests/contracts/ -v --tb=short

## Tier 3: Platform integration tests (real Hippo + Canon in-process)
test-platform:
	@echo "── Tier 3: Platform tests ────────────────────────────────────"
	uv run pytest tests/platform/ -v --tb=short

## Run all tiers without stopping on failure (full report)
test-all:
	@echo "── Tier 1: Hippo unit tests ──────────────────────────────────"
	-cd hippo && uv run pytest tests/ -v --tb=short -q
	@echo "── Tier 1: Canon unit tests ──────────────────────────────────"
	-cd canon && uv run pytest tests/ -v --tb=short -q
	@echo "── Tier 2: Contract tests ────────────────────────────────────"
	-uv run pytest tests/contracts/ -v --tb=short
	@echo "── Tier 3: Platform tests ────────────────────────────────────"
	-uv run pytest tests/platform/ -v --tb=short

## Show xfail tests (known gaps — check if any have been fixed)
test-xfail:
	uv run pytest tests/ -v -r x --tb=short 2>&1 | grep -E "XFAIL|XPASS|xfail"

## ── Docker targets ──────────────────────────────────────────

## Build all Docker images
build:
	docker compose build

## Start the full stack (detached)
up:
	docker compose up -d

## Stop and remove containers
down:
	docker compose down

## Tail logs from all services
logs:
	docker compose logs -f

## Run tests inside containers
docker-test:
	docker compose run --rm hippo hippo --help
	docker compose run --rm canon python -c "import canon; print('canon OK')"
	docker compose run --rm cappella python -c "import cappella; print('cappella OK')"

## Show status of all services
ps:
	docker compose ps

help:
	@grep -E '^##' Makefile | sed 's/## //'
