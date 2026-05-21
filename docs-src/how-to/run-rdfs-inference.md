# Run RDFS Inference

Use `RDFS_RETE_MATERIALIZED` when you want RDFLib graph writes to maintain RDFS
closure automatically.

```python
from rdflib import Namespace
from rdflib.namespace import RDF, RDFS
from rdflib_reasoning.engine import RDFS_RETE_MATERIALIZED

EX = Namespace("urn:example:")

dataset = RDFS_RETE_MATERIALIZED.dataset()
graph = dataset.default_graph

graph.add((EX.alice, RDF.type, EX.Person))
graph.add((EX.Person, RDFS.subClassOf, EX.Mammal))
graph.add((EX.Mammal, RDFS.subClassOf, EX.Animal))

assert (EX.alice, RDF.type, EX.Animal) in graph
```

The returned object is an ordinary RDFLib `Dataset`; the reasoner is attached
through the dataset store. Add triples through the normal RDFLib APIs.

For a complete walkthrough, see the
[RDFS inference tutorial](../tutorials/notebooks/demo-rdfs-inference.ipynb).
For API details, see {doc}`../autoapi/engine/api/index`.
