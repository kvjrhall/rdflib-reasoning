# Run OWL 2 RL Inference

Use `OWL2_RL_RETE_MATERIALIZED` when you want RDFLib graph writes to maintain
OWL 2 RL closure automatically.

```python
from rdflib import Namespace
from rdflib.namespace import OWL, RDF
from rdflib_reasoning.engine import OWL2_RL_RETE_MATERIALIZED

EX = Namespace("urn:example:")

dataset = OWL2_RL_RETE_MATERIALIZED.dataset()
graph = dataset.default_graph

graph.add((EX.Person, OWL.equivalentClass, EX.Human))
graph.add((EX.alice, RDF.type, EX.Person))

assert (EX.alice, RDF.type, EX.Human) in graph
```

The returned object is an ordinary RDFLib `Dataset`; the reasoner is attached
through the dataset store. Add triples through the normal RDFLib APIs.

The specification includes both OWL 2 RL entailment rules and contradiction
diagnostics. The default recorder policy raises when a contradiction is
detected; see [Enable contradiction diagnostics](enable-contradiction-diagnostics.md)
to retain records without raising.

For API details, see {doc}`../autoapi/engine/api/index`.
