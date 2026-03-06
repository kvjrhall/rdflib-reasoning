# RDFLib Reasoning Engine

Agentic AI should be able to take advantage of basic reasoning in an efficient manner.

[RDFS](https://www.w3.org/TR/rdf11-mt/#entailment-rules-informative) and [OWL 2 RL reasoning](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs_using_Rules) define the semantics for two entailment regemes.
These regemes can be computed using forward-chaining rules, though approaches would be smart to provide [special handling for transiive closures](https://jena.apache.org/documentation/inference/index.html#transitive).
The `rdflib-reasoning-engine` package provides an efficient general purpose forward chaining rule engine (i.e., RETE) that works with RDFLib.

The `rdflib-reasoning-engine` package is part of the `rdflib-reasoning` metapackage.
