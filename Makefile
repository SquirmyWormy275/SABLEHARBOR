PYTHON ?= python
PROFILE ?= standard
SCENARIO ?= base
SEED ?= 20260831
RUN_ID ?= $(shell uv run shfin run-id $(PROFILE) --scenario $(SCENARIO) --seed $(SEED))

.PHONY: bootstrap db-up db-down migrate seed-canon generate post close validate reports report workbooks package package-units test lint typecheck ci
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
	uv run shfin post --generation-run-id $(RUN_ID)

close:
	uv run shfin close --through 2026-08 --generation-run-id $(RUN_ID)

validate:
	uv run shfin validate --generation-run-id $(RUN_ID)

report:
	uv run shfin report --generation-run-id $(RUN_ID)

reports: report

workbooks:
	uv run shfin workbooks --generation-run-id $(RUN_ID)

package:
	uv run shfin package-release --generation-run-id $(RUN_ID)

package-units:
	uv run shfin package-business-units --generation-run-id $(RUN_ID)

test:
	uv run pytest

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run mypy src

ci: lint typecheck test
