.PHONY: test test-unit test-integration test-cov install-test lint clean \
	docker-build docker-run docker-stop docker-logs docker-shell docker-clean \
	dev run install

# Development commands
install:
	uv sync

dev:
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

run:
	uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Docker commands
docker-build:
	docker build -t pooled-app .

docker-run:
	docker run -d --name pooled-app -p 8000:8000 pooled-app

docker-run-it:
	docker run -it --rm --name pooled-app -p 8000:8000 pooled-app

docker-stop:
	docker stop pooled-app || true
	docker rm pooled-app || true

docker-logs:
	docker logs -f pooled-app

docker-shell:
	docker exec -it pooled-app /bin/bash

docker-health:
	docker inspect --format='{{.State.Health.Status}}' pooled-app

docker-clean:
	docker stop pooled-app || true
	docker rm pooled-app || true
	docker rmi pooled-app || true

docker-restart: docker-stop docker-build docker-run

# Install test dependencies
install-test:
	uv sync --extra test

# Run all tests
test:
	uv run pytest

# Run only unit tests
test-unit:
	uv run pytest tests/unit/ -m unit

# Run only integration tests  
test-integration:
	uv run pytest tests/integration/ -m integration

# Run tests with coverage report
test-cov:
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Run tests with verbose output
test-verbose:
	uv run pytest -v

# Run specific test file
test-file:
	uv run pytest $(FILE) -v

# Run tests and generate coverage badge
test-badge:
	uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# Clean test artifacts
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Install and run tests
install-and-test: install-test test
