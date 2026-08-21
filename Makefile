# Agentic (Rust) development Makefile.
# Rust binary targets plus content-tooling targets for areas/docs.

CARGO ?= cargo
COVERAGE_MIN ?= 80

.PHONY: help install dev build release-build test test-unit test-integration \
	e2e test-coverage lint fmt clean check-no-pycache lint-content \
	build-docs sync-diagrams assess-areas

help:
	@echo "Agentic Makefile targets:"
	@echo "  build            - cargo build (debug)"
	@echo "  release-build    - cargo build --release (self-contained binary)"
	@echo "  test             - all tests: unit + integration + e2e blackbox"
	@echo "  test-unit        - unit tests only (cargo test --bin agentic)"
	@echo "  test-integration - CLI integration tests (tests/cli.rs)"
	@echo "  e2e              - real-run blackbox e2e tests (tests/e2e_blackbox.rs)"
	@echo "  test-coverage    - coverage with $(COVERAGE_MIN)% line gate (cargo llvm-cov)"
	@echo "  lint             - cargo fmt --check + clippy -D warnings + content lint"
	@echo "  fmt              - cargo fmt"
	@echo "  clean            - cargo clean + report cleanup"
	@echo "  install          - install release binary to ~/.local/bin"
	@echo "  build-docs       - build docs catalog (content tooling)"
	@echo "  sync-diagrams    - sync workflow diagrams (content tooling)"
	@echo "  assess-areas     - area quality scorecards (content tooling)"

build:
	$(CARGO) build

release-build:
	$(CARGO) build --release

install: release-build
	./target/release/agentic self-install --force

dev:
	@echo "Run: cargo run -- tui"

test: test-unit test-integration e2e

test-unit:
	$(CARGO) test --bin agentic

test-integration:
	$(CARGO) test --test cli

e2e:
	$(CARGO) test --test e2e_blackbox

test-coverage:
	$(CARGO) llvm-cov --fail-under-lines $(COVERAGE_MIN) --summary-only

lint:
	$(CARGO) fmt --check
	$(CARGO) clippy --all-targets -- -D warnings
	$(MAKE) lint-content

fmt:
	$(CARGO) fmt

clean:
	$(CARGO) clean
	rm -f reports/area-quality.json reports/area-quality.md

# --- Content tooling (areas/docs payload, unchanged from the bash era) ---

lint-content:
	PYTHONPYCACHEPREFIX=/tmp/agentic-pycache-check python3 -m py_compile scripts/build_docs_catalog.py scripts/lint_prompts.py scripts/assess_area_quality.py scripts/sync_workflow_diagrams.py
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/lint_prompts.py --strict
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_workflow_diagrams.py --check
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_docs_catalog.py --validate --output /tmp/agentic-catalog-check.json
	$(MAKE) check-no-pycache

check-no-pycache:
	@if find . -path ./target -prune -o -name '__pycache__' -print -o -name '*.pyc' -print | grep -q .; then \
		echo "[agentic][error] __pycache__/*.pyc artifacts found"; exit 1; \
	fi

build-docs:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_workflow_diagrams.py --check
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_docs_catalog.py --output docs/site/catalog.json --validate

sync-diagrams:
	python3 scripts/sync_workflow_diagrams.py

assess-areas:
	python3 scripts/assess_area_quality.py --json-output reports/area-quality.json --markdown-output reports/area-quality.md
