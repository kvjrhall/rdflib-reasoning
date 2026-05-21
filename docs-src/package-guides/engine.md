# Engine Package

The `rdflib-reasoning-engine` package provides the RDFLib-integrated reasoning
core. Its current baseline centers on RDFLib-backed fixed-point materialization,
dependency-aware retraction, contradiction diagnostics when contradiction rules
are enabled, derivation logging, and RDFS rule support.

Use this package when you need:

- forward-chaining rule execution over RDFLib-backed data;
- RDFS entailment support;
- statement retraction through ordinary RDFLib `Graph.remove(...)` calls;
- contradiction diagnostics through enabled OWL 2 RL contradiction rules or
  custom rules using `ContradictionConsequent`;
- proof and derivation reconstruction primitives;
- RDF 1.1 triple well-formedness enforcement at the engine boundary.

For a quick tour of the direct engine surface, see:

- [RDFS inference demo](../tutorials/notebooks/demo-rdfs-inference.ipynb)
- [RDFS retraction demo](../tutorials/notebooks/demo-rdfs-retraction.ipynb)
- [Contradiction rules demo](../tutorials/notebooks/demo-contradiction-rules.ipynb)

For focused tasks, see:

- [Run RDFS inference](../how-to/run-rdfs-inference.md)
- [Retract inferences](../how-to/retract-inferences.md)
- [Inspect a proof](../how-to/inspect-a-proof.md)
- [Enable contradiction diagnostics](../how-to/enable-contradiction-diagnostics.md)

For conceptual background, see:

- [Materialization and retraction](../concepts/materialization-and-retraction.md)
- [Proofs and derivations](../concepts/proofs-and-derivations.md)
- [Contradiction diagnostics](../concepts/contradiction-diagnostics.md)

For generated API docs, see {doc}`../autoapi/engine/index`.
