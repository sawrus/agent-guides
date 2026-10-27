.PHONY: help test lint

help:
	@echo "test - check that every manifest document names apiVersion, kind, and metadata"
	@echo "lint - style checks for manifests"

test:
	python3 tools/check_k8s.py test k8s

lint:
	python3 tools/check_k8s.py lint k8s
