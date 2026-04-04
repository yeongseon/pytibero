PYTHON ?= python3
PACKAGE := pytibero

.PHONY: install test test-docker test-e2e-docker lint format check-e2e-env

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest --cov=$(PACKAGE) --cov-report=term-missing --cov-fail-under=95

test-docker:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from unit

check-e2e-env:
	@if [ -z "$$TIBERO_LICENSE_FILE" ]; then \
		echo "TIBERO_LICENSE_FILE is required."; \
		echo "Example: export TIBERO_LICENSE_FILE=/abs/path/to/license.xml"; \
		exit 1; \
	fi
	@if [ ! -f "$$TIBERO_LICENSE_FILE" ]; then \
		echo "TIBERO_LICENSE_FILE does not point to an existing file: $$TIBERO_LICENSE_FILE"; \
		exit 1; \
	fi

test-e2e-docker: check-e2e-env
	docker compose -f docker-compose.e2e.yml up --build --abort-on-container-exit --exit-code-from e2e

lint:
	ruff check .

format:
	ruff format .
