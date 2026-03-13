# Engine Package

The `rdflib-reasoning-engine` package provides the reasoning core for the repository. Its
current baseline centers on add-only fixed-point materialization, derivation logging, and the
RDFS rule baseline described in the architecture and roadmap.

Use this package when you need:

- forward-chaining rule execution over RDFLib-backed data
- RDFS entailment support
- proof and derivation reconstruction primitives
- RDF 1.1 triple well-formedness enforcement at the engine boundary

For generated API docs, see {doc}`../autoapi/engine/index`.
