PYTHON ?= python
PROFILE ?= smoke
SCENARIO ?= base
SEED ?= 20260831

.PHONY: bootstrap db-up db-down migrate seed-canon generate post close validate reports report workbooks package test lint typecheck ci
bootstrap:
	uv sync --all-extras

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	uv run alembic upgrade head

seed-canon:
	uv run shfin seed-canon

generate:
	uv run shfin generate --profile $(PROFILE) --scenario $(SCENARIO) --seed $(SEED)

post:
	uv run shfin post

close:
	uv run shfin close --through 2026-08

validate:
	uv run shfin validate

report:
	uv run shfin report

reports: report

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
