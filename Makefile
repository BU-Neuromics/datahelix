# DataHelix Platform Test Runner
# See TESTING.md for the full test strategy and failure protocol.

.PHONY: test test-unit test-contracts test-platform test-all help \
        ledger-test ledger-assemble ledger-query certify-local deploy-gate

PYTHONPATH := hippo/src:canon/src:cappella/src:aperture/src
export PYTHONPATH

## Run all tiers in order (fails fast at each stage)
test: test-unit test-contracts test-platform
	@echo ""
	@echo "✅ All tiers passed."

## Tier 1: Component unit tests
test-unit:
	@echo "── Tier 1: Mosaic unit tests ─────────────────────────────────"
	cd hippo && uv run pytest tests/ -v --tb=short -q
	@echo "── Tier 1: Canon unit tests ──────────────────────────────────"
	cd canon && uv run pytest tests/ -v --tb=short -q

## Tier 2: Contract tests (behavioral API specs)
test-contracts:
	@echo "── Tier 2: Contract tests ────────────────────────────────────"
	uv run pytest tests/contracts/ -v --tb=short

## Tier 3: Platform integration tests (real Mosaic + Canon in-process)
test-platform:
	@echo "── Tier 3: Platform tests ────────────────────────────────────"
	uv run pytest tests/platform/ -v --tb=short

## Run all tiers without stopping on failure (full report)
test-all:
	@echo "── Tier 1: Mosaic unit tests ─────────────────────────────────"
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

## ── Certification / certified-frontier ledger (platform ADR-0001) ──

## Run the ledger tooling unit tests
ledger-test:
	cd certification && uv run --with pytest python -m pytest tests/ -q

## Rebuild compatibility.json from the certified/* ledger tags
ledger-assemble:
	cd certification && python3 -m ledger.cli --repo .. assemble --out compatibility.json

## Query partner versions certified with a line, e.g. ANCHOR=aperture LINE=1.4.* PARTNER=mosaic
## ("mosaic" and the legacy "hippo" name are the same component line — decision 1.7)
ledger-query:
	cd certification && python3 -m ledger.cli --repo .. query \
		--anchor "$(ANCHOR)" --line "$(LINE)" --partner "$(PARTNER)"

## Boot the pinned composition and run the golden-path suite locally (needs published images)
certify-local:
	MOSAIC_IMAGE=$${MOSAIC_IMAGE:?set to <image>@<digest>} \
	APERTURE_IMAGE=$${APERTURE_IMAGE:?set to <image>@<digest>} \
	bash certification/scripts/run_composition.sh

## Deploy pre-flight: refuse an uncertified pair (wire into your deploy tooling)
deploy-gate:
	bash certification/scripts/deploy_gate.sh certification/composition.lock.json

## ── Container deployment ────────────────────────────────────
## The hand-rolled root docker-compose stack was removed — single-node
## container deployment is now a packaged recipe. See deploy/recipes/solo/
## (its own Makefile: make init / up / migrate / down), boot-tested by the
## `Solo recipe` CI workflow.

help:
	@grep -E '^##' Makefile | sed 's/## //'
