# Contributing to RDFLib Reasoning

This guide is for human contributors. Development Agent instructions are
defined in the repository [AGENTS.md](../AGENTS.md) files.

## Requirements

- Scripts MUST use `Bash >= 5.3.9`
- Python package installation MUST use `uv`
- Repository validation SHOULD run in the `rdflib-reasoning` conda environment
  when that environment is available.

## Local Setup

Clone the repository, activate the project conda environment, and sync the
workspace with `uv`:

```sh
conda activate rdflib-reasoning
uv sync --extra dev
```

Install notebook and research dependencies when you need to run or update the
checked-in notebooks:

```sh
uv sync --extra dev --extra research
```

The root `Makefile` wraps these setup flows:

- `make install`
- `make install-dev`
- `make install-research`
- `make install-all`
- `make notebook`

## Validation

Run the focused validation command for the kind of change you made:

- Markdown-only documentation changes: `make check`
- Significant Python changes: `make validate test`
- Unit tests only: `make test`
- Linting without type checking: `make check`
- Linting with type checking: `make validate`

If your active shell does not expose the project tools, run validation through
the conda environment:

```sh
conda run --live-stream -n rdflib-reasoning make check
conda run --live-stream -n rdflib-reasoning make validate test
```

`make test` writes coverage artifacts such as `.coverage`, `coverage.xml`, and
`htmlcov/`.

## Development Documentation

Before substantial feature work, release planning, or architecture-affecting
changes, read:

- [docs/dev/architecture.md](../docs/dev/architecture.md)
- [docs/dev/roadmap.md](../docs/dev/roadmap.md)

When a change affects package behavior, middleware capabilities, architecture,
or release scope, keep the implementation, architecture, roadmap, and relevant
decision records aligned.

## Sphinx Documentation

The published documentation site is built from `docs-src/`. It should present
the repository as a dependable Python package project first, with research
context used where it helps explain motivation, examples, or design tradeoffs.

Keep Sphinx pages synchronized with public behavior. If a change affects
installation, package layout, supported workflows, middleware capabilities,
schema-visible behavior, notebook tutorial paths, or documented examples, update
the relevant `docs-src/` page in the same PR or note that no published page is
affected.

Use Sphinx pages for tutorials, how-to guides, conceptual explanations, and
curated navigation. Keep API details in docstrings so generated AutoAPI pages
remain the reference source. Prefer verified examples, and call out optional
dependencies or external services when an example cannot run in the default
developer environment.

Run `make docs` for Sphinx changes. Markdown Sphinx pages should also pass
`make check`.

## Docstrings

Public Python docstrings use Google style and are part of the published API
documentation. Keep docstrings synchronized with behavior in the same change
that modifies public parameters, return values, exceptions, side effects,
schema-visible behavior, tool-visible behavior, supported RDF forms, or any
implementation detail already described by a public docstring.

Reusable notebook helper modules under `notebooks/**/*.py` follow the same
docstring policy. Notebook files under `notebooks/**/*.ipynb` are exempt from
docstring linting because they are demonstration artifacts rather than reusable
Python modules.

`D100` through `D107` are currently ignored while missing public docstrings are
backfilled deliberately. Do not add misleading or stale docstrings, and do not
expand the ignore set for reusable source code. Use `make check` before opening
a PR that changes docstrings or Ruff docstring configuration.

## Notebooks

Notebooks are part of the repository's research record and public examples, not
a separate published package. Use the `research` extra before running or editing
them:

```sh
uv sync --extra dev --extra research
```

For the current notebook entry points and suggested reading order, see
[notebooks/README.md](../notebooks/README.md).

## Publishing

- Merges to `main` publish built distributions to TestPyPI through
  `.github/workflows/build.yml`.
- Releases publish built distributions to PyPI through
  `.github/workflows/release.yml`.
- Publishing MUST use GitHub Actions OIDC Trusted Publishing rather than
  long-lived API tokens.
- GitHub environments MUST remain separate: use `testpypi` for the TestPyPI
  sanity-check workflow and `pypi` for the release workflow.
- Trusted Publishers MUST be configured on TestPyPI for
  `.github/workflows/build.yml` and on PyPI for
  `.github/workflows/release.yml`.
- Trusted Publisher registrations MUST cover each distribution name in this
  repository: `rdflib-reasoning`, `rdflib-reasoning-axioms`,
  `rdflib-reasoning-engine`, and `rdflib-reasoning-middleware`.
