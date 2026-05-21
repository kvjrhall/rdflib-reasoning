# Retract Inferences

Use ordinary RDFLib removal APIs to retract asserted triples. The engine removes
dependent inferred triples when their support disappears.

```python
from rdflib import Namespace
from rdflib.namespace import RDF, RDFS
from rdflib_reasoning.engine import RDFS_RETE_MATERIALIZED

EX = Namespace("urn:example:")

dataset = RDFS_RETE_MATERIALIZED.dataset()
graph = dataset.default_graph

graph.add((EX.alice, RDF.type, EX.Person))
graph.add((EX.Person, RDFS.subClassOf, EX.Animal))

assert (EX.alice, RDF.type, EX.Animal) in graph

graph.remove((EX.alice, RDF.type, EX.Person))

assert (EX.alice, RDF.type, EX.Animal) not in graph
```

Retraction is support-aware: removing one asserted triple retracts only the
inferences that depended on that assertion. Other asserted triples and
independently supported inferences remain.

For a complete walkthrough, see the
[RDFS retraction tutorial](../tutorials/notebooks/demo-rdfs-retraction.ipynb).
For API details, see {doc}`../autoapi/engine/rete_store/index`.
