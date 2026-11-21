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

`axiomatize` is the strict graph-lifting entrypoint: it recovers Implemented
OWL 2 structural forms from an RDFLib graph into a deterministic tuple of
`StructuralElement` instances. Unsupported or unclaimed triples raise
`UnsupportedGraphError` rather than returning a partial view. Coverage,
including OWL 2 RL profile notes and forms that are not yet Implemented
(ontology headers, imports, and the annotation axiom family), is documented in
the [axioms package feature matrix](https://github.com/kvjrhall/rdflib-reasoning/blob/main/rdflib-reasoning-axioms/README.md#feature-matrix).

For generated API docs, see {doc}`../autoapi/axiom/index`.
