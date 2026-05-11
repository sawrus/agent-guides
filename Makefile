.PHONY: help install dev test test-cli test-tui test-cross lint fmt clean build assess-areas

help:
	@printf '%s\n' \
		"Available targets:" \
		"  install       Install local development prerequisites" \
		"  dev           Show local development entrypoints" \
		"  test          Run end-to-end tests (all groups)" \
		"  test-cli      Run CLI end-to-end tests" \
		"  test-tui      Run TUI end-to-end tests" \
		"  test-cross    Run cross-mode end-to-end tests" \
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

test-cli:
	bash tests/e2e/cli.e2e.sh

test-tui:
	bash tests/e2e/tui.e2e.sh

test-cross:
	bash tests/e2e/cross.e2e.sh

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
