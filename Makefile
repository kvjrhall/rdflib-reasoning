.PHONY: audit check clean docs docs-linkcheck docs-serve help install install-all install-dev install-research notebook specs specs-fetch specs-index specs-normalize test validate

PYTHON ?= python
TESTS ?=

help:  # show this help (targets and descriptions)
	@echo "Targets:"
	@awk -F'[:#]' '/^[a-zA-Z0-9_-]+:.*#/ {gsub(/^[ \t]+/,"",$$3); printf "  %-12s %s\n", $$1, $$3}' $(MAKEFILE_LIST)

check: install-dev  # install dev deps, then execute all pre-commit hooks
	uv run pre-commit run --all-files

audit: install-dev  # audit the resolved Python environment for known vulnerabilities
	uv run pip-audit

clean:  # remove generated docs, test, coverage, and build artifacts
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf docs-build
	rm -rf docs-src/autoapi
	rm -rf htmlcov
	rm -rf site
	rm -rf dist
	rm -rf build
	rm -rf src/*.egg-info
	rm -rf rdflib-reasoning-axioms/src/*.egg-info
	rm -rf rdflib-reasoning-engine/src/*.egg-info
	rm -rf rdflib-reasoning-middleware/src/*.egg-info
	rm -f .coverage
	rm -f coverage.xml

docs: install-dev  # build the Sphinx documentation site
	uv run sphinx-build -W --keep-going -b html docs-src docs-build/html

docs-linkcheck: install-dev  # validate external links referenced by the Sphinx docs
	uv run sphinx-build -W --keep-going -b linkcheck docs-src docs-build/linkcheck

docs-serve: install-dev  # serve the Sphinx documentation site locally
	uv run python -m http.server 8000 --directory docs-build/html

install:  # install the base metapackage workspace
	uv sync

install-dev:  # install base + developer tooling extras
	uv sync --extra dev

install-research:  # install base + notebook/research extras
	uv sync --extra research

install-all:  # install base + all optional extras used in this repository
	uv sync --extra dev --extra research

notebook: install-research  # launch Jupyter Lab from the synced environment
	uv run jupyter lab

test: install-dev  # install dev deps, then run pytest unit tests. E.g., `make test [TESTS=<test_file.py>]`
	uv run pytest $(TESTS)

validate: check  # install dev deps, run all pre-commit hooks, then run mypy
	uv run mypy

specs-fetch:  # fetch raw W3C specs into docs/specs/<name>/raw.html
	bash docs/specs/fetch-w3c.sh
	bash docs/specs/jena-inspiration/fetch-jena.sh

specs-normalize:  # normalize each existing raw.html to optimized.html
	for raw in docs/specs/*/raw.html; do \
	  dir=$$(dirname "$$raw"); \
	  $(PYTHON) docs/specs/w3c-normalize.py "$$raw" -o "$$dir/optimized.html"; \
	done

specs-index:  # generate INDEX.md and index-data.json for indexed specs and crosswalks
	$(PYTHON) docs/specs/rdf11-semantics/create-index.py
	$(PYTHON) docs/specs/owl2-mapping-to-rdf/create-index.py
	$(PYTHON) docs/specs/owl2-reasoning-profiles/create-index.py
	$(PYTHON) docs/specs/owl2-semantics-rdf/create-index.py
	$(PYTHON) docs/specs/owl2-crosswalks/create-crosswalks.py

specs: specs-fetch specs-normalize specs-index  # fetch, normalize, and build all indexed spec and crosswalk artifacts
