# RDFLib Reasoning Engine

Agentic AI should be able to take advantage of basic reasoning in an efficient manner.

[RDFS](https://www.w3.org/TR/rdf11-mt/#entailment-rules-informative) and [OWL 2 RL reasoning](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs_using_Rules) define the semantics for two entailment regimes.
These regimes can be computed using forward-chaining rules, though practical approaches may also benefit from [special handling for transitive closures](https://jena.apache.org/documentation/inference/index.html#transitive).
The `rdflib-reasoning-engine` package provides an efficient general purpose forward chaining rule engine (i.e., RETE) that works with RDFLib.

## Feature Matrix

Status values:

- `Implemented`: available in the package today
- `In progress`: scaffolding or partial implementation exists, but the feature is not yet wired end-to-end
- `Not started`: identified feature target with no concrete implementation yet

### RDFS entailment rules

This matrix tracks the intermediate RDFS rule target using the cached RDF 1.1 Semantics specification at [`docs/specs/rdf11-semantics/optimized.html`](../docs/specs/rdf11-semantics/optimized.html). The informative RDFS entailment rules are identified there as `rdfs1` through `rdfs13`.

| Feature | Spec reference | Status |
| --- | --- | --- |
| Datatype typing propagation | `rdfs1` | Not started |
| Domain inference | `rdfs2` | Not started |
| Range inference | `rdfs3` | Not started |
| Resource typing axioms | `rdfs4a`, `rdfs4b` | Not started |
| Subproperty transitivity | `rdfs5` | Not started |
| Every property is a subproperty of itself | `rdfs6` | Not started |
| Subproperty inheritance | `rdfs7` | Not started |
| Class typing for `rdfs:Class` | `rdfs8` | Not started |
| Subclass typing from membership in `rdfs:Class` | `rdfs9` | Not started |
| Every class is a subclass of itself | `rdfs10` | Not started |
| Subclass transitivity | `rdfs11` | Not started |
| Container membership property typing | `rdfs12` | Not started |
| Datatype subclass typing | `rdfs13` | Not started |

### OWL 2 RL rules

The authoritative local reference for this matrix is [`docs/specs/owl2-reasoning-profiles/INDEX.md`](../docs/specs/owl2-reasoning-profiles/INDEX.md), which indexes Section 4.3 of the cached OWL 2 Profiles specification.

| Feature | Spec reference | Status |
| --- | --- | --- |
| Equality rules | `eq-ref`, `eq-sym`, `eq-trans`, `eq-rep-s`, `eq-rep-p`, `eq-rep-o`, `eq-diff1`, `eq-diff2`, `eq-diff3` | Not started |
| Property assertion and typing rules | `prp-ap`, `prp-dom`, `prp-rng` | Not started |
| Functional and inverse-functional property rules | `prp-fp`, `prp-ifp` | Not started |
| Irreflexive, symmetric, asymmetric, and transitive property rules | `prp-irp`, `prp-symp`, `prp-asyp`, `prp-trp` | Not started |
| Subproperty, equivalent property, and property disjointness rules | `prp-spo1`, `prp-spo2`, `prp-eqp1`, `prp-eqp2`, `prp-pdw`, `prp-adp` | Not started |
| Inverse property rules | `prp-inv1`, `prp-inv2` | Not started |
| Key and negative property assertion rules | `prp-key`, `prp-npa1`, `prp-npa2` | Not started |
| Core class rules | `cls-thing`, `cls-nothing1`, `cls-nothing2`, `cls-int1`, `cls-int2`, `cls-uni`, `cls-com`, `cls-oo` | Not started |
| Some/all values from and has-value rules | `cls-svf1`, `cls-svf2`, `cls-avf`, `cls-hv1`, `cls-hv2` | Not started |
| Max cardinality rules | `cls-maxc1`, `cls-maxc2`, `cls-maxqc1`, `cls-maxqc2`, `cls-maxqc3`, `cls-maxqc4` | Not started |
| Class axiom rules | `cax-sco`, `cax-eqc1`, `cax-eqc2`, `cax-dw`, `cax-adc` | Not started |
| Datatype rules | `dt-type1`, `dt-type2`, `dt-eq`, `dt-diff`, `dt-not-type` | Not started |
| Schema vocabulary rules | `scm-cls`, `scm-sco`, `scm-eqc1`, `scm-eqc2`, `scm-op`, `scm-dp`, `scm-spo`, `scm-eqp1`, `scm-eqp2`, `scm-dom1`, `scm-dom2`, `scm-rng1`, `scm-rng2`, `scm-hv`, `scm-svf1`, `scm-svf2`, `scm-avf1`, `scm-avf2`, `scm-int`, `scm-uni` | Not started |

### Engine capabilities

This matrix tracks functional engine features independent of standards coverage.

| Feature | Status | Notes |
| --- | --- | --- |
| Alpha memory / node support | In progress | Shared alpha nodes now perform literal filtering and retain persistent alpha memory across incremental updates |
| Beta memory / join node support | In progress | Shared beta nodes now perform left-deep joins and retain persistent partial-match memory across incremental updates |
| Triple pattern matching | In progress | Public Rule IR, compiler normalization, and `NetworkMatcher` now execute RDFLib-variable triple patterns end-to-end |
| Rule firing and agenda management | In progress | `Agenda` now orders activations by salience and breadth-first depth; richer conflict resolution policy remains future work |
| Inference materialization | In progress | Compiled logical productions now execute to fixed point in `RETEEngine`, and `RETEStore` materializes inferred triples into RDFLib contexts |
| RDF triple well-formedness enforcement | Implemented | The engine rejects or warns-and-skips triples with literal subjects or non-IRI predicates, preventing malformed triples from entering working memory or derived outputs |
| Builtin predicate / function support | In progress | Predicate conditions compile and execute through the RETE matcher using injected read-only predicate hooks |
| Rule action callbacks | In progress | Callback consequents now execute through the agenda with read-only invocation context; richer signature validation and retraction-time policy remain future work |
| Derivation / trace logging | In progress | Engine-native `DerivationRecord` values are now emitted for new logical conclusions produced by fired rules |
| JTMS-compatible support bookkeeping | In progress | `WorkingMemory`, `DependencyGraph`, and `Justification` records now track stated facts and multi-parent support for derived facts; recursive retraction remains future work |
| Explanation reconstruction | In progress | Proof models and reconstruction protocol exist, but derivation records are not yet rebuilt into concrete `DirectProof` paths |
| Contradiction / inconsistency handling | Not started | Detecting, surfacing, or managing incompatible conclusions |
| Specialized transitive relation index | Not started | Intended optimization path for `rdfs:subClassOf` and `rdfs:subPropertyOf` first; broader general transitive-property support remains a later design question |

## Current integration baseline

The supported RDFLib integration path is `Store` events -> `BatchDispatcher` ->
`RETEStore` -> `RETEEngine`.

The `rdflib-reasoning-engine` package is part of the `rdflib-reasoning` metapackage.
