.PHONY: help live live-primitives verify

help:
	@echo "live - paid synthetic JEV experiment; capped at 0.01 USD by default"
	@echo "live-primitives - append one mixed-type call within the same saved budget"
	@echo "verify - validate and summarize saved responses offline"

live:
	PYTHONDONTWRITEBYTECODE=1 python3 docs/jev-rnd/experiment.py

live-primitives:
	PYTHONDONTWRITEBYTECODE=1 JEV_RND_PRIMITIVES=1 python3 docs/jev-rnd/experiment.py

verify:
	PYTHONDONTWRITEBYTECODE=1 python3 docs/jev-rnd/analyze.py
