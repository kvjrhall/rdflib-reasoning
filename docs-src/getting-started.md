# Getting Started

## Environment

Development in this repository is expected to use the `rdflib-reasoning` conda environment.

## Installation

Base install:

```sh
pip install -e .
```

Developer tooling:

```sh
pip install -e .[dev]
```

Notebook and research tooling:

```sh
pip install -e .[research]
```

Full local workspace:

```sh
pip install -e .[dev,research]
```

If you use `uv`, the equivalent commands are:

```sh
uv sync
uv sync --extra dev
uv sync --extra research
uv sync --extra dev --extra research
```

## Common Commands

```sh
make install-all
make check
make validate
make test
make docs
make docs-serve
```

## Documentation Build

- Sphinx generates the HTML site.
- MyST Parser allows the site content to stay Markdown-first.
- API reference pages are generated from Python source via `sphinx-autoapi`.
- Remote API cross references can target external docs such as
  {py:class}`python:dict`, {py:class}`pydantic:BaseModel`, and
  {py:class}`rdflib.graph.Dataset`.
