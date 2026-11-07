# Inspect a Proof

Attach an in-memory derivation logger when you need to reconstruct a
`DirectProof` for an inferred triple.

```python
from dataclasses import replace

from rdflib_reasoning.engine import (
    RDFS_RETE_MATERIALIZED,
    DerivationProofReconstructor,
    InMemoryDerivationLogger,
    TripleFact,
    render_proof_markdown,
)

logger = InMemoryDerivationLogger()
spec = replace(
    RDFS_RETE_MATERIALIZED,
    derivation_logger_factory=lambda _context: logger,
)

dataset = spec.dataset()
graph = dataset.default_graph

# Add asserted triples, then choose the inferred triple you want to explain.
goal = TripleFact(context=graph.identifier, triple=(subject, predicate, object_))
proof = DerivationProofReconstructor().reconstruct(goal, logger.records)

print(render_proof_markdown(proof, namespace_manager=graph.namespace_manager))
```

The proof reconstructor works from derivation records. It is not a
`graph.explain(...)` shortcut; callers choose the goal and supply the derivation
records they want to inspect.

For rendered examples, see the
[RDFS inference tutorial](../tutorials/notebooks/demo-rdfs-inference.ipynb),
[OWL 2 RL inference tutorial](../tutorials/notebooks/demo-owl2-rl-inference.ipynb),
and
[proof reconstruction tutorial](../tutorials/notebooks/demo-proof-reconstructor.ipynb).
For API details, see {doc}`../autoapi/engine/derivation/index` and
{doc}`../autoapi/engine/proof_rendering/index`.
