# Getting Started

## Install

Install the published metapackage:

```sh
pip install rdflib-reasoning
```

The metapackage depends on the published component packages:

- `rdflib-reasoning-axioms`
- `rdflib-reasoning-engine`
- `rdflib-reasoning-middleware`

Component packages can also be installed directly when you only need one part
of the system.

## Local Checkout

Development in this repository is expected to use the `rdflib-reasoning` conda
environment.

Base install:

```sh
uv sync
```

Developer tooling:

```sh
uv sync --extra dev
```

Notebook and research tooling:

```sh
uv sync --extra research
```

Full local workspace:

```sh
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
