# Proofs And Derivations

The engine records derivations as rule applications over RDF facts. A derivation
record is close to execution: it captures the rule, premises, conclusions,
bindings, context, and depth observed while the engine was materializing
inferences or diagnostics.

A proof is a presentation- and interchange-oriented reconstruction over those
records. `DirectProof` gives callers a typed proof tree with a goal, proof node,
verdict, and optional notes. It can be rendered to Markdown or Mermaid text, or
inspected as a Pydantic model.

This separation matters:

- Derivation records are useful for engine-adjacent logging and reconstruction.
- Proof models are useful for package consumers, notebooks, review tools, and
  future evaluation surfaces.
- Renderers are presentation helpers; they do not change the underlying proof
  payload.

Use proof reconstruction when you need to explain why a particular inferred
triple or contradiction was produced. Do not treat it as a replacement for graph
querying; first choose the goal you want to explain.

Related guides:

- [Inspect a proof](../how-to/inspect-a-proof.md)
- [Proof reconstruction tutorial](../tutorials/notebooks/demo-proof-reconstructor.ipynb)
- [Generated proof API](../autoapi/engine/proof/index)
