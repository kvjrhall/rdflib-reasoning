# Materialization And Retraction

`rdflib-reasoning-engine` integrates reasoning with RDFLib by wrapping a store.
Callers continue to use normal RDFLib `Dataset` and `Graph` APIs, while the
reasoning store listens to graph mutations and maintains inferred triples.

Materialization means inferred triples are written into the graph-facing store
as rule conclusions become supported. For RDFS, adding a type assertion and a
subclass chain can immediately make the transitive type visible through normal
membership checks.

Retraction is support-aware. Inferred triples are removed when the asserted
facts that supported them are removed. If another rule path still supports the
same inferred triple, the triple remains visible.

Use this model when you want reasoning to feel like part of ordinary RDFLib
graph usage. Use lower-level engine objects only when you need custom rules,
custom builtins, or per-context control.

Related guides:

- [Run RDFS inference](../how-to/run-rdfs-inference.md)
- [Retract inferences](../how-to/retract-inferences.md)
- [RDFS inference tutorial](../tutorials/notebooks/demo-rdfs-inference.ipynb)
- [OWL 2 RL inference tutorial](../tutorials/notebooks/demo-owl2-rl-inference.ipynb)
- [RDFS retraction tutorial](../tutorials/notebooks/demo-rdfs-retraction.ipynb)
