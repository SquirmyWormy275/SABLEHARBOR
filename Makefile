PYTHON ?= python
PROFILE ?= standard
SCENARIO ?= base
SEED ?= 20260831
RUN_ID ?= $(shell uv run shfin run-id $(PROFILE) --scenario $(SCENARIO) --seed $(SEED))

.PHONY: bootstrap db-up db-down migrate seed-canon generate post close validate reports report workbooks package package-units test lint typecheck ci
bootstrap:
	uv sync --frozen --all-extras

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

.PHONY: help check-fast check-wiki check-geo-review check-operations wiki-visual wiki-publish
help:
	@echo 'make bootstrap         Install locked development dependencies'
	@echo 'make check-fast        Lint, types, Wiki links and focused Wiki tests'
	@echo 'make check-wiki        Wiki navigation, accessibility and exporter checks'
	@echo 'make wiki-visual       Browser checks (install Chromium once; see tools/ci/README.md)'
	@echo 'make check-geo-review  Reproduce geographic review batches and their tests'
	@echo 'make check-operations Run business/operations/planning tests without full packaging'
	@echo 'make ci               Full root test suite, lint and types'
	@echo 'make wiki-publish     Publish clean accepted main using existing Git authentication'

check-fast: lint typecheck check-wiki

check-wiki:
	uv run python -m unittest discover -s tests/wiki -q
	uv run python tools/wiki/audit.py --output var/wiki-navigation.json

wiki-visual:
	uv run --with-requirements tools/wiki/visual/requirements.txt python tools/wiki/visual/check.py

check-geo-review:
	uv run python geospatial/adjudication/review_blackridge.py --check
	uv run python -m geospatial.adjudication.review_reference_layers --check
	uv run python -m geospatial.adjudication.review_catalog --check
	uv run python -m pytest geospatial/tests/test_*adjudication.py -q

check-operations:
	uv run python -m pytest enterprise/operations/tests enterprise/business/tests industrial/planning/tests -q

wiki-publish:
	uv run python -m tools.wiki.publish

.PHONY: wiki-freshness
wiki-freshness: ## Compare the published Wiki with current reading inputs
	uv run python -m tools.wiki.freshness
