.PHONY: check help install install-all install-dev install-research notebook specs specs-fetch specs-index specs-normalize test validate

help:  # show this help (targets and descriptions)
	@echo "Targets:"
	@awk -F'[:#]' '/^[a-zA-Z0-9_-]+:.*#/ {gsub(/^[ \t]+/,"",$$3); printf "  %-12s %s\n", $$1, $$3}' $(MAKEFILE_LIST)

check:  # execute all pre-commit hooks
	pre-commit run --all-files

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
	uv run mypy src rdflib-reasoning-axioms/src rdflib-reasoning-engine/src

specs-fetch:  # fetch raw W3C specs into docs/specs/<name>/raw.html
	bash docs/specs/fetch-w3c.sh

specs-normalize: specs-fetch  # normalize each raw.html to optimized.html
	for raw in docs/specs/*/raw.html; do \
	  dir=$$(dirname "$$raw"); \
	  python docs/specs/w3c-normalize.py "$$raw" -o "$$dir/optimized.html"; \
	done

specs-index: specs-normalize  # generate INDEX.md for owl2-mapping-to-rdf
	python docs/specs/owl2-mapping-to-rdf/create-index.py

specs: specs-index  # fetch, normalize, and build OWL-RDF index (run all specs pipeline)
