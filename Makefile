.PHONY: help install dev test test-all test-cli test-tui test-mcp test-cross test-doctor test-markers test-opencode-plugins test-telegram-plugin test-ubuntu-blackbox test-real-agent-doctor test-real-blackbox test-real-blackbox-codex test-real-blackbox-opencode test-real-blackbox-telegram test-real-opencode-mapper test-coverage _test-coverage-steps lint fmt clean build assess-areas

define timed_step
	@label='$(1)'; \
	start=$$(date +%s); \
	timestamp=$$(date '+%Y-%m-%d %H:%M:%S'); \
	printf '%s [make-timing] START %s\n' "$$timestamp" "$$label"; \
	$(2); \
	status=$$?; \
	end=$$(date +%s); \
	elapsed=$$((end - start)); \
	timestamp=$$(date '+%Y-%m-%d %H:%M:%S'); \
	if [ "$$status" -eq 0 ]; then \
	  printf '%s [make-timing] OK %s elapsed=%ss\n' "$$timestamp" "$$label" "$$elapsed"; \
	else \
	  printf '%s [make-timing] FAIL %s elapsed=%ss exit=%s\n' "$$timestamp" "$$label" "$$elapsed" "$$status"; \
	fi; \
	exit "$$status"
endef

help:
	@printf '%s\n' \
		"Available targets:" \
		"  install       Install local development prerequisites" \
		"  dev           Show local development entrypoints" \
		"  test          Run fast deterministic end-to-end tests" \
		"  test-all      Run fast tests, real blackbox, and coverage" \
		"  test-cli      Run CLI end-to-end tests" \
		"  test-tui      Run TUI end-to-end tests" \
		"  test-mcp      Run MCP selection/config end-to-end tests" \
		"  test-cross    Run cross-mode end-to-end tests" \
		"  test-doctor   Run deterministic doctor end-to-end tests" \
		"  test-markers  Run generated marker and idempotency tests" \
		"  test-opencode-plugins  Run OpenCode plugin deterministic tests" \
		"  test-telegram-plugin   Run Telegram plugin deterministic tests" \
		"  test-ubuntu-blackbox   Run make test in a clean Docker Ubuntu image" \
		"  test-real-agent-doctor  Run real agent doctor checks" \
		"  test-real-blackbox      Run real Codex/OpenCode/Telegram blackbox tests" \
		"  test-real-blackbox-codex  Run real Codex blackbox test" \
		"  test-real-blackbox-opencode  Run real OpenCode blackbox test" \
		"  test-real-blackbox-telegram  Run real OpenCode Telegram blackbox test" \
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
	$(call timed_step,test-cli,bash tests/e2e/cli.e2e.sh)
	$(call timed_step,test-tui,bash tests/e2e/tui.e2e.sh)
	$(call timed_step,test-mcp,bash tests/e2e/mcp.e2e.sh)
	$(call timed_step,test-cross,bash tests/e2e/cross.e2e.sh)
	$(call timed_step,test-opencode-plugins,bash tests/e2e/opencode_plugins.e2e.sh)
	$(call timed_step,test-telegram-plugin,bash tests/e2e/telegram_plugin.e2e.sh)

test-all:
	$(call timed_step,test,$(MAKE) test)
	$(call timed_step,test-doctor,bash tests/e2e/doctor.e2e.sh)
	$(call timed_step,test-markers,bash tests/e2e/markers.e2e.sh)
	$(call timed_step,test-real-blackbox-codex,AGENTIC_REAL_BLACKBOX_ONLY=codex bash tests/e2e/real_agent_blackbox.e2e.sh)
	$(call timed_step,test-real-blackbox-opencode,AGENTIC_REAL_BLACKBOX_ONLY=opencode bash tests/e2e/real_agent_blackbox.e2e.sh)
	$(call timed_step,test-real-opencode-mapper,AGENTIC_REAL_BLACKBOX_ONLY=opencode-mapper bash tests/e2e/real_agent_blackbox.e2e.sh)
	$(call timed_step,test-real-blackbox-telegram,AGENTIC_REAL_BLACKBOX_ONLY=telegram bash tests/e2e/real_agent_blackbox.e2e.sh)
	$(call timed_step,test-coverage,$(MAKE) test-coverage)

test-cli:
	$(call timed_step,test-cli,bash tests/e2e/cli.e2e.sh)

test-tui:
	$(call timed_step,test-tui,bash tests/e2e/tui.e2e.sh)

test-mcp:
	$(call timed_step,test-mcp,bash tests/e2e/mcp.e2e.sh)

test-cross:
	$(call timed_step,test-cross,bash tests/e2e/cross.e2e.sh)

test-doctor:
	$(call timed_step,test-doctor,bash tests/e2e/doctor.e2e.sh)

test-markers:
	$(call timed_step,test-markers,bash tests/e2e/markers.e2e.sh)

test-opencode-plugins:
	$(call timed_step,test-opencode-plugins,bash tests/e2e/opencode_plugins.e2e.sh)

test-telegram-plugin:
	$(call timed_step,test-telegram-plugin,bash tests/e2e/telegram_plugin.e2e.sh)

test-ubuntu-blackbox:
	$(call timed_step,test-ubuntu-blackbox,bash tests/e2e/ubuntu_blackbox.e2e.sh)

test-real-agent-doctor:
	$(call timed_step,test-real-agent-doctor,bash tests/e2e/real_agent_doctor.e2e.sh)

test-real-blackbox:
	$(call timed_step,test-real-blackbox-codex,AGENTIC_REAL_BLACKBOX_ONLY=codex bash tests/e2e/real_agent_blackbox.e2e.sh)
	$(call timed_step,test-real-blackbox-opencode,AGENTIC_REAL_BLACKBOX_ONLY=opencode bash tests/e2e/real_agent_blackbox.e2e.sh)
	$(call timed_step,test-real-opencode-mapper,AGENTIC_REAL_BLACKBOX_ONLY=opencode-mapper bash tests/e2e/real_agent_blackbox.e2e.sh)
	$(call timed_step,test-real-blackbox-telegram,AGENTIC_REAL_BLACKBOX_ONLY=telegram bash tests/e2e/real_agent_blackbox.e2e.sh)

test-real-blackbox-codex:
	$(call timed_step,test-real-blackbox-codex,AGENTIC_REAL_BLACKBOX_ONLY=codex bash tests/e2e/real_agent_blackbox.e2e.sh)

test-real-blackbox-opencode:
	$(call timed_step,test-real-blackbox-opencode,AGENTIC_REAL_BLACKBOX_ONLY=opencode bash tests/e2e/real_agent_blackbox.e2e.sh)

test-real-blackbox-telegram:
	$(call timed_step,test-real-blackbox-telegram,AGENTIC_REAL_BLACKBOX_ONLY=telegram bash tests/e2e/real_agent_blackbox.e2e.sh)

test-real-opencode-mapper:
	$(call timed_step,test-real-opencode-mapper,AGENTIC_REAL_BLACKBOX_ONLY=opencode-mapper bash tests/e2e/real_agent_blackbox.e2e.sh)

test-coverage:
	@if [ -n "$${AGENTIC_COVERAGE_TRACE_FILE:-}" ]; then \
	  trace_file="$$AGENTIC_COVERAGE_TRACE_FILE"; \
	else \
	  trace_file="$$(mktemp /tmp/agentic-coverage.XXXXXX)"; \
	fi; \
	$(MAKE) _test-coverage-steps AGENTIC_COVERAGE_TRACE_FILE="$$trace_file"

_test-coverage-steps:
	$(call timed_step,test-coverage-agentic,AGENTIC_COVERAGE_TRACE_FILE="$(AGENTIC_COVERAGE_TRACE_FILE)" AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/agentic.e2e.sh >/tmp/agentic-coverage-agentic.log 2>&1)
	$(call timed_step,test-coverage-tui,AGENTIC_COVERAGE_TRACE_FILE="$(AGENTIC_COVERAGE_TRACE_FILE)" AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/tui.e2e.sh >/tmp/agentic-coverage-tui.log 2>&1)
	$(call timed_step,test-coverage-cross,AGENTIC_COVERAGE_TRACE_FILE="$(AGENTIC_COVERAGE_TRACE_FILE)" AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/cross.e2e.sh >/tmp/agentic-coverage-cross.log 2>&1)
	$(call timed_step,test-coverage-markers,AGENTIC_COVERAGE_TRACE_FILE="$(AGENTIC_COVERAGE_TRACE_FILE)" AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/markers.e2e.sh >/tmp/agentic-coverage-markers.log 2>&1)
	$(call timed_step,test-coverage-cli,AGENTIC_COVERAGE_TRACE_FILE="$(AGENTIC_COVERAGE_TRACE_FILE)" AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/cli.e2e.sh >/tmp/agentic-coverage-cli.log 2>&1)
	$(call timed_step,test-coverage-doctor,AGENTIC_COVERAGE_TRACE_FILE="$(AGENTIC_COVERAGE_TRACE_FILE)" AGENTIC_TEST_CLI="$(CURDIR)/tests/e2e/coverage_shim.sh" bash tests/e2e/doctor.e2e.sh >/tmp/agentic-coverage-doctor.log 2>&1)
	$(call timed_step,test-coverage-parse,bash tests/e2e/coverage_parse.sh "$(AGENTIC_COVERAGE_TRACE_FILE)")

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
