.PHONY: check help install install-all install-dev install-research notebook specs specs-fetch specs-index specs-normalize test validate

PYTHON ?= python

help:  # show this help (targets and descriptions)
	@echo "Targets:"
	@awk -F'[:#]' '/^[a-zA-Z0-9_-]+:.*#/ {gsub(/^[ \t]+/,"",$$3); printf "  %-12s %s\n", $$1, $$3}' $(MAKEFILE_LIST)

check:  # execute all pre-commit hooks
	uv run pre-commit run --all-files

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

test:  # run pytest unit tests
	uv run pytest

validate: check  # run mypy type check & all pre-commit hooks
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
