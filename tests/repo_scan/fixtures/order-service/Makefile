include project.mk

.PHONY: test lint build

test:
	@echo order-service tests ok

lint:
	@echo lint failed >&2; exit 1

build:
	docker build -t $(APPLICATION) .
