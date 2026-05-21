# Enable Contradiction Diagnostics

Extend a reasoner specification with contradiction rules when you want diagnostic
events for inconsistent patterns. Contradiction rules emit records; they do not
materialize ordinary triples.

```python
from dataclasses import replace

from rdflib_reasoning.engine import (
    OWL2_RL_CONTRADICTION_RULES,
    RDFS_RETE_MATERIALIZED,
    InMemoryContradictionRecorder,
)

recorder = InMemoryContradictionRecorder(warn=False)
spec = replace(
    RDFS_RETE_MATERIALIZED,
    contradiction_recorder_factory=lambda _context: recorder,
).extend(more_rules=OWL2_RL_CONTRADICTION_RULES)

dataset = spec.dataset()
graph = dataset.default_graph

# Add triples that may trigger contradiction rules.
records = recorder.records
```

Use `RaiseOnContradictionRecorder` when contradictions should raise after being
recorded, `InMemoryContradictionRecorder` when callers should inspect records
after graph updates, and `DropContradictionRecorder` when retention is not
needed.

For a complete walkthrough, see the
[contradiction rules tutorial](../tutorials/notebooks/demo-contradiction-rules.ipynb).
For API details, see {doc}`../autoapi/engine/derivation/index` and
{doc}`../autoapi/engine/rulesets/owl2_rl_contradictions/index`.
