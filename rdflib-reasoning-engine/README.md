# RDFLib Reasoning Engine

Agentic AI should be able to take advantage of basic reasoning in an efficient manner.

[RDFS](https://www.w3.org/TR/rdf11-mt/#entailment-rules-informative) and [OWL 2 RL reasoning](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs_using_Rules) define the semantics for two entailment regimes.
These regimes can be computed using forward-chaining rules, though practical approaches may also benefit from [special handling for transitive closures](https://jena.apache.org/documentation/inference/index.html#transitive).
The `rdflib-reasoning-engine` package provides an efficient general purpose forward chaining rule engine (i.e., RETE) that works with RDFLib.

## Tutorials and demos

If you want to see the current RDFS inference surface in action, start with:

- [../notebooks/demo-rdfs-inference.ipynb](../notebooks/demo-rdfs-inference.ipynb): compact end-to-end tutorial for RDFLib-backed RDFS materialization plus a proof view of the rule applications behind one inferred triple
- [../notebooks/demo-rdfs-retraction.ipynb](../notebooks/demo-rdfs-retraction.ipynb): ordinary RDFLib `graph.remove(...)` usage with dependency-aware retraction of inferred triples
- [../notebooks/demo-contradiction-rules.ipynb](../notebooks/demo-contradiction-rules.ipynb): dual-channel OWL 2 RL contradiction diagnostics (`ContradictionRecord`), recorder policies, contradiction-goal proof reconstruction, and rendering
- [../notebooks/demo-proof-reconstructor.ipynb](../notebooks/demo-proof-reconstructor.ipynb): proof-focused companion notebook covering proof reconstruction, Mermaid rendering, markdown rendering, and raw proof inspection

The RDFLib integration is intentionally ordinary at the call site: adding triples
materializes supported conclusions, and removing asserted triples retracts dependent
conclusions through the same `Graph` API. Contradiction diagnostics are likewise
engine-managed when the active ruleset includes contradiction-producing rules; if no
recorder is supplied, the default policy records the contradiction and raises.

## Feature Matrix

Status values:

- `Implemented`: available in the package today
- `In progress`: scaffolding or partial implementation exists, but the feature is not yet wired end-to-end
- `Not started`: identified feature target with no concrete implementation yet

### RDFS entailment rules

This matrix tracks the intermediate RDFS rule target using the cached RDF 1.1 Semantics specification at [`docs/specs/rdf11-semantics/optimized.html`](../docs/specs/rdf11-semantics/optimized.html). The informative RDFS entailment rules are identified there as `rdfs1` through `rdfs13`.

| Feature | Spec reference | Status |
| --- | --- | --- |
| Property typing | `rdfs1` | Implemented |
| Domain inference | `rdfs2` | Implemented |
| Range inference | `rdfs3` | Implemented |
| Resource typing axioms | `rdfs4a`, `rdfs4b` | Implemented |
| Subproperty transitivity | `rdfs5` | Implemented |
| Every property is a subproperty of itself | `rdfs6` | Implemented |
| Subproperty inheritance | `rdfs7` | Implemented |
| Class typing for `rdfs:Class` | `rdfs8` | Implemented |
| Subclass typing propagation | `rdfs9` | Implemented |
| Every class is a subclass of itself | `rdfs10` | Implemented |
| Subclass transitivity | `rdfs11` | Implemented |
| Container membership property inheritance | `rdfs12` | Implemented |
| Datatype subclass typing | `rdfs13` | Implemented |

### OWL 2 RL contradiction diagnostics (false-family, non-mutating)

These rules do not materialize new entailment triples into logical closure. They emit `ContradictionConsequent` actions and `ContradictionRecord` diagnostics (dual-channel model per DR-027). Coverage is limited by the current rule IR and builtins; see `rdflib_reasoning.engine.rulesets.owl2_rl_contradictions`. Each row tracks exactly one OWL 2 RL rule identifier from [`docs/specs/owl2-reasoning-profiles/INDEX.md`](../docs/specs/owl2-reasoning-profiles/INDEX.md).

| Feature | Spec reference | Status |
| --- | --- | --- |
| Equality conflict (sameAs and differentFrom) | `eq-diff1` | Implemented |
| AllDifferent members equality conflict | `eq-diff2` | Not started |
| DistinctMembers equality conflict | `eq-diff3` | Not started |
| Irreflexive property used reflexively | `prp-irp` | Implemented |
| Asymmetric property used in both directions | `prp-asyp` | Implemented |
| Property disjointness conflict | `prp-pdw` | Not started |
| AllDisjointProperties conflict | `prp-adp` | Not started |
| Negative object property assertion vs positive assertion | `prp-npa1` | Implemented |
| Negative data property assertion vs positive assertion | `prp-npa2` | Implemented |
| Individual typed as `owl:Nothing` | `cls-nothing2` | Implemented |
| Complement class overlap | `cls-com` | Not started |
| Max cardinality zero violation | `cls-maxc1` | Not started |
| Qualified max cardinality zero violation | `cls-maxqc1` | Not started |
| Thing-qualified max cardinality zero violation | `cls-maxqc2` | Not started |
| Disjoint class overlap | `cax-dw` | Not started |
| AllDisjointClasses overlap | `cax-adc` | Not started |
| Datatype value-space violation | `dt-not-type` | Not started |

### OWL 2 RL entailment rules (triple materialization)

The authoritative local reference for this matrix is [`docs/specs/owl2-reasoning-profiles/INDEX.md`](../docs/specs/owl2-reasoning-profiles/INDEX.md), which indexes Section 4.3 of the cached OWL 2 Profiles specification. Status here refers to **forward-chaining materialization** of OWL 2 RL entailment rules. Rule identifiers that have `false` consequents in the specification are listed under [OWL 2 RL contradiction diagnostics](#owl-2-rl-contradiction-diagnostics-false-family-non-mutating) above. Each row tracks exactly one OWL 2 RL rule identifier.

| Feature | Spec reference | Status |
| --- | --- | --- |
| Reflexive equality | `eq-ref` | Not started |
| Symmetric equality | `eq-sym` | Not started |
| Transitive equality | `eq-trans` | Not started |
| Subject equality replacement | `eq-rep-s` | Not started |
| Predicate equality replacement | `eq-rep-p` | Not started |
| Object equality replacement | `eq-rep-o` | Not started |
| Built-in annotation property typing | `prp-ap` | Not started |
| Property domain inference | `prp-dom` | Not started |
| Property range inference | `prp-rng` | Not started |
| Functional property equality | `prp-fp` | Not started |
| Inverse-functional property equality | `prp-ifp` | Not started |
| Symmetric property assertion | `prp-symp` | Not started |
| Transitive property assertion | `prp-trp` | Not started |
| Subproperty assertion inheritance | `prp-spo1` | Not started |
| Property chain assertion | `prp-spo2` | Not started |
| Equivalent property forward assertion | `prp-eqp1` | Not started |
| Equivalent property reverse assertion | `prp-eqp2` | Not started |
| Inverse property forward assertion | `prp-inv1` | Not started |
| Inverse property reverse assertion | `prp-inv2` | Not started |
| HasKey individual equality | `prp-key` | Not started |
| `owl:Thing` class typing | `cls-thing` | Not started |
| `owl:Nothing` class typing | `cls-nothing1` | Not started |
| Intersection membership introduction | `cls-int1` | Not started |
| Intersection membership projection | `cls-int2` | Not started |
| Union membership introduction | `cls-uni` | Not started |
| SomeValuesFrom membership | `cls-svf1` | Not started |
| SomeValuesFrom Thing membership | `cls-svf2` | Not started |
| AllValuesFrom value typing | `cls-avf` | Not started |
| HasValue property assertion | `cls-hv1` | Not started |
| HasValue membership | `cls-hv2` | Not started |
| Max cardinality equality | `cls-maxc2` | Not started |
| Qualified max cardinality equality | `cls-maxqc3` | Not started |
| Thing-qualified max cardinality equality | `cls-maxqc4` | Not started |
| OneOf membership | `cls-oo` | Not started |
| Subclass membership inheritance | `cax-sco` | Not started |
| Equivalent class forward membership | `cax-eqc1` | Not started |
| Equivalent class reverse membership | `cax-eqc2` | Not started |
| Supported datatype typing | `dt-type1` | Not started |
| Literal datatype membership | `dt-type2` | Not started |
| Literal same-value equality | `dt-eq` | Not started |
| Literal different-value inequality | `dt-diff` | Not started |
| Class schema closure | `scm-cls` | Not started |
| Subclass transitivity | `scm-sco` | Not started |
| Equivalent class to subclasses | `scm-eqc1` | Not started |
| Mutual subclasses to equivalent class | `scm-eqc2` | Not started |
| Object property schema closure | `scm-op` | Not started |
| Datatype property schema closure | `scm-dp` | Not started |
| Subproperty transitivity | `scm-spo` | Not started |
| Equivalent property to subproperties | `scm-eqp1` | Not started |
| Mutual subproperties to equivalent property | `scm-eqp2` | Not started |
| Domain subclass propagation | `scm-dom1` | Not started |
| Domain subproperty propagation | `scm-dom2` | Not started |
| Range subclass propagation | `scm-rng1` | Not started |
| Range subproperty propagation | `scm-rng2` | Not started |
| HasValue schema subclass | `scm-hv` | Not started |
| SomeValuesFrom filler subclass | `scm-svf1` | Not started |
| SomeValuesFrom property subclass | `scm-svf2` | Not started |
| AllValuesFrom filler subclass | `scm-avf1` | Not started |
| AllValuesFrom property subclass | `scm-avf2` | Not started |
| Intersection schema projection | `scm-int` | Not started |
| Union schema injection | `scm-uni` | Not started |

### Engine capabilities

This matrix tracks functional engine features independent of standards coverage.

| Feature | Status | Notes |
| --- | --- | --- |
| Alpha memory / node support | Implemented | Shared alpha nodes perform literal filtering and retain persistent alpha memory across incremental updates |
| Beta memory / join node support | Implemented | Shared beta nodes perform left-deep joins and retain persistent partial-match memory across incremental updates |
| Triple pattern matching | Implemented | Public Rule IR, compiler normalization, and `NetworkMatcher` execute RDFLib-variable triple patterns end-to-end |
| Rule firing and agenda management | Implemented | `Agenda` orders activations by salience and breadth-first depth; richer conflict resolution policy remains future work |
| Inference materialization | Implemented | Compiled logical productions execute to fixed point in `RETEEngine`, and `RETEStore` materializes inferred triples into RDFLib contexts |
| RDF triple well-formedness enforcement | Implemented | The engine rejects or warns-and-skips triples with literal subjects or non-IRI predicates, preventing malformed triples from entering working memory or derived outputs |
| Builtin predicate support | Implemented | Predicate conditions compile and execute through the RETE matcher using injected read-only predicate hooks |
| Rule action callbacks | Implemented | Callback consequents execute through the agenda with read-only invocation context so instrumentation and other non-mutating side effects remain visible; richer signature validation and retraction-time policy remain future work |
| Derivation / trace logging | Implemented | Engine-native `DerivationRecord` values are emitted for new logical conclusions produced by fired rules |
| JTMS-compatible support bookkeeping | Implemented | `WorkingMemory`, `DependencyGraph`, and `Justification` records track stated facts and multi-parent support for derived facts |
| JTMS support verification APIs | Implemented | `SupportSnapshot` and `TMSController` verifier methods expose read-only checks for current support, hypothetical support-path invalidation, transitive support, and dependency traversal |
| Recursive retraction | Implemented | `TMSController.retract_triple` performs Mark-Verify-Sweep over the dependency graph; `RETEEngine.retract_triples` composes the TMS primitive, evicts stale alpha/beta partial matches, and is idempotent for already-absent triples; `RETEStore.remove` drives the `BatchDispatcher` chain and re-materializes triples the engine still derives with a `RetractionRematerializeWarning` per DR-025 |
| Triple-goal explanation reconstruction | Implemented | `DerivationProofReconstructor` rebuilds `DirectProof` trees from non-silent derivation records for triple-goal explanations |
| Contradiction detection diagnostics | Implemented | Dual-channel contradiction detection records non-mutating contradiction diagnostics (`ContradictionRecord`) for currently modeled OWL 2 RL `false`-family rules; selectable recorders (`RaiseOnContradictionRecorder` default, `InMemoryContradictionRecorder`, `DropContradictionRecorder`) expose queryable diagnostics where retention applies |
| Contradiction explanation reconstruction | Implemented | `DerivationProofReconstructor` rebuilds contradiction-goal `DirectProof` (verdict `contradiction`) from `ContradictionRecord` diagnostics; premises are surfaced as leaf facts (nested derivation proofs for each premise are not required by the baseline DR-027 contract); markdown/Mermaid/notebook rendering uses the same `ProofRenderer` path as triple-goal proofs |
| Proof rendering (markdown and Mermaid) | Implemented | Presentation-focused rendering over canonical `DirectProof` data includes namespace-aware shortening and notebook display adapters via optional extras |
| Specialized transitive relation index | Not started | Intended optimization path for `rdfs:subClassOf` and `rdfs:subPropertyOf` first; broader general transitive-property support remains a later design question |

## Current integration baseline

The supported RDFLib integration path is `Store` events -> `BatchDispatcher` ->
`RETEStore` -> `RETEEngine`.

The `rdflib-reasoning-engine` package is part of the `rdflib-reasoning` metapackage.
