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

Most applications should start from the canonical reasoner specifications exposed
at the package root. For example, the production RDFS materialization path is:

```python
from rdflib import Namespace
from rdflib.namespace import RDF, RDFS
from rdflib_reasoning.engine import RDFS_RETE_MATERIALIZED

EX = Namespace("urn:example:")

dataset = RDFS_RETE_MATERIALIZED.dataset()
graph = dataset.default_graph

graph.add((EX.alice, RDF.type, EX.Person))
graph.add((EX.Person, RDFS.subClassOf, EX.Mammal))

assert (EX.alice, RDF.type, EX.Mammal) in graph
```

Advanced integrations that need direct per-context engine construction can derive
a fresh `RETEEngineFactory` from the same specification with
`RDFS_RETE_MATERIALIZED.engine_factory()`.

## Feature Matrix

Status values:

- ✅ `Implemented`: available in the package today
- ⬜ `Not started`: identified feature target with no concrete implementation yet
- `In progress`: scaffolding or partial implementation exists, but the feature is not yet wired end-to-end

### RDFS entailment rules

This matrix tracks the intermediate RDFS rule target using the cached RDF 1.1 Semantics specification at [`docs/specs/rdf11-semantics/optimized.html`](../docs/specs/rdf11-semantics/optimized.html). The informative RDFS entailment rules are identified there as `rdfs1` through `rdfs13`.

| Feature | Spec reference | Status |
| --- | --- | --- |
| Property typing | `rdfs1` | ✅ |
| Domain inference | `rdfs2` | ✅ |
| Range inference | `rdfs3` | ✅ |
| Resource typing axioms | `rdfs4a`, `rdfs4b` | ✅ |
| Subproperty transitivity | `rdfs5` | ✅ |
| Every property is a subproperty of itself | `rdfs6` | ✅ |
| Subproperty inheritance | `rdfs7` | ✅ |
| Class typing for `rdfs:Class` | `rdfs8` | ✅ |
| Subclass typing propagation | `rdfs9` | ✅ |
| Every class is a subclass of itself | `rdfs10` | ✅ |
| Subclass transitivity | `rdfs11` | ✅ |
| Container membership property inheritance | `rdfs12` | ✅ |
| Datatype subclass typing | `rdfs13` | ✅ |

### OWL 2 RL contradiction diagnostics (false-family, non-mutating)

These rules do not materialize new entailment triples into logical closure. They emit `ContradictionConsequent` actions and `ContradictionRecord` diagnostics (dual-channel model per DR-027). Coverage is limited by the current rule IR and builtins; see `rdflib_reasoning.engine.rulesets.owl2_rl_contradictions`. Each row tracks exactly one OWL 2 RL rule identifier from [`docs/specs/owl2-reasoning-profiles/INDEX.md`](../docs/specs/owl2-reasoning-profiles/INDEX.md).

| Feature | Spec reference | Status |
| --- | --- | --- |
| Equality conflict (sameAs and differentFrom) | `eq-diff1` | ✅ |
| AllDifferent members equality conflict | `eq-diff2` | ⬜ |
| DistinctMembers equality conflict | `eq-diff3` | ⬜ |
| Irreflexive property used reflexively | `prp-irp` | ✅ |
| Asymmetric property used in both directions | `prp-asyp` | ✅ |
| Property disjointness conflict | `prp-pdw` | ⬜ |
| AllDisjointProperties conflict | `prp-adp` | ⬜ |
| Negative object property assertion vs positive assertion | `prp-npa1` | ✅ |
| Negative data property assertion vs positive assertion | `prp-npa2` | ✅ |
| Individual typed as `owl:Nothing` | `cls-nothing2` | ✅ |
| Complement class overlap | `cls-com` | ⬜ |
| Max cardinality zero violation | `cls-maxc1` | ⬜ |
| Qualified max cardinality zero violation | `cls-maxqc1` | ⬜ |
| Thing-qualified max cardinality zero violation | `cls-maxqc2` | ⬜ |
| Disjoint class overlap | `cax-dw` | ⬜ |
| AllDisjointClasses overlap | `cax-adc` | ⬜ |
| Datatype value-space violation | `dt-not-type` | ⬜ |

### OWL 2 RL entailment rules (triple materialization)

The authoritative local reference for this matrix is [`docs/specs/owl2-reasoning-profiles/INDEX.md`](../docs/specs/owl2-reasoning-profiles/INDEX.md), which indexes Section 4.3 of the cached OWL 2 Profiles specification. Status here refers to **forward-chaining materialization** of OWL 2 RL entailment rules. Rule identifiers that have `false` consequents in the specification are listed under [OWL 2 RL contradiction diagnostics](#owl-2-rl-contradiction-diagnostics-false-family-non-mutating) above. Each row tracks exactly one OWL 2 RL rule identifier.

| Feature | Spec reference | Status |
| --- | --- | --- |
| Reflexive equality | `eq-ref` | ⬜ |
| Symmetric equality | `eq-sym` | ⬜ |
| Transitive equality | `eq-trans` | ⬜ |
| Subject equality replacement | `eq-rep-s` | ⬜ |
| Predicate equality replacement | `eq-rep-p` | ⬜ |
| Object equality replacement | `eq-rep-o` | ⬜ |
| Built-in annotation property typing | `prp-ap` | ⬜ |
| Property domain inference | `prp-dom` | ⬜ |
| Property range inference | `prp-rng` | ⬜ |
| Functional property equality | `prp-fp` | ⬜ |
| Inverse-functional property equality | `prp-ifp` | ⬜ |
| Symmetric property assertion | `prp-symp` | ⬜ |
| Transitive property assertion | `prp-trp` | ⬜ |
| Subproperty assertion inheritance | `prp-spo1` | ⬜ |
| Property chain assertion | `prp-spo2` | ⬜ |
| Equivalent property forward assertion | `prp-eqp1` | ⬜ |
| Equivalent property reverse assertion | `prp-eqp2` | ⬜ |
| Inverse property forward assertion | `prp-inv1` | ⬜ |
| Inverse property reverse assertion | `prp-inv2` | ⬜ |
| HasKey individual equality | `prp-key` | ⬜ |
| `owl:Thing` class typing | `cls-thing` | ⬜ |
| `owl:Nothing` class typing | `cls-nothing1` | ⬜ |
| Intersection membership introduction | `cls-int1` | ⬜ |
| Intersection membership projection | `cls-int2` | ⬜ |
| Union membership introduction | `cls-uni` | ⬜ |
| SomeValuesFrom membership | `cls-svf1` | ⬜ |
| SomeValuesFrom Thing membership | `cls-svf2` | ⬜ |
| AllValuesFrom value typing | `cls-avf` | ⬜ |
| HasValue property assertion | `cls-hv1` | ⬜ |
| HasValue membership | `cls-hv2` | ⬜ |
| Max cardinality equality | `cls-maxc2` | ⬜ |
| Qualified max cardinality equality | `cls-maxqc3` | ⬜ |
| Thing-qualified max cardinality equality | `cls-maxqc4` | ⬜ |
| OneOf membership | `cls-oo` | ⬜ |
| Subclass membership inheritance | `cax-sco` | ⬜ |
| Equivalent class forward membership | `cax-eqc1` | ⬜ |
| Equivalent class reverse membership | `cax-eqc2` | ⬜ |
| Supported datatype typing | `dt-type1` | ⬜ |
| Literal datatype membership | `dt-type2` | ⬜ |
| Literal same-value equality | `dt-eq` | ⬜ |
| Literal different-value inequality | `dt-diff` | ⬜ |
| Class schema closure | `scm-cls` | ⬜ |
| Subclass transitivity | `scm-sco` | ⬜ |
| Equivalent class to subclasses | `scm-eqc1` | ⬜ |
| Mutual subclasses to equivalent class | `scm-eqc2` | ⬜ |
| Object property schema closure | `scm-op` | ⬜ |
| Datatype property schema closure | `scm-dp` | ⬜ |
| Subproperty transitivity | `scm-spo` | ⬜ |
| Equivalent property to subproperties | `scm-eqp1` | ⬜ |
| Mutual subproperties to equivalent property | `scm-eqp2` | ⬜ |
| Domain subclass propagation | `scm-dom1` | ⬜ |
| Domain subproperty propagation | `scm-dom2` | ⬜ |
| Range subclass propagation | `scm-rng1` | ⬜ |
| Range subproperty propagation | `scm-rng2` | ⬜ |
| HasValue schema subclass | `scm-hv` | ⬜ |
| SomeValuesFrom filler subclass | `scm-svf1` | ⬜ |
| SomeValuesFrom property subclass | `scm-svf2` | ⬜ |
| AllValuesFrom filler subclass | `scm-avf1` | ⬜ |
| AllValuesFrom property subclass | `scm-avf2` | ⬜ |
| Intersection schema projection | `scm-int` | ⬜ |
| Union schema injection | `scm-uni` | ⬜ |

### Engine capabilities

This matrix tracks functional engine features independent of standards coverage.

| Feature | Status | Notes |
| --- | --- | --- |
| Alpha memory / node support | ✅ | Shared alpha nodes perform literal filtering and retain persistent alpha memory across incremental updates |
| Beta memory / join node support | ✅ | Shared beta nodes perform left-deep joins and retain persistent partial-match memory across incremental updates |
| Triple pattern matching | ✅ | Public Rule IR, compiler normalization, and `NetworkMatcher` execute RDFLib-variable triple patterns end-to-end |
| Rule firing and agenda management | ✅ | `Agenda` orders activations by salience and breadth-first depth; richer conflict resolution policy remains future work |
| Inference materialization | ✅ | Compiled logical productions execute to fixed point in `RETEEngine`, and `RETEStore` materializes inferred triples into RDFLib contexts |
| RDF triple well-formedness enforcement | ✅ | The engine rejects or warns-and-skips triples with literal subjects or non-IRI predicates, preventing malformed triples from entering working memory or derived outputs |
| Builtin predicate support | ✅ | Predicate conditions compile and execute through the RETE matcher using injected read-only predicate hooks; see [Builtin predicates](#builtin-predicates) |
| Rule action callbacks | ✅ | Callback consequents execute through the agenda with read-only invocation context so instrumentation and other non-mutating side effects remain visible; richer signature validation and retraction-time policy remain future work |
| Derivation / trace logging | ✅ | Engine-native `DerivationRecord` values are emitted for new logical conclusions produced by fired rules |
| JTMS-compatible support bookkeeping | ✅ | `WorkingMemory`, `DependencyGraph`, and `Justification` records track stated facts and multi-parent support for derived facts |
| JTMS support verification APIs | ✅ | `SupportSnapshot` and `TMSController` verifier methods expose read-only checks for current support, hypothetical support-path invalidation, transitive support, and dependency traversal |
| Recursive retraction | ✅ | `TMSController.retract_triple` performs Mark-Verify-Sweep over the dependency graph; `RETEEngine.retract_triples` composes the TMS primitive, evicts stale alpha/beta partial matches, and is idempotent for already-absent triples; `RETEStore.remove` drives the `BatchDispatcher` chain and re-materializes triples the engine still derives with a `RetractionRematerializeWarning` per DR-025 |
| Triple-goal explanation reconstruction | ✅ | `DerivationProofReconstructor` rebuilds `DirectProof` trees from non-silent derivation records for triple-goal explanations |
| Contradiction detection diagnostics | ✅ | Dual-channel contradiction detection records non-mutating contradiction diagnostics (`ContradictionRecord`) for currently modeled OWL 2 RL `false`-family rules; selectable recorders (`RaiseOnContradictionRecorder` default, `InMemoryContradictionRecorder`, `DropContradictionRecorder`) expose queryable diagnostics where retention applies |
| Contradiction explanation reconstruction | ✅ | `DerivationProofReconstructor` rebuilds contradiction-goal `DirectProof` (verdict `contradiction`) from `ContradictionRecord` diagnostics; premises are surfaced as leaf facts (nested derivation proofs for each premise are not required by the baseline DR-027 contract); markdown/Mermaid/notebook rendering uses the same `ProofRenderer` path as triple-goal proofs |
| Proof rendering (markdown and Mermaid) | ✅ | Presentation-focused rendering over canonical `DirectProof` data includes namespace-aware shortening and notebook display adapters via optional extras |
| Specialized transitive relation index | ⬜ | Intended optimization path for `rdfs:subClassOf` and `rdfs:subPropertyOf` first; broader general transitive-property support remains a later design question |

### Builtin predicates

Read-only `PredicateCondition` hooks registered through
`rdflib_reasoning.engine.builtins` (`DEFAULT_PREDICATE_BUILTINS` today; additional
hooks via `Builtins.extend`). Predicates MUST NOT mutate working memory or
logical closure (DR-005). Rule IDs below cite current RDFS production / conformant
profiles and intended OWL 2 RL usage; blank usage cells mean the predicate is
shipped for general guards but is not yet referenced by a checked-in ruleset.

OWL 2 RL `LIST[…]` atoms are **not** planned as predicate builtins: they expand
to `rdf:first` / `rdf:rest` triple conditions (or equivalent engine list joins).
Contradiction outcomes use `ContradictionConsequent`, not predicate builtins.

| Builtin | Status | RDFS / OWL 2 RL rule usage | Description |
| --- | --- | --- | --- |
| `different_terms` | ✅ | RDFS production: `rdfs2` (exclude `rdfs:Resource` domain), `rdfs7`, `rdfs9`. Intended OWL 2 RL: optional ≠ guards where two bound fillers must be distinct (for example production variants of `cls-maxc2`, `cls-maxqc3`, `cls-maxqc4`, `prp-fp`, `prp-ifp`) | True when every argument is a distinct RDFLib node (syntactic identity, not datatype value-space equality) |
| `same_term` | ✅ | Available inverse of `different_terms`; no checked-in RDFS/RL rule uses it yet | True when every argument is the same RDFLib node (syntactic identity) |
| `not_literal` | ✅ | RDFS: `rdfs3` (range object must be a legal RDF 1.1 subject); conformant `rdfs4b`. Intended OWL 2 RL: `prp-rng` and other rules that conclude `rdf:type` on a bound object | True when no argument is an RDF literal |
| `is_literal` | ✅ | Intended OWL 2 RL: `dt-type2`, `dt-eq`, `dt-diff`, `dt-not-type` (and related literal filters) | True when every argument is an RDF literal (convenience inverse of `not_literal`) |
| `term_in` | ✅ | Available inverse of `term_not_in`; no checked-in RDFS/RL rule uses it yet | True when the first argument equals one of the remaining arguments |
| `term_not_in` | ✅ | RDFS production: `rdfs3` (suppress selected vocabulary objects such as `rdfs:Class` / `rdfs:Resource`) | True when the first argument equals none of the remaining arguments |
| `literal_same_value` | ✅ | Intended OWL 2 RL: `dt-eq` | True when two literals denote the same data value (value-space / RDF equality, not node identity) |
| `literal_different_value` | ✅ | Intended OWL 2 RL: `dt-diff` | True when two literals denote different data values |
| `literal_in_datatype` | ✅ | Intended OWL 2 RL: `dt-type2` (and supporting checks for datatype membership) | True when a literal's data value is contained in the value space of a datatype IRI |
| `literal_not_in_datatype` | ✅ | Intended OWL 2 RL: `dt-not-type` (contradiction diagnostics channel) | True when a literal's data value is not contained in the value space of a datatype IRI |

## Current integration baseline

The supported RDFLib integration path is `Store` events -> `BatchDispatcher` ->
`RETEStore` -> `RETEEngine`.

The `rdflib-reasoning-engine` package is part of the `rdflib-reasoning` metapackage.
