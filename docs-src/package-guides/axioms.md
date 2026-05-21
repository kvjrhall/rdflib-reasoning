# Axioms Package

The `rdflib-reasoning-axioms` package defines graph-backed Pydantic models for
RDF and OWL structural data. It is the package to use when RDF graph content
needs a typed Python representation that can also project back to triples or
quads.

Use this package when you need:

- immutable graph-scoped data models;
- typed structural elements that can emit RDF triples and quads;
- JSON-schema-friendly boundaries for tools, middleware, and downstream Python
  callers.

For generated API docs, see {doc}`../autoapi/axiom/index`.
