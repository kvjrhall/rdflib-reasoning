# Engine Package

The `rdflib-reasoning-engine` package provides the reasoning core for the repository. Its
current baseline centers on RDFLib-backed fixed-point materialization, dependency-aware
retraction, contradiction diagnostics when contradiction rules are enabled, derivation
logging, and the RDFS rule baseline described in the architecture and roadmap.

Use this package when you need:

- forward-chaining rule execution over RDFLib-backed data
- RDFS entailment support
- statement retraction through ordinary RDFLib `Graph.remove(...)` calls
- contradiction diagnostics through enabled OWL 2 RL contradiction rules (or custom rules having `ContradictionConsequent`)
- proof and derivation reconstruction primitives
- RDF 1.1 triple well-formedness enforcement at the engine boundary

For a quick tour of the direct engine surface, see:

- [RDFS inference demo](../../notebooks/demo-rdfs-inference.ipynb)
- [RDFS retraction demo](../../notebooks/demo-rdfs-retraction.ipynb)
- [Contradiction rules demo](../../notebooks/demo-contradiction-rules.ipynb)

For generated API docs, see {doc}`../autoapi/engine/index`.
