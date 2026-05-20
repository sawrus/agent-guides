.PHONY: help install dev test test-cli test-tui test-cross test-doctor test-markers test-opencode-plugins test-telegram-plugin test-real-agent-doctor test-real-blackbox test-real-opencode-mapper test-coverage lint fmt clean build assess-areas

help:
	@printf '%s\n' \
		"Available targets:" \
		"  install       Install local development prerequisites" \
		"  dev           Show local development entrypoints" \
		"  test          Run end-to-end tests (all groups)" \
		"  test-cli      Run CLI end-to-end tests" \
		"  test-tui      Run TUI end-to-end tests" \
		"  test-cross    Run cross-mode end-to-end tests" \
		"  test-doctor   Run deterministic doctor end-to-end tests" \
		"  test-markers  Run generated marker and idempotency tests" \
		"  test-opencode-plugins  Run OpenCode plugin deterministic tests" \
		"  test-telegram-plugin   Run Telegram plugin deterministic tests" \
		"  test-real-agent-doctor  Run real agent doctor checks" \
		"  test-real-blackbox      Run real Codex/OpenCode/Telegram blackbox tests" \
		"  test-real-opencode-mapper  Run real OpenCode mapper input blackbox" \
		"  test-coverage  Run traced e2e coverage for agentic" \
		"  lint          Run prompt and catalog validation" \
		"  fmt           Check formatting hooks placeholder" \
		"  clean         Remove generated reports" \
		"  build         Build generated docs catalog" \
		"  assess-areas  Generate area quality scorecards"

install:
	@printf '%s\n' "No install step required."

dev:
	@printf '%s\n' "Use ./agentic tui or ./agentic install ..."

test:
	bash tests/e2e/cli.e2e.sh
	bash tests/e2e/tui.e2e.sh
	bash tests/e2e/cross.e2e.sh
	bash tests/e2e/doctor.e2e.sh
	bash tests/e2e/markers.e2e.sh
	bash tests/e2e/opencode_plugins.e2e.sh
	bash tests/e2e/telegram_plugin.e2e.sh
	bash tests/e2e/real_agent_blackbox.e2e.sh
	$(MAKE) test-coverage

test-cli:
	bash tests/e2e/cli.e2e.sh

test-tui:
	bash tests/e2e/tui.e2e.sh

test-cross:
	bash tests/e2e/cross.e2e.sh

test-doctor:
	bash tests/e2e/doctor.e2e.sh

test-markers:
	bash tests/e2e/markers.e2e.sh

test-opencode-plugins:
	bash tests/e2e/opencode_plugins.e2e.sh

test-telegram-plugin:
	bash tests/e2e/telegram_plugin.e2e.sh

test-real-agent-doctor:
	bash tests/e2e/real_agent_doctor.e2e.sh

test-real-blackbox:
	bash tests/e2e/real_agent_blackbox.e2e.sh

test-real-opencode-mapper:
	AGENTIC_REAL_BLACKBOX_ONLY=opencode-mapper bash tests/e2e/real_agent_blackbox.e2e.sh

test-coverage:
	AGENTIC_COVERAGE_TRACE_FILE=$$(mktemp /tmp/agentic-coverage.XXXXXX) bash -c 'AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/agentic.e2e.sh >/tmp/agentic-coverage-agentic.log 2>&1 && AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/tui.e2e.sh >/tmp/agentic-coverage-tui.log 2>&1 && AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/cross.e2e.sh >/tmp/agentic-coverage-cross.log 2>&1 && AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/markers.e2e.sh >/tmp/agentic-coverage-markers.log 2>&1 && AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/cli.e2e.sh >/tmp/agentic-coverage-cli.log 2>&1 && AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/doctor.e2e.sh >/tmp/agentic-coverage-doctor.log 2>&1 && bash tests/e2e/coverage_parse.sh "$$AGENTIC_COVERAGE_TRACE_FILE"'

lint:
	bash -n agentic
	python3 -m py_compile scripts/build_docs_catalog.py scripts/lint_prompts.py scripts/assess_area_quality.py
	python3 scripts/lint_prompts.py --strict
	python3 scripts/build_docs_catalog.py --validate --output /tmp/agentic-catalog-check.json

fmt:
	@printf '%s\n' "No formatter configured."

clean:
	rm -f reports/area-quality.json reports/area-quality.md

build:
	python3 scripts/build_docs_catalog.py --output docs/site/catalog.json --validate

assess-areas:
	python3 scripts/assess_area_quality.py --json-output reports/area-quality.json --markdown-output reports/area-quality.md
