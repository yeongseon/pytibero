PYTHON ?= python3
PACKAGE := pytibero

.PHONY: install test test-docker test-e2e-docker lint format

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest --cov=$(PACKAGE) --cov-report=term-missing --cov-fail-under=95

test-docker:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from unit

test-e2e-docker:
	docker compose -f docker-compose.e2e.yml up --build --abort-on-container-exit --exit-code-from e2e

lint:
	ruff check .

format:
	ruff format .

