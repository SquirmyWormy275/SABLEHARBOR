PYTHON ?= python
PROFILE ?= smoke
SCENARIO ?= base
SEED ?= 20260831

.PHONY: bootstrap migrate generate validate report workbooks package test lint typecheck ci
bootstrap:
	uv sync --all-extras

migrate:
	uv run alembic upgrade head

generate:
	uv run shfin generate --profile $(PROFILE) --scenario $(SCENARIO) --seed $(SEED)

validate:
	uv run shfin validate

report:
	uv run shfin report

workbooks:
	uv run shfin workbooks

package:
	uv run shfin package-release

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

ci: lint typecheck test
