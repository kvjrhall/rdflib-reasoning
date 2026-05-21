# Sphinx Documentation Guidance

The `docs-src/` tree is the source for the published Sphinx documentation site.
It is package-consumer documentation first. It SHOULD make `rdflib-reasoning`
look like a dependable Python package project used in research, not a notebook
archive with incidental package code.

## Audience and Scope

- Write first for downstream Python developers evaluating, installing, using,
  or extending the packages.
- Research context MAY appear when it clarifies motivation, examples, or design
  tradeoffs, but it SHOULD NOT dominate first-contact pages.
- Development Agent-only policy belongs in `AGENTS.md`, `docs/dev/`, or local
  package guidance, not in published user-facing pages unless it directly
  affects package use.
- Generated API details belong in docstrings and AutoAPI output. Curated Sphinx
  pages SHOULD link to API reference pages rather than restating signatures,
  parameter lists, or exhaustive class inventories.

## Content Model

Use the following documentation forms deliberately:

- **Tutorials**: learning-oriented walkthroughs that produce a first successful
  result.
- **How-to guides**: goal-oriented recipes for specific tasks.
- **Concepts**: explanations of RDF, reasoning, middleware, schema boundaries,
  or design tradeoffs needed to use the packages correctly.
- **Reference**: generated API pages from docstrings, plus minimal curated
  navigation and package overview pages.

A new public capability SHOULD usually have at least one curated page when the
generated API reference alone would not teach a package consumer how or why to
use it.

## Drift Policy

Sphinx documentation drift is a correctness issue. When a change affects public
package behavior, installation requirements, package layout, supported
workflows, middleware capabilities, schema-visible behavior, notebook tutorial
paths, or documented examples, the Development Agent MUST update the affected
Sphinx page in the same change or explicitly confirm that no published page
describes the changed behavior.

When moving, renaming, splitting, merging, or deleting public modules, packages,
or examples, the Development Agent MUST review affected toctrees, package-guide
links, API index links, and cross references.

Tutorials and how-to guides SHOULD use examples that are tested or manually
verified. If an example cannot run in the default developer environment, the
page SHOULD name the required optional dependency, external service, credential,
or notebook environment.

Notebook-derived documentation SHOULD link to the source notebook instead of
copying large notebook bodies into Sphinx prose. Reusable Python helpers under
`notebooks/**/*.py` SHOULD be documented as reusable code; notebook cells in
`notebooks/**/*.ipynb` remain demonstration artifacts.

## Validation

- Run `make docs` after changing Sphinx source, toctrees, MyST syntax, cross
  references, AutoAPI configuration, or examples rendered by the published site.
- Run `make check` for Markdown changes.
- Run `make docs-linkcheck` when adding or changing external links on published
  pages, unless the link target is intentionally not reachable in local
  validation.
