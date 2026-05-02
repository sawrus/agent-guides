.PHONY: help install dev test lint fmt clean build assess-areas test-unit test-e2e test-blackbox coverage ci

help:
	@printf '%s\n' \
		"Available targets:" \
		"  install       Install local development prerequisites" \
		"  dev           Show local development entrypoints" \
		"  test-unit     Run unit tests" \
		"  test-e2e      Run end-to-end tests" \
		"  test-blackbox Run blackbox contract tests" \
		"  coverage      Run coverage gate (>=80%)" \
		"  test          Run all tests" \
		"  lint          Run prompt and catalog validation" \
		"  fmt           Check formatting hooks placeholder" \
		"  clean         Remove generated reports" \
		"  build         Build generated docs catalog" \
		"  ci            Run full local CI pipeline" \
		"  assess-areas  Generate area quality scorecards"

install:
	@printf '%s\n' "No install step required."

dev:
	@printf '%s\n' "Use ./agentic tui or ./agentic install ..."

test-unit:
	python3 -m unittest discover -s tests/unit -p 'test_*.py'

test-e2e:
	bash tests/e2e/agentic.e2e.sh
	bash tests/e2e/memory_hub.e2e.sh

test-blackbox:
	python3 -m unittest discover -s tests/blackbox -p 'test_*.py'

coverage:
	python3 scripts/coverage_gate.py --threshold 80 --output reports/coverage/summary.json

test: test-unit test-e2e test-blackbox

lint:
	bash -n agentic
	python3 -m py_compile scripts/build_docs_catalog.py scripts/lint_prompts.py scripts/assess_area_quality.py scripts/coverage_gate.py
	python3 scripts/lint_prompts.py --strict
	python3 scripts/build_docs_catalog.py --validate --output /tmp/agentic-catalog-check.json

fmt:
	@printf '%s\n' "No formatter configured."

clean:
	rm -f reports/area-quality.json reports/area-quality.md
	rm -rf reports/coverage

build:
	python3 scripts/build_docs_catalog.py --output docs/site/catalog.json --validate

ci: fmt lint test coverage

assess-areas:
	python3 scripts/assess_area_quality.py --json-output reports/area-quality.json --markdown-output reports/area-quality.md
