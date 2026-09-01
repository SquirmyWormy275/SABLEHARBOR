PYTHON ?= python
PROFILE ?= smoke
SCENARIO ?= base
SEED ?= 20260831

.PHONY: bootstrap migrate generate validate test lint typecheck ci
bootstrap:
	uv sync --all-extras

migrate:
	uv run shfin init-db

generate:
	uv run shfin generate --profile $(PROFILE) --scenario $(SCENARIO) --seed $(SEED)

validate:
	uv run shfin validate

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

ci: lint typecheck test
