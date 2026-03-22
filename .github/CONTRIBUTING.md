# Contributing to RDFLib Reasoning

## Requirements

- Scripts MUST use `Bash >= 5.3.9`
- Python package installation MUST use `uv`

## Publishing

- Merges to `main` publish built distributions to TestPyPI through `.github/workflows/build.yml`.
- Releases publish built distributions to PyPI through `.github/workflows/release.yml`.
- Publishing MUST use GitHub Actions OIDC Trusted Publishing rather than long-lived API tokens.
- GitHub environments MUST remain separate: use `testpypi` for the TestPyPI sanity-check workflow and `pypi` for the release workflow.
- Trusted Publishers MUST be configured on TestPyPI for `.github/workflows/build.yml` and on PyPI for `.github/workflows/release.yml`.
- Trusted Publisher registrations MUST cover each distribution name in this repository: `rdflib-reasoning`, `rdflib-reasoning-axioms`, `rdflib-reasoning-engine`, and `rdflib-reasoning-middleware`.
