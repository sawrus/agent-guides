# Agentic (Rust) development Makefile.
# Rust binary targets plus content-tooling targets for areas/docs.

CARGO ?= cargo
COVERAGE_MIN ?= 80

.PHONY: help install dev build release-build test test-unit test-integration \
	e2e test-coverage lint fmt clean check-no-pycache check-version-sync \
	lint-content test-content build-docs sync-diagrams assess-areas jev-rnd-verify blackbox blackbox-codex blackbox-opencode blackbox-claude test-jev-hooks test-notify test-jev-sdk test-gate \
	context-budget bench-v1 bench-prepare bench bench-selftest bench-report bench-regrade

help:
	@echo "Agentic Makefile targets:"
	@echo "  build            - cargo build (debug)"
	@echo "  release-build    - cargo build --release (self-contained binary)"
	@echo "  test             - all tests: unit + integration + e2e blackbox"
	@echo "  test-unit        - unit tests only (cargo test --bin agentic)"
	@echo "  test-integration - CLI integration tests (tests/cli.rs)"
	@echo "  test-content     - post-task review content contract tests"
	@echo "  e2e              - offline e2e tests with fake agent CLIs"
	@echo "  test-coverage    - coverage with $(COVERAGE_MIN)% line gate (cargo llvm-cov)"
	@echo "  lint             - cargo fmt --check + clippy -D warnings + content lint"
	@echo "  fmt              - cargo fmt"
	@echo "  clean            - cargo clean + report cleanup"
	@echo "  install          - install release binary to ~/.local/bin"
	@echo "  build-docs       - build docs catalog (content tooling)"
	@echo "  sync-diagrams    - sync workflow diagrams (content tooling)"
	@echo "  assess-areas     - area quality scorecards (content tooling)"
	@echo "  jev-rnd-verify   - inspect saved research results offline"
	@echo "  test-notify      - offline Telegram notifier tests (fake Bot API)"
	@echo "  test-gate        - offline quality gate tests (Stop checks, PreToolUse guard)"
	@echo "  blackbox         - real local Codex/OpenCode/Claude + JEV calculator checks (paid)"
	@echo "  blackbox-codex   - real Codex + JEV calculator check"
	@echo "  blackbox-opencode - real OpenCode V2 + JEV calculator check"
	@echo "  blackbox-claude  - real Claude Code + JEV + Telegram hook calculator check"
	@echo "  context-budget   - offline always-on context tokens per host (K1)"
	@echo "  bench-selftest   - offline check of the SDLC benchmark graders"
	@echo "  bench-v1         - build the v1 baseline binary from BENCH_V1_REF"
	@echo "  bench-prepare    - create benchmark projects and installs, no model calls"
	@echo "  bench            - real plain/v1/lean SDLC benchmark (paid, BENCH_ARGS)"
	@echo "  bench-regrade    - offline: grade saved benchmark cells with the current tasks.json"
	@echo "  bench-report     - offline Markdown report from saved benchmark results"

build:
	$(CARGO) build

jev-rnd-verify:
	$(MAKE) -f docs/jev-rnd/Makefile verify

# Live tests consume JEV quota and the locally authenticated agent's quota.
BLACKBOX_ARGS ?=
blackbox: build
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/blackbox_jev.py --host all $(BLACKBOX_ARGS)

blackbox-codex: build
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/blackbox_jev.py --host codex $(BLACKBOX_ARGS)

blackbox-opencode: build
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/blackbox_jev.py --host opencode $(BLACKBOX_ARGS)

blackbox-claude: build
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/blackbox_jev.py --host claude $(BLACKBOX_ARGS)

# Offline: always-on context estimate; set CONTEXT_BUDGET_MAX to fail above a token budget.
CONTEXT_BUDGET_MAX ?=
context-budget: build
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/context_budget.py $(if $(CONTEXT_BUDGET_MAX),--max-tokens $(CONTEXT_BUDGET_MAX))

# SDLC benchmark (docs/agentic-v2-lean/README.md). Only `bench` calls models and spends quota.
BENCH_V1_REF ?= b92d7ef
BENCH_OUT ?= .agentic-blackbox/bench
BENCH_ARGS ?=
bench-selftest:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/bench_sdlc.py --selftest

bench-v1:
	@test -d target/bench-v1 || git worktree add --detach target/bench-v1 $(BENCH_V1_REF)
	cd target/bench-v1 && $(CARGO) build -q

bench-prepare: build
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/bench_sdlc.py --prepare-only --out $(BENCH_OUT) $(BENCH_ARGS)

bench: build
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/bench_sdlc.py --out $(BENCH_OUT) $(BENCH_ARGS)

bench-regrade:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/bench_sdlc.py --out $(BENCH_OUT) --regrade

bench-report:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/bench_sdlc.py --out $(BENCH_OUT) --report $(BENCH_OUT)/report.md

test-jev-hooks:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=extensions/codex/hooks/jev:tests/notify python3 -m unittest discover -s tests/jev

test-gate:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=extensions/codex/hooks/gate python3 -m unittest discover -s tests/gate

test-notify:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=extensions/codex/hooks/notify:tests/notify python3 -m unittest discover -s tests/notify

release-build:
	$(CARGO) build --release

install: release-build
	./target/release/agentic self-install --force

dev:
	@echo "Run: cargo run -- tui"

test: test-unit test-integration e2e test-content test-jev-hooks test-notify test-gate bench-selftest

test-content:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3 -m unittest discover -s tests/content

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
	$(MAKE) check-version-sync
	$(MAKE) lint-content

fmt:
	$(CARGO) fmt

clean:
	$(CARGO) clean
	rm -f reports/area-quality.json reports/area-quality.md

# --- Content tooling (areas/docs payload, unchanged from the bash era) ---

lint-content:
	PYTHONPYCACHEPREFIX=/tmp/agentic-pycache-check python3 -m py_compile extensions/codex/hooks/gate/gate.py scripts/context_budget.py scripts/bench_sdlc.py scripts/build_docs_catalog.py scripts/lint_prompts.py scripts/lint_review_pipeline.py scripts/assess_area_quality.py scripts/sync_workflow_diagrams.py
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/lint_prompts.py --strict
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/lint_review_pipeline.py
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_workflow_diagrams.py --check
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_docs_catalog.py --validate --output /tmp/agentic-catalog-check.json
	$(MAKE) check-no-pycache

check-version-sync:
	@cargo_version=$$(sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -n1); \
	npm_version=$$(node -p "require('./package.json').version" 2>/dev/null || \
		sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' package.json | head -n1); \
	if [ "$$cargo_version" != "$$npm_version" ]; then \
		echo "[agentic][error] version mismatch: Cargo.toml=$$cargo_version package.json=$$npm_version"; exit 1; \
	fi

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

# Pinned SDK check; install dependencies into SDK_DIR, outside the project.
SDK_DIR ?= /tmp/agentic-jev-sdk
test-jev-sdk:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_jev_sdk.py --sdk-dir $(SDK_DIR)
