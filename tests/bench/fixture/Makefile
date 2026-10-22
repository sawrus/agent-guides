.PHONY: help test lint

help:
	@echo "test - run unit tests"
	@echo "lint - compile and style checks"

test:
	python3 -m unittest discover -s tests -t .

lint:
	python3 tools/lint.py inventory tests
